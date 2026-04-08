"""
Copyright (c) 2026 Paulo Cachim
ui/tab_chart_options.py  –  plotviz
TabChartOptionsMixin: _build_chart_option_groups() — per chart-type option widgets.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QPushButton, QGroupBox, QCheckBox,
)
from ui.tab_builders import _CMAP_LIST


class TabChartOptionsMixin:
    def _build_chart_option_groups(self, layout):
        def _row(*widgets):
            h = QHBoxLayout()
            for w in widgets: h.addWidget(w)
            return h

        # ── Bar (chart-mode options only) ─────────────────────────────────────
        self.bar_group = QGroupBox('Bar Options')
        bg = QVBoxLayout(self.bar_group)
        self.bar_stacked    = QCheckBox('Stacked');    self.bar_stacked.stateChanged.connect(self.update_preview);    bg.addWidget(self.bar_stacked)
        self.bar_horizontal = QCheckBox('Horizontal'); self.bar_horizontal.stateChanged.connect(self.update_preview); bg.addWidget(self.bar_horizontal)
        layout.addWidget(self.bar_group)

        # ── Histogram (chart-mode options only) ───────────────────────────────
        self.hist_group = QGroupBox('Histogram Options')
        hg = QVBoxLayout(self.hist_group)
        hg.addLayout(_row(QLabel('Bins:'), self._make_spin('hist_bins', 2, 500, 20)))
        self.hist_density    = QCheckBox('Density (normalise)'); self.hist_density.stateChanged.connect(self.update_preview);    hg.addWidget(self.hist_density)
        self.hist_cumulative = QCheckBox('Cumulative');           self.hist_cumulative.stateChanged.connect(self.update_preview); hg.addWidget(self.hist_cumulative)
        hg.addLayout(_row(QLabel('Type:'), self._make_combo('hist_histtype', ['bar','barstacked','step','stepfilled'])))
        hg.addLayout(_row(QLabel('Orientation:'), self._make_combo('hist_orientation', ['vertical','horizontal'])))
        layout.addWidget(self.hist_group)

        # ── Heatmap / Contour / 3D Surface ────────────────────────────────────
        self.heat_group = QGroupBox('Heatmap / Contour / 3D Options')
        hgb = QVBoxLayout(self.heat_group)
        hgb.addLayout(_row(QLabel('Colormap:'), self._make_combo('cmap_combo', _CMAP_LIST)))
        hgb.addLayout(_row(QLabel('Contour levels:'), self._make_spin('contour_levels', 3, 100, 10)))
        hgb.addLayout(_row(QLabel('Alpha:'), self._make_dbl_spin('heat_alpha', 0.05, 1.0, 1.0, 0.05)))
        hgb.addLayout(_row(QLabel('Interpolation:'), self._make_combo('heat_interpolation',
            ['nearest','bilinear','bicubic','lanczos','spline16','gaussian'])))
        self.heat_colorbar     = QCheckBox('Show colorbar');         self.heat_colorbar.setChecked(True);     self.heat_colorbar.stateChanged.connect(self.update_preview);     hgb.addWidget(self.heat_colorbar)
        self.heat_filled_contour = QCheckBox('Filled contour');      self.heat_filled_contour.setChecked(True); self.heat_filled_contour.stateChanged.connect(self.update_preview); hgb.addWidget(self.heat_filled_contour)
        self.heat_contour_lines  = QCheckBox('Contour line overlay'); self.heat_contour_lines.setChecked(True);  self.heat_contour_lines.stateChanged.connect(self.update_preview);  hgb.addWidget(self.heat_contour_lines)
        hgb.addLayout(_row(QLabel('3D stride:'), self._make_spin('surf_stride', 1, 10, 1)))
        self.surf_wireframe = QCheckBox('Wireframe (3D)'); self.surf_wireframe.stateChanged.connect(self.update_preview); hgb.addWidget(self.surf_wireframe)
        layout.addWidget(self.heat_group)

        # ── Pie ───────────────────────────────────────────────────────────────
        self.pie_group = QGroupBox('Pie Options')
        pg = QVBoxLayout(self.pie_group)
        self.pie_autopct = QCheckBox('Show %');   self.pie_autopct.setChecked(True); self.pie_autopct.stateChanged.connect(self.update_preview); pg.addWidget(self.pie_autopct)
        self.pie_shadow  = QCheckBox('Shadow');                                       self.pie_shadow.stateChanged.connect(self.update_preview);  pg.addWidget(self.pie_shadow)
        self.pie_donut   = QCheckBox('Donut');                                        self.pie_donut.stateChanged.connect(self.update_preview);   pg.addWidget(self.pie_donut)
        self.pie_explode_first = QCheckBox('Explode first slice');                    self.pie_explode_first.stateChanged.connect(self.update_preview); pg.addWidget(self.pie_explode_first)
        pg.addLayout(_row(QLabel('Start angle:'), self._make_dbl_spin('pie_startangle', 0, 360, 90, 15)))
        pg.addLayout(_row(QLabel('Label dist:'),  self._make_dbl_spin('pie_labeldistance', 0.5, 2.0, 1.1, 0.05)))
        pg.addLayout(_row(QLabel('Pct dist:'),    self._make_dbl_spin('pie_pctdistance', 0.3, 1.5, 0.6, 0.05)))
        layout.addWidget(self.pie_group)

        # ── Area (chart-mode options only) ────────────────────────────────────
        self.area_group = QGroupBox('Area Options')
        ag = QVBoxLayout(self.area_group)
        ag.addLayout(_row(QLabel('Baseline:'), self._make_dbl_spin('area_baseline', -1e6, 1e6, 0.0, 1.0)))
        self.area_stacked = QCheckBox('Stacked'); self.area_stacked.stateChanged.connect(self.update_preview); ag.addWidget(self.area_stacked)
        layout.addWidget(self.area_group)

        # ── Violin ────────────────────────────────────────────────────────────
        self.violin_group = QGroupBox('Violin Options')
        vg = QVBoxLayout(self.violin_group)
        self.violin_show_means   = QCheckBox('Show means');   self.violin_show_means.setChecked(True);   self.violin_show_means.stateChanged.connect(self.update_preview);   vg.addWidget(self.violin_show_means)
        self.violin_show_medians = QCheckBox('Show medians'); self.violin_show_medians.setChecked(True); self.violin_show_medians.stateChanged.connect(self.update_preview); vg.addWidget(self.violin_show_medians)
        self.violin_show_extrema = QCheckBox('Show extrema'); self.violin_show_extrema.stateChanged.connect(self.update_preview); vg.addWidget(self.violin_show_extrema)
        vg.addLayout(_row(QLabel('Points:'), self._make_combo('violin_points', ['100','200','500','1000'])))
        vg.addLayout(_row(QLabel('bw_method:'), self._make_combo('violin_bw', ['scott','silverman'])))
        self.violin_vert = QCheckBox('Vertical'); self.violin_vert.setChecked(True); self.violin_vert.stateChanged.connect(self.update_preview); vg.addWidget(self.violin_vert)
        layout.addWidget(self.violin_group)

        # ── Boxplot ───────────────────────────────────────────────────────────
        self.boxplot_group = QGroupBox('Boxplot Options')
        bxg = QVBoxLayout(self.boxplot_group)
        self.box_show_means   = QCheckBox('Show means');      self.box_show_means.stateChanged.connect(self.update_preview);                bxg.addWidget(self.box_show_means)
        self.box_show_medians = QCheckBox('Show medians');    self.box_show_medians.setChecked(True); self.box_show_medians.stateChanged.connect(self.update_preview); bxg.addWidget(self.box_show_medians)
        self.box_notch        = QCheckBox('Notch');           self.box_notch.stateChanged.connect(self.update_preview);                     bxg.addWidget(self.box_notch)
        self.box_showfliers   = QCheckBox('Show outliers');   self.box_showfliers.setChecked(True); self.box_showfliers.stateChanged.connect(self.update_preview); bxg.addWidget(self.box_showfliers)
        self.box_vert         = QCheckBox('Vertical');        self.box_vert.setChecked(True);       self.box_vert.stateChanged.connect(self.update_preview);        bxg.addWidget(self.box_vert)
        bxg.addLayout(_row(QLabel('Whiskers (IQR ×):'), self._make_dbl_spin('box_whis', 0.5, 5.0, 1.5, 0.25)))
        bxg.addLayout(_row(QLabel('Alpha:'), self._make_dbl_spin('box_alpha', 0.05, 1.0, 0.7, 0.05)))
        layout.addWidget(self.boxplot_group)

        # ── Step (chart-mode options only) ────────────────────────────────────
        self.step_group = QGroupBox('Step Options')
        stg = QVBoxLayout(self.step_group)
        stg.addLayout(_row(QLabel('Where:'), self._make_combo('step_where', ['pre','post','mid'])))
        layout.addWidget(self.step_group)

        # ── Stem (chart-mode options only) ────────────────────────────────────
        self.stem_group = QGroupBox('Stem Options')
        smg = QVBoxLayout(self.stem_group)
        smg.addLayout(_row(QLabel('Baseline:'), self._make_dbl_spin('stem_baseline', -1e9, 1e9, 0.0, 0.1)))
        layout.addWidget(self.stem_group)

        # ── Waterfall ─────────────────────────────────────────────────────────
        self.waterfall_group = QGroupBox('Waterfall Options')
        wfg = QVBoxLayout(self.waterfall_group)
        self.waterfall_connector = QCheckBox('Show connectors'); self.waterfall_connector.setChecked(True); self.waterfall_connector.stateChanged.connect(self.update_preview); wfg.addWidget(self.waterfall_connector)
        wfg.addLayout(_row(QLabel('Bar width:'),    self._make_dbl_spin('waterfall_width', 0.05, 1.0, 0.6, 0.05)))
        wfg.addLayout(_row(QLabel('Pos color:'),    self._make_color_btn('waterfall_pos_color', '#2ecc71')))
        wfg.addLayout(_row(QLabel('Neg color:'),    self._make_color_btn('waterfall_neg_color', '#e74c3c')))
        wfg.addLayout(_row(QLabel('Alpha:'),        self._make_dbl_spin('waterfall_alpha', 0.05, 1.0, 1.0, 0.05)))
        layout.addWidget(self.waterfall_group)

        # ── Hist2D ────────────────────────────────────────────────────────────
        self.hist2d_group = QGroupBox('2D Histogram Options')
        h2g = QVBoxLayout(self.hist2d_group)
        h2g.addLayout(_row(QLabel('Bins X:'), self._make_spin('hist2d_bins_x', 2, 200, 20),
                           QLabel('Y:'),      self._make_spin('hist2d_bins_y', 2, 200, 20)))
        h2g.addLayout(_row(QLabel('Alpha:'),  self._make_dbl_spin('hist2d_alpha', 0.05, 1.0, 1.0, 0.05)))
        h2g.addLayout(_row(QLabel('Colormap:'), self._make_combo('hist2d_cmap_combo', _CMAP_LIST)))
        self.hist2d_colorbar = QCheckBox('Show colorbar'); self.hist2d_colorbar.setChecked(True); self.hist2d_colorbar.stateChanged.connect(self.update_preview); h2g.addWidget(self.hist2d_colorbar)
        self.hist2d_log      = QCheckBox('Log color scale'); self.hist2d_log.stateChanged.connect(self.update_preview); h2g.addWidget(self.hist2d_log)
        layout.addWidget(self.hist2d_group)

        # ── Hexbin ────────────────────────────────────────────────────────────
        self.hexbin_group = QGroupBox('Hexbin Options')
        hxg = QVBoxLayout(self.hexbin_group)
        hxg.addLayout(_row(QLabel('Grid size:'), self._make_spin('hexbin_gridsize', 5, 100, 20)))
        hxg.addLayout(_row(QLabel('Alpha:'),     self._make_dbl_spin('hexbin_alpha', 0.05, 1.0, 1.0, 0.05)))
        hxg.addLayout(_row(QLabel('Colormap:'),  self._make_combo('hexbin_cmap_combo', _CMAP_LIST)))
        self.hexbin_colorbar = QCheckBox('Show colorbar'); self.hexbin_colorbar.setChecked(True); self.hexbin_colorbar.stateChanged.connect(self.update_preview); hxg.addWidget(self.hexbin_colorbar)
        self.hexbin_log      = QCheckBox('Log scale counts'); self.hexbin_log.stateChanged.connect(self.update_preview); hxg.addWidget(self.hexbin_log)
        layout.addWidget(self.hexbin_group)

        # ── Radar / Spider (chart-mode options only) ──────────────────────────
        self.radar_group = QGroupBox('Radar / Spider Options')
        rdr = QVBoxLayout(self.radar_group)
        rdr.addLayout(_row(QLabel('Grid levels:'), self._make_spin('radar_gridlevels', 3, 10, 5)))
        layout.addWidget(self.radar_group)

        # ── ECDF (chart-mode options only) ────────────────────────────────────
        self.ecdf_group = QGroupBox('ECDF Options')
        ecg = QVBoxLayout(self.ecdf_group)
        self.ecdf_complementary = QCheckBox('Complementary (1 − F)'); self.ecdf_complementary.stateChanged.connect(self.update_preview); ecg.addWidget(self.ecdf_complementary)
        layout.addWidget(self.ecdf_group)

        # ── Quiver ────────────────────────────────────────────────────────────
        self.quiver_group = QGroupBox('Quiver (Vector Field) Options')
        qvg = QVBoxLayout(self.quiver_group)
        qvg.addLayout(_row(QLabel('U col (dx):'), self._make_col_combo('quiver_u_combo', '(none)')))
        qvg.addLayout(_row(QLabel('V col (dy):'), self._make_col_combo('quiver_v_combo', '(none)')))
        qvg.addLayout(_row(QLabel('Scale:'),      self._make_dbl_spin('quiver_scale', 0.01, 1000, 1.0, 0.01)))
        qvg.addLayout(_row(QLabel('Arrow width:'), self._make_dbl_spin('quiver_width', 0.001, 0.05, 0.005, 0.001, decimals=3)))
        self.quiver_color_by_mag = QCheckBox('Color by magnitude'); self.quiver_color_by_mag.stateChanged.connect(self.update_preview); qvg.addWidget(self.quiver_color_by_mag)
        qvg.addLayout(_row(QLabel('Colormap:'), self._make_combo('quiver_cmap_combo', _CMAP_LIST)))
        layout.addWidget(self.quiver_group)

    # ── Widget factory helpers ─────────────────────────────────────────────────
