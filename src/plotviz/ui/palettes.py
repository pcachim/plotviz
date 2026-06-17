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
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
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
        self._update_margin_ranges()
        self._update_title_pos_ranges()
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
        # Reset so next window resize scales from the manually-set size.
        # Use canvas dimensions so baseline stays consistent with _apply_resize_and_preview.
        if hasattr(self, 'canvas'):
            self._window_size_baseline = (self.canvas.width(), self.canvas.height())
        self.update_preview()

    def _on_fig_unit_changed(self, unit):
        """When unit changes, convert current displayed values to the new unit."""
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

        # ── Also convert the four margin spinboxes ────────────────────────────
        # Read current physical values using prev_unit, convert to inches, then
        # to the new unit — same pattern as fig_width/fig_height above.
        m_vals_in = []
        for sp in (self.fig_left, self.fig_right, self.fig_bottom, self.fig_top):
            v = sp.value()
            if prev_unit == 'cm':
                m_vals_in.append(v / 2.54)
            elif prev_unit == 'pixels':
                m_vals_in.append(v / self.dpi_spin.value())
            else:
                m_vals_in.append(v)

        # Update ranges (caps at new fig dimension) without proportional rescaling —
        # _on_fig_unit_changed has already done the conversion explicitly above.
        self._in_scale_figsize = True
        self._update_margin_ranges()
        self._in_scale_figsize = False
        for sp, val_in in zip(
            (self.fig_left, self.fig_right, self.fig_bottom, self.fig_top),
            m_vals_in,
        ):
            sp.blockSignals(True)
            if unit == 'cm':
                sp.setValue(round(val_in * 2.54, 1))
            elif unit == 'inches':
                sp.setValue(round(val_in, 2))
            elif unit == 'pixels':
                sp.setValue(round(val_in * self.dpi_spin.value()))
            sp.blockSignals(False)

        # ── Convert title_x / title_y the same way ────────────────────────────
        if hasattr(self, 'title_x') and hasattr(self, 'title_y'):
            tx_in = self.title_x.value()
            ty_in = self.title_y.value()
            if prev_unit == 'cm':
                tx_in, ty_in = tx_in / 2.54, ty_in / 2.54
            elif prev_unit == 'pixels':
                tx_in = tx_in / self.dpi_spin.value()
                ty_in = ty_in / self.dpi_spin.value()
            self._update_title_pos_ranges()
            self.title_x.blockSignals(True)
            self.title_y.blockSignals(True)
            if unit == 'cm':
                self.title_x.setValue(round(tx_in * 2.54, 1))
                self.title_y.setValue(round(ty_in * 2.54, 1))
            elif unit == 'inches':
                self.title_x.setValue(round(tx_in, 2))
                self.title_y.setValue(round(ty_in, 2))
            elif unit == 'pixels':
                self.title_x.setValue(round(tx_in * self.dpi_spin.value()))
                self.title_y.setValue(round(ty_in * self.dpi_spin.value()))
            self.title_x.blockSignals(False)
            self.title_y.blockSignals(False)

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

    def _update_margin_ranges(self):
        """Keep margin spinbox maxima equal to the current figure dimensions,
        and proportionally rescale margin values when dimensions change.

        right ≤ fig_width and top ≤ fig_height (both in the current fig_unit),
        except when a colorbar chart type is active — in that case the right
        margin is uncapped so the colorbar can bleed beyond the figure edge.
        Called whenever fig_width, fig_height, fig_unit, or chart type changes.

        Proportional rescaling is skipped when called from _scale_figsize
        (which already rescales in step 4) or from _on_fig_unit_changed
        (which already converts values to the new unit).  Both callers set
        _in_scale_figsize = True before calling this method.
        """
        if not all(hasattr(self, a) for a in
                   ('fig_left', 'fig_right', 'fig_bottom', 'fig_top',
                    'fig_width', 'fig_height', 'fig_unit')):
            return
        w    = self.fig_width.value()
        h    = self.fig_height.value()
        unit = self.fig_unit.currentText()
        if unit == 'cm':
            dec, step, large = 1, 0.1, 9999.0
        elif unit == 'inches':
            dec, step, large = 2, 0.05, 9999.0
        else:   # pixels
            dec, step, large = 0, 5.0, 99999.0
        right_cap = large if self._has_colorbar_subplot() else w

        # Proportionally rescale margin values when figure dimensions change
        # manually (spinbox edit or preset change).  Use fig_left/bottom maximums
        # as a reliable proxy for the previous fig_width/height — they are always
        # set to the figure dimension by this very method (never to 'large').
        # Skip when _scale_figsize or _on_fig_unit_changed is handling it.
        if not getattr(self, '_in_scale_figsize', False):
            old_w = self.fig_left.maximum()    # previous fig_width
            old_h = self.fig_bottom.maximum()  # previous fig_height
            if old_w > 0 and old_w != w:
                for sp, new_dim in (
                    (self.fig_left,  w),
                    (self.fig_right, w),   # cap applied below; use w for scaling
                ):
                    scaled = sp.value() * (w / old_w)
                    sp.blockSignals(True)
                    sp.setValue(max(0.0, min(w, scaled)))
                    sp.blockSignals(False)
            if old_h > 0 and old_h != h:
                for sp in (self.fig_bottom, self.fig_top):
                    scaled = sp.value() * (h / old_h)
                    sp.blockSignals(True)
                    sp.setValue(max(0.0, min(h, scaled)))
                    sp.blockSignals(False)

        for sp, cap in (
            (self.fig_left,   w),
            (self.fig_right,  right_cap),
            (self.fig_bottom, h),
            (self.fig_top,    h),
        ):
            sp.setRange(0.0, cap)
            sp.setDecimals(dec)
            sp.setSingleStep(step)

    def _update_title_pos_ranges(self):
        """Keep title_x max = fig_width and title_y max = fig_height (physical units).

        When the figure dimensions change and we are NOT inside _scale_figsize
        (which already handled proportional scaling), we scale title_x / title_y
        to maintain their fractional position so the title doesn't jump or
        disappear when the figure is made smaller.
        """
        if not all(hasattr(self, a) for a in
                   ('title_x', 'title_y', 'fig_width', 'fig_height', 'fig_unit')):
            return
        w    = self.fig_width.value()
        h    = self.fig_height.value()
        unit = self.fig_unit.currentText()
        if unit == 'cm':
            dec, step = 1, 0.1
        elif unit == 'inches':
            dec, step = 2, 0.05
        else:   # pixels
            dec, step = 0, 5.0

        # _scale_figsize has already written the correct proportional values;
        # don't touch them again — just update the range bounds.
        if getattr(self, '_in_scale_figsize', False):
            self.title_x.setRange(0.0, w)
            self.title_x.setDecimals(dec)
            self.title_x.setSingleStep(step)
            self.title_y.setRange(0.0, h)
            self.title_y.setDecimals(dec)
            self.title_y.setSingleStep(step)
            return

        # Outside _scale_figsize: figure size changed via manual spinbox edit,
        # preset selection, or unit conversion.  Scale title_x/y proportionally
        # so they keep the same fractional position within the figure.
        old_w_max = self.title_x.maximum()   # previous fig_width (range max)
        old_h_max = self.title_y.maximum()   # previous fig_height (range max)

        for sp, new_max, old_max in (
            (self.title_x, w, old_w_max),
            (self.title_y, h, old_h_max),
        ):
            if old_max > 0 and old_max != new_max:
                # Scale the current value to maintain fractional position,
                # then clamp to the new range.
                scaled = sp.value() * (new_max / old_max)
                sp.blockSignals(True)
                sp.setRange(0.0, new_max)
                sp.setDecimals(dec)
                sp.setSingleStep(step)
                sp.setValue(max(0.0, min(new_max, scaled)))
                sp.blockSignals(False)
            else:
                sp.setRange(0.0, new_max)
                sp.setDecimals(dec)
                sp.setSingleStep(step)

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

    def _pick_ann_color(self, target):
        """Legacy shim — routes to the generic attr picker."""
        mapping = {'font': 'ann_fontcolor', 'bg': 'ann_bgcolor', 'edge': 'ann_edgecolor'}
        if target in mapping:
            self._pick_ann_color_attr(mapping[target])

    def _place_at_override(self):
        try: x,y = float(self.ann_x_override.text()), float(self.ann_y_override.text())
        except ValueError:
            QMessageBox.warning(self,'Invalid','Enter numeric X and Y.')
            return
        if not self.canvas.axes_list: return
        self._sync_ann_style()
        self.canvas._place_text_annotation(self.canvas.axes_list[0], 0, x, y)
