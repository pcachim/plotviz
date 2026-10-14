"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_helpers.py  –  plotviz
WidgetHelpersMixin: Small widget factory helpers shared by all tab builders (spinboxes, combos, colour buttons).
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QDoubleSpinBox,
)


class WidgetHelpersMixin:
    # ── Widget factory helpers ─────────────────────────────────────────────────
    def _make_spin(self, attr, lo, hi, val):
        w = QSpinBox()
        w.setRange(lo, hi)
        w.setValue(val)
        setattr(self, attr, w)
        w.valueChanged.connect(self.update_preview)
        return w

    def _make_dbl_spin(self, attr, lo, hi, val, step, decimals=None):
        w = QDoubleSpinBox()
        w.setRange(lo, hi)
        w.setValue(val)
        w.setSingleStep(step)
        if decimals is not None: w.setDecimals(decimals)
        setattr(self, attr, w)
        w.valueChanged.connect(self.update_preview)
        return w

    def _make_combo(self, attr, items, default=None):
        w = QComboBox()
        w.addItems(items)
        if default is not None:
            idx = w.findText(default)
            if idx >= 0: w.setCurrentIndex(idx)
        setattr(self, attr, w)
        w.currentTextChanged.connect(self.update_preview)
        return w

    def _make_edgecolor_combo(self, attr, default='none'):
        items = ['none','black','white','gray','auto']
        w = QComboBox()
        w.addItems(items)
        idx = w.findText(default)
        w.setCurrentIndex(max(idx, 0))
        setattr(self, attr, w)
        w.currentTextChanged.connect(self.update_preview)
        return w

    def _make_col_combo(self, attr, sentinel='(none)'):
        w = QComboBox()
        w.addItem(sentinel)
        setattr(self, attr, w)
        w.currentTextChanged.connect(self.update_preview)
        return w

    # ── Shared color-picker helpers ───────────────────────────────────────────
    _SW_CSS = 'background-color:{};border:1px solid #888;border-radius:2px;'

    def _color_sw(self, hex_color='#000000'):
        """Create a 22×22 solid-square swatch QLabel."""
        sw = QLabel()
        sw.setFixedSize(22, 22)
        sw.setStyleSheet(self._SW_CSS.format(hex_color))
        return sw

    def _make_color_btn(self, attr, default_hex):
        """Return a QWidget [■ swatch | … btn] for attr; swatch stored as self.<attr>_sw.

        Does NOT overwrite self.<attr> if it is already set — prevents widget
        construction from clobbering a colour restored from a saved file.
        """
        from PyQt6.QtWidgets import QPushButton
        from PyQt6.QtGui import QColor
        from ui.helpers import _show_color_dialog
        if not getattr(self, attr, None):
            setattr(self, attr, default_hex)
        current = getattr(self, attr, default_hex)
        sw = self._color_sw(current)
        setattr(self, attr + '_sw', sw)
        btn = QPushButton('…')
        btn.setFixedWidth(28)
        def _pick():
            pal = self._active_palette_colors() if hasattr(self, '_active_palette_colors') else None
            col = _show_color_dialog(QColor(getattr(self, attr)), self, pal)
            if col.isValid():
                setattr(self, attr, col.name())
                sw.setStyleSheet(self._SW_CSS.format(col.name()))
                self.update_preview()
        btn.clicked.connect(_pick)
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        h.addWidget(sw)
        h.addWidget(btn)
        h.addStretch()
        return container
