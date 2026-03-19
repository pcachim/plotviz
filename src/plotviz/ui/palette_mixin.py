"""
Copyright (c) 2026 Paulo Cachim
ui/palette_mixin.py  –  plotviz
PaletteMixin: custom palette editor dialog, palette import/export helpers.
"""
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QWidget, QMessageBox, QInputDialog, QFileDialog,
)
from PyQt6.QtGui import QColor
from ui.helpers import _show_color_dialog, _get_dir, _remember_dir


class PaletteMixin:
    def _open_palette_editor(self):
        """Open a dialog to create or edit a custom colour palette."""
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                      QLineEdit, QPushButton, QListWidget,
                                      QDialogButtonBox, QMessageBox)
        from ui.tab_builders import get_all_palettes, add_custom_palette, _CUSTOM_PALETTES
        from ui.helpers import _show_color_dialog

        dlg = QDialog(self)
        dlg.setWindowTitle('Palette Editor')
        dlg.setMinimumWidth(420)
        vlay = QVBoxLayout(dlg)

        # ── Palette name ──────────────────────────────────────────────────────
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel('Name:'))
        name_edit = QLineEdit('My Palette')
        name_row.addWidget(name_edit)
        vlay.addLayout(name_row)

        # ── 16 colour swatches ────────────────────────────────────────────────
        vlay.addWidget(QLabel('Colours (click to change):'))
        swatch_grid = QHBoxLayout(); swatch_grid.setSpacing(4)

        default_colors = list(self._active_palette_colors())
        # Pad or trim to 16
        while len(default_colors) < 16:
            default_colors.append('#cccccc')
        default_colors = default_colors[:16]
        edit_colors = list(default_colors)

        swatch_btns = []
        def _make_swatch(i):
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(f'background:{edit_colors[i]};border:1px solid #666;border-radius:3px;')
            btn.setToolTip(edit_colors[i])
            def _pick(checked=False, idx=i):
                c = _show_color_dialog(QColor(edit_colors[idx]), dlg)
                if c.isValid():
                    edit_colors[idx] = c.name()
                    swatch_btns[idx].setStyleSheet(
                        f'background:{c.name()};border:1px solid #666;border-radius:3px;')
                    swatch_btns[idx].setToolTip(c.name())
            btn.clicked.connect(_pick)
            return btn

        for i in range(16):
            btn = _make_swatch(i)
            swatch_btns.append(btn)
            swatch_grid.addWidget(btn)
        vlay.addLayout(swatch_grid)

        # ── Load from existing palette ─────────────────────────────────────────
        load_row = QHBoxLayout()
        load_row.addWidget(QLabel('Load from:'))
        from PyQt6.QtWidgets import QComboBox as _QCB
        base_combo = _QCB()
        base_combo.addItems(list(get_all_palettes().keys()))
        load_row.addWidget(base_combo)
        def _load_base():
            all_p = get_all_palettes()
            cols = list(all_p.get(base_combo.currentText(), []))
            while len(cols) < 16: cols.append('#cccccc')
            for i, c in enumerate(cols[:16]):
                edit_colors[i] = c
                swatch_btns[i].setStyleSheet(
                    f'background:{c};border:1px solid #666;border-radius:3px;')
                swatch_btns[i].setToolTip(c)
        btn_load_base = QPushButton('Load')
        btn_load_base.clicked.connect(_load_base)
        load_row.addWidget(btn_load_base)
        load_row.addStretch()
        vlay.addLayout(load_row)

        # ── OK / Cancel ────────────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        vlay.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        pal_name = name_edit.text().strip()
        if not pal_name:
            QMessageBox.warning(self, 'Name required', 'Please enter a palette name.')
            return

        add_custom_palette(pal_name, list(edit_colors))

        # Refresh combo and select the new palette
        self.palette_combo.blockSignals(True)
        if self.palette_combo.findText(pal_name) < 0:
            self.palette_combo.addItem(pal_name)
        self.palette_combo.setCurrentText(pal_name)
        self.palette_combo.blockSignals(False)
        self._on_palette_changed(pal_name)

    def _custom_palettes_json(self):
        """Return _CUSTOM_PALETTES as a JSON string for saving."""
        from ui.tab_builders import _CUSTOM_PALETTES
        return json.dumps(_CUSTOM_PALETTES, indent=2)

    def _load_custom_palettes_json(self, json_str):
        """Load custom palettes from a JSON string."""
        from ui.tab_builders import add_custom_palette
        try:
            data = json.loads(json_str)
            for name, colors in data.items():
                add_custom_palette(name, colors)
            # Rebuild combo
            self.palette_combo.blockSignals(True)
            from ui.tab_builders import get_all_palettes
            existing = [self.palette_combo.itemText(i)
                        for i in range(self.palette_combo.count())]
            for name in get_all_palettes():
                if name not in existing:
                    self.palette_combo.addItem(name)
            self.palette_combo.blockSignals(False)
        except Exception as e:
            pass  # silently ignore corrupt palette data

    def _unlock_curve_color(self):
        """Remove the color lock from the currently selected curve."""
        curve = self.curve_select.currentText()
        if curve and curve in self.curve_styles:
            s = self.curve_styles[curve]
            s.pop('color_locked', None)
            # Find the row index for this label and re-assign palette color
            for row in range(self.series_table.rowCount()):
                lbl_item = self.series_table.item(row, 2)
                if lbl_item and lbl_item.text() == curve:
                    new_color = self._palette_color(self._local_palette_index(row))
                    s['color'] = new_color
                    s['marker_color'] = new_color
                    self.curve_color = new_color
                    self.curve_marker_color = new_color
                    self.curve_color_label.setStyleSheet(f'color:{new_color};font-size:16px;')
                    self.curve_marker_color_label.setStyleSheet(f'color:{new_color};font-size:16px;')
                    break
            self.curve_styles[curve] = s
        self._refresh_lock_indicator()
        self.update_preview()

    def _refresh_lock_indicator(self):
        """Show/hide the 🔒 label next to the curve color based on lock state."""
        if not hasattr(self, 'curve_lock_label'):
            return
        curve = self.curve_select.currentText()
        locked = self.curve_styles.get(curve, {}).get('color_locked', False)
        self.curve_lock_label.setVisible(locked)

    # ═══════════════════════════════════════════════════════════════════════════
    # COLORS
    # ═══════════════════════════════════════════════════════════════════════════
    def _active_palette_colors(self):
        """Return the list of hex colors for the current palette."""
        all_pals = get_all_palettes()
        pal = getattr(self, '_color_palette', 'Matplotlib')
        return all_pals.get(pal, COLOR_PALETTES['Matplotlib'])

