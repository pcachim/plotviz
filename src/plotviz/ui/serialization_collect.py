"""
Copyright (c) 2026 Paulo Cachim
ui/serialization_collect.py  –  plotviz
Collect UI widget state into dicts for save/serialization.
"""


class SerializationCollectMixin:
    def _collect_settings(self):
        """Gather all UI settings into a JSON-serialisable dict.
        Series, column assignments and dataset references are NOT stored here —
        they live in series.json / data.json inside the project archive."""
        def _rb_val(group):
            for btn in group.buttons():
                if btn.isChecked():
                    return btn.property('scale_value')
            return 'linear'

        s = {}
        # Format header
        s['_app']     = 'plotviz'
        s['_version'] = '1.2'  # 1.1 added tick/formatter fields; 1.2 adds palette + color_locked

        s['chart_type'] = self.chart_type_combo.currentText()

        # Title (global – stored in style tab, not per-subplot)
        s['title_show']   = self.title_check.isChecked()
        s['title_text']   = self.title_input.text()
        s['title_font']   = self.title_font.currentText()
        s['title_size']   = self.title_size.value()
        s['title_color']  = self.title_color

        # Per-subplot axes (all axes customisation lives in subplot dicts)
        def _ser(d): return {str(k): v for k, v in d.items()}
        s['sp_titles']             = _ser(self.sp_titles)
        s['subplot_title_show']    = _ser(self.subplot_title_show)
        s['subplot_title_font']    = _ser(self.subplot_title_font)
        s['subplot_title_size']    = _ser(self.subplot_title_size)
        s['subplot_title_color']   = _ser(self.subplot_title_color)
        s['title_x']      = self.title_x.value() if hasattr(self, 'title_x') else 0.5
        s['title_y']      = self.title_y.value() if hasattr(self, 'title_y') else 0.97
        s['sp_hspace']    = self.sp_hspace.value() if hasattr(self, 'sp_hspace') else 0.35
        s['sp_wspace']    = self.sp_wspace.value() if hasattr(self, 'sp_wspace') else 0.35
        s['subplot_xlabels']       = _ser(self.subplot_xlabels)
        s['subplot_xlabel_show']   = _ser(self.subplot_xlabel_show)
        s['subplot_ylabels']       = _ser(self.subplot_ylabels)
        s['subplot_ylabel_show']   = _ser(self.subplot_ylabel_show)
        s['subplot_y2labels']      = _ser(self.subplot_y2labels)
        s['subplot_y2label_show']  = _ser(self.subplot_y2label_show)
        s['subplot_legends']       = _ser(self.subplot_legends)
        s['subplot_legend_locs']   = _ser(self.subplot_legend_locs)
        s['subplot_xlims']         = _ser(self.subplot_xlims)
        s['subplot_ylims']         = _ser(self.subplot_ylims)
        s['subplot_y2lims']        = _ser(self.subplot_y2lims)
        s['subplot_xscales']       = _ser(self.subplot_xscales)
        s['subplot_yscales']       = _ser(self.subplot_yscales)
        s['subplot_xtick_sizes']   = _ser(self.subplot_xtick_sizes)
        s['subplot_ytick_sizes']   = _ser(self.subplot_ytick_sizes)
        s['subplot_xtick_dir']     = _ser(self.subplot_xtick_dir)
        s['subplot_ytick_dir']     = _ser(self.subplot_ytick_dir)
        s['subplot_xtick_minor']   = _ser(self.subplot_xtick_minor)
        s['subplot_ytick_minor']   = _ser(self.subplot_ytick_minor)
        s['subplot_xtick_rotation']= _ser(self.subplot_xtick_rotation)
        s['subplot_ytick_rotation']= _ser(self.subplot_ytick_rotation)
        s['subplot_xtick_step']    = _ser(self.subplot_xtick_step)
        s['subplot_ytick_step']    = _ser(self.subplot_ytick_step)
        s['subplot_x_formatter']   = _ser(self.subplot_x_formatter)
        s['subplot_y_formatter']   = _ser(self.subplot_y_formatter)
        s['subplot_xticks_show']   = _ser(self.subplot_xticks_show)
        s['subplot_yticks_show']   = _ser(self.subplot_yticks_show)
        s['subplot_ann_visible']   = _ser(self.subplot_ann_visible)

        # Axis label fonts/colors (global – same for all subplots, stored in Axes tab)
        s['xlabel_font']  = self.xlabel_font.currentText()
        s['xlabel_size']  = self.xlabel_size.value()
        s['xlabel_color'] = self.xlabel_color
        s['ylabel_font']  = self.ylabel_font.currentText()
        s['ylabel_size']  = self.ylabel_size.value()
        s['ylabel_color'] = self.ylabel_color
        s['y2label_font'] = self.y2label_font.currentText()
        s['y2label_size'] = self.y2label_size.value()
        s['y2label_color']= self.y2label_color

        # Style
        s['color_palette']  = getattr(self, '_color_palette', 'Matplotlib')
        s['preset']         = self.preset_combo.currentText()
        s['chart_bg_color'] = self.chart_bg_color
        s['chart_fg_color'] = self.chart_fg_color
        s['plot_bg_color']  = self.plot_bg_color
        s['border_top']     = self.border_top.isChecked()
        s['border_bottom']  = self.border_bottom.isChecked()
        s['border_left']    = self.border_left.isChecked()
        s['border_right']   = self.border_right.isChecked()
        s['curve_styles']   = self.curve_styles

        # Figure size
        s['fig_preset']  = self.fig_preset_combo.currentText()
        s['fig_unit']    = self.fig_unit.currentText()
        s['fig_width']   = self.fig_width.value()
        s['fig_height']  = self.fig_height.value()
        s['fig_left']    = self.fig_left.value()
        s['fig_right']   = self.fig_right.value()
        s['fig_bottom']  = self.fig_bottom.value()
        s['fig_top']     = self.fig_top.value()

        # Grid
        s['grid_on']              = self.grid_check.isChecked()
        s['grid_color']           = self.grid_color
        s['grid_linestyle']       = self.grid_linestyle.currentText()
        s['grid_linewidth']       = self.grid_linewidth.value()
        s['grid_alpha']           = self.grid_alpha.value()
        s['minor_grid_on']        = self.minor_grid_check.isChecked()
        s['minor_grid_color']     = self.minor_grid_color
        s['minor_grid_linestyle'] = self.minor_grid_linestyle.currentText()
        s['minor_grid_linewidth'] = self.minor_grid_linewidth.value()
        s['minor_grid_alpha']     = self.minor_grid_alpha.value()

        s['dpi']        = self.dpi_spin.value()

        # Fit curve style
        s['fit_color']     = self.fit_color
        s['fit_linestyle'] = self.fit_ls_combo.currentText()
        s['fit_linewidth'] = self.fit_lw_spin.value()
        s['fit_ci_index']  = self.fit_ci_combo.currentIndex()
        s['fit_pi_index']  = self.fit_pi_combo.currentIndex()
        s['fit_ci_alpha']  = self.fit_ci_alpha_spin.value()

        # Fit results (JSON-serializable subset — func is reconstructed from model name)
        if hasattr(self, '_last_fit') and self._last_fit is not None:
            fit = self._last_fit
            s['fit_result'] = {
                'model':    fit.get('model', ''),
                'eq_str':   fit.get('eq_str', ''),
                'r2':       float(fit['r2']) if fit.get('r2') is not None else None,
                'xc':       fit.get('xc', ''),
                'yc':       fit.get('yc', ''),
                'lbl':      fit.get('lbl', ''),
                'popt':     [float(v) for v in fit['popt']] if fit.get('popt') is not None else [],
                'pcov':     [[float(v) for v in row] for row in fit['pcov']] if fit.get('pcov') is not None else [],
                'xd':       [float(v) for v in fit['xd']] if fit.get('xd') is not None else [],
                'yd':       [float(v) for v in fit['yd']] if fit.get('yd') is not None else [],
                'stats':    fit.get('stats', {}),
            }
        else:
            s['fit_result'] = None

        # Subplots layout
        s['subplot_rows']   = self.subplot_rows
        s['subplot_cols']   = self.subplot_cols
        s['subplot_mosaic'] = getattr(self, '_subplot_mosaic', None)
        s['sp_sharex']      = self.sp_sharex.isChecked()
        s['sp_sharey']      = self.sp_sharey.isChecked()

        # Chart-type specific
        s['hist_bins']           = self.hist_bins.value()
        s['hist_density']        = self.hist_density.isChecked()
        s['bar_width']           = self.bar_width.value()
        s['bar_stacked']         = self.bar_stacked.isChecked()
        s['bar_horizontal']      = self.bar_horizontal.isChecked()
        s['scatter_size']        = self.scatter_size.value()
        s['scatter_alpha']       = self.scatter_alpha.value()
        s['err_capsize']         = self.err_capsize.value()
        s['cmap']                = self.cmap_combo.currentText()
        s['contour_levels']      = self.contour_levels.value()
        s['heat_colorbar']       = self.heat_colorbar.isChecked()
        s['pie_autopct']         = self.pie_autopct.isChecked()
        s['pie_shadow']          = self.pie_shadow.isChecked()
        s['area_alpha']          = self.area_alpha.value()
        s['area_stacked']        = self.area_stacked.isChecked()
        s['violin_show_means']   = self.violin_show_means.isChecked()
        s['violin_show_medians'] = self.violin_show_medians.isChecked()

        # Default annotation style (applied to new annotations; not per-annotation)
        s['ann_fontcolor']  = getattr(self, 'ann_fontcolor',  '#000000')
        s['ann_fontsize']   = self.ann_fontsize.value()
        s['ann_font']       = self.ann_font.currentText()
        s['ann_bgcolor']    = getattr(self, 'ann_bgcolor',    '#ffffcc')
        s['ann_bg_alpha']   = self.ann_bg_alpha.value()
        s['ann_edgecolor']  = getattr(self, 'ann_edgecolor',  '#aaaaaa')

        # Line / default series style
        s['line_default_style']    = self.line_default_style.currentText()
        s['line_default_marker']   = self.line_default_marker.currentText()
        s['line_default_lw']       = self.line_default_lw.value()
        s['line_default_markersize'] = self.line_default_markersize.value()

        s['_version'] = '1.3'   # 1.3 adds ann style + line defaults
        return s

    def _collect_series_meta(self):
        """Collect series table + subplot assignments into a separate dict."""
        series_data = []
        for row in range(self.series_table.rowCount()):
            xcb = self.series_table.cellWidget(row, 0)
            ycb = self.series_table.cellWidget(row, 1)
            lbl = self.series_table.item(row, 2)
            type_cb = self.series_table.cellWidget(row, 3)
            plot_spin = self.series_table.cellWidget(row, 4)
            y2_item = self.series_table.item(row, 5)
            series_data.append({
                'x_col':       xcb.currentText() if xcb else '',
                'y_col':       ycb.currentText() if ycb else '',
                'label':       lbl.text() if lbl else f'Series {row+1}',
                'series_type': type_cb.currentText() if type_cb else 'Line',
                'plot_num':    plot_spin.value() if plot_spin else 1,
                'y2':          y2_item.checkState() == Qt.CheckState.Checked if y2_item else False,
            })
        return {
            'series':               series_data,
            'z_col':                self.combo_z.currentText(),
            'err_col':              self.combo_err.currentText(),
            'subplot_chart_types':  {str(k): v for k, v in self.subplot_chart_types.items()},
            'subplot_legend_locs':  {str(k): v for k, v in self.subplot_legend_locs.items()},
        }

