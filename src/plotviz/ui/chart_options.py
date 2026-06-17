"""
Copyright (c) 2026 Paulo Cachim
ui/chart_options.py  –  plotviz

ChartOptionsMixin: show/hide and populate the per-chart-type option groups as
the selected chart type changes. Split out of main_window; mixed into
PlotVizApp so it shares the option widgets and series state via `self`.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit, QScrollArea

from ui.tab_builders import WHOLE_CHART_TYPES, PLOT_MODE_GROUPS, TYPE_TO_PLOT_MODE


class ChartOptionsMixin:
    def _update_option_group_visibility(self, ct):
        """Show/hide chart-type option groups (Data tab) and series-type option
        groups (Series tab) for the given chart type."""
        if not hasattr(self, 'hist_group'):
            return

        # ── Data tab: chart-mode groups ───────────────────────────────────────
        data_vis = {
            self.bar_group:          ct == 'Bar',
            self.hist_group:         ct == 'Histogram',
            self.heat_group:         ct in ('Heatmap', 'Contour', '3D Surface'),
            self.pie_group:          ct == 'Pie',
            self.area_group:         ct == 'Area',
            self.fill_between_group: ct == 'Fill Between',
            self.violin_group:       ct == 'Violin',
            self.boxplot_group:      ct == 'Boxplot',
            self.step_group:         ct == 'Step',
            self.stem_group:         ct == 'Stem',
            self.waterfall_group:    ct == 'Waterfall',
            self.hist2d_group:       ct == 'Hist2D',
            self.hexbin_group:       ct == 'Hexbin',
            self.radar_group:        ct == 'Radar',
            self.ecdf_group:         ct == 'ECDF',
            self.quiver_group:       ct == 'Quiver',
            self.barbs_group:        ct == 'Barbs',
            self.streamplot_group:   ct == 'Streamplot',
        }
        if hasattr(self, 'tri_group'):
            data_vis[self.tri_group] = ct == 'Tricontour'
        for grp, show in data_vis.items():
            grp.setVisible(show)

        # Bug 9 / Fix 2: within heat_group, show only the controls relevant to each type.
        # Interpolation is an imshow parameter — only Heatmap uses it.
        # Contour levels / style / line-style only apply to Contour.
        # 3D stride / wireframe only apply to 3D Surface.
        # vmin/vmax and colorbar apply to all three.
        if hasattr(self, '_heat_interpolation_row'):
            self._heat_interpolation_row.setVisible(ct == 'Heatmap')
        if hasattr(self, '_heat_contour_levels_row'):
            self._heat_contour_levels_row.setVisible(ct == 'Contour')
        if hasattr(self, '_heat_contour_style_row'):
            self._heat_contour_style_row.setVisible(ct == 'Contour')
        if hasattr(self, '_heat_contour_line_style_row'):
            self._heat_contour_line_style_row.setVisible(ct == 'Contour')
        if hasattr(self, '_heat_3d_row'):
            self._heat_3d_row.setVisible(ct == '3D Surface')
        if hasattr(self, '_layout_3d_view_widget'):
            self._layout_3d_view_widget.setVisible(ct == '3D Surface')
        if hasattr(self, '_z_axis_widget'):
            self._z_axis_widget.setVisible(ct in {'3D Surface', 'Heatmap', 'Contour', 'Tricontour'})
        # Fix 4: vmin/vmax shown for Heatmap and Contour
        if hasattr(self, '_heat_vminmax_row'):
            self._heat_vminmax_row.setVisible(ct in ('Heatmap', 'Contour'))

        # ── Series tab: per-series type groups ────────────────────────────────
        for attr, show in [
            ('st_line_group',         ct == 'Line'),
            ('st_scatter_group',      ct == 'Scatter'),
            ('st_bar_group',          ct == 'Bar'),
            ('st_hist_group',         ct == 'Histogram'),
            ('st_err_group',          ct == 'Errorbar'),
            ('st_area_group',         ct == 'Area'),
            ('st_fill_between_group', ct == 'Fill Between'),
            ('st_step_group',         ct == 'Step'),
            ('st_bubble_group',       ct == 'Bubble'),
            ('st_polar_group',        ct == 'Polar'),
            ('st_radar_group',        ct == 'Radar'),
            ('st_ecdf_group',         ct == 'ECDF'),
        ]:
            grp = getattr(self, attr, None)
            if grp is not None:
                grp.setVisible(show)

        # ── Column-picker visibility ───────────────────────────────────────────
        if hasattr(self, '_combo_z_widget'):
            self._combo_z_widget.setVisible(ct in ('Heatmap', 'Contour', 'Tricontour', '3D Surface'))
        if hasattr(self, '_combo_err_widget'):
            self._combo_err_widget.setVisible(ct == 'Errorbar')
        if hasattr(self, '_combo_fill_y2_widget'):
            self._combo_fill_y2_widget.setVisible(ct == 'Fill Between')

    def _on_chart_type_changed(self, ct):
        """Hidden chart_type_combo changed — update subplot_chart_types and option groups.
        No longer pushes to series table rows; that is now _on_plot_mode_changed's job.
        """
        from ui.tab_builders import WHOLE_CHART_TYPES
        if hasattr(self, 'series_sp_active'):
            n = self.subplot_rows * self.subplot_cols
            active_sp = (self.series_sp_active.currentIndex() + 1) if n > 1 else 1
            active_idx = active_sp - 1
            if ct in WHOLE_CHART_TYPES:
                self.subplot_chart_types[active_idx] = ct
            else:
                if self.subplot_chart_types.get(active_idx) in WHOLE_CHART_TYPES:
                    self.subplot_chart_types[active_idx] = ct
        self._update_option_group_visibility(ct)
        self._update_margin_ranges()
        if hasattr(self, 'datasets'):
            self.update_preview()

    def _on_plot_mode_changed(self, mode):
        """Plot Mode combo changed — repopulate type cells in the active subplot's rows
        to only contain the types that belong to this mode, then update option groups.
        """
        from ui.tab_builders import PLOT_MODE_GROUPS, WHOLE_CHART_TYPES
        allowed = PLOT_MODE_GROUPS.get(mode, [])
        if not allowed:
            return
        n = self.subplot_rows * self.subplot_cols
        active_sp = (self.series_sp_active.currentIndex() + 1) if (n > 1 and hasattr(self, 'series_sp_active')) else 1
        active_idx = active_sp - 1
        # Persist the mode for this subplot
        self.subplot_plot_modes[active_idx] = mode
        # Repopulate every visible type combo for the active subplot
        if hasattr(self, 'series_table'):
            for row in range(self.series_table.rowCount()):
                spin = self.series_table.cellWidget(row, 4)
                row_sp = spin.value() if (spin and n > 1) else 1
                if row_sp != active_sp:
                    continue
                type_cb = self.series_table.cellWidget(row, 3)
                if type_cb:
                    current = type_cb.currentText()
                    type_cb.blockSignals(True)
                    type_cb.clear()
                    type_cb.addItems(allowed)
                    new_idx = type_cb.findText(current) if current in allowed else 0
                    type_cb.setCurrentIndex(new_idx)
                    type_cb.blockSignals(False)
        first_type = allowed[0]
        # Sync the hidden chart_type_combo
        if hasattr(self, 'chart_type_combo'):
            self.chart_type_combo.blockSignals(True)
            i = self.chart_type_combo.findText(first_type)
            if i >= 0:
                self.chart_type_combo.setCurrentIndex(i)
            self.chart_type_combo.blockSignals(False)
        # Update subplot_chart_types for whole-chart projections
        if first_type in WHOLE_CHART_TYPES:
            self.subplot_chart_types[active_idx] = first_type
        else:
            if self.subplot_chart_types.get(active_idx) in WHOLE_CHART_TYPES:
                self.subplot_chart_types[active_idx] = first_type
        self._update_option_group_visibility(first_type)
        if hasattr(self, 'datasets'):
            self.update_preview()

    # ── Per-subplot chart-option fields ──────────────────────────────────────
    # Each entry: (widget_attr, storage_key, default_value, widget_kind)
    # widget_kind: 'spin' | 'dbl' | 'check' | 'combo' | 'color'
    # These are the Data-tab chart-level option groups; each subplot stores its
    # own copy in self.subplot_chart_opts[subplot_idx].
    CHART_OPT_FIELDS = [
        # Bar
        ('bar_stacked',         'bar_stacked',         False,     'check'),
        ('bar_horizontal',      'bar_horizontal',       False,     'check'),
        # Histogram
        ('hist_bins',           'hist_bins',            20,        'spin'),
        ('hist_density',        'hist_density',         False,     'check'),
        ('hist_cumulative',     'hist_cumulative',      False,     'check'),
        ('hist_histtype',       'hist_histtype',        'bar',     'combo'),
        ('hist_orientation',    'hist_orientation',     'vertical','combo'),
        # Heatmap / Contour / 3D
        ('cmap_combo',          'cmap',                 'viridis', 'combo'),
        ('contour_levels',      'contour_levels',       10,        'spin'),
        ('heat_alpha',          'heat_alpha',           1.0,       'dbl'),
        ('heat_interpolation',  'heat_interpolation',   'nearest', 'combo'),
        ('heat_colorbar',       'heat_colorbar',        True,      'check'),
        ('heat_colorbar_shrink','heat_colorbar_shrink', 1.0,       'dbl'),
        ('heat_filled_contour', 'heat_filled_contour',  True,      'check'),
        ('heat_contour_lines',  'heat_contour_lines',   True,      'check'),
        ('surf_stride',         'surf_stride',          1,         'spin'),
        ('surf_wireframe',      'surf_wireframe',       False,     'check'),
        # Fix 4/5: new heat/contour controls
        ('heat_vminmax_enable', 'heat_vminmax_enable',  False,     'check'),
        ('heat_vmin',           'heat_vmin',            0.0,       'dbl'),
        ('heat_vmax',           'heat_vmax',            1.0,       'dbl'),
        ('contour_line_width',  'contour_line_width',   0.5,       'dbl'),
        ('contour_line_color',  'contour_line_color',   '#000000', 'color'),
        # Tricontour
        ('tri_cmap_combo',      'tri_cmap',             'rainbow',          'combo'),
        ('tri_levels',          'tri_levels',           10,                 'spin'),
        ('tri_alpha',           'tri_alpha',            1.0,                'dbl'),
        ('tri_fill_mode',       'tri_fill_mode',        'Filled contour',   'combo'),
        ('tri_lines',           'tri_lines',            True,               'check'),
        ('tri_triplot',         'tri_triplot',          False,              'check'),
        ('tri_colorbar',        'tri_colorbar',         True,               'check'),
        ('tri_colorbar_shrink', 'tri_colorbar_shrink',  1.0,                'dbl'),
        # Pie
        ('pie_autopct',         'pie_autopct',          True,      'check'),
        ('pie_shadow',          'pie_shadow',           False,     'check'),
        ('pie_donut',           'pie_donut',            False,     'check'),
        ('pie_explode_first',   'pie_explode_first',    False,     'check'),
        ('pie_startangle',      'pie_startangle',       90.0,      'dbl'),
        ('pie_labeldistance',   'pie_labeldistance',    1.1,       'dbl'),
        ('pie_pctdistance',     'pie_pctdistance',      0.6,       'dbl'),
        # Area
        ('area_stacked',        'area_stacked',         False,     'check'),
        ('area_baseline',       'area_baseline',        0.0,       'dbl'),
        # Violin
        ('violin_show_means',   'violin_show_means',    True,      'check'),
        ('violin_show_medians', 'violin_show_medians',  True,      'check'),
        ('violin_show_extrema', 'violin_show_extrema',  False,     'check'),
        ('violin_points',       'violin_points',        '100',     'combo'),
        ('violin_bw',           'violin_bw',            'scott',   'combo'),
        ('violin_vert',         'violin_vert',          True,      'check'),
        # Boxplot
        ('box_show_means',      'box_show_means',       False,     'check'),
        ('box_show_medians',    'box_show_medians',     True,      'check'),
        ('box_notch',           'box_notch',            False,     'check'),
        ('box_showfliers',      'box_showfliers',       True,      'check'),
        ('box_vert',            'box_vert',             True,      'check'),
        ('box_whis',            'box_whis',             1.5,       'dbl'),
        ('box_alpha',           'box_alpha',            0.7,       'dbl'),
        # Step
        ('step_where',          'step_where',           'pre',     'combo'),
        # Stem
        ('stem_baseline',       'stem_baseline',        0.0,       'dbl'),
        # Waterfall
        ('waterfall_connector', 'waterfall_connector',  True,      'check'),
        ('waterfall_width',     'waterfall_width',      0.6,       'dbl'),
        ('waterfall_alpha',     'waterfall_alpha',      1.0,       'dbl'),
        ('waterfall_pos_color', 'waterfall_pos_color',  '#2ecc71', 'color'),
        ('waterfall_neg_color', 'waterfall_neg_color',  '#e74c3c', 'color'),
        # Hist2D
        ('hist2d_bins_x',       'hist2d_bins_x',        20,        'spin'),
        ('hist2d_bins_y',       'hist2d_bins_y',        20,        'spin'),
        ('hist2d_alpha',        'hist2d_alpha',         1.0,       'dbl'),
        ('hist2d_cmap_combo',   'hist2d_cmap',          'viridis', 'combo'),
        ('hist2d_colorbar',     'hist2d_colorbar',      True,      'check'),
        ('hist2d_log',          'hist2d_log',           False,     'check'),
        # Hexbin
        ('hexbin_gridsize',     'hexbin_gridsize',      20,        'spin'),
        ('hexbin_alpha',        'hexbin_alpha',         1.0,       'dbl'),
        ('hexbin_cmap_combo',   'hexbin_cmap',          'viridis', 'combo'),
        ('hexbin_colorbar',     'hexbin_colorbar',      True,      'check'),
        ('hexbin_log',          'hexbin_log',           False,     'check'),
        # Radar
        ('radar_gridlevels',    'radar_gridlevels',     5,         'spin'),
        # ECDF
        ('ecdf_complementary',  'ecdf_complementary',   False,     'check'),
        # Quiver
        ('quiver_scale',        'quiver_scale',         1.0,       'dbl'),
        ('quiver_width',        'quiver_width',         0.005,     'dbl'),
        ('quiver_color_by_mag', 'quiver_color_by_mag',  False,     'check'),
        ('quiver_cmap_combo',   'quiver_cmap',          'viridis', 'combo'),
        # Barbs
        ('barbs_length',        'barbs_length',         7.0,       'dbl'),
        ('barbs_pivot_combo',   'barbs_pivot',          'tip',     'combo'),
        ('barbs_alpha',         'barbs_alpha',          0.85,      'dbl'),
        ('barbs_color_by_mag',  'barbs_color_by_mag',   False,     'check'),
        ('barbs_cmap_combo',    'barbs_cmap',           'viridis', 'combo'),
        # Streamplot
        ('stream_density',      'stream_density',       1.0,       'dbl'),
        ('stream_arrowsize',    'stream_arrowsize',     1.0,       'dbl'),
        ('stream_linewidth',    'stream_linewidth',     1.5,       'dbl'),
        ('stream_color_by_mag', 'stream_color_by_mag',  False,     'check'),
        ('stream_cmap_combo',   'stream_cmap',          'viridis', 'combo'),
    ]

    def _default_chart_opts(self):
        """Return a dict of chart option defaults for a fresh subplot."""
        return {key: default for _, key, default, _ in self.CHART_OPT_FIELDS}

    def _save_chart_opts(self, idx):
        """Read all chart option widgets and persist to subplot_chart_opts[idx]."""
        opts = self.subplot_chart_opts.setdefault(idx, self._default_chart_opts())
        for attr, key, default, kind in self.CHART_OPT_FIELDS:
            w = getattr(self, attr, None)
            if w is None:
                continue
            if kind == 'spin':
                opts[key] = w.value()
            elif kind == 'dbl':
                opts[key] = w.value()
            elif kind == 'check':
                opts[key] = w.isChecked()
            elif kind == 'combo':
                opts[key] = w.currentText()
            elif kind == 'color':
                opts[key] = getattr(self, attr, default)
        # Fix 6: save explicit contour levels QLineEdit (not in CHART_OPT_FIELDS — no 'text' kind)
        if hasattr(self, 'contour_levels_explicit'):
            opts['contour_levels_explicit'] = self.contour_levels_explicit.text()

    def _load_chart_opts(self, idx):
        """Load subplot_chart_opts[idx] values into the chart option widgets."""
        opts = self.subplot_chart_opts.get(idx, self._default_chart_opts())
        for attr, key, default, kind in self.CHART_OPT_FIELDS:
            w = getattr(self, attr, None)
            val = opts.get(key, default)
            if w is None:
                if kind == 'color':
                    setattr(self, attr, val)
                continue
            if kind == 'spin':
                w.blockSignals(True)
                w.setValue(int(val))
                w.blockSignals(False)
            elif kind == 'dbl':
                w.blockSignals(True)
                w.setValue(float(val))
                w.blockSignals(False)
            elif kind == 'check':
                w.blockSignals(True)
                w.setChecked(bool(val))
                w.blockSignals(False)
            elif kind == 'combo':
                w.blockSignals(True)
                i = w.findText(str(val))
                if i >= 0: w.setCurrentIndex(i)
                w.blockSignals(False)
            elif kind == 'color':
                setattr(self, attr, val)
                btn = getattr(self, attr + '_btn', None)
                if btn: btn.setStyleSheet(f'background-color:{val};border:1px solid #888;')
                # Also update the swatch if it exists (for contour_line_color etc.)
                sw = getattr(self, attr + '_sw', None)
                if sw: sw.setStyleSheet(self._SW_CSS.format(val))
        # Fix 6: load explicit contour levels QLineEdit
        if hasattr(self, 'contour_levels_explicit'):
            self.contour_levels_explicit.blockSignals(True)
            self.contour_levels_explicit.setText(opts.get('contour_levels_explicit', ''))
            self.contour_levels_explicit.blockSignals(False)

    # ── Per-subplot canvas / grid opts ───────────────────────────────────────
    def _default_canvas_opts(self):
        return {
            'bg': '#ffffff', 'fg': '#000000', 'plot_bg': '#ffffff',
            'border_top': True, 'border_bottom': True,
            'border_left': True, 'border_right': True,
        }

    def _default_grid_opts(self):
        return {
            'enabled': True,  'color': '#cccccc', 'ls': '--', 'lw': 0.5,  'alpha': 0.4,
            'minor_enabled': False, 'minor_color': '#e8e8e8', 'minor_ls': ':',
            'minor_lw': 0.3, 'minor_alpha': 0.2,
        }

    def _save_canvas_grid_opts(self, idx):
        """Persist current widget values → subplot_canvas_opts[idx] / subplot_grid_opts[idx]."""
        if not all(hasattr(self, a) for a in ('border_top', 'grid_check', 'grid_linestyle')):
            return
        self.subplot_canvas_opts[idx] = {
            'bg':            getattr(self, 'chart_bg_color', '#ffffff'),
            'fg':            getattr(self, 'chart_fg_color', '#000000'),
            'plot_bg':       getattr(self, 'plot_bg_color',  '#ffffff'),
            'border_top':    self.border_top.isChecked(),
            'border_bottom': self.border_bottom.isChecked(),
            'border_left':   self.border_left.isChecked(),
            'border_right':  self.border_right.isChecked(),
            '3d_elev':       self.view3d_elev_spin.value() if hasattr(self, 'view3d_elev_spin') else 30,
            '3d_azim':       self.view3d_azim_spin.value() if hasattr(self, 'view3d_azim_spin') else -60,
        }
        self.subplot_grid_opts[idx] = {
            'enabled':       self.grid_check.isChecked(),
            'color':         getattr(self, 'grid_color',       '#cccccc'),
            'ls':            self.grid_linestyle.currentText(),
            'lw':            self.grid_linewidth.value(),
            'alpha':         self.grid_alpha.value(),
            'minor_enabled': self.minor_grid_check.isChecked(),
            'minor_color':   getattr(self, 'minor_grid_color', '#e8e8e8'),
            'minor_ls':      self.minor_grid_linestyle.currentText(),
            'minor_lw':      self.minor_grid_linewidth.value(),
            'minor_alpha':   self.minor_grid_alpha.value(),
        }

    def _load_canvas_grid_opts(self, idx):
        """Load subplot_canvas_opts[idx] / subplot_grid_opts[idx] → widgets."""
        if not all(hasattr(self, a) for a in ('border_top', 'grid_check', 'grid_linestyle')):
            return
        co = self.subplot_canvas_opts.get(idx, self._default_canvas_opts())
        go = self.subplot_grid_opts.get(idx, self._default_grid_opts())
        _SW = 'background-color:{};border:1px solid #888;border-radius:2px;'
        # Canvas colors
        for attr, key in [('chart_bg_color', 'bg'), ('chart_fg_color', 'fg'),
                           ('plot_bg_color',  'plot_bg')]:
            val = co.get(key, getattr(self, attr, '#ffffff'))
            setattr(self, attr, val)
            sw = getattr(self, attr + '_swatch', None)
            if sw:
                sw.setStyleSheet(_SW.format(val))
        # Border checkboxes
        for w, key in [(self.border_top,    'border_top'),
                       (self.border_bottom, 'border_bottom'),
                       (self.border_left,   'border_left'),
                       (self.border_right,  'border_right')]:
            w.blockSignals(True); w.setChecked(co.get(key, True)); w.blockSignals(False)
        # Major grid
        self.grid_check.blockSignals(True)
        self.grid_check.setChecked(go.get('enabled', True))
        self.grid_check.blockSignals(False)
        val = go.get('color', '#cccccc')
        self.grid_color = val
        if hasattr(self, 'grid_color_sw'):
            self.grid_color_sw.setStyleSheet(_SW.format(val))
        self.grid_linestyle.blockSignals(True)
        i = self.grid_linestyle.findText(go.get('ls', '--'))
        if i >= 0: self.grid_linestyle.setCurrentIndex(i)
        self.grid_linestyle.blockSignals(False)
        self.grid_linewidth.blockSignals(True)
        self.grid_linewidth.setValue(go.get('lw', 0.5))
        self.grid_linewidth.blockSignals(False)
        self.grid_alpha.blockSignals(True)
        self.grid_alpha.setValue(go.get('alpha', 0.4))
        self.grid_alpha.blockSignals(False)
        # Minor grid
        self.minor_grid_check.blockSignals(True)
        self.minor_grid_check.setChecked(go.get('minor_enabled', False))
        self.minor_grid_check.blockSignals(False)
        val = go.get('minor_color', '#e8e8e8')
        self.minor_grid_color = val
        if hasattr(self, 'minor_grid_color_sw'):
            self.minor_grid_color_sw.setStyleSheet(_SW.format(val))
        self.minor_grid_linestyle.blockSignals(True)
        i = self.minor_grid_linestyle.findText(go.get('minor_ls', ':'))
        if i >= 0: self.minor_grid_linestyle.setCurrentIndex(i)
        self.minor_grid_linestyle.blockSignals(False)
        self.minor_grid_linewidth.blockSignals(True)
        self.minor_grid_linewidth.setValue(go.get('minor_lw', 0.3))
        self.minor_grid_linewidth.blockSignals(False)
        self.minor_grid_alpha.blockSignals(True)
        self.minor_grid_alpha.setValue(go.get('minor_alpha', 0.2))
        self.minor_grid_alpha.blockSignals(False)
        # 3D view angles
        if hasattr(self, 'view3d_elev_spin'):
            for sl, sp, key, default in [
                (self.view3d_elev_slider, self.view3d_elev_spin, '3d_elev',  30),
                (self.view3d_azim_slider, self.view3d_azim_spin, '3d_azim', -60),
            ]:
                val = co.get(key, default)
                sl.blockSignals(True); sp.blockSignals(True)
                sl.setValue(val);       sp.setValue(val)
                sl.blockSignals(False); sp.blockSignals(False)

    def _on_layout_sp_changed(self, idx):
        """Layout tab subplot selector changed: save old subplot, load new one."""
        if idx < 0:
            return
        old_idx = self.sp_active.currentIndex() if hasattr(self, 'sp_active') else 0
        if old_idx >= 0 and old_idx != idx:
            self._save_canvas_grid_opts(old_idx)
        # Sync all subplot selectors silently
        for combo_attr in ('sp_active', 'series_sp_active', 'ann_sp_active',
                           'series_curve_sp_active', 'global_sp_active'):
            combo = getattr(self, combo_attr, None)
            if combo is not None:
                combo.blockSignals(True)
                combo.setCurrentIndex(idx)
                combo.blockSignals(False)
        self._load_canvas_grid_opts(idx)
        self.update_preview()

    # ── Per-series option fields ──────────────────────────────────────────────
    # Each entry: (widget_attr, storage_key, default_value, widget_kind)
    # widget_kind: 'spin' | 'dbl' | 'check' | 'combo'
    # Only per-series visual params live here (Series tab groups).
    # Chart-mode params (bar_stacked, hist_bins, etc.) are now per-subplot
    # via subplot_chart_opts / _save_chart_opts / _load_chart_opts.
    _SERIES_OPTION_FIELDS = [
        # Line (per-series visual) — linestyle/lw/marker/markersize from Per-Curve
        ('line_drawstyle',          'line_drawstyle',   'default', 'combo'),
        # Scatter (per-series visual) — marker from Per-Curve
        ('scatter_size',            'sc_size',          20,        'spin'),
        ('scatter_alpha',           'sc_alpha',         0.7,       'dbl'),
        ('scatter_edgecolor',       'sc_edgecolor',     'none',    'combo'),
        ('scatter_lw',              'sc_lw',            0.5,       'dbl'),
        ('scatter_colorby_check',   'sc_colorby',       False,     'check'),
        ('scatter_cmap_combo',      'sc_cmap',          'viridis', 'combo'),
        # Bar (per-series visual only; stacked/horizontal saved at chart level)
        ('bar_width',               'bar_width',        0.8,       'dbl'),
        ('bar_alpha',               'bar_alpha',        1.0,       'dbl'),
        ('bar_edgecolor',           'bar_edgecolor',    'none',    'combo'),
        ('bar_edge_lw',             'bar_edge_lw',      0.5,       'dbl'),
        ('bar_colorbyval',          'bar_colorbyval',   False,     'check'),
        # Histogram (per-series visual only; bins/density/etc. saved at chart level)
        ('hist_alpha',              'hist_alpha',       0.7,       'dbl'),
        ('hist_edgecolor',          'hist_edgecolor',   'white',   'combo'),
        # Errorbar (per-series visual) — marker/linewidth from Per-Curve
        ('err_capsize',             'err_capsize',      4,         'spin'),
        ('err_capthick',            'err_capthick',     1.5,       'dbl'),
        ('err_elinewidth',          'err_elinewidth',   1.5,       'dbl'),
        ('err_barsabove',           'err_barsabove',    False,     'check'),
        # Area (per-series visual only; stacked/baseline saved at chart level)
        ('area_alpha',              'area_alpha',       0.4,       'dbl'),
        ('area_lw',                 'area_lw',          0.8,       'dbl'),
        ('area_showline',           'area_showline',    True,      'check'),
        # Fill Between (per-series visual; Y2 column saved via combo_fill_y2)
        ('fill_between_alpha',      'fill_between_alpha',   0.4,   'dbl'),
        ('fill_between_lw',         'fill_between_lw',      0.8,   'dbl'),
        ('fill_between_showline',   'fill_between_showline', True,  'check'),
        # Step (per-series visual only; where saved at chart level) — lw from Per-Curve
        ('step_fill',               'step_fill',        False,     'check'),
        ('step_fill_alpha',         'step_fill_alpha',  0.2,       'dbl'),
        # Stem — marker/lw/markersize all from Per-Curve; no type-specific opts
        # Bubble (per-series visual) — marker from Per-Curve
        ('bubble_scale',            'bubble_scale',     200.0,     'dbl'),
        ('bubble_alpha',            'bubble_alpha',     0.6,       'dbl'),
        ('bubble_edgecolor',        'bubble_edgecolor', 'none',    'combo'),
        # Polar (per-series visual) — linestyle/lw/marker from Per-Curve
        ('polar_fill',              'pol_fill',         False,     'check'),
        ('polar_fill_alpha',        'pol_fill_alpha',   0.2,       'dbl'),
        # Radar (per-series visual only; gridlevels saved at chart level) — lw from Per-Curve
        ('radar_fill',              'rad_fill',         True,      'check'),
        ('radar_fill_alpha',        'rad_fill_alpha',   0.25,      'dbl'),
        # ECDF (per-series visual only; complementary saved at chart level) — lw from Per-Curve
        ('ecdf_markers',            'ecdf_markers',     False,     'check'),
        ('ecdf_alpha',              'ecdf_alpha',       1.0,       'dbl'),
        # Quiver params are chart-mode — saved at chart level, not per-series
    ]

    def _series_opts_key(self, row):
        """Return the curve_styles label for a series table row, or None."""
        lbl_item = self.series_table.item(row, 2)
        if lbl_item and lbl_item.text():
            return lbl_item.text()
        ycb = self.series_table.cellWidget(row, 1)
        return ycb.currentText() if ycb else None

    def _save_series_options(self):
        """Persist the current option-group widget values into curve_styles for
        whichever series is currently selected in the Per-Curve combo (curve_select).
        The Series tab is self-contained — no dependency on the Data tab table.

        IMPORTANT: always ends with update_preview() so the chart reflects the
        new values.  Some option widgets (e.g. radar_fill) also have a direct
        stateChanged→update_preview connection that fires *before* this method
        (Qt delivers signals in connection order).  Without the call here the
        chart would render with the old stored value and only update on the next
        external event, making the checkbox appear inverted."""
        if getattr(self, '_loading_series_options', False):
            return
        cs = getattr(self, 'curve_select', None)
        label = cs.currentText() if cs else None
        if not label:
            return
        entry = self.curve_styles.setdefault(label, {})
        opts = entry.setdefault('opts', {})
        for attr, key, _default, kind in self._SERIES_OPTION_FIELDS:
            w = getattr(self, attr, None)
            if w is None:
                continue
            if kind == 'spin':
                opts[key] = w.value()
            elif kind == 'dbl':
                opts[key] = w.value()
            elif kind == 'check':
                opts[key] = w.isChecked()
            elif kind == 'combo':
                opts[key] = w.currentText()
            elif kind == 'color':
                # w is the hex string stored directly on self (not a Qt widget)
                opts[key] = w if isinstance(w, str) else _default
        # Redraw *after* saving so the chart always reflects the current widget
        # state, not the stale stored value from the earlier direct signal.
        if hasattr(self, 'datasets'):
            self.update_preview()

    def _load_series_options_by_label(self, label):
        """Push stored per-series option values into the option-group widgets for
        the given series label.  The Series tab calls this directly; the Data tab
        wrapper (_load_series_options) resolves a row to a label first."""
        entry = self.curve_styles.setdefault(label, {}) if label else {}
        stored = entry.get('opts', {}) if label else {}
        opts = {key: stored.get(key, default)
                for _, key, default, _ in self._SERIES_OPTION_FIELDS}
        if label:
            entry['opts'] = opts  # persist so plot_engine always finds full opts

        self._loading_series_options = True
        try:
            for attr, key, default, kind in self._SERIES_OPTION_FIELDS:
                w = getattr(self, attr, None)
                if w is None:
                    continue
                val = opts.get(key, default)
                if kind == 'color':
                    setattr(self, attr, val)
                    btn = getattr(self, attr + '_btn', None)
                    if btn:
                        btn.setStyleSheet(f'background-color:{val};border:1px solid #888;')
                    continue
                w.blockSignals(True)
                try:
                    if kind in ('spin', 'dbl'):
                        w.setValue(val)
                    elif kind == 'check':
                        w.setChecked(bool(val))
                    elif kind == 'combo':
                        i = w.findText(str(val))
                        if i >= 0:
                            w.setCurrentIndex(i)
                finally:
                    w.blockSignals(False)
        finally:
            self._loading_series_options = False

    def _load_series_options(self, row):
        """Row-based wrapper — resolves label from the series table then delegates."""
        label = self._series_opts_key(row)
        self._load_series_options_by_label(label)

    def _connect_series_option_signals(self):
        """Connect every option-group widget to _save_series_options so that any
        change is immediately persisted to the selected series.  Called once after
        all tab builders have run (end of __init__)."""
        for attr, _key, _default, kind in self._SERIES_OPTION_FIELDS:
            w = getattr(self, attr, None)
            if w is None:
                continue
            if kind in ('spin', 'dbl'):
                w.valueChanged.connect(self._save_series_options)
            elif kind == 'check':
                w.stateChanged.connect(self._save_series_options)
            elif kind == 'combo':
                w.currentTextChanged.connect(self._save_series_options)
            elif kind == 'color':
                # attr is a hex string on self; the button is at attr + '_btn'
                btn = getattr(self, attr + '_btn', None)
                if btn:
                    btn.clicked.connect(self._save_series_options)

    def _on_cell_widget_focused(self, old_widget, new_widget):
        """Called whenever application focus changes.  If the newly focused widget
        is a cell widget embedded inside the series table, select that row so that
        _save_series_options always targets the correct series."""
        if new_widget is None:
            return
        if getattr(self, '_loading_series_options', False):
            return
        if not hasattr(self, 'series_table'):
            return
        for r in range(self.series_table.rowCount()):
            if self.series_table.isRowHidden(r):
                continue
            for c in range(self.series_table.columnCount()):
                if self.series_table.cellWidget(r, c) is new_widget:
                    self.series_table.selectRow(r)
                    return

    def _on_series_selection_changed(self):
        """Series table row selected — update the selected-series label, load that
        series' stored option values into the option-group widgets, sync the hidden
        chart_type_combo and option group visibility.
        When no visible row is selected, hide all option groups.
        """
        if not hasattr(self, 'chart_type_combo'):
            return
        # Only consider visible (non-hidden) rows — hidden rows from other subplots
        # can remain in Qt's selection model after setRowHidden.
        selected_rows = set(
            idx.row() for idx in self.series_table.selectedIndexes()
            if not self.series_table.isRowHidden(idx.row())
        )
        lbl_widget = getattr(self, '_selected_series_label', None)
        if not selected_rows:
            if lbl_widget:
                lbl_widget.setText('▶  No series selected')
                lbl_widget.setStyleSheet('font-weight:bold; color:#aaa; font-size:11px; padding:2px 0;')
            if hasattr(self, 'hist_group'):
                # Data tab chart-mode groups
                for grp in (self.bar_group, self.hist_group, self.heat_group,
                            self.pie_group, self.area_group, self.fill_between_group,
                            self.violin_group, self.boxplot_group, self.step_group,
                            self.stem_group, self.waterfall_group, self.hist2d_group,
                            self.hexbin_group, self.radar_group, self.ecdf_group,
                            self.quiver_group, self.barbs_group, self.streamplot_group):
                    grp.setVisible(False)
                if hasattr(self, 'tri_group'):
                    self.tri_group.setVisible(False)
                # Series tab per-series groups
                for _attr in ('st_line_group','st_scatter_group','st_bar_group',
                              'st_hist_group','st_err_group','st_area_group',
                              'st_fill_between_group','st_step_group','st_stem_group',
                              'st_bubble_group','st_polar_group','st_radar_group',
                              'st_ecdf_group'):
                    _g = getattr(self, _attr, None)
                    if _g: _g.setVisible(False)
            if hasattr(self, '_combo_z_widget'):        self._combo_z_widget.setVisible(False)
            if hasattr(self, '_combo_err_widget'):      self._combo_err_widget.setVisible(False)
            if hasattr(self, '_combo_fill_y2_widget'):  self._combo_fill_y2_widget.setVisible(False)
            return
        row = min(selected_rows)
        # Update the selected-series label
        lbl_item = self.series_table.item(row, 2)
        series_name = lbl_item.text() if lbl_item and lbl_item.text() else f'Series {row+1}'
        if lbl_widget:
            lbl_widget.setText(f'▶  {series_name}')
            lbl_widget.setStyleSheet('font-weight:bold; color:#1a6fc4; font-size:11px; padding:2px 0;')
        type_cb = self.series_table.cellWidget(row, 3)
        if not type_cb:
            return
        ct = type_cb.currentText()
        # Sync hidden chart_type_combo and option group visibility
        self._sync_combo_from_type(ct)
        # Sync plot_mode_combo silently — must NOT fire _on_plot_mode_changed
        if hasattr(self, 'plot_mode_combo'):
            mode = TYPE_TO_PLOT_MODE.get(ct, 'Standard')
            self.plot_mode_combo.blockSignals(True)
            i = self.plot_mode_combo.findText(mode)
            if i >= 0:
                self.plot_mode_combo.setCurrentIndex(i)
            self.plot_mode_combo.blockSignals(False)
        # Series type options are driven by curve_select on the Series tab, not
        # by data-tab row selection — see load_curve_style / _save_series_options.

    def _on_series_label_double_click(self, item):
        """Explicitly start in-place editing when the user double-clicks the
        Label column (col 2) in the series table.  This is a belt-and-suspenders
        fix for PyQt6 environments where the default DoubleClicked edit trigger
        is not reliably firing for items inside a QScrollArea."""
        if item is not None and item.column() == 2:
            self.series_table.editItem(item)

    def _sync_combo_from_type(self, ct):
        """Sync the hidden chart_type_combo and option groups to the given type.
        Called whenever a series row's Type cell changes or a row is selected.
        """
        if not hasattr(self, 'chart_type_combo'):
            return
        from ui.tab_builders import WHOLE_CHART_TYPES
        self.chart_type_combo.blockSignals(True)
        i = self.chart_type_combo.findText(ct)
        if i >= 0:
            self.chart_type_combo.setCurrentIndex(i)
        self.chart_type_combo.blockSignals(False)
        self._update_option_group_visibility(ct)
        # Keep subplot_chart_types correct for whole-chart projections
        if ct in WHOLE_CHART_TYPES and hasattr(self, 'series_sp_active'):
            n = self.subplot_rows * self.subplot_cols
            active_sp = (self.series_sp_active.currentIndex() + 1) if n > 1 else 1
            self.subplot_chart_types[active_sp - 1] = ct

    def _on_series_row_type_changed(self, ct):
        """A Type combo inside the series table was changed directly by the user.
        Sync combos/option-group visibility for the new type.  Only update the
        Series tab option widgets if the changed row matches curve_select — the
        Series tab is self-contained around curve_select and we must not push
        a different series' opts into the widgets while curve_select shows another.
        """
        self._sync_combo_from_type(ct)
        selected_rows = set(idx.row() for idx in self.series_table.selectedIndexes())
        if selected_rows:
            row = min(selected_rows)
            changed_label = self._series_opts_key(row)
            cs = getattr(self, 'curve_select', None)
            if cs and cs.currentText() == changed_label:
                self._load_series_options_by_label(changed_label)
        if hasattr(self, 'datasets'):
            self.update_preview()
