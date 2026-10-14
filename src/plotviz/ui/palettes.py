"""
Copyright (c) 2026 Paulo Cachim
ui/palettes.py  –  plotviz

PaletteColorMixin: the custom-palette editor, active-palette colour resolution,
and (de)serialisation of custom palettes. Split out of main_window; mixed into
PlotVizApp so it shares the palette widgets and state via `self`.
"""
import json

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout,
)
from core.constants import _HEATMAP_GROUP_TYPES
from core.geometry import to_inches, from_inches
from ui.helpers import _show_color_dialog
from ui.tab_builders import (
    COLOR_PALETTES, get_all_palettes, add_custom_palette, _CUSTOM_PALETTES,
)


class PaletteColorMixin:
    def _open_palette_editor(self):
        """Open a dialog to create or edit a custom colour palette."""

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
        swatch_grid = QHBoxLayout()
        swatch_grid.setSpacing(4)

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
        return json.dumps(_CUSTOM_PALETTES, indent=2)

    def _load_custom_palettes_json(self, json_str):
        """Load custom palettes from a JSON string."""
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
        except (ValueError, AttributeError, TypeError, KeyError):
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
                    _sw_css = 'background-color:{};border:1px solid #888;border-radius:2px;'
                    self.curve_color_label.setStyleSheet(_sw_css.format(new_color))
                    self.curve_marker_color_label.setStyleSheet(_sw_css.format(new_color))
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

    def pick_color(self, target):
        # Determine current color for initial value
        _cur = {
            'chart_bg':     getattr(self, 'chart_bg_color',    '#ffffff'),
            'chart_fg':     getattr(self, 'chart_fg_color',    '#000000'),
            'plot_bg':      getattr(self, 'plot_bg_color',     '#ffffff'),
            'title':        getattr(self, 'title_color',       '#000000'),
            'xlabel':       getattr(self, 'xlabel_color',      '#000000'),
            'ylabel':       getattr(self, 'ylabel_color',      '#000000'),
            'y2label':      getattr(self, 'y2label_color',     '#000000'),
            'zlabel':       getattr(self, 'zlabel_color',      '#000000'),
            'curve':        getattr(self, 'curve_color',       '#1f77b4'),
            'curve_marker': getattr(self, 'curve_marker_color','#1f77b4'),
        }.get(target, '#000000')
        color = _show_color_dialog(
            QColor(_cur), self, palette_colors=self._active_palette_colors())
        if not color.isValid(): return
        hx = color.name()
        # Chart-canvas colors (per-subplot: stored in subplot_canvas_opts)
        if target in ('chart_bg', 'chart_fg', 'plot_bg'):
            attr = target + '_color'
            setattr(self, attr, hx)
            getattr(self, attr + '_swatch').setStyleSheet(
                f'background-color:{hx};border:1px solid #888;border-radius:2px;')
            # Persist to per-subplot dict immediately
            sp_idx = self.layout_sp_active.currentIndex() if hasattr(self, 'layout_sp_active') else 0
            if sp_idx < 0: sp_idx = 0
            self._save_canvas_grid_opts(sp_idx)
            self.update_preview()
            return
        mapping = {
            'title':        ('title_color',        'title_color_swatch',       'style'),
            'xlabel':       ('xlabel_color',        'xlabel_color_label',       'style'),
            'ylabel':       ('ylabel_color',        'ylabel_color_label',       'style'),
            'y2label':      ('y2label_color',       'y2label_color_label',      'style'),
            'zlabel':       ('zlabel_color',        'zlabel_color_label',       'style'),
            'curve':        ('curve_color',         'curve_color_label',        'swatch'),
            'curve_marker': ('curve_marker_color',  'curve_marker_color_label', 'swatch'),
        }
        if target not in mapping:
            import logging
            logging.getLogger('plotviz').warning('pick_color: unknown target %r — ignored', target)
            return
        attr, lbl_attr, mode = mapping[target]
        setattr(self, attr, hx)
        lbl = getattr(self, lbl_attr)
        lbl.setStyleSheet(f'background-color:{hx};border:1px solid #888;border-radius:2px;')
        if target in ('curve', 'curve_marker'):
            self.save_curve_style(lock_color=True)
        self.update_preview()

    def _sync_ann_style(self):
        if not hasattr(self,'canvas'): return
        self.canvas.ann_style = {
            'fontsize':   self.ann_fontsize.value(),
            'fontcolor':  self.ann_fontcolor,
            'fontfamily': self.ann_font.currentText(),
            'bg_color':   self.ann_bgcolor,
            'bg_alpha':   self.ann_bg_alpha.value(),
            'edge_color': self.ann_edgecolor,
        }

    def _fig_size_in_inches(self):
        """Convert current fig_width/fig_height spinbox values to inches."""
        unit = self.fig_unit.currentText()
        dpi = self.dpi_spin.value()
        return (to_inches(self.fig_width.value(), unit, dpi),
                to_inches(self.fig_height.value(), unit, dpi))

    def _on_fig_preset_changed(self, idx):
        """Apply a size preset (values are always in cm; convert to current unit)."""
        _, w_cm, h_cm = self._fig_presets[idx]
        if w_cm is None: return  # Custom — don't touch spinboxes
        unit = self.fig_unit.currentText()
        dpi = self.dpi_spin.value()
        # Preset values are in cm; convert to the active unit.
        w = from_inches(to_inches(w_cm, 'cm', dpi), unit, dpi)
        h = from_inches(to_inches(h_cm, 'cm', dpi), unit, dpi)
        if unit != 'pixels':
            w, h = round(w, 2), round(h, 2)
        else:
            w, h = round(w), round(h)
        self.fig_width.blockSignals(True)
        self.fig_height.blockSignals(True)
        self.fig_width.setValue(w)
        self.fig_height.setValue(h)
        self.fig_width.blockSignals(False)
        self.fig_height.blockSignals(False)
        # Margins and the title position are fractions of the figure, so they simply
        # follow the new size: only what the spinboxes display has to be refreshed.
        self._refresh_geometry_widgets()
        # Reset baseline so the next window resize scales correctly from the
        # newly-applied preset dimensions rather than the stale previous baseline.
        if hasattr(self, 'canvas'):
            self._window_size_baseline = (self.canvas.width(), self.canvas.height())
        self.update_preview()

    def _on_figsize_manual_change(self):
        """When user edits W/H manually, switch preset combo to 'Custom'.

        Also resets _window_size_baseline to the current window size so that
        the next window-resize event computes its scale factor relative to the
        moment the user last touched the spinboxes — not relative to whenever
        the previous auto-resize fired.
        """
        self.fig_preset_combo.blockSignals(True)
        self.fig_preset_combo.setCurrentText('Custom')
        self.fig_preset_combo.blockSignals(False)
        self._refresh_geometry_widgets()
        # Reset so next window resize scales from the manually-set size.
        # Use canvas dimensions so baseline stays consistent with _apply_resize_and_preview.
        if hasattr(self, 'canvas'):
            self._window_size_baseline = (self.canvas.width(), self.canvas.height())
        self.update_preview()

    def _on_fig_unit_changed(self, unit):
        """When unit changes, convert the figure W/H to the new unit.

        Margins and the title position need no conversion: they are stored as
        fractions of the figure and only their displayed values are refreshed.
        """
        # Read the current size using the *previous* unit (before the combo updated).
        # currentTextChanged fires after the combo already reflects the new value, so
        # we must convert manually from _prev_fig_unit rather than via _fig_size_in_inches().
        prev_unit = getattr(self, '_prev_fig_unit', 'cm')
        dpi = self.dpi_spin.value()
        wi = to_inches(self.fig_width.value(), prev_unit, dpi)
        hi = to_inches(self.fig_height.value(), prev_unit, dpi)
        self._prev_fig_unit = unit
        self.fig_width.blockSignals(True)
        self.fig_height.blockSignals(True)
        if unit == 'cm':
            self.fig_width.setRange(2, 500)
            self.fig_height.setRange(2, 500)
            self.fig_width.setDecimals(1)
            self.fig_height.setDecimals(1)
            self.fig_width.setSingleStep(0.5)
            self.fig_height.setSingleStep(0.5)
            self.fig_width.setValue(round(from_inches(wi, 'cm', dpi), 1))
            self.fig_height.setValue(round(from_inches(hi, 'cm', dpi), 1))
        elif unit == 'inches':
            self.fig_width.setRange(1, 200)
            self.fig_height.setRange(1, 200)
            self.fig_width.setDecimals(2)
            self.fig_height.setDecimals(2)
            self.fig_width.setSingleStep(0.25)
            self.fig_height.setSingleStep(0.25)
            self.fig_width.setValue(round(wi, 2))
            self.fig_height.setValue(round(hi, 2))
        elif unit == 'pixels':
            self.fig_width.setRange(50, 20000)
            self.fig_height.setRange(50, 20000)
            self.fig_width.setDecimals(0)
            self.fig_height.setDecimals(0)
            self.fig_width.setSingleStep(10)
            self.fig_height.setSingleStep(10)
            self.fig_width.setValue(round(from_inches(wi, 'pixels', dpi)))
            self.fig_height.setValue(round(from_inches(hi, 'pixels', dpi)))
        self.fig_width.blockSignals(False)
        self.fig_height.blockSignals(False)
        self._refresh_geometry_widgets()
        self.update_preview()

    # Chart types that render a colorbar inside the axes-box area.
    # For these the right margin is allowed to exceed fig_width so the
    # user can deliberately push the colorbar outside the figure boundary.
    _COLORBAR_TYPES = _HEATMAP_GROUP_TYPES

    def _has_colorbar_subplot(self):
        """Return True if any active subplot uses a colorbar chart type."""
        return any(
            ct in self._COLORBAR_TYPES
            for ct in self.subplot_chart_types.values()
        )

    # ── Figure geometry: margins and title position ──────────────────────────
    # The margins (left, right, bottom, top) and the title position (x, y) are
    # stored as FRACTIONS of the figure — self._fig_margins and self._title_frac.
    # The spinboxes only *display* fraction x figure size in the current unit.
    # Editing a spinbox changes that one fraction; changing the figure size, the
    # unit or the preset changes nothing but the displayed numbers. So the layout
    # never drifts (no rounding accumulation) and needs no rescaling logic.
    _DEFAULT_MARGINS = (0.10, 0.95, 0.10, 0.95)   # left, right, bottom, top
    _DEFAULT_TITLE_FRAC = (0.5, 0.97)             # x, y

    def _geom_widgets_ready(self):
        return all(hasattr(self, a) for a in (
            'fig_left', 'fig_right', 'fig_bottom', 'fig_top',
            'title_x', 'title_y', 'fig_width', 'fig_height', 'fig_unit'))

    def _fig_dims(self):
        """Figure (width, height) as shown in the spinboxes, in the current unit."""
        return self.fig_width.value(), self.fig_height.value()

    def _refresh_geometry_widgets(self):
        """Re-derive the margin and title spinboxes from the stored fractions.

        Signals are blocked while writing, so this never feeds back into the
        fractions. Fractions outside what the spinboxes allow (e.g. a right margin
        past the figure edge once no colorbar chart is active) are clamped.
        """
        if not self._geom_widgets_ready():
            return
        if not hasattr(self, '_fig_margins'):
            self._fig_margins = list(self._DEFAULT_MARGINS)
        if not hasattr(self, '_title_frac'):
            self._title_frac = list(self._DEFAULT_TITLE_FRAC)
        w, h = self._fig_dims()
        if w <= 0 or h <= 0:
            return
        unit = self.fig_unit.currentText()
        if unit == 'cm':
            dec, step, large = 1, 0.1, 9999.0
        elif unit == 'inches':
            dec, step, large = 2, 0.05, 9999.0
        else:   # pixels
            dec, step, large = 0, 5.0, 99999.0
        # Right margin may pass the figure edge when a colorbar chart is active, so
        # the colorbar can deliberately bleed outside the figure.
        right_cap = large if self._has_colorbar_subplot() else w
        for i, (sp, dim, cap) in enumerate((
                (self.fig_left,   w, w),
                (self.fig_right,  w, right_cap),
                (self.fig_bottom, h, h),
                (self.fig_top,    h, h))):
            self._fig_margins[i] = max(0.0, min(cap / dim, self._fig_margins[i]))
            sp.blockSignals(True)
            sp.setRange(0.0, cap)
            sp.setDecimals(dec)
            sp.setSingleStep(step)
            sp.setValue(self._fig_margins[i] * dim)
            sp.blockSignals(False)
        for i, (sp, dim) in enumerate(((self.title_x, w), (self.title_y, h))):
            self._title_frac[i] = max(0.0, min(1.0, self._title_frac[i]))
            sp.blockSignals(True)
            sp.setRange(0.0, dim)
            sp.setDecimals(dec)
            sp.setSingleStep(step)
            sp.setValue(self._title_frac[i] * dim)
            sp.blockSignals(False)

    def _on_margin_edited(self, idx, value):
        """A margin spinbox was edited: store that one margin as a fraction."""
        w, h = self._fig_dims()
        dim = w if idx < 2 else h
        if dim > 0:
            self._fig_margins[idx] = value / dim
        self.update_preview()

    def _on_title_pos_edited(self, idx, value):
        """A title-position spinbox was edited: store it as a fraction."""
        w, h = self._fig_dims()
        dim = w if idx == 0 else h
        if dim > 0:
            self._title_frac[idx] = value / dim
        self.update_preview()

    def _set_margin_fractions(self, left, right, bottom, top):
        """Set all four margins (fractions) and refresh what the spinboxes show."""
        self._fig_margins = [float(left), float(right), float(bottom), float(top)]
        self._refresh_geometry_widgets()

    def _set_title_fractions(self, x, y):
        """Set the title position (fractions) and refresh what the spinboxes show."""
        self._title_frac = [float(x), float(y)]
        self._refresh_geometry_widgets()

    def _pick_grid_color(self, which):
        cur = self.grid_color if which == 'major' else self.minor_grid_color
        color = _show_color_dialog(
            QColor(cur), self, palette_colors=self._active_palette_colors())
        if not color.isValid(): return
        hx = color.name()
        if which == 'major':
            self.grid_color = hx
            self.grid_color_sw.setStyleSheet(f'background-color:{hx};border:1px solid #888;border-radius:2px;')
        else:
            self.minor_grid_color = hx
            self.minor_grid_color_sw.setStyleSheet(f'background-color:{hx};border:1px solid #888;border-radius:2px;')
        # Persist to per-subplot dict immediately
        sp_idx = self.layout_sp_active.currentIndex() if hasattr(self, 'layout_sp_active') else 0
        if sp_idx < 0: sp_idx = 0
        self._save_canvas_grid_opts(sp_idx)
        self.update_preview()

    def _pick_ann_color_attr(self, attr):
        """Generic color picker that writes to self.<attr> and updates <attr>_sw swatch."""
        cur = getattr(self, attr, '#000000')
        color = _show_color_dialog(
            QColor(cur), self, palette_colors=self._active_palette_colors())
        if not color.isValid(): return
        hx = color.name()
        setattr(self, attr, hx)
        sw = getattr(self, attr + '_sw', None)
        if sw: sw.setStyleSheet(f'background-color:{hx};border:1px solid #888;border-radius:2px;')
        self._sync_ann_style()

    def _place_at_override(self):
        try: x,y = float(self.ann_x_override.text()), float(self.ann_y_override.text())
        except ValueError:
            QMessageBox.warning(self,'Invalid','Enter numeric X and Y.')
            return
        if not self.canvas.axes_list: return
        self._sync_ann_style()
        self.canvas._place_text_annotation(self.canvas.axes_list[0], 0, x, y)
