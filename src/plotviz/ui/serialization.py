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

        # Fit curve style (fit_color/fit_linestyle/fit_linewidth removed in 2.0.0 —
        # fit curves are styled via curve_styles like any other series)
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
            'quiver_u_col':         self.quiver_u_combo.currentText() if hasattr(self, 'quiver_u_combo') else '(none)',
            'quiver_v_col':         self.quiver_v_combo.currentText() if hasattr(self, 'quiver_v_combo') else '(none)',
            'bubble_size_col':      self.bubble_size_combo.currentText() if hasattr(self, 'bubble_size_combo') else '(uniform)',
            'err_xerr_col':         self.err_xerr_combo.currentText() if hasattr(self, 'err_xerr_combo') else '(none)',
            'subplot_chart_types':  {str(k): v for k, v in self.subplot_chart_types.items()},
            'subplot_plot_modes':   {str(k): v for k, v in self.subplot_plot_modes.items()},
            'subplot_legend_locs':  {str(k): v for k, v in self.subplot_legend_locs.items()},
        }

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

        # Fit CI/PI bands (fit_color/fit_linestyle/fit_linewidth removed in 2.0.0)
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
            type_cb.currentIndexChanged.connect(self.update_preview)
            type_cb.currentIndexChanged.connect(self._on_series_selection_changed)
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

        # Restore subplot chart types, plot modes, and legend locs
        saved_ct = m.get('subplot_chart_types', {})
        self.subplot_chart_types = {int(k): v for k, v in saved_ct.items()}
        saved_ll = m.get('subplot_legend_locs', {})
        self.subplot_legend_locs = {int(k): v for k, v in saved_ll.items()}
        saved_pm = m.get('subplot_plot_modes', {})
        _mode_compat = {'Lines & Scatter': 'Standard', 'Bar & Histogram': 'Histogram', 'normal': 'Standard'}
        self.subplot_plot_modes = {int(k): _mode_compat.get(v, v) for k, v in saved_pm.items()}
        for idx in range(n_subplots):
            self.subplot_chart_types.setdefault(idx, 'Line')
            self.subplot_legend_locs.setdefault(idx, 'best')
            self.subplot_plot_modes.setdefault(idx, 'Standard')

        # Restore extra column combos (quiver U/V, bubble size, X error)
        for attr, key, sentinel in [
            ('quiver_u_combo',    'quiver_u_col',    '(none)'),
            ('quiver_v_combo',    'quiver_v_col',    '(none)'),
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
        fp, _ = QFileDialog.getSaveFileName(
            self, 'Export Palette Bundle', _get_dir(),
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
                    QMessageBox.warning(self, 'Invalid', 'No palette.json in file.'); return
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
        fp, _ = QFileDialog.getSaveFileName(
            self, 'Save Chart', _default_dir,
            'plotviz File (*.pviz);;All Files (*)')
        if not fp: return
        _remember_dir(fp)
        if not fp.endswith('.pviz'): fp += '.pviz'
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
        # Also include z, err, bubble-size, quiver U/V, and x-error columns
        for attr, sentinel in [
            ('combo_z',           '(none)'),
            ('combo_err',         '(none)'),
            ('bubble_size_combo', '(uniform)'),
            ('quiver_u_combo',    '(none)'),
            ('quiver_v_combo',    '(none)'),
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
                # Also keep z, err, bubble-size, quiver U/V, and x-error columns
                for key, sentinel in [
                    ('z_col',           '(none)'),
                    ('err_col',         '(none)'),
                    ('bubble_size_col', '(uniform)'),
                    ('quiver_u_col',    '(none)'),
                    ('quiver_v_col',    '(none)'),
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
                    QMessageBox.warning(self, 'Invalid', 'No settings.json in archive.'); return
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
            self, 'Open Chart', _get_dir(), 'plotviz File (*.pviz);;All Files (*)')
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
                    QMessageBox.warning(self, 'Invalid', 'No settings.json in archive.'); return
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

