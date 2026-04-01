"""
Copyright (c) 2026 Paulo Cachim
ui/serialization_apply.py  –  plotviz
Apply saved dict back onto UI widgets for load/undo.
"""
from PyQt6.QtCore import Qt


class SerializationApplyMixin:
    def _apply_settings(self, s):
        """Restore all UI settings from a dict."""
        def _set_rb(group, value):
            for btn in group.buttons():
                if btn.property('scale_value') == value:
                    btn.setChecked(True); return

        self.combo_x.blockSignals(True); self.y_list.blockSignals(True)

        i = self.chart_type_combo.findText(s.get('chart_type', 'Line'))
        if i >= 0: self.chart_type_combo.setCurrentIndex(i)

        # Dark mode

        pal = s.get('color_palette', 'Matplotlib')
        self._color_palette = pal
        # Add to combo if it's a custom palette not yet registered
        if self.palette_combo.findText(pal) < 0:
            self.palette_combo.addItem(pal)
        i = self.palette_combo.findText(pal)
        if i >= 0:
            self.palette_combo.blockSignals(True)
            self.palette_combo.setCurrentIndex(i)
            self.palette_combo.blockSignals(False)
        self._refresh_palette_swatches()

        # Style preset (must restore before color overrides so they're not clobbered)
        i = self.preset_combo.findText(s.get('preset', 'Default'))
        if i >= 0:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(i)
            self.preset_combo.blockSignals(False)

        # Colors (update internal attr + swatch/hex labels if they exist)
        for attr, default, sw, hx in [
            ('chart_bg_color','#ffffff','chart_bg_color_swatch','chart_bg_color_hex'),
            ('chart_fg_color','#000000','chart_fg_color_swatch','chart_fg_color_hex'),
            ('plot_bg_color', '#ffffff','plot_bg_color_swatch', 'plot_bg_color_hex'),
        ]:
            v = s.get(attr, default)
            setattr(self, attr, v)
            if hasattr(self, sw): getattr(self, sw).setStyleSheet(f'color:{v};font-size:18px;')
            if hasattr(self, hx): getattr(self, hx).setText(v)

        self.border_top.setChecked(s.get('border_top', True))
        self.border_bottom.setChecked(s.get('border_bottom', True))
        self.border_left.setChecked(s.get('border_left', True))
        self.border_right.setChecked(s.get('border_right', True))

        # Restore per-series style overrides; normalise color_locked to bool
        raw_styles = s.get('curve_styles', {})
        self.curve_styles = {}
        for lbl, style in raw_styles.items():
            if isinstance(style, dict):
                style = dict(style)
                style['color_locked'] = bool(style.get('color_locked', False))
            self.curve_styles[lbl] = style

        i = self.fig_unit.findText(s.get('fig_unit','cm'))
        if i >= 0: self.fig_unit.setCurrentIndex(i)
        self.fig_width.setValue(s.get('fig_width', 20.0))
        self.fig_height.setValue(s.get('fig_height', 15.0))
        i = self.fig_preset_combo.findText(s.get('fig_preset', '20 × 15 cm'))
        if i >= 0:
            self.fig_preset_combo.blockSignals(True)
            self.fig_preset_combo.setCurrentIndex(i)
            self.fig_preset_combo.blockSignals(False)
        self.fig_left.setValue(s.get('fig_left', 0.10))
        self.fig_right.setValue(s.get('fig_right', 0.95))
        self.fig_bottom.setValue(s.get('fig_bottom', 0.10))
        self.fig_top.setValue(s.get('fig_top', 0.95))

        self.grid_check.setChecked(s.get('grid_on', True))
        self.grid_color = s.get('grid_color','#cccccc')
        self.grid_color_sw.setStyleSheet(f"color:{self.grid_color};font-size:15px;")
        i = self.grid_linestyle.findText(s.get('grid_linestyle','--'))
        if i >= 0: self.grid_linestyle.setCurrentIndex(i)
        self.grid_linewidth.setValue(s.get('grid_linewidth', 0.5))
        self.grid_alpha.setValue(s.get('grid_alpha', 0.4))
        self.minor_grid_check.setChecked(s.get('minor_grid_on', False))
        self.minor_grid_color = s.get('minor_grid_color','#e8e8e8')
        self.minor_grid_color_sw.setStyleSheet(f"color:{self.minor_grid_color};font-size:15px;")
        i = self.minor_grid_linestyle.findText(s.get('minor_grid_linestyle',':'))
        if i >= 0: self.minor_grid_linestyle.setCurrentIndex(i)
        self.minor_grid_linewidth.setValue(s.get('minor_grid_linewidth', 0.3))
        self.minor_grid_alpha.setValue(s.get('minor_grid_alpha', 0.2))

        self.dpi_spin.setValue(s.get('dpi', 300))

        # Global title
        self.title_check.setChecked(s.get('title_show', True))
        self.title_input.setText(s.get('title_text', ''))
        i = self.title_font.findText(s.get('title_font', 'sans-serif'))
        if i >= 0: self.title_font.setCurrentIndex(i)
        self.title_size.setValue(s.get('title_size', 14))
        tc = s.get('title_color', '#000000')
        self.title_color = tc
        if hasattr(self, 'title_color_label'):
            self.title_color_label.setStyleSheet(f'color:{tc};font-size:16px;')
        i = self.xlabel_font.findText(s.get('xlabel_font','sans-serif'))
        if i >= 0: self.xlabel_font.setCurrentIndex(i)
        self.xlabel_size.setValue(s.get('xlabel_size', 11))
        self.xlabel_color = s.get('xlabel_color','#000000')
        self.xlabel_color_label.setStyleSheet(f'color:{self.xlabel_color};font-size:16px;')
        i = self.ylabel_font.findText(s.get('ylabel_font','sans-serif'))
        if i >= 0: self.ylabel_font.setCurrentIndex(i)
        self.ylabel_size.setValue(s.get('ylabel_size', 11))
        self.ylabel_color = s.get('ylabel_color','#000000')
        self.ylabel_color_label.setStyleSheet(f'color:{self.ylabel_color};font-size:16px;')
        i = self.y2label_font.findText(s.get('y2label_font','sans-serif'))
        if i >= 0: self.y2label_font.setCurrentIndex(i)
        self.y2label_size.setValue(s.get('y2label_size', 11))
        self.y2label_color = s.get('y2label_color','#000000')
        self.y2label_color_label.setStyleSheet(f'color:{self.y2label_color};font-size:16px;')

        # Subplots (layout + appearance only — column assignments come from series.json)
        mosaic = s.get('subplot_mosaic', None)
        self._subplot_mosaic = mosaic
        self.sp_rows.blockSignals(True); self.sp_cols.blockSignals(True)
        self.sp_rows.setValue(s.get('subplot_rows', 1))
        self.sp_cols.setValue(s.get('subplot_cols', 1))
        self.sp_rows.blockSignals(False); self.sp_cols.blockSignals(False)
        self.subplot_rows = s.get('subplot_rows', 1)
        self.subplot_cols = s.get('subplot_cols', 1)
        if mosaic is not None:
            n_cells = len(dict.fromkeys(c for row in mosaic for c in row))
            self.on_subplot_layout_changed(n_override=n_cells)
        else:
            self.on_subplot_layout_changed()
        def _di(key, default={}): return {int(k): v for k, v in s.get(key, default).items()}
        def _dlim(key):
            return {int(k): (tuple(v) if v else None) for k, v in s.get(key, {}).items()}
        self.sp_titles             = _di('sp_titles', {'0': ''})
        self.subplot_title_show    = _di('subplot_title_show', {'0': True})
        self.subplot_title_font    = _di('subplot_title_font', {'0': 'sans-serif'})
        self.subplot_title_size    = _di('subplot_title_size', {'0': 11})
        self.subplot_title_color   = _di('subplot_title_color', {'0': '#000000'})
        if hasattr(self, 'title_x'): self.title_x.setValue(s.get('title_x', 0.5))
        if hasattr(self, 'title_y'):
            _ty = s['title_y'] if 'title_y' in s else s.get('title_y_offset', 0.97)
            self.title_y.setValue(min(max(float(_ty), 0.50), 1.00))
        if hasattr(self, 'sp_hspace'): self.sp_hspace.setValue(s.get('sp_hspace', 0.35))
        if hasattr(self, 'sp_wspace'): self.sp_wspace.setValue(s.get('sp_wspace', 0.35))
        self.subplot_xlabels       = _di('subplot_xlabels', {'0': ''})
        self.subplot_xlabel_show   = _di('subplot_xlabel_show', {'0': True})
        self.subplot_ylabels       = _di('subplot_ylabels', {'0': ''})
        self.subplot_ylabel_show   = _di('subplot_ylabel_show', {'0': True})
        self.subplot_y2labels      = _di('subplot_y2labels', {'0': ''})
        self.subplot_y2label_show  = _di('subplot_y2label_show', {'0': True})
        self.subplot_legends          = _di('subplot_legends', {'0': True})
        self.subplot_legend_locs      = _di('subplot_legend_locs', {'0': 'best'})
        self.subplot_legend_x         = _di('subplot_legend_x', {'0': 0.01})
        self.subplot_legend_y         = _di('subplot_legend_y', {'0': 0.99})
        self.subplot_legend_fontsize  = _di('subplot_legend_fontsize', {'0': 9})
        self.subplot_legend_ncols     = _di('subplot_legend_ncols', {'0': 1})
        self.subplot_legend_frameon   = _di('subplot_legend_frameon', {'0': True})
        self.subplot_legend_color     = _di('subplot_legend_color', {'0': '#000000'})
        self.subplot_legend_facecolor = _di('subplot_legend_facecolor', {'0': '#ffffff'})
        self.subplot_legend_alpha     = _di('subplot_legend_alpha', {'0': 0.8})
        self.subplot_legend_edgecolor = _di('subplot_legend_edgecolor', {'0': '#cccccc'})
        self.subplot_xlims         = _dlim('subplot_xlims')
        self.subplot_ylims         = _dlim('subplot_ylims')
        self.subplot_y2lims        = _dlim('subplot_y2lims')
        self.subplot_xscales       = _di('subplot_xscales', {'0': 'linear'})
        self.subplot_yscales       = _di('subplot_yscales', {'0': 'linear'})
        self.subplot_xtick_sizes   = _di('subplot_xtick_sizes', {'0': 9})
        self.subplot_ytick_sizes   = _di('subplot_ytick_sizes', {'0': 9})
        self.subplot_xtick_dir     = _di('subplot_xtick_dir',   {'0': 'out'})
        self.subplot_ytick_dir     = _di('subplot_ytick_dir',   {'0': 'out'})
        self.subplot_xtick_minor   = _di('subplot_xtick_minor', {'0': False})
        self.subplot_ytick_minor   = _di('subplot_ytick_minor', {'0': False})
        self.subplot_xtick_rotation= _di('subplot_xtick_rotation', {'0': 0})
        self.subplot_ytick_rotation= _di('subplot_ytick_rotation', {'0': 0})
        self.subplot_xtick_step    = _di('subplot_xtick_step',  {'0': 0.0})
        self.subplot_ytick_step    = _di('subplot_ytick_step',  {'0': 0.0})
        self.subplot_x_formatter   = _di('subplot_x_formatter', {'0': 'auto'})
        self.subplot_y_formatter   = _di('subplot_y_formatter', {'0': 'auto'})
        self.subplot_xticks_show   = _di('subplot_xticks_show', {'0': True})
        self.subplot_yticks_show   = _di('subplot_yticks_show', {'0': True})
        self.subplot_ann_visible   = _di('subplot_ann_visible', {'0': True})
        self.sp_sharex.setChecked(s.get('sp_sharex', False))
        self.sp_sharey.setChecked(s.get('sp_sharey', False))
        # Reload Axes tab widgets for subplot 0
        self.on_active_subplot_changed()

        # Fit CI/PI bands (fit_color/fit_linestyle/fit_linewidth removed in 2.0.0 —
        # fit curves are now styled via curve_styles like any other series)
        self.fit_ci_combo.setCurrentIndex(s.get('fit_ci_index', 0))
        self.fit_pi_combo.setCurrentIndex(s.get('fit_pi_index', 0))
        self.fit_ci_alpha_spin.setValue(s.get('fit_ci_alpha', 0.25))

        # Restore fit results
        fr = s.get('fit_result')
        if fr and fr.get('model') and fr.get('popt'):
            import numpy as _np
            from data.scientific import CurveFitter as _CF
            try:
                model   = fr['model']
                func    = _CF.MODELS.get(model)
                popt    = _np.array(fr['popt'])
                pcov    = _np.array(fr['pcov']) if fr.get('pcov') else _np.zeros((len(popt), len(popt)))
                xd      = _np.array(fr['xd'])
                yd      = _np.array(fr['yd']) if fr.get('yd') else _np.zeros_like(xd)
                self._last_fit = dict(
                    model=model, func=func, popt=popt, pcov=pcov,
                    xd=xd, yd=yd,
                    xc=fr.get('xc',''), yc=fr.get('yc',''), lbl=fr.get('lbl',''),
                    eq_str=fr.get('eq_str',''), r2=fr.get('r2'),
                    stats=fr.get('stats', {}),
                )
                self._refresh_fit_results_panel()
            except Exception:
                self._last_fit = None
        else:
            self._last_fit = None

        # Chart-type specific
        self.hist_bins.setValue(s.get('hist_bins', 20))
        self.hist_density.setChecked(s.get('hist_density', False))
        self.bar_width.setValue(s.get('bar_width', 0.8))
        self.bar_stacked.setChecked(s.get('bar_stacked', False))
        self.bar_horizontal.setChecked(s.get('bar_horizontal', False))
        self.scatter_size.setValue(s.get('scatter_size', 20))
        self.scatter_alpha.setValue(s.get('scatter_alpha', 0.8))
        self.err_capsize.setValue(s.get('err_capsize', 4))
        i = self.cmap_combo.findText(s.get('cmap','viridis'))
        if i >= 0: self.cmap_combo.setCurrentIndex(i)
        self.contour_levels.setValue(s.get('contour_levels', 10))
        self.heat_colorbar.setChecked(s.get('heat_colorbar', True))
        self.pie_autopct.setChecked(s.get('pie_autopct', True))
        self.pie_shadow.setChecked(s.get('pie_shadow', False))
        self.area_alpha.setValue(s.get('area_alpha', 0.4))
        self.area_stacked.setChecked(s.get('area_stacked', False))
        self.violin_show_means.setChecked(s.get('violin_show_means', True))
        self.violin_show_medians.setChecked(s.get('violin_show_medians', True))

        # ── Annotation default style ─────────────────────────────────────────
        def _set_ann_color(attr, default):
            v = s.get(attr, default)
            setattr(self, attr, v)
            sw = getattr(self, attr + '_sw', None)
            if sw:
                sw.setStyleSheet(f'color:{v};font-size:16px;')

        _set_ann_color('ann_fontcolor', '#000000')
        _set_ann_color('ann_bgcolor',   '#ffffcc')
        _set_ann_color('ann_edgecolor', '#aaaaaa')
        self.ann_fontsize.blockSignals(True)
        self.ann_fontsize.setValue(s.get('ann_fontsize', 10))
        self.ann_fontsize.blockSignals(False)
        i = self.ann_font.findText(s.get('ann_font', 'sans-serif'))
        if i >= 0:
            self.ann_font.blockSignals(True)
            self.ann_font.setCurrentIndex(i)
            self.ann_font.blockSignals(False)
        self.ann_bg_alpha.blockSignals(True)
        self.ann_bg_alpha.setValue(s.get('ann_bg_alpha', 0.9))
        self.ann_bg_alpha.blockSignals(False)

        # ── Line / series defaults ───────────────────────────────────────────
        for attr, default in [
            ('line_default_style',      '-'),
            ('line_default_marker',     'None'),
        ]:
            w = getattr(self, attr, None)
            if w:
                i = w.findText(s.get(attr, default))
                if i >= 0:
                    w.blockSignals(True); w.setCurrentIndex(i); w.blockSignals(False)
        for attr, default in [
            ('line_default_lw',         1.5),
            ('line_default_markersize', 6.0),
        ]:
            w = getattr(self, attr, None)
            if w:
                w.blockSignals(True); w.setValue(s.get(attr, default)); w.blockSignals(False)

        self.combo_x.blockSignals(False); self.y_list.blockSignals(False)

        # ── Post-load UI sync ────────────────────────────────────────────────
        # Refresh curve selector and load the first curve's style into the swatch
        self._refresh_curve_select()
        self.load_curve_style()          # updates curve_color_label + lock indicator
        # Palette swatches
        if hasattr(self, '_palette_swatches'):
            self._refresh_palette_swatches()
        # Sync annotation canvas style from restored defaults
        self._sync_ann_style()

    def _apply_series_meta(self, m):
        """Restore series table and subplot assignments from series.json dict."""
        from ui.tab_builders import PER_SERIES_TYPES
        old_y2_cols = set(m.get('y2_cols', []))
        cols = sorted(self.datasets)
        n_subplots = max(1, self.subplot_rows * self.subplot_cols)
        self.series_table.blockSignals(True)
        self.series_table.setRowCount(0)
        for sd in m.get('series', []):
            row = self.series_table.rowCount()
            self.series_table.insertRow(row)

            # X combo — signals blocked during construction
            cb_x = QComboBox(); cb_x.blockSignals(True)
            cb_x.addItems(cols)
            i = cb_x.findText(sd.get('x_col', ''))
            if i >= 0: cb_x.setCurrentIndex(i)
            cb_x.blockSignals(False)
            cb_x.currentIndexChanged.connect(self._on_x_col_changed)
            self.series_table.setCellWidget(row, 0, cb_x)

            # Y combo — signals blocked during construction
            cb_y = QComboBox(); cb_y.blockSignals(True)
            cb_y.addItems(cols)
            i = cb_y.findText(sd.get('y_col', ''))
            if i >= 0: cb_y.setCurrentIndex(i)
            cb_y.blockSignals(False)
            cb_y.currentIndexChanged.connect(self.update_preview)
            self.series_table.setCellWidget(row, 1, cb_y)

            self.series_table.setItem(row, 2, QTableWidgetItem(sd.get('label', f'Series {row+1}')))

            # Type combo
            type_cb = QComboBox(); type_cb.addItems(PER_SERIES_TYPES)
            saved_type = sd.get('series_type', 'Line')
            ti = type_cb.findText(saved_type)
            if ti >= 0: type_cb.setCurrentIndex(ti)
            type_cb.currentIndexChanged.connect(self.update_preview)
            type_cb.currentIndexChanged.connect(self._on_series_selection_changed)
            self.series_table.setCellWidget(row, 3, type_cb)

            # Plot spinbox
            plot_spin = QSpinBox()
            plot_spin.setRange(1, n_subplots)
            plot_spin.setValue(min(sd.get('plot_num', 1), n_subplots))
            plot_spin.valueChanged.connect(self.update_preview)
            plot_spin.valueChanged.connect(lambda _: self._filter_series_table_by_subplot())
            self.series_table.setCellWidget(row, 4, plot_spin)

            # Y2 checkbox
            y2_item = QTableWidgetItem()
            y2_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            is_y2 = sd.get('y2', sd.get('y_col', '') in old_y2_cols)
            y2_item.setCheckState(Qt.CheckState.Checked if is_y2 else Qt.CheckState.Unchecked)
            self.series_table.setItem(row, 5, y2_item)

        self.series_table.blockSignals(False)

        # Auto-assign palette colors to any series that has no color lock.
        # Handles old files (no curve_styles entry) and new files where the
        # user never manually picked a color.
        for row in range(self.series_table.rowCount()):
            lbl_item = self.series_table.item(row, 2)
            lbl = lbl_item.text() if lbl_item else f'Series {row+1}'
            entry = self.curve_styles.get(lbl, {})
            if not entry.get('color_locked', False):
                auto_color = self._palette_color(row)
                entry['color'] = auto_color
                entry['marker_color'] = auto_color
                self.curve_styles[lbl] = entry

        i = self.combo_z.findText(m.get('z_col', '(none)'))
        if i >= 0: self.combo_z.setCurrentIndex(i)
        i = self.combo_err.findText(m.get('err_col', '(none)'))
        if i >= 0: self.combo_err.setCurrentIndex(i)

        # Restore subplot chart types
        saved_ct = m.get('subplot_chart_types', {})
        self.subplot_chart_types = {int(k): v for k, v in saved_ct.items()}
        saved_ll = m.get('subplot_legend_locs', {})
        self.subplot_legend_locs = {int(k): v for k, v in saved_ll.items()}
        for idx in range(n_subplots):
            self.subplot_chart_types.setdefault(idx, 'Line')
            self.subplot_legend_locs.setdefault(idx, 'best')
        self._refresh_curve_select()
        self._filter_series_table_by_subplot()


    # ═══════════════════════════════════════════════════════════════════════════
    # .pviz SAVE / LOAD  (zip containing settings.json + data.json + images/)
    # ═══════════════════════════════════════════════════════════════════════════

