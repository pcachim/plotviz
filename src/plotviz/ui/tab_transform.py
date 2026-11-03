"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_transform.py  –  plotviz
TransformTabMixin: the Transform page of the Data tab (smoothing, decimation, calculus,
scaling and resampling of a loaded series; the result is stored as a new series).
"""
from dataclasses import dataclass
from typing import Any

import numpy as np
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox, QPushButton, QStackedWidget, QScrollArea, QCheckBox, QSizePolicy,
)
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:                                   # matplotlib < 3.5
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from core.dates import DateArray, is_date, parse_date
from data.transforms import OPERATIONS, apply_operation, default_suffix, downsample_minmax
from ui.mixin_base import MixinBase

_NO_X = '(none: use index)'
PREVIEW_LIVE_LIMIT = 50_000       # above this many points the preview waits for the button
PREVIEW_DELAY_MS = 300            # live preview: wait this long after the last change


@dataclass
class TransformPlan:
    """What Apply would do, worked out without changing anything (the preview draws it)."""
    key: str
    label: str
    params: dict[str, Any]
    x_name: str
    y_name: str
    x: Any                    # the input x (None when there is none)
    y: Any
    x_out: Any                # the result's x (None: unchanged / none)
    y_out: Any
    y_new: str                # the names the result would be stored under
    x_new: str | None         # a new x series, when the transform made or changed x
    reused: str | None        # an existing series that already is x_out
    x_is_date: bool

    @property
    def made(self):
        return ([self.x_new] if self.x_new else []) + [self.y_new]


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
            conditions = {}
            for name, label, kind, default, extra, *rest in op['params']:
                w = self._tf_make_param_widget(kind, default, extra)
                widgets[name] = w
                pform.addRow(label + ':', w)
                if rest:                         # shown only for some choices of another parameter
                    conditions[name] = rest[0]
            for name, condition in conditions.items():
                self._tf_show_when(pform, widgets, name, condition)
            if not op['params']:
                pform.addRow(QLabel('No parameters'))
            self.tf_param_stack.addWidget(page)
            self._tf_param_widgets.append(widgets)
        layout.addWidget(self.tf_param_stack)

        self._tf_build_preview(layout)

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
        self._tf_size_param_stack()
        self._tf_connect_preview_triggers()
        self._tf_draw_hint('Choose a series and an operation; the preview shows here.')

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
            self._tf_size_param_stack()

    def _tf_size_param_stack(self):
        """The parameter area is as tall as the operation shown, not as the tallest operation."""
        current = self.tf_param_stack.currentIndex()
        for i in range(self.tf_param_stack.count()):
            vertical = QSizePolicy.Policy.Preferred if i == current else QSizePolicy.Policy.Ignored
            self.tf_param_stack.widget(i).setSizePolicy(QSizePolicy.Policy.Preferred, vertical)
        self.tf_param_stack.updateGeometry()

    @staticmethod
    def _tf_show_when(form, widgets, name, condition):
        """Show the row of parameter *name* only while the choice parameter(s) in
        *condition* ({param: [values]}) have one of the listed values."""
        def update(*_):
            visible = all(widgets[other].currentText() in values
                          for other, values in condition.items())
            form.setRowVisible(widgets[name], visible)
        for other in condition:
            widgets[other].currentTextChanged.connect(update)
        update()

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
            w.setDecimals(6)
            w.setRange(*extra)
            w.setSpecialValueText('auto')
            w.setValue(extra[0])
            return w
        if kind == 'int':
            w = QSpinBox()
            w.setRange(*extra)
        elif kind == 'float':
            w = QDoubleSpinBox()
            w.setDecimals(6)
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
        self._tf_schedule_preview()

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

    def _compute_transform(self):
        """Work out what Apply would create, without changing anything: a TransformPlan.
        Raises ValueError with a message for the panel when it cannot be done."""
        y_name = self.tf_y_combo.currentText()
        if y_name not in self.datasets:
            raise ValueError('No y series selected')
        x_name = self.tf_x_combo.currentText()
        x = np.asarray(self.datasets[x_name], dtype=float) if x_name in self.datasets else None
        y = np.asarray(self.datasets[y_name], dtype=float)
        if x is not None and len(x) != len(y):
            raise ValueError(f'x has {len(x)} points but y has {len(y)}')
        key = self.tf_op_combo.currentData()
        if key is None:
            raise ValueError('No operation selected')
        params = self._tf_params()
        x_out, y_out = apply_operation(key, x, y, **params)

        suffix = default_suffix(key, params)
        y_new = self._tf_store(self.tf_out_name.text().strip() or f'{y_name}_{suffix}')
        x_is_date = is_date(self.datasets.get(x_name)) and key != 'fft_spectrum'
        if x_out is not None and x_is_date:
            x_out = DateArray(x_out)                # the x is still dates (frequencies are not)
        # A new x only when the transform made or changed it (trim, decimate, FFT, peaks)
        reused = next((n for n, v in self.datasets.items()   # x_out is already a loaded series
                       if x_out is not None and len(v) == len(x_out) and np.array_equal(v, x_out)), None)
        x_new = None
        if x_out is not None and reused is None and (x is None or not np.array_equal(x_out, x)):
            x_new = self._tf_store(f'{x_name if x is not None else y_name + "_x"}_{suffix}')
        label = next(op['label'] for op in OPERATIONS if op['key'] == key)
        return TransformPlan(key, label, params, x_name, y_name, x, y, x_out, y_out, y_new, x_new, reused,
                             x_is_date)

    def _apply_transform(self):
        try:
            plan = self._compute_transform()
            if plan.x_new:
                self.datasets[plan.x_new] = plan.x_out
            self.datasets[plan.y_new] = plan.y_out
            self._schedule_undo_snapshot('Transform')
            self.update_lists()
            note = (f'; its x is the existing "{plan.reused}"'
                    if plan.reused and plan.reused != plan.x_name else '')
            self.tf_status.setText(
                f'✓  Created {", ".join(plan.made)}  ({len(plan.y_out)} points{note}),'
                f' from y = {plan.y_name}' + (f', x = {plan.x_name}' if plan.x is not None else ''))
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
            self.tf_status.setText(f'❌  {e}')

    # ── Preview: what Apply would make, in a small plot ───────────────────────────

    def _tf_build_preview(self, layout):
        layout.addWidget(self._sec_label('Preview'))
        row = QHBoxLayout()
        row.setSpacing(6)
        self.tf_preview_btn = QPushButton('👁  Preview')
        self.tf_preview_btn.setToolTip('Draw the result of the operation, without creating anything')
        self.tf_preview_btn.clicked.connect(lambda: self._tf_update_preview(forced=True))
        row.addWidget(self.tf_preview_btn)
        self.tf_live_check = QCheckBox('Live')
        self.tf_live_check.setChecked(True)
        self.tf_live_check.setToolTip(f'Redraw as you change the series, the operation or a parameter '
                                      f'(paused above {PREVIEW_LIVE_LIMIT:,} points: use the button)')
        row.addWidget(self.tf_live_check)
        self.tf_log_check = QCheckBox('log y')
        self.tf_log_check.setToolTip('Logarithmic y axis for the preview (useful for a spectrum)')
        row.addWidget(self.tf_log_check)
        row.addStretch()
        layout.addLayout(row)
        self.tf_preview_canvas = FigureCanvas(Figure(figsize=(3.6, 2.2)))
        self.tf_preview_canvas.setMinimumHeight(170)
        self.tf_preview_ax = self.tf_preview_canvas.figure.add_subplot(111)
        layout.addWidget(self.tf_preview_canvas)
        self.tf_preview_info = QLabel('')
        self.tf_preview_info.setWordWrap(True)
        self.tf_preview_info.setStyleSheet('color:#555;font-size:11px;')
        layout.addWidget(self.tf_preview_info)
        self._tf_last_plan = None
        self._tf_preview_timer = QTimer(self)
        self._tf_preview_timer.setSingleShot(True)
        self._tf_preview_timer.setInterval(PREVIEW_DELAY_MS)
        self._tf_preview_timer.timeout.connect(lambda: self._tf_update_preview(forced=False))

    def _tf_connect_preview_triggers(self):
        """Any change of what the operation depends on asks for a (live) preview."""
        for combo in (self.tf_y_combo, self.tf_x_combo):
            combo.currentTextChanged.connect(self._tf_schedule_preview)
        self.tf_op_combo.currentIndexChanged.connect(self._tf_schedule_preview)
        self.tf_live_check.toggled.connect(self._tf_schedule_preview)
        self.tf_log_check.toggled.connect(self._tf_redraw_last)
        for widgets in self._tf_param_widgets:
            for w in widgets.values():
                if isinstance(w, QComboBox):
                    w.currentTextChanged.connect(self._tf_schedule_preview)
                elif isinstance(w, QLineEdit):
                    w.textChanged.connect(self._tf_schedule_preview)
                else:
                    w.valueChanged.connect(self._tf_schedule_preview)

    def _tf_schedule_preview(self, *_):
        """A live preview a moment after the last change (not for very long series)."""
        if not hasattr(self, '_tf_preview_timer'):
            return
        if not self.tf_live_check.isChecked():
            self._tf_preview_timer.stop()
            if self._tf_last_plan is not None or self.tf_preview_info.text():
                self.tf_preview_info.setText('Changed: click Preview to update.')
            return
        n = len(self.datasets.get(self.tf_y_combo.currentText(), ()))
        if n > PREVIEW_LIVE_LIMIT:
            self._tf_preview_timer.stop()
            self.tf_preview_info.setText(f'Live is paused for {n:,} points: click Preview.')
            return
        self._tf_preview_timer.start()

    def _tf_update_preview(self, forced):
        """Compute the plan and draw it; problems are written in the plot, not raised."""
        self._tf_preview_timer.stop()
        if not forced and not (self.tf_live_check.isChecked() and self.tf_preview_canvas.isVisible()):
            return                                       # no drawing for a page nobody is looking at
        try:
            plan = self._compute_transform()
        except Exception as e:  # noqa: BLE001 - any failure of the operation is shown to the user
            self._tf_last_plan = None
            self._tf_draw_hint(str(e), error=True)
            return
        self._tf_last_plan = plan
        self._tf_draw_plan(plan)

    def _tf_redraw_last(self, *_):
        if self._tf_last_plan is not None:
            self._tf_draw_plan(self._tf_last_plan)

    def _tf_style_axes(self):
        """The mini plot follows the window's colours."""
        pal = self.palette()
        bg, fg = pal.window().color().name(), pal.windowText().color().name()
        fig, ax = self.tf_preview_canvas.figure, self.tf_preview_ax
        fig.patch.set_facecolor(bg)
        ax.set_facecolor(bg)
        ax.tick_params(colors=fg, labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor(fg)
        fig.subplots_adjust(left=0.15, right=0.97, top=0.95, bottom=0.17)
        return fg

    def _tf_draw_hint(self, message, error=False):
        ax = self.tf_preview_ax
        ax.clear()
        fg = self._tf_style_axes()
        ax.set_xticks([])
        ax.set_yticks([])
        ax.text(0.5, 0.5, message, transform=ax.transAxes, ha='center', va='center', wrap=True,
                fontsize=8, color='#c0392b' if error else fg)
        self.tf_preview_info.setText('❌  ' + message if error else '')
        self.tf_preview_canvas.draw_idle()

    def _tf_draw_plan(self, plan):
        ax = self.tf_preview_ax
        ax.clear()
        fg = self._tf_style_axes()
        n_in, n_out = len(plan.y), len(plan.y_out)
        x_in = plan.x if plan.x is not None else np.arange(n_in, dtype=float)
        if plan.x_out is not None:
            x_res = np.asarray(plan.x_out, dtype=float)
        elif n_out == n_in:
            x_res = x_in
        else:                                   # no x, and points were dropped: spread them over the original
            x_res = np.linspace(x_in[0], x_in[-1], n_out) if n_out > 1 else x_in[:1]
        result_colour = self._palette_color(1)
        if plan.key != 'fft_spectrum':          # a spectrum has other axes than the series
            ax.plot(*downsample_minmax(x_in, plan.y), color='#9a9a9a', lw=0.9, label='original')
        rx, ry = downsample_minmax(x_res, plan.y_out)
        if plan.key == 'peaks':
            ax.plot(rx, ry, 'o', color=result_colour, ms=5, label=f'{n_out} peak(s)')
        else:
            ax.plot(rx, ry, color=result_colour, lw=1.3, marker='.' if n_out <= 200 else None,
                    ms=3.5, label='result')
        finite = plan.y_out[np.isfinite(plan.y_out)]
        if self.tf_log_check.isChecked() and len(finite) and finite.min() > 0:
            ax.set_yscale('log')
        if plan.x_is_date:
            import matplotlib.dates as mdates
            ax.xaxis_date()
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
        leg = ax.legend(fontsize=7, loc='best', frameon=False)
        for text in leg.get_texts():
            text.set_color(fg)
        names = ' and '.join(f'"{n}"' for n in plan.made)
        extra = f'; x also changes, in "{plan.x_new}"' if plan.x_new else ''
        self.tf_preview_info.setText(f'{plan.label}: {n_out:,} points → would create {names}{extra}.')
        self.tf_preview_canvas.draw_idle()
