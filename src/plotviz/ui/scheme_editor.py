"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/scheme_editor.py  –  plotviz
SchemeEditorDialog: create or edit a colour scheme in one place (colours, grid, borders,
palette), the counterpart of the palette editor.
"""
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QComboBox, QCheckBox, QPushButton, QGroupBox,
)

from ui.helpers import _show_color_dialog

# (scheme key, label, fallback used when the scheme does not define the key)
_COLOR_FIELDS = [
    ('chart_bg_color',   'Figure background', '#ffffff'),
    ('plot_bg_color',    'Plot background',   '#ffffff'),
    ('chart_fg_color',   'Foreground',        '#000000'),
    ('title_color',      'Title',             '#000000'),
    ('xlabel_color',     'X label',           '#000000'),
    ('ylabel_color',     'Y label',           '#000000'),
    ('grid_color',       'Grid',              '#cccccc'),
    ('minor_grid_color', 'Minor grid',        '#e8e8e8'),
]
_BORDER_FIELDS = [('border_top', 'Top'), ('border_bottom', 'Bottom'),
                  ('border_left', 'Left'), ('border_right', 'Right')]
_SW_CSS = 'background:{};border:1px solid #666;border-radius:3px;'


class SchemeEditorDialog(QDialog):
    """Edits a copy of *scheme*; `result_scheme()` returns it with every edited key set.

    Keys the dialog does not show (fonts, grid line style, annotation colours...) are
    carried over unchanged. *registry* is name → scheme, offered under "Load from".
    """

    def __init__(self, parent, name, scheme, registry, palettes, palette_colors=None):
        super().__init__(parent)
        self.setWindowTitle('Colour Scheme Editor')
        self.setMinimumWidth(380)
        self._scheme = dict(scheme)
        self._registry = registry
        self._palette_colors = palette_colors
        self._colors = {}
        self._swatches = {}

        lay = QVBoxLayout(self)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel('Name:'))
        self._name = QLineEdit(name)
        name_row.addWidget(self._name)
        lay.addLayout(name_row)

        load_row = QHBoxLayout()
        load_row.addWidget(QLabel('Load from:'))
        self._base = QComboBox()
        self._base.addItems(list(registry))
        load_row.addWidget(self._base, 1)
        btn_load = QPushButton('Load')
        btn_load.clicked.connect(self._load_base)
        load_row.addWidget(btn_load)
        lay.addLayout(load_row)

        grp = QGroupBox('Colours (click to change)')
        grid = QGridLayout(grp)
        grid.setHorizontalSpacing(8)
        for i, (key, label, _fallback) in enumerate(_COLOR_FIELDS):
            row, col = divmod(i, 2)
            cell = QHBoxLayout()
            btn = QPushButton()
            btn.setFixedSize(28, 22)
            btn.clicked.connect(lambda _=False, k=key: self._pick(k))
            self._swatches[key] = btn
            cell.addWidget(btn)
            cell.addWidget(QLabel(label))
            cell.addStretch()
            grid.addLayout(cell, row, col)
        lay.addWidget(grp)

        style = QGroupBox('Grid and borders')
        sl = QVBoxLayout(style)
        grid_row = QHBoxLayout()
        self._grid_on = QCheckBox('Grid')
        self._minor_on = QCheckBox('Minor grid')
        grid_row.addWidget(self._grid_on)
        grid_row.addWidget(self._minor_on)
        grid_row.addStretch()
        sl.addLayout(grid_row)
        border_row = QHBoxLayout()
        border_row.addWidget(QLabel('Borders:'))
        self._borders = {}
        for key, label in _BORDER_FIELDS:
            cb = QCheckBox(label)
            self._borders[key] = cb
            border_row.addWidget(cb)
        border_row.addStretch()
        sl.addLayout(border_row)
        lay.addWidget(style)

        pal_row = QHBoxLayout()
        pal_row.addWidget(QLabel('Palette:'))
        self._palette = QComboBox()
        self._palette.addItems(list(palettes))
        pal_row.addWidget(self._palette, 1)
        lay.addLayout(pal_row)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Ok).setText('Save && apply')
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        self._fill(self._scheme)

    def _fill(self, scheme):
        for key, _label, fallback in _COLOR_FIELDS:
            self._set_color(key, scheme.get(key, fallback))
        self._grid_on.setChecked(bool(scheme.get('grid_on', True)))
        self._minor_on.setChecked(bool(scheme.get('minor_grid_on', False)))
        for key, _label in _BORDER_FIELDS:
            self._borders[key].setChecked(bool(scheme.get(key, True)))
        i = self._palette.findText(scheme.get('color_palette', 'Matplotlib'))
        if i >= 0:
            self._palette.setCurrentIndex(i)

    def _set_color(self, key, hex_color):
        self._colors[key] = hex_color
        self._swatches[key].setStyleSheet(_SW_CSS.format(hex_color))
        self._swatches[key].setToolTip(hex_color)

    def _pick(self, key):
        c = _show_color_dialog(QColor(self._colors[key]), self,
                               palette_colors=self._palette_colors)
        if c.isValid():
            self._set_color(key, c.name())

    def _load_base(self):
        base = self._registry.get(self._base.currentText())
        if base:
            self._scheme = {**self._scheme, **base}
            self._fill(self._scheme)

    def scheme_name(self):
        return self._name.text().strip()

    def result_scheme(self):
        out = dict(self._scheme)
        out.update(self._colors)
        out['grid_on'] = self._grid_on.isChecked()
        out['minor_grid_on'] = self._minor_on.isChecked()
        for key, cb in self._borders.items():
            out[key] = cb.isChecked()
        out['color_palette'] = self._palette.currentText()
        return out
