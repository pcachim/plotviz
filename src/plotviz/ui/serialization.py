"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.

ui/serialization.py  –  plotviz
Mixin providing settings collection/apply, series meta, and project save/load.
"""
import json, zipfile, os, tempfile
from ui.helpers import _get_dir, _remember_dir
import numpy as np
from PyQt6.QtWidgets import (
    QFileDialog, QMessageBox, QComboBox, QTableWidgetItem, QSpinBox,
)
from PyQt6.QtCore import Qt


class SerializationMixin:
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
        s['title_font']     = self.title_font.currentText()
        s['title_size']     = self.title_size.value()
        s['title_color']    = self.title_color
        s['title_rotation'] = self.title_rotation.value()
        s['title_ha']       = self.title_ha.currentText()

        # Per-subplot axes (all axes customisation lives in subplot dicts)
        def _ser(d): return {str(k): v for k, v in d.items()}
        s['sp_titles']             = _ser(self.sp_titles)
        s['subplot_title_show']    = _ser(self.subplot_title_show)
        s['subplot_title_font']     = _ser(self.subplot_title_font)
        s['subplot_title_size']     = _ser(self.subplot_title_size)
        s['subplot_title_color']    = _ser(self.subplot_title_color)
        s['subplot_title_pad']      = _ser(self.subplot_title_pad)
        s['subplot_title_rotation'] = _ser(self.subplot_title_rotation)
        s['subplot_title_ha']       = _ser(self.subplot_title_ha)
        s['title_x']         = self.title_x.value() if hasattr(self, 'title_x') else 0.5
        s['title_y']         = self.title_y.value() if hasattr(self, 'title_y') else 0.97
        s['title_pos_format'] = 'physical'   # v>=2.5.8: title_x/y in fig_unit, not fractions
        s['sp_hspace']    = self.sp_hspace.value() if hasattr(self, 'sp_hspace') else 0.35
        s['sp_wspace']    = self.sp_wspace.value() if hasattr(self, 'sp_wspace') else 0.35
        s['subplot_xlabels']       = _ser(self.subplot_xlabels)
        s['subplot_xlabel_show']   = _ser(self.subplot_xlabel_show)
        s['subplot_ylabels']       = _ser(self.subplot_ylabels)
        s['subplot_ylabel_show']   = _ser(self.subplot_ylabel_show)
        s['subplot_y2labels']      = _ser(self.subplot_y2labels)
        s['subplot_y2label_show']  = _ser(self.subplot_y2label_show)
        s['subplot_legends']          = _ser(self.subplot_legends)
        s['subplot_legend_locs']      = _ser(self.subplot_legend_locs)
        s['subplot_legend_x']         = _ser(self.subplot_legend_x)
        s['subplot_legend_y']         = _ser(self.subplot_legend_y)
        s['subplot_legend_fontsize']  = _ser(self.subplot_legend_fontsize)
        s['subplot_legend_ncols']     = _ser(self.subplot_legend_ncols)
        s['subplot_legend_frameon']   = _ser(self.subplot_legend_frameon)
        s['subplot_legend_color']     = _ser(self.subplot_legend_color)
        s['subplot_legend_facecolor'] = _ser(self.subplot_legend_facecolor)
        s['subplot_legend_alpha']     = _ser(self.subplot_legend_alpha)
        s['subplot_legend_edgecolor'] = _ser(self.subplot_legend_edgecolor)
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
        s['subplot_equal_aspect']  = _ser(self.subplot_equal_aspect)
        s['subplot_xaxis_pos']     = _ser(self.subplot_xaxis_pos)
        s['subplot_yaxis_pos']     = _ser(self.subplot_yaxis_pos)
        s['subplot_ann_visible']   = _ser(self.subplot_ann_visible)

        # Axis label fonts/colors (global – same for all subplots, stored in Axes tab)
        s['xlabel_font']  = self.xlabel_font.currentText()
        s['xlabel_size']  = self.xlabel_size.value()
        s['xlabel_color'] = self.xlabel_color
        s['subplot_xlabel_rotation'] = _ser(self.subplot_xlabel_rotation)
        s['subplot_xlabel_labelpad'] = _ser(self.subplot_xlabel_labelpad)
        s['subplot_xlabel_loc']      = _ser(self.subplot_xlabel_loc)
        s['subplot_xlabel_ha']       = _ser(self.subplot_xlabel_ha)
        s['ylabel_font']  = self.ylabel_font.currentText()
        s['ylabel_size']  = self.ylabel_size.value()
        s['ylabel_color'] = self.ylabel_color
        s['subplot_ylabel_rotation'] = _ser(self.subplot_ylabel_rotation)
        s['subplot_ylabel_labelpad'] = _ser(self.subplot_ylabel_labelpad)
        s['subplot_ylabel_loc']      = _ser(self.subplot_ylabel_loc)
        s['subplot_ylabel_ha']       = _ser(self.subplot_ylabel_ha)
        s['y2label_font'] = self.y2label_font.currentText()
        s['y2label_size'] = self.y2label_size.value()
        s['y2label_color']= self.y2label_color
        s['y2label_rotation'] = self.y2label_rotation.value()
        s['y2label_labelpad'] = self.y2label_labelpad.value()
        s['y2label_loc']      = self.y2label_loc.currentText()
        s['y2label_ha']       = self.y2label_ha.currentText()

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
        s['fig_preset']       = self.fig_preset_combo.currentText()
        s['fig_unit']         = self.fig_unit.currentText()
        s['fig_width']        = self.fig_width.value()
        s['fig_height']       = self.fig_height.value()
        s['fig_left']         = self.fig_left.value()
        s['fig_right']        = self.fig_right.value()
        s['fig_bottom']       = self.fig_bottom.value()
        s['fig_top']          = self.fig_top.value()
        s['margin_format']    = 'physical'   # v≥2.5.8: margins in fig_unit, not fractions

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

        # Fit curve style (fit_color/fit_linestyle/fit_linewidth removed in 2.0.0 —
        # fit curves are styled via curve_styles like any other series)
        s['fit_ci_index']  = self.fit_ci_combo.currentIndex()
        s['fit_pi_index']  = self.fit_pi_combo.currentIndex()
        s['fit_ci_alpha']  = self.fit_ci_alpha_spin.value()

        # Fit results (JSON-serializable subset — func is reconstructed from model name)
        _fits_raw = {}
        for _nm, fit in (getattr(self, '_fits', None) or {}).items():
            if fit.get('popt') is not None:
                _fits_raw[_nm] = {
                    'model':  fit.get('model', ''),
                    'eq_str': fit.get('eq_str', ''),
                    'r2':     float(fit['r2']) if fit.get('r2') is not None else None,
                    'xc':     fit.get('xc', ''),
                    'yc':     fit.get('yc', ''),
                    'lbl':    fit.get('lbl', ''),
                    'popt':   [float(v) for v in fit['popt']],
                    'pcov':   [[float(v) for v in row] for row in fit['pcov']] if fit.get('pcov') is not None else [],
                    'xd':     [float(v) for v in fit['xd']] if fit.get('xd') is not None else [],
                    'yd':     [float(v) for v in fit['yd']] if fit.get('yd') is not None else [],
                    'stats':  fit.get('stats', {}),
                    'ci_idx': fit.get('ci_idx', 0),
                    'pi_idx': fit.get('pi_idx', 0),
                }
        s['fits']       = _fits_raw
        s['fit_result'] = None  # legacy sentinel

        # Subplots layout
        s['subplot_rows']   = self.subplot_rows
        s['subplot_cols']   = self.subplot_cols
        s['subplot_mosaic'] = getattr(self, '_subplot_mosaic', None)
        s['sp_sharex']      = self.sp_sharex.isChecked()
        s['sp_sharey']      = self.sp_sharey.isChecked()

        # ── Chart-mode params (apply to entire chart, not per-series) ───────────
        # Bar
        s['bar_stacked']         = self.bar_stacked.isChecked()
        s['bar_horizontal']      = self.bar_horizontal.isChecked()
        # Histogram
        s['hist_bins']           = self.hist_bins.value()
        s['hist_density']        = self.hist_density.isChecked()
        s['hist_cumulative']     = self.hist_cumulative.isChecked()
        s['hist_histtype']       = self.hist_histtype.currentText()
        s['hist_orientation']    = self.hist_orientation.currentText()
        # Heatmap / Contour / 3D
        s['cmap']                = self.cmap_combo.currentText()
        s['contour_levels']      = self.contour_levels.value()
        s['heat_alpha']          = self.heat_alpha.value()
        s['heat_interpolation']  = self.heat_interpolation.currentText()
        s['heat_colorbar']       = self.heat_colorbar.isChecked()
        s['heat_colorbar_shrink'] = self.heat_colorbar_shrink.value() if hasattr(self, 'heat_colorbar_shrink') else 1.0
        s['heat_filled_contour'] = self.heat_filled_contour.isChecked()
        s['heat_contour_lines']  = self.heat_contour_lines.isChecked()
        s['surf_stride']         = self.surf_stride.value()
        s['surf_wireframe']      = self.surf_wireframe.isChecked()
        # Fix 4/5/6: new heat/contour controls
        s['heat_vminmax_enable'] = self.heat_vminmax_enable.isChecked() if hasattr(self, 'heat_vminmax_enable') else False
        s['heat_vmin']           = self.heat_vmin.value()               if hasattr(self, 'heat_vmin')           else 0.0
        s['heat_vmax']           = self.heat_vmax.value()               if hasattr(self, 'heat_vmax')           else 1.0
        s['contour_line_color']  = getattr(self, 'contour_line_color',  '#000000')
        s['contour_line_width']  = self.contour_line_width.value()      if hasattr(self, 'contour_line_width')  else 0.5
        s['contour_levels_explicit'] = self.contour_levels_explicit.text() if hasattr(self, 'contour_levels_explicit') else ''
        # Tricontour
        s['tri_cmap']        = self.tri_cmap_combo.currentText()
        s['tri_levels']      = self.tri_levels.value()
        s['tri_alpha']       = self.tri_alpha.value()
        s['tri_fill_mode']   = self.tri_fill_mode.currentText()
        s['tri_lines']       = self.tri_lines.isChecked()
        s['tri_triplot']     = self.tri_triplot.isChecked()
        s['tri_colorbar']    = self.tri_colorbar.isChecked()
        s['tri_colorbar_shrink'] = self.tri_colorbar_shrink.value() if hasattr(self, 'tri_colorbar_shrink') else 1.0
        # Pie
        s['pie_autopct']         = self.pie_autopct.isChecked()
        s['pie_shadow']          = self.pie_shadow.isChecked()
        s['pie_donut']           = self.pie_donut.isChecked()
        s['pie_explode_first']   = self.pie_explode_first.isChecked()
        s['pie_startangle']      = self.pie_startangle.value()
        s['pie_labeldistance']   = self.pie_labeldistance.value()
        s['pie_pctdistance']     = self.pie_pctdistance.value()
        # Area
        s['area_stacked']        = self.area_stacked.isChecked()
        s['area_baseline']       = self.area_baseline.value()
        # Violin
        s['violin_show_means']   = self.violin_show_means.isChecked()
        s['violin_show_medians'] = self.violin_show_medians.isChecked()
        s['violin_show_extrema'] = self.violin_show_extrema.isChecked()
        s['violin_points']       = self.violin_points.currentText()
        s['violin_bw']           = self.violin_bw.currentText()
        s['violin_vert']         = self.violin_vert.isChecked()
        # Boxplot
        s['box_show_means']      = self.box_show_means.isChecked()
        s['box_show_medians']    = self.box_show_medians.isChecked()
        s['box_notch']           = self.box_notch.isChecked()
        s['box_showfliers']      = self.box_showfliers.isChecked()
        s['box_vert']            = self.box_vert.isChecked()
        s['box_whis']            = self.box_whis.value()
        s['box_alpha']           = self.box_alpha.value()
        # Step
        s['step_where']          = self.step_where.currentText()
        # Stem
        s['stem_baseline']       = self.stem_baseline.value()
        # Waterfall
        s['waterfall_connector'] = self.waterfall_connector.isChecked()
        s['waterfall_width']     = self.waterfall_width.value()
        s['waterfall_alpha']     = self.waterfall_alpha.value()
        s['waterfall_pos_color'] = getattr(self, 'waterfall_pos_color', '#2ecc71')
        s['waterfall_neg_color'] = getattr(self, 'waterfall_neg_color', '#e74c3c')
        # Hist2D
        s['hist2d_bins_x']       = self.hist2d_bins_x.value()
        s['hist2d_bins_y']       = self.hist2d_bins_y.value()
        s['hist2d_alpha']        = self.hist2d_alpha.value()
        s['hist2d_cmap']         = self.hist2d_cmap_combo.currentText()
        s['hist2d_colorbar']     = self.hist2d_colorbar.isChecked()
        s['hist2d_log']          = self.hist2d_log.isChecked()
        # Hexbin
        s['hexbin_gridsize']     = self.hexbin_gridsize.value()
        s['hexbin_alpha']        = self.hexbin_alpha.value()
        s['hexbin_cmap']         = self.hexbin_cmap_combo.currentText()
        s['hexbin_colorbar']     = self.hexbin_colorbar.isChecked()
        s['hexbin_log']          = self.hexbin_log.isChecked()
        # Radar
        s['radar_gridlevels']    = self.radar_gridlevels.value()
        # ECDF
        s['ecdf_complementary']  = self.ecdf_complementary.isChecked()
        # Quiver
        s['quiver_scale']        = self.quiver_scale.value()
        s['quiver_width']        = self.quiver_width.value()
        s['quiver_color_by_mag'] = self.quiver_color_by_mag.isChecked()
        s['quiver_cmap']         = self.quiver_cmap_combo.currentText()
        # Barbs
        s['barbs_length']        = self.barbs_length.value()
        s['barbs_pivot']         = self.barbs_pivot_combo.currentText()
        s['barbs_alpha']         = self.barbs_alpha.value()
        s['barbs_color_by_mag']  = self.barbs_color_by_mag.isChecked()
        s['barbs_cmap']          = self.barbs_cmap_combo.currentText()
        # Streamplot
        s['stream_density']      = self.stream_density.value()
        s['stream_arrowsize']    = self.stream_arrowsize.value()
        s['stream_linewidth']    = self.stream_linewidth.value()
        s['stream_color_by_mag'] = self.stream_color_by_mag.isChecked()
        s['stream_cmap']         = self.stream_cmap_combo.currentText()

        # Default annotation style (applied to new annotations; not per-annotation)
        s['ann_fontcolor']  = getattr(self, 'ann_fontcolor',  '#000000')
        s['ann_fontsize']   = self.ann_fontsize.value()
        s['ann_font']       = self.ann_font.currentText()
        s['ann_bgcolor']    = getattr(self, 'ann_bgcolor',    '#ffffcc')
        s['ann_bg_alpha']   = self.ann_bg_alpha.value()
        s['ann_edgecolor']  = getattr(self, 'ann_edgecolor',  '#aaaaaa')

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
            'fill_y2_col':          self.combo_fill_y2.currentText() if hasattr(self, 'combo_fill_y2') else '(none)',
            'quiver_u_col':         self.quiver_u_combo.currentText() if hasattr(self, 'quiver_u_combo') else '(none)',
            'quiver_v_col':         self.quiver_v_combo.currentText() if hasattr(self, 'quiver_v_combo') else '(none)',
            'barbs_u_col':          self.barbs_u_combo.currentText()  if hasattr(self, 'barbs_u_combo')  else '(none)',
            'barbs_v_col':          self.barbs_v_combo.currentText()  if hasattr(self, 'barbs_v_combo')  else '(none)',
            'stream_u_col':         self.stream_u_combo.currentText() if hasattr(self, 'stream_u_combo') else '(none)',
            'stream_v_col':         self.stream_v_combo.currentText() if hasattr(self, 'stream_v_combo') else '(none)',
            'bubble_size_col':      self.bubble_size_combo.currentText() if hasattr(self, 'bubble_size_combo') else '(uniform)',
            'err_xerr_col':         self.err_xerr_combo.currentText() if hasattr(self, 'err_xerr_combo') else '(none)',
            'subplot_chart_types':  {str(k): v for k, v in self.subplot_chart_types.items()},
            'subplot_plot_modes':   {str(k): v for k, v in self.subplot_plot_modes.items()},
            'subplot_legend_locs':  {str(k): v for k, v in self.subplot_legend_locs.items()},
            'subplot_chart_opts':   {str(k): v for k, v in self.subplot_chart_opts.items()},
        }

    def _apply_settings(self, s):
        """Restore all UI settings from a dict."""
        def _set_rb(group, value):
            for btn in group.buttons():
                if btn.property('scale_value') == value:
                    btn.setChecked(True)
                    return

        self.combo_x.blockSignals(True)
        self.y_list.blockSignals(True)

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

        _SW_CSS = 'background-color:{};border:1px solid #888;border-radius:2px;'

        # Colors (update internal attr + swatch labels if they exist)
        for attr, default, sw in [
            ('chart_bg_color','#ffffff','chart_bg_color_swatch'),
            ('chart_fg_color','#000000','chart_fg_color_swatch'),
            ('plot_bg_color', '#ffffff','plot_bg_color_swatch'),
        ]:
            v = s.get(attr, default)
            setattr(self, attr, v)
            if hasattr(self, sw): getattr(self, sw).setStyleSheet(_SW_CSS.format(v))

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
        if i >= 0:
            self.fig_unit.blockSignals(True)
            self.fig_unit.setCurrentIndex(i)
            self.fig_unit.blockSignals(False)
            # Sync the unit-change helper's "previous unit" tracker and fix ranges
            # so the first interactive switch after load converts from the right unit.
            restored_unit = self.fig_unit.currentText()
            self._prev_fig_unit = restored_unit
            if restored_unit == 'cm':
                self.fig_width.setRange(2, 500); self.fig_height.setRange(2, 500)
                self.fig_width.setDecimals(1);   self.fig_height.setDecimals(1)
                self.fig_width.setSingleStep(0.5); self.fig_height.setSingleStep(0.5)
            elif restored_unit == 'inches':
                self.fig_width.setRange(1, 200); self.fig_height.setRange(1, 200)
                self.fig_width.setDecimals(2);   self.fig_height.setDecimals(2)
                self.fig_width.setSingleStep(0.25); self.fig_height.setSingleStep(0.25)
            elif restored_unit == 'pixels':
                self.fig_width.setRange(50, 20000); self.fig_height.setRange(50, 20000)
                self.fig_width.setDecimals(0);      self.fig_height.setDecimals(0)
                self.fig_width.setSingleStep(10);   self.fig_height.setSingleStep(10)
        self.fig_width.setValue(s.get('fig_width', 20.0))
        self.fig_height.setValue(s.get('fig_height', 15.0))
        i = self.fig_preset_combo.findText(s.get('fig_preset', '20 × 15 cm'))
        if i >= 0:
            self.fig_preset_combo.blockSignals(True)
            self.fig_preset_combo.setCurrentIndex(i)
            self.fig_preset_combo.blockSignals(False)

        # ── Restore margin spinboxes ──────────────────────────────────────────
        # Ranges must match the restored unit and figure dimensions.
        self._update_margin_ranges()

        # Detect old saves (pre-2.5.8) where margins were stored as fractions [0, 1].
        # In that format fig_left ≤ 1 and fig_right ≤ 1; convert to current physical unit.
        _raw_l = s.get('fig_left',   0.10)
        _raw_r = s.get('fig_right',  0.95)
        _raw_b = s.get('fig_bottom', 0.10)
        _raw_t = s.get('fig_top',    0.95)
        if s.get('margin_format') != 'physical':
            # Old format: values are fractions → convert to physical unit
            _ru  = self.fig_unit.currentText()
            _wi, _hi = self._fig_size_in_inches()
            if _ru == 'cm':
                _fw, _fh, _dec = _wi * 2.54, _hi * 2.54, 1
            elif _ru == 'pixels':
                _fw, _fh, _dec = _wi * self.dpi_spin.value(), _hi * self.dpi_spin.value(), 0
            else:
                _fw, _fh, _dec = _wi, _hi, 2
            _raw_l = round(_raw_l * _fw, _dec)
            _raw_r = round(_raw_r * _fw, _dec)
            _raw_b = round(_raw_b * _fh, _dec)
            _raw_t = round(_raw_t * _fh, _dec)
        self.fig_left.setValue(_raw_l)
        self.fig_right.setValue(_raw_r)
        self.fig_bottom.setValue(_raw_b)
        self.fig_top.setValue(_raw_t)

        self.grid_check.setChecked(s.get('grid_on', True))
        self.grid_color = s.get('grid_color','#cccccc')
        self.grid_color_sw.setStyleSheet(_SW_CSS.format(self.grid_color))
        i = self.grid_linestyle.findText(s.get('grid_linestyle','--'))
        if i >= 0: self.grid_linestyle.setCurrentIndex(i)
        self.grid_linewidth.setValue(s.get('grid_linewidth', 0.5))
        self.grid_alpha.setValue(s.get('grid_alpha', 0.4))
        self.minor_grid_check.setChecked(s.get('minor_grid_on', False))
        self.minor_grid_color = s.get('minor_grid_color','#e8e8e8')
        self.minor_grid_color_sw.setStyleSheet(_SW_CSS.format(self.minor_grid_color))
        i = self.minor_grid_linestyle.findText(s.get('minor_grid_linestyle',':'))
        if i >= 0: self.minor_grid_linestyle.setCurrentIndex(i)
        self.minor_grid_linewidth.setValue(s.get('minor_grid_linewidth', 0.3))
        self.minor_grid_alpha.setValue(s.get('minor_grid_alpha', 0.2))

        # Flush color/grid changes into per-subplot caches so the plot engine
        # sees them immediately (e.g. when a color scheme is applied).
        # _apply_settings updates the widget attrs but the render path reads from
        # subplot_canvas_opts / subplot_grid_opts, so those must be kept in sync.
        if hasattr(self, '_save_canvas_grid_opts') and hasattr(self, 'subplot_canvas_opts'):
            idxs = list(self.subplot_canvas_opts.keys()) if self.subplot_canvas_opts else [0]
            for _sp in idxs:
                self._save_canvas_grid_opts(_sp)

        self.dpi_spin.setValue(s.get('dpi', 300))

        # Global title
        self.title_check.setChecked(s.get('title_show', True))
        self.title_input.setText(s.get('title_text', ''))
        i = self.title_font.findText(s.get('title_font', 'sans-serif'))
        if i >= 0: self.title_font.setCurrentIndex(i)
        self.title_size.setValue(s.get('title_size', 14))
        tc = s.get('title_color', '#000000')
        self.title_color = tc
        if hasattr(self, 'title_color_swatch'):
            self.title_color_swatch.setStyleSheet(_SW_CSS.format(tc))
        self.title_rotation.blockSignals(True)
        self.title_rotation.setValue(s.get('title_rotation', 0))
        self.title_rotation.blockSignals(False)
        _i = self.title_ha.findText(s.get('title_ha', 'center'))
        if _i >= 0:
            self.title_ha.blockSignals(True)
            self.title_ha.setCurrentIndex(_i)
            self.title_ha.blockSignals(False)
        i = self.xlabel_font.findText(s.get('xlabel_font','sans-serif'))
        if i >= 0: self.xlabel_font.setCurrentIndex(i)
        self.xlabel_size.setValue(s.get('xlabel_size', 11))
        self.xlabel_color = s.get('xlabel_color','#000000')
        self.xlabel_color_label.setStyleSheet(_SW_CSS.format(self.xlabel_color))
        i = self.ylabel_font.findText(s.get('ylabel_font','sans-serif'))
        if i >= 0: self.ylabel_font.setCurrentIndex(i)
        self.ylabel_size.setValue(s.get('ylabel_size', 11))
        self.ylabel_color = s.get('ylabel_color','#000000')
        self.ylabel_color_label.setStyleSheet(_SW_CSS.format(self.ylabel_color))
        i = self.y2label_font.findText(s.get('y2label_font','sans-serif'))
        if i >= 0: self.y2label_font.setCurrentIndex(i)
        self.y2label_size.setValue(s.get('y2label_size', 11))
        self.y2label_color = s.get('y2label_color','#000000')
        self.y2label_color_label.setStyleSheet(_SW_CSS.format(self.y2label_color))
        self.y2label_rotation.setValue(s.get('y2label_rotation', 90))
        self.y2label_labelpad.setValue(s.get('y2label_labelpad', 4))
        i = self.y2label_loc.findText(s.get('y2label_loc', 'center'))
        if i >= 0: self.y2label_loc.setCurrentIndex(i)
        i = self.y2label_ha.findText(s.get('y2label_ha', 'center'))
        if i >= 0: self.y2label_ha.setCurrentIndex(i)

        # Subplots (layout + appearance only — column assignments come from series.json)
        mosaic = s.get('subplot_mosaic', None)
        self._subplot_mosaic = mosaic
        self.sp_rows.blockSignals(True)
        self.sp_cols.blockSignals(True)
        self.sp_rows.setValue(s.get('subplot_rows', 1))
        self.sp_cols.setValue(s.get('subplot_cols', 1))
        self.sp_rows.blockSignals(False)
        self.sp_cols.blockSignals(False)
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
        self.subplot_xlabel_rotation = _di('subplot_xlabel_rotation', {'0': 0})
        self.subplot_xlabel_labelpad = _di('subplot_xlabel_labelpad', {'0': 4})
        self.subplot_xlabel_loc      = _di('subplot_xlabel_loc',      {'0': 'center'})
        self.subplot_xlabel_ha       = _di('subplot_xlabel_ha',       {'0': 'center'})
        self.subplot_ylabel_rotation = _di('subplot_ylabel_rotation', {'0': 90})
        self.subplot_ylabel_labelpad = _di('subplot_ylabel_labelpad', {'0': 4})
        self.subplot_ylabel_loc      = _di('subplot_ylabel_loc',      {'0': 'center'})
        self.subplot_ylabel_ha       = _di('subplot_ylabel_ha',       {'0': 'center'})
        self.sp_titles             = _di('sp_titles', {'0': ''})
        self.subplot_title_show    = _di('subplot_title_show', {'0': True})
        self.subplot_title_font     = _di('subplot_title_font',    {'0': 'sans-serif'})
        self.subplot_title_size     = _di('subplot_title_size',    {'0': 11})
        self.subplot_title_color    = _di('subplot_title_color',   {'0': '#000000'})
        self.subplot_title_pad      = _di('subplot_title_pad',     {'0': 6})
        self.subplot_title_rotation = _di('subplot_title_rotation',{'0': 0})
        self.subplot_title_ha       = _di('subplot_title_ha',      {'0': 'center'})
        if hasattr(self, 'title_x') and hasattr(self, 'title_y'):
            _raw_tx = float(s.get('title_x', 0.5))
            _raw_ty = float(s['title_y'] if 'title_y' in s else s.get('title_y_offset', 0.97))
            if s.get('title_pos_format') != 'physical':
                # Old format: values are fractions [0,1] — convert to physical units.
                _wi, _hi = self._fig_size_in_inches()
                _ru = self.fig_unit.currentText()
                if _ru == 'cm':
                    _fw, _fh, _dec = _wi * 2.54, _hi * 2.54, 1
                elif _ru == 'pixels':
                    _fw, _fh, _dec = _wi * self.dpi_spin.value(), _hi * self.dpi_spin.value(), 0
                else:
                    _fw, _fh, _dec = _wi, _hi, 2
                _raw_tx = round(_raw_tx * _fw, _dec)
                _raw_ty = round(_raw_ty * _fh, _dec)
            self._update_title_pos_ranges()
            self.title_x.setValue(_raw_tx)
            self.title_y.setValue(_raw_ty)
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
        self.subplot_equal_aspect  = _di('subplot_equal_aspect', {'0': False})
        self.subplot_xaxis_pos     = _di('subplot_xaxis_pos',    {'0': 'bottom'})
        self.subplot_yaxis_pos     = _di('subplot_yaxis_pos',    {'0': 'left'})
        self.subplot_ann_visible   = _di('subplot_ann_visible', {'0': True})
        self.sp_sharex.setChecked(s.get('sp_sharex', False))
        self.sp_sharey.setChecked(s.get('sp_sharey', False))
        # Reload Axes tab widgets for subplot 0
        self.on_active_subplot_changed()

        # Restore per-series fits
        import numpy as _np
        from data.scientific import CurveFitter as _CF
        self._fits = {}
        self._last_fit = None
        _fits_saved = s.get('fits') or {}
        _legacy_fr  = s.get('fit_result')
        if _legacy_fr and _legacy_fr.get('model') and _legacy_fr.get('popt'):
            _nm_leg = _legacy_fr.get('lbl', '') + f" ({_legacy_fr.get('model','')} fit)"
            if _nm_leg not in _fits_saved:
                _fits_saved[_nm_leg] = _legacy_fr
        for _nm, fr in _fits_saved.items():
            if not (fr.get('model') and fr.get('popt')): continue
            try:
                model = fr['model']
                func = _CF.MODELS.get(model)
                popt  = _np.array(fr['popt'])
                pcov  = _np.array(fr['pcov']) if fr.get('pcov') else _np.zeros((len(popt), len(popt)))
                xd    = _np.array(fr['xd'])
                yd    = _np.array(fr['yd']) if fr.get('yd') else _np.zeros_like(xd)
                self._fits[_nm] = dict(model=model, func=func, popt=popt, pcov=pcov,
                    xd=xd, yd=yd, xc=fr.get('xc',''), yc=fr.get('yc',''), lbl=fr.get('lbl',''),
                    eq_str=fr.get('eq_str',''), r2=fr.get('r2'), stats=fr.get('stats',{}),
                    ci_idx=fr.get('ci_idx',0), pi_idx=fr.get('pi_idx',0))
            except Exception: pass
        for _nm in list(self._fits):
            if hasattr(self, '_update_confidence_band_for'):
                self._update_confidence_band_for(_nm)
        if self._fits:
            self._last_fit = next(iter(self._fits.values()))
            if hasattr(self, '_refresh_fit_results_panel'):
                self._refresh_fit_results_panel()
        # CI/PI combo display state
        self.fit_ci_combo.blockSignals(True)
        self.fit_pi_combo.blockSignals(True)
        self.fit_ci_alpha_spin.setValue(s.get('fit_ci_alpha', 0.25))
        self.fit_ci_combo.blockSignals(False)
        self.fit_pi_combo.blockSignals(False)

        # ── Chart-mode params ────────────────────────────────────────────────────
        def _cb(w, key, default): w.setChecked(s.get(key, default))
        def _sp(w, key, default): w.setValue(s.get(key, default))
        def _co(w, key, default):
            # str() guard: legacy files may store combo values as int/float
            i = w.findText(str(s.get(key, default)))
            if i >= 0: w.setCurrentIndex(i)

        # Bar
        _cb(self.bar_stacked,    'bar_stacked',    False)
        _cb(self.bar_horizontal, 'bar_horizontal', False)
        # Histogram
        _sp(self.hist_bins, 'hist_bins', 20)
        _cb(self.hist_density,    'hist_density',    False)
        _cb(self.hist_cumulative, 'hist_cumulative', False)
        _co(self.hist_histtype,   'hist_histtype',   'bar')
        _co(self.hist_orientation,'hist_orientation','vertical')
        # Heatmap / Contour / 3D
        # Bug 10: restore default must match tab_builders initialisation (default='rainbow').
        # Using 'viridis' here caused silently wrong cmap on files saved without a 'cmap' key.
        _co(self.cmap_combo,          'cmap',             'rainbow')
        _sp(self.contour_levels,      'contour_levels',   10)
        _sp(self.heat_alpha,          'heat_alpha',       1.0)
        _co(self.heat_interpolation,  'heat_interpolation','nearest')
        _cb(self.heat_colorbar,       'heat_colorbar',     True)
        if hasattr(self, 'heat_colorbar_shrink'):
            self.heat_colorbar_shrink.blockSignals(True)
            self.heat_colorbar_shrink.setValue(float(s.get('heat_colorbar_shrink', 1.0)))
            self.heat_colorbar_shrink.blockSignals(False)
        if hasattr(self, '_heat_colorbar_size_row'):
            self._heat_colorbar_size_row.setVisible(self.heat_colorbar.isChecked())
        _cb(self.heat_filled_contour, 'heat_filled_contour', True)
        _cb(self.heat_contour_lines,  'heat_contour_lines',  True)
        _sp(self.surf_stride,         'surf_stride',      1)
        _cb(self.surf_wireframe,      'surf_wireframe',   False)
        # Fix 4/5/6: new heat/contour controls
        if hasattr(self, 'heat_vminmax_enable'):
            self.heat_vminmax_enable.blockSignals(True)
            self.heat_vminmax_enable.setChecked(bool(s.get('heat_vminmax_enable', False)))
            self.heat_vminmax_enable.blockSignals(False)
            self.heat_vmin.setEnabled(self.heat_vminmax_enable.isChecked())
            self.heat_vmax.setEnabled(self.heat_vminmax_enable.isChecked())
        if hasattr(self, 'heat_vmin'):
            self.heat_vmin.blockSignals(True)
            self.heat_vmin.setValue(float(s.get('heat_vmin', 0.0)))
            self.heat_vmin.blockSignals(False)
        if hasattr(self, 'heat_vmax'):
            self.heat_vmax.blockSignals(True)
            self.heat_vmax.setValue(float(s.get('heat_vmax', 1.0)))
            self.heat_vmax.blockSignals(False)
        if hasattr(self, 'contour_line_color'):
            _clc = s.get('contour_line_color', '#000000')
            self.contour_line_color = _clc
            sw = getattr(self, 'contour_line_color_sw', None)
            if sw: sw.setStyleSheet(self._SW_CSS.format(_clc))
        if hasattr(self, 'contour_line_width'):
            self.contour_line_width.blockSignals(True)
            self.contour_line_width.setValue(float(s.get('contour_line_width', 0.5)))
            self.contour_line_width.blockSignals(False)
        if hasattr(self, 'contour_levels_explicit'):
            self.contour_levels_explicit.blockSignals(True)
            self.contour_levels_explicit.setText(s.get('contour_levels_explicit', ''))
            self.contour_levels_explicit.blockSignals(False)
        # Tricontour
        _co(self.tri_cmap_combo, 'tri_cmap',     'rainbow')
        _sp(self.tri_levels,     'tri_levels',   10)
        _sp(self.tri_alpha,      'tri_alpha',    1.0)
        # Backward compat: old saves used tri_filled/tri_tripcolor booleans
        if 'tri_fill_mode' in s:
            _co(self.tri_fill_mode, 'tri_fill_mode', 'Filled contour')
        elif s.get('tri_tripcolor', False):
            self.tri_fill_mode.setCurrentText('Face colours')
        elif s.get('tri_filled', True):
            self.tri_fill_mode.setCurrentText('Filled contour')
        else:
            self.tri_fill_mode.setCurrentText('None')
        _cb(self.tri_lines,      'tri_lines',    True)
        _cb(self.tri_triplot,    'tri_triplot',  False)
        _cb(self.tri_colorbar,   'tri_colorbar', True)
        if hasattr(self, 'tri_colorbar_shrink'):
            self.tri_colorbar_shrink.blockSignals(True)
            self.tri_colorbar_shrink.setValue(float(s.get('tri_colorbar_shrink', 1.0)))
            self.tri_colorbar_shrink.blockSignals(False)
        if hasattr(self, '_tri_colorbar_size_row'):
            self._tri_colorbar_size_row.setVisible(self.tri_colorbar.isChecked())
        # Pie
        _cb(self.pie_autopct,       'pie_autopct',      True)
        _cb(self.pie_shadow,        'pie_shadow',       False)
        _cb(self.pie_donut,         'pie_donut',        False)
        _cb(self.pie_explode_first, 'pie_explode_first',False)
        _sp(self.pie_startangle,    'pie_startangle',   90.0)
        _sp(self.pie_labeldistance, 'pie_labeldistance',1.1)
        _sp(self.pie_pctdistance,   'pie_pctdistance',  0.6)
        # Area
        _cb(self.area_stacked,  'area_stacked',  False)
        _sp(self.area_baseline, 'area_baseline', 0.0)
        # Violin
        _cb(self.violin_show_means,   'violin_show_means',   True)
        _cb(self.violin_show_medians, 'violin_show_medians', True)
        _cb(self.violin_show_extrema, 'violin_show_extrema', False)
        _co(self.violin_points,       'violin_points',       '100')
        _co(self.violin_bw,           'violin_bw',           'scott')
        _cb(self.violin_vert,         'violin_vert',         True)
        # Boxplot
        _cb(self.box_show_means,   'box_show_means',   False)
        _cb(self.box_show_medians, 'box_show_medians', True)
        _cb(self.box_notch,        'box_notch',        False)
        _cb(self.box_showfliers,   'box_showfliers',   True)
        _cb(self.box_vert,         'box_vert',         True)
        _sp(self.box_whis,         'box_whis',         1.5)
        _sp(self.box_alpha,        'box_alpha',        0.7)
        # Step
        _co(self.step_where, 'step_where', 'pre')
        # Stem
        _sp(self.stem_baseline, 'stem_baseline', 0.0)
        # Waterfall
        _cb(self.waterfall_connector, 'waterfall_connector', True)
        _sp(self.waterfall_width,     'waterfall_width',     0.6)
        _sp(self.waterfall_alpha,     'waterfall_alpha',     1.0)
        for _attr, _key, _def in [
            ('waterfall_pos_color', 'waterfall_pos_color', '#2ecc71'),
            ('waterfall_neg_color', 'waterfall_neg_color', '#e74c3c'),
        ]:
            _v = s.get(_key, _def)
            setattr(self, _attr, _v)
            _sw = getattr(self, _attr + '_sw', None)
            if _sw: _sw.setStyleSheet(
                f'background-color:{_v};border:1px solid #888;border-radius:2px;')
        # Hist2D
        _sp(self.hist2d_bins_x,  'hist2d_bins_x',  20)
        _sp(self.hist2d_bins_y,  'hist2d_bins_y',  20)
        _sp(self.hist2d_alpha,   'hist2d_alpha',   1.0)
        _co(self.hist2d_cmap_combo, 'hist2d_cmap', 'viridis')
        _cb(self.hist2d_colorbar,'hist2d_colorbar', True)
        _cb(self.hist2d_log,     'hist2d_log',      False)
        # Hexbin
        _sp(self.hexbin_gridsize,    'hexbin_gridsize', 20)
        _sp(self.hexbin_alpha,       'hexbin_alpha',    1.0)
        _co(self.hexbin_cmap_combo,  'hexbin_cmap',     'viridis')
        _cb(self.hexbin_colorbar,    'hexbin_colorbar', True)
        _cb(self.hexbin_log,         'hexbin_log',      False)
        # Radar
        _sp(self.radar_gridlevels, 'radar_gridlevels', 5)
        # ECDF
        _cb(self.ecdf_complementary, 'ecdf_complementary', False)
        # Quiver
        _sp(self.quiver_scale,       'quiver_scale',       1.0)
        _sp(self.quiver_width,       'quiver_width',       0.005)
        _cb(self.quiver_color_by_mag,'quiver_color_by_mag',False)
        _co(self.quiver_cmap_combo,  'quiver_cmap',        'viridis')
        # Barbs
        _sp(self.barbs_length,       'barbs_length',       7.0)
        _co(self.barbs_pivot_combo,  'barbs_pivot',        'tip')
        _sp(self.barbs_alpha,        'barbs_alpha',        0.85)
        _cb(self.barbs_color_by_mag, 'barbs_color_by_mag', False)
        _co(self.barbs_cmap_combo,   'barbs_cmap',         'viridis')
        # Streamplot
        _sp(self.stream_density,     'stream_density',     1.0)
        _sp(self.stream_arrowsize,   'stream_arrowsize',   1.0)
        _sp(self.stream_linewidth,   'stream_linewidth',   1.5)
        _cb(self.stream_color_by_mag,'stream_color_by_mag',False)
        _co(self.stream_cmap_combo,  'stream_cmap',        'viridis')

        # ── Annotation default style ─────────────────────────────────────────
        def _set_ann_color(attr, default):
            v = s.get(attr, default)
            setattr(self, attr, v)
            sw = getattr(self, attr + '_sw', None)
            if sw:
                sw.setStyleSheet(
                    f'background-color:{v};border:1px solid #888;border-radius:2px;')

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

        self.combo_x.blockSignals(False)
        self.y_list.blockSignals(False)

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
        from ui.tab_builders import PER_SERIES_TYPES, PLOT_MODE_GROUPS
        old_y2_cols = set(m.get('y2_cols', []))
        cols = sorted(self.datasets)
        n_subplots = max(1, self.subplot_rows * self.subplot_cols)

        # Resolve subplot_plot_modes from the saved data *before* building the
        # series rows so each type combo is restricted to the correct mode.
        # The full restore (including setdefault fills) still happens later in
        # the method; we only need the mapping here.
        _mode_compat = {'Lines & Scatter': 'Standard', 'Bar & Histogram': 'Histogram', 'normal': 'Standard'}
        _saved_modes = {
            int(k): _mode_compat.get(v, v)
            for k, v in m.get('subplot_plot_modes', {}).items()
        }

        self.series_table.blockSignals(True)
        self.series_table.setRowCount(0)
        for sd in m.get('series', []):
            row = self.series_table.rowCount()
            self.series_table.insertRow(row)

            # X combo — signals blocked during construction
            cb_x = QComboBox()
            cb_x.blockSignals(True)
            cb_x.addItems(cols)
            i = cb_x.findText(sd.get('x_col', ''))
            if i >= 0: cb_x.setCurrentIndex(i)
            cb_x.blockSignals(False)
            cb_x.currentIndexChanged.connect(self._on_x_col_changed)
            self.series_table.setCellWidget(row, 0, cb_x)

            # Y combo — signals blocked during construction
            cb_y = QComboBox()
            cb_y.blockSignals(True)
            cb_y.addItems(cols)
            i = cb_y.findText(sd.get('y_col', ''))
            if i >= 0: cb_y.setCurrentIndex(i)
            cb_y.blockSignals(False)
            cb_y.currentIndexChanged.connect(self.update_preview)
            self.series_table.setCellWidget(row, 1, cb_y)

            # Label — explicitly set editable flag so double-click editing works reliably
            _lbl_item = QTableWidgetItem(sd.get('label', f'Series {row+1}'))
            _lbl_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
            self.series_table.setItem(row, 2, _lbl_item)

            # Type combo — restricted to the plot mode of this series' subplot,
            # matching the behaviour when rows are added interactively.
            plot_num = sd.get('plot_num', 1)
            subplot_idx = max(0, plot_num - 1)
            _mode = _saved_modes.get(subplot_idx, 'Standard')
            _allowed = list(PLOT_MODE_GROUPS.get(_mode, PER_SERIES_TYPES))
            type_cb = QComboBox()
            type_cb.addItems(_allowed)
            saved_type = sd.get('series_type', 'Line')
            ti = type_cb.findText(saved_type)
            if ti >= 0: type_cb.setCurrentIndex(ti)
            type_cb.currentTextChanged.connect(self._on_series_row_type_changed)
            self.series_table.setCellWidget(row, 3, type_cb)

            # Plot spinbox
            plot_spin = QSpinBox()
            plot_spin.setRange(1, n_subplots)
            plot_spin.setValue(min(sd.get('plot_num', 1), n_subplots))
            plot_spin.valueChanged.connect(self.update_preview)
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
        if hasattr(self, 'combo_fill_y2'):
            i = self.combo_fill_y2.findText(m.get('fill_y2_col', '(none)'))
            if i >= 0: self.combo_fill_y2.setCurrentIndex(i)

        # Restore subplot chart types, plot modes, legend locs, and chart opts
        saved_ct = m.get('subplot_chart_types', {})
        self.subplot_chart_types = {int(k): v for k, v in saved_ct.items()}
        saved_ll = m.get('subplot_legend_locs', {})
        self.subplot_legend_locs = {int(k): v for k, v in saved_ll.items()}
        saved_pm = m.get('subplot_plot_modes', {})
        _mode_compat = {'Lines & Scatter': 'Standard', 'Bar & Histogram': 'Histogram', 'normal': 'Standard'}
        self.subplot_plot_modes = {int(k): _mode_compat.get(v, v) for k, v in saved_pm.items()}
        # Restore per-subplot chart options (backward-compat: old files won't have this key)
        saved_co = m.get('subplot_chart_opts', {})
        self.subplot_chart_opts = {int(k): v for k, v in saved_co.items()}
        _defaults = self._default_chart_opts() if hasattr(self, '_default_chart_opts') else {}
        for idx in range(n_subplots):
            self.subplot_chart_types.setdefault(idx, 'Line')
            self.subplot_legend_locs.setdefault(idx, 'best')
            self.subplot_plot_modes.setdefault(idx, 'Standard')
            # Merge saved opts with defaults so any newly-added keys are present
            if idx not in self.subplot_chart_opts:
                self.subplot_chart_opts[idx] = dict(_defaults)
            else:
                merged = dict(_defaults)
                merged.update(self.subplot_chart_opts[idx])
                self.subplot_chart_opts[idx] = merged

        # Restore extra column combos (quiver/barbs/streamplot U/V, bubble size, X error)
        for attr, key, sentinel in [
            ('quiver_u_combo',    'quiver_u_col',    '(none)'),
            ('quiver_v_combo',    'quiver_v_col',    '(none)'),
            ('barbs_u_combo',     'barbs_u_col',     '(none)'),
            ('barbs_v_combo',     'barbs_v_col',     '(none)'),
            ('stream_u_combo',    'stream_u_col',    '(none)'),
            ('stream_v_combo',    'stream_v_col',    '(none)'),
            ('bubble_size_combo', 'bubble_size_col', '(uniform)'),
            ('err_xerr_combo',    'err_xerr_col',    '(none)'),
        ]:
            w = getattr(self, attr, None)
            if w:
                val = m.get(key, sentinel)
                i = w.findText(val)
                w.blockSignals(True)
                w.setCurrentIndex(i if i >= 0 else 0)
                w.blockSignals(False)

        # Load the chart-option widgets for the active subplot so the UI
        # immediately reflects the restored per-subplot values.
        if hasattr(self, '_load_chart_opts') and hasattr(self, 'sp_active'):
            _active = self.sp_active.currentIndex()
            self._load_chart_opts(max(0, _active))

        self._refresh_curve_select()

    # ═══════════════════════════════════════════════════════════════════════════
    # .pviz SAVE / LOAD  (zip containing settings.json + data.json + images/)
    # ═══════════════════════════════════════════════════════════════════════════

    def _collect_annotations_meta(self):
        """
        Return a JSON-serialisable list describing every annotation.
        Image annotations store the basename of the embedded file; the
        caller is responsible for including the actual bytes in the archive.
        """
        out = []
        for ann in self.canvas.annotations:
            a = {k: v for k, v in ann.items() if k != 'artist'}
            if 'style' in a and isinstance(a['style'], dict):
                a['style'] = dict(a['style'])
            if ann['type'] == 'image':
                a['image_file'] = 'images/' + os.path.basename(ann['filepath'])
                # keep filepath for runtime use but don't embed full path
                del a['filepath']
            out.append(a)
        return out

    def _export_palette_bundle(self):
        """Save a .pvizp file containing only the custom colour palettes."""
        _stem = (os.path.splitext(os.path.basename(self._current_filepath))[0]
                 if getattr(self, '_current_filepath', None) else 'untitled')
        fp, _ = QFileDialog.getSaveFileName(
            self, 'Save Palette', os.path.join(_get_dir(), _stem + '.pvizp'),
            'plotviz Palette Bundle (*.pvizp);;All Files (*)')
        if not fp: return
        _remember_dir(fp)
        if not fp.endswith('.pvizp'): fp += '.pvizp'
        try:
            custom_pal_json = self._custom_palettes_json()
            with zipfile.ZipFile(fp, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('palette.json', custom_pal_json)
            QMessageBox.information(self, 'Saved', f'Palette bundle saved:\n{fp}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _import_palette_bundle(self):
        """Load a .pvizp palette bundle file (via file dialog)."""
        fp, _ = QFileDialog.getOpenFileName(
            self, 'Import Palette Bundle', _get_dir(),
            'plotviz Palette Bundle (*.pvizp);;All Files (*)')
        if not fp: return
        _remember_dir(fp)
        self._import_palette_bundle_from_path(fp)

    def _import_palette_bundle_from_path(self, fp: str):
        """Load a .pvizp palette bundle directly from *fp* (no dialog)."""
        import config.settings as _cfg
        _cfg.remember_dir(fp)
        self._import_palette_bundle_inner(fp)

    def _import_palette_bundle_inner(self, fp: str):
        """Core logic for importing a .pvizp palette bundle — no dialogs."""
        try:
            with zipfile.ZipFile(fp, 'r') as zf:
                if 'palette.json' not in zf.namelist():
                    QMessageBox.warning(self, 'Invalid', 'No palette.json in file.')
                    return
                self._load_custom_palettes_json(zf.read('palette.json').decode())
            QMessageBox.information(self, 'Imported', 'Palette bundle imported.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _save_template(self):
        """Save a .pvizt that contains only settings (no data, no annotations)."""
        fp, _ = QFileDialog.getSaveFileName(
            self, 'Save Template', _get_dir(),
            'plotviz Template (*.pvizt);;All Files (*)')
        if not fp: return
        _remember_dir(fp)
        if not fp.endswith('.pvizt'): fp += '.pvizt'
        try:
            settings = self._collect_settings()
            settings['_file_type'] = 'template'
            with zipfile.ZipFile(fp, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('settings.json', json.dumps(settings, indent=2))
            QMessageBox.information(self, 'Saved', f'Template saved:\n{fp}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _load_template(self):
        """Load a .pvizt template (settings only — no data required)."""
        fp, _ = QFileDialog.getOpenFileName(
            self, 'Load Template', _get_dir(), 'plotviz Template (*.pvizt);;All Files (*)')
        if not fp: return
        _remember_dir(fp)
        import config.settings as _cfg
        _cfg.remember_dir(fp)
        self._load_template_inner(fp)

    def _save_project(self):
        """
        Save a full .pviz:
          settings.json  -- appearance/config (no column names)
          series.json    -- series table + subplot column assignments
          data.json      -- datasets (all or used-only, per user choice)
          images/<n>     -- any image files used in annotations
        """
        import os as _os
        _default_dir = _get_dir()
        if getattr(self, '_current_filepath', None):
            _stem = _os.path.splitext(_os.path.basename(self._current_filepath))[0]
            _default_dir = _os.path.join(_os.path.dirname(self._current_filepath), _stem)
        else:
            _default_dir = _os.path.join(_default_dir, 'new chart')
        fp, _ = QFileDialog.getSaveFileName(
            self, 'Save Chart', _default_dir,
            'plotviz File (*.pviz);;zip Archive (*.zip);;All Files (*)')
        if not fp: return
        _remember_dir(fp)
        # Accept .pviz or .zip; fall back to .pviz for any other extension
        if not (fp.endswith('.pviz') or fp.endswith('.zip')):
            fp += '.pviz'
        self._current_filepath = fp
        self._update_window_title()
        self._is_dirty = False

        # ── Ask which columns to save ─────────────────────────────────────────
        # Collect the set of columns actually used in the series table
        used_cols = set()
        for row in range(self.series_table.rowCount()):
            for col_idx in (0, 1):
                cb = self.series_table.cellWidget(row, col_idx)
                if cb:
                    txt = cb.currentText()
                    if txt and txt in self.datasets:
                        used_cols.add(txt)
        # Also include z, err, bubble-size, quiver/barbs/streamplot U/V, and x-error columns
        for attr, sentinel in [
            ('combo_z',           '(none)'),
            ('combo_err',         '(none)'),
            ('bubble_size_combo', '(uniform)'),
            ('quiver_u_combo',    '(none)'),
            ('quiver_v_combo',    '(none)'),
            ('barbs_u_combo',     '(none)'),
            ('barbs_v_combo',     '(none)'),
            ('stream_u_combo',    '(none)'),
            ('stream_v_combo',    '(none)'),
            ('err_xerr_combo',    '(none)'),
        ]:
            cb = getattr(self, attr, None)
            if cb:
                txt = cb.currentText()
                if txt and txt != sentinel and txt in self.datasets:
                    used_cols.add(txt)

        all_cols = set(self.datasets.keys())
        if used_cols >= all_cols:
            # All columns are in use — save everything silently, no dialog needed
            used_only = False
        else:
            dlg = QMessageBox(self)
            dlg.setWindowTitle('Save data')
            dlg.setText('Which dataset columns do you want to save?')
            dlg.setInformativeText(
                '<b>Used series only</b> saves the columns currently assigned '
                'in the Series table — keeps the file small.<br><br>'
                '<b>All columns</b> preserves every loaded column so you can '
                'reassign axes after reopening.'
            )
            btn_used = dlg.addButton('Used series only', QMessageBox.ButtonRole.AcceptRole)
            btn_all  = dlg.addButton('All columns',      QMessageBox.ButtonRole.AcceptRole)
            dlg.addButton(QMessageBox.StandardButton.Cancel)
            dlg.exec()
            clicked = dlg.clickedButton()
            if clicked is None or clicked not in (btn_used, btn_all):
                return
            used_only = (clicked is btn_used)

        try:
            settings = self._collect_settings()
            settings['_file_type'] = 'project'
            settings['annotations'] = self._collect_annotations_meta()

            series_meta = self._collect_series_meta()

            # Determine which column keys to keep
            if used_only:
                keep = set()
                for sd in series_meta.get('series', []):
                    for key in ('x_col', 'y_col'):
                        col = sd.get(key, '')
                        if col and col in self.datasets:
                            keep.add(col)
                # Also keep z, err, bubble-size, quiver/barbs/streamplot U/V, and x-error columns
                for key, sentinel in [
                    ('z_col',           '(none)'),
                    ('err_col',         '(none)'),
                    ('bubble_size_col', '(uniform)'),
                    ('quiver_u_col',    '(none)'),
                    ('quiver_v_col',    '(none)'),
                    ('barbs_u_col',     '(none)'),
                    ('barbs_v_col',     '(none)'),
                    ('stream_u_col',    '(none)'),
                    ('stream_v_col',    '(none)'),
                    ('err_xerr_col',    '(none)'),
                ]:
                    col = series_meta.get(key, '')
                    if col and col != sentinel and col in self.datasets:
                        keep.add(col)
            else:
                keep = set(self.datasets.keys())

            datasets = {}
            for k in keep:
                v = self.datasets[k]
                is_cat = hasattr(v, 'dtype') and v.dtype.kind in ('U', 'S', 'O')
                datasets[k] = {
                    'dtype': 'object' if is_cat else 'float',
                    'values': (v.tolist() if hasattr(v, 'tolist') else list(v)),
                }

            with zipfile.ZipFile(fp, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('settings.json', json.dumps(settings,    indent=2))
                zf.writestr('series.json',   json.dumps(series_meta, indent=2))
                zf.writestr('data.json',     json.dumps(datasets,    indent=2))
                custom_pal_json = self._custom_palettes_json()
                if custom_pal_json != '{}':
                    zf.writestr('palette.json', custom_pal_json)
                seen = set()
                for ann in self.canvas.annotations:
                    if ann['type'] == 'image':
                        src = ann.get('filepath', '')
                        if src and os.path.isfile(src):
                            bname = os.path.basename(src)
                            if bname not in seen:
                                zf.write(src, 'images/' + bname)
                                seen.add(bname)

            import config.settings as _cfg
            _cfg.add_recent_file(fp)
            if hasattr(self, '_rebuild_recent_files_ui'):
                self._rebuild_recent_files_ui()
            saved_cols = len(datasets)
            total_cols = len(self.datasets)
            detail = f'{saved_cols} of {total_cols} column(s)' if used_only else f'all {total_cols} column(s)'
            QMessageBox.information(self, 'Saved', f'Chart saved ({detail}):\n{fp}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _load_project_from_path(self, fp: str):
        """Load a .pviz directly from *fp* (no file dialog — used by recent-files list and Finder open)."""
        import config.settings as _cfg
        _cfg.add_recent_file(fp)
        _cfg.remember_dir(fp)
        if hasattr(self, '_rebuild_recent_files_ui'):
            self._rebuild_recent_files_ui()
        self._current_filepath = fp
        self._update_window_title()
        self._load_project_inner(fp)

    def _load_template_from_path(self, fp: str):
        """Load a .pvizt directly from *fp* (no file dialog — used by Finder open)."""
        import config.settings as _cfg
        _cfg.remember_dir(fp)
        self._load_template_inner(fp)

    def _load_template_inner(self, fp: str):
        """Core logic for loading a .pvizt archive — no dialogs."""
        try:
            with zipfile.ZipFile(fp, 'r') as zf:
                names = zf.namelist()
                if 'settings.json' not in names:
                    QMessageBox.warning(self, 'Invalid', 'No settings.json in archive.')
                    return
                settings = json.loads(zf.read('settings.json'))
            self._applying_settings = True
            try:
                self._apply_settings(settings)
            finally:
                self._applying_settings = False
            self.update_preview()
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _load_project(self):
        """Load a full .pviz: restore datasets, settings, series and annotations."""
        fp, _ = QFileDialog.getOpenFileName(
            self, 'Open Chart', _get_dir(), 'plotviz File (*.pviz);;zip File (*.zip);;All Files (*)')
        if not fp: return
        _remember_dir(fp)
        import config.settings as _cfg
        _cfg.add_recent_file(fp)
        if hasattr(self, '_rebuild_recent_files_ui'):
            self._rebuild_recent_files_ui()
        self._current_filepath = fp
        self._update_window_title()
        self._load_project_inner(fp)

    def _load_project_inner(self, fp: str, silent: bool = False):
        """Core logic for loading a .pviz archive.
        Pass silent=True to suppress all QMessageBox dialogs (e.g. on startup).
        """
        # ── Silent reset: clear all stale state before loading ──────────────────
        # Mirrors _reset_app but without prompts or default-settings application.
        # This ensures that opening a second .pviz (without clicking New Plot) is
        # equivalent to a fresh start — no stale datasets, styles, subplot modes,
        # series rows, or type-combo contents can bleed through from the old file.
        self.datasets.clear()
        self.curve_styles.clear()
        if hasattr(self, 'canvas'):
            self.canvas.annotations.clear()
        self._last_fit = None
        self._subplot_mosaic = None
        # Clear subplot-state dicts so on_subplot_layout_changed's setdefault
        # calls never see stale values from a previously loaded file.
        self.subplot_chart_types.clear()
        self.subplot_plot_modes.clear()
        self.subplot_chart_opts.clear()
        # Clear the series table BEFORE _apply_settings or any signal-triggered
        # redraws can reference the now-empty datasets and crash.
        if hasattr(self, 'series_table'):
            self.series_table.blockSignals(True)
            self.series_table.setRowCount(0)
            self.series_table.blockSignals(False)
        # ───────────────────────────────────────────────────────────────────────
        try:
            with zipfile.ZipFile(fp, 'r') as zf:
                names = zf.namelist()
                if 'settings.json' not in names:
                    QMessageBox.warning(self, 'Invalid', 'No settings.json in archive.')
                    return
                settings    = json.loads(zf.read('settings.json'))
                series_meta = json.loads(zf.read('series.json')) if 'series.json' in names else None
                # Load custom palettes if present
                if 'palette.json' in names:
                    self._load_custom_palettes_json(zf.read('palette.json').decode())
                # Backwards compat: series embedded inside old settings.json
                if series_meta is None and 'series' in settings:
                    series_meta = {
                        'series':  settings.get('series', []),
                        'z_col':   settings.get('z_col', '(none)'),
                        'err_col': settings.get('err_col', '(none)'),
                        'y2_cols': settings.get('y2_cols', []),
                    }
                if 'data.json' in names:
                    raw_ds = json.loads(zf.read('data.json'))
                    self.datasets = {}
                    for k, v in raw_ds.items():
                        # New format: {'dtype': 'float'|'object', 'values': [...]}
                        # Old format: plain list
                        if isinstance(v, dict) and 'values' in v:
                            vals = v['values']
                            if v.get('dtype') == 'object':
                                self.datasets[k] = np.array(vals, dtype=object)
                            else:
                                self.datasets[k] = np.array(vals, dtype=float)
                        else:
                            # Backwards compat: plain list — infer dtype
                            try:
                                self.datasets[k] = np.array(v, dtype=float)
                            except (ValueError, TypeError):
                                self.datasets[k] = np.array(v, dtype=object)
                else:
                    self.datasets = {}
                img_dir = tempfile.mkdtemp(prefix='plotviz_imgs_')
                for name in names:
                    if name.startswith('images/') and name != 'images/':
                        bname = os.path.basename(name)
                        dest  = os.path.join(img_dir, bname)
                        with open(dest, 'wb') as f2:
                            f2.write(zf.read(name))

            # ── Restore order matters: ──────────────────────────────────────────
            # 1. Apply all settings EXCEPT subplot layout (which triggers signals
            #    that read subplot dicts before they've been populated).
            #    We block sp_rows/sp_cols signals, set the values, restore state
            #    manually at the end.
            self.sp_rows.blockSignals(True)
            self.sp_cols.blockSignals(True)
            self._applying_settings = True
            try:
                self._apply_settings(settings)
            finally:
                # Keep _applying_settings True while unblocking so any deferred
                # valueChanged signals from sp_rows/sp_cols don't fire update_preview
                # before the series table is restored (steps 2-5 below).
                self.sp_rows.blockSignals(False)
                self.sp_cols.blockSignals(False)

            # 2. Refresh dataset combos now that self.datasets is populated.
            #    Keep _applying_settings=True through steps 2-5 so no intermediate
            #    update_preview fires on a half-built state.
            self._applying_settings = True
            try:
                self.update_lists()

                # 3. Apply subplot layout — now all dicts are populated so
                #    on_subplot_layout_changed reads correct values.
                self.subplot_rows = settings.get('subplot_rows', 1)
                self.subplot_cols = settings.get('subplot_cols', 1)
                mosaic = settings.get('subplot_mosaic', None)
                self._subplot_mosaic = mosaic
                if mosaic is not None:
                    n_cells = len(dict.fromkeys(c for row in mosaic for c in row))
                    self.on_subplot_layout_changed(n_override=n_cells)
                else:
                    self.on_subplot_layout_changed()

                # 4. Restore series table.
                if series_meta:
                    self._apply_series_meta(series_meta)

                # 5. Sync the active-subplot UI panel.
                self.on_active_subplot_changed()
            finally:
                self._applying_settings = False

            # 6. Restore annotations.
            ann_meta = settings.get('annotations', [])
            self.canvas.annotations = []
            self.canvas.clear_annotations()
            for a in ann_meta:
                if a.get('type') == 'image' and 'image_file' in a:
                    bname = os.path.basename(a['image_file'])
                    a['filepath'] = os.path.join(img_dir, bname)
            self.canvas.annotations = [
                {k: v for k, v in a.items() if k != 'image_file'}
                for a in ann_meta
            ]
            for a, orig in zip(self.canvas.annotations, ann_meta):
                if a.get('type') == 'image' and 'image_file' in orig:
                    bname = os.path.basename(orig['image_file'])
                    a['filepath'] = os.path.join(img_dir, bname)

            self.update_preview()
            # Fresh start: clear undo history so first undo from here is the loaded state
            if hasattr(self, '_undo_stack'):
                self._undo_stack.clear()
                self._redo_stack.clear()
                if hasattr(self, '_snapshot'):
                    self._snapshot()
                self._update_undo_buttons()
            self._is_dirty = False
            if not silent:
                QMessageBox.information(self, 'Loaded', 'Chart loaded successfully.')
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, 'Error', str(e))

