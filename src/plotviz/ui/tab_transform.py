"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_transform.py  –  plotviz
TransformTabMixin: the Transform page of the Data tab (smoothing, decimation, calculus,
scaling and resampling of a loaded series; the result is stored as a new series).
"""
import numpy as np
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox, QPushButton, QStackedWidget, QScrollArea,
)

from core.dates import DateArray, is_date, parse_date
from data.transforms import OPERATIONS, apply_operation, default_suffix
from ui.mixin_base import MixinBase

_NO_X = '(none: use index)'


class TransformTabMixin(MixinBase):
    def create_transform_page(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(6)

        layout.addWidget(self._sec_label('Series'))
        form = QFormLayout()
        form.setSpacing(4)
        self.tf_y_combo = QComboBox()
        self.tf_x_combo = QComboBox()
        self.tf_y_combo.setToolTip('The values that are smoothed, resampled, differentiated…')
        self.tf_x_combo.setToolTip('Optional x series. Needed by resampling; used for the '
                                   'spacing of derivative/integral and trimmed together with y.')
        form.addRow('x (the horizontal axis):', self.tf_x_combo)
        form.addRow('y (the series to transform):', self.tf_y_combo)
        layout.addLayout(form)

        layout.addWidget(self._sec_label('Operation'))
        self.tf_op_combo = QComboBox()
        group = None
        for op in OPERATIONS:
            if op['group'] != group:             # a bold, unselectable header per group
                group = op['group']
                self.tf_op_combo.addItem(group)
                header = self.tf_op_combo.model().item(self.tf_op_combo.count() - 1)
                header.setFlags(Qt.ItemFlag.NoItemFlags)
                font = QFont()
                font.setBold(True)
                header.setFont(font)
            self.tf_op_combo.addItem(op['label'], op['key'])
        layout.addWidget(self.tf_op_combo)

        # One parameter page per operation, built from the registry
        self.tf_param_stack = QStackedWidget()
        self._tf_param_widgets = []          # per operation: {param name: widget}
        for op in OPERATIONS:
            page = QWidget()
            pform = QFormLayout(page)
            pform.setContentsMargins(0, 0, 0, 0)
            pform.setSpacing(4)
            widgets = {}
            for name, label, kind, default, extra in op['params']:
                w = self._tf_make_param_widget(kind, default, extra)
                widgets[name] = w
                pform.addRow(label + ':', w)
            if not op['params']:
                pform.addRow(QLabel('No parameters'))
            self.tf_param_stack.addWidget(page)
            self._tf_param_widgets.append(widgets)
        layout.addWidget(self.tf_param_stack)

        layout.addWidget(self._sec_label('Result'))
        out_row = QHBoxLayout()
        out_row.setSpacing(4)
        out_row.addWidget(QLabel('Name:'))
        self.tf_out_name = QLineEdit()
        self.tf_out_name.setPlaceholderText('auto, e.g. y_MA5')
        out_row.addWidget(self.tf_out_name)
        layout.addLayout(out_row)

        btn = QPushButton('▶  Apply')
        btn.setToolTip('Creates a new series; the original is left untouched.')
        btn.clicked.connect(self._apply_transform)
        layout.addWidget(btn)
        self.tf_status = QLabel('')
        self.tf_status.setWordWrap(True)
        self.tf_status.setStyleSheet('color:#555;font-size:11px;')
        layout.addWidget(self.tf_status)
        layout.addStretch()

        self.tf_op_combo.setCurrentIndex(1)       # index 0 is a group header
        self.tf_op_combo.currentIndexChanged.connect(self._tf_op_changed)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll

    def _tf_op_index(self):
        key = self.tf_op_combo.currentData()
        return next(i for i, op in enumerate(OPERATIONS) if op['key'] == key)

    def _tf_op_changed(self, _):
        if self.tf_op_combo.currentData() is not None:
            self.tf_param_stack.setCurrentIndex(self._tf_op_index())

    @staticmethod
    def _tf_make_param_widget(kind, default, extra):
        if kind == 'optx':                   # a number, or a date on a date x; blank = open
            w = QLineEdit()
            w.setPlaceholderText('auto')
            w.setProperty('optx_param', True)
            return w
        if kind == 'series':                 # filled from the loaded datasets
            w = QComboBox()
            w.setProperty('series_param', True)
            return w
        if kind == 'optfloat':               # the minimum shows "auto" and means "not set"
            w = QDoubleSpinBox()
            w.setDecimals(4)
            w.setRange(*extra)
            w.setSpecialValueText('auto')
            w.setValue(extra[0])
            return w
        if kind == 'int':
            w = QSpinBox()
            w.setRange(*extra)
        elif kind == 'float':
            w = QDoubleSpinBox()
            w.setDecimals(4)
            w.setRange(*extra)
            w.setSingleStep(0.1)
        else:
            w = QComboBox()
            w.addItems(extra)
            w.setCurrentText(default)
            return w
        w.setValue(default)
        return w

    def _refresh_transform_combos(self, cols):
        """Keep the series combos in sync with the loaded datasets (called by update_lists)."""
        for combo, extra in ((self.tf_y_combo, []), (self.tf_x_combo, [_NO_X])):
            prev = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(extra + list(cols))
            i = combo.findText(prev)
            combo.setCurrentIndex(i if i >= 0 else 0)
            combo.blockSignals(False)

        for widgets in self._tf_param_widgets:      # the "series" parameters
            for w in widgets.values():
                if w.property('series_param'):
                    prev = w.currentText()
                    w.clear()
                    w.addItems(list(cols))
                    w.setCurrentIndex(max(w.findText(prev), 0))

    def _tf_parse_x_value(self, text):
        if not text:
            return None
        if is_date(self.datasets.get(self.tf_x_combo.currentText())):
            return parse_date(text)
        return float(text)

    def _tf_params(self):
        params = {}
        for name, w in self._tf_param_widgets[self._tf_op_index()].items():
            if w.property('series_param'):
                params[name] = self.datasets.get(w.currentText())
            elif w.property('optx_param'):
                params[name] = self._tf_parse_x_value(w.text().strip())
            elif isinstance(w, QComboBox):
                params[name] = w.currentText()
            elif isinstance(w, QDoubleSpinBox) and w.specialValueText() and w.value() == w.minimum():
                params[name] = None
            else:
                params[name] = w.value()
        return params

    def _tf_store(self, base):
        name, cnt = base, 1
        while name in self.datasets:
            name = f'{base}_{cnt}'
            cnt += 1
        return name

    def _apply_transform(self):
        try:
            y_name = self.tf_y_combo.currentText()
            if y_name not in self.datasets:
                self.tf_status.setText('❌  No y series selected')
                return
            x_name = self.tf_x_combo.currentText()
            x = np.asarray(self.datasets[x_name], dtype=float) if x_name in self.datasets else None
            y = np.asarray(self.datasets[y_name], dtype=float)
            if x is not None and len(x) != len(y):
                self.tf_status.setText(f'❌  x has {len(x)} points but y has {len(y)}')
                return
            key = self.tf_op_combo.currentData()
            params = self._tf_params()
            x_out, y_out = apply_operation(key, x, y, **params)

            suffix = default_suffix(key, params)
            y_new = self._tf_store(self.tf_out_name.text().strip() or f'{y_name}_{suffix}')
            made = [y_new]
            if x_out is not None and is_date(self.datasets.get(x_name)) and key != 'fft_spectrum':
                x_out = DateArray(x_out)            # the x is still dates (frequencies are not)
            # A new x only when the transform made or changed it (trim, decimate, FFT, peaks)
            reused = next((n for n, v in self.datasets.items()   # x_out is already a loaded series
                           if x_out is not None and len(v) == len(x_out) and np.array_equal(v, x_out)), None)
            if x_out is not None and reused is None and (x is None or not np.array_equal(x_out, x)):
                x_new = self._tf_store(f'{x_name if x is not None else y_name + "_x"}_{suffix}')
                self.datasets[x_new] = x_out
                made.insert(0, x_new)
            self.datasets[y_new] = y_out
            self.update_lists()
            note = f'; its x is the existing "{reused}"' if reused and reused != x_name else ''
            self.tf_status.setText(
                f'✓  Created {", ".join(made)}  ({len(y_out)} points{note}),'
                f' from y = {y_name}' + (f', x = {x_name}' if x is not None else ''))
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
            self.tf_status.setText(f'❌  {e}')
