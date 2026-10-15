"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_series.py  –  plotviz
SeriesTabMixin: create_series_tab(): series table and per-series options.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QPushButton, QCheckBox, QScrollArea, QGroupBox, QSizePolicy, QPlainTextEdit,
)
from PyQt6.QtGui import QFont
from data.scientific import CurveFitter
from ui.tab_constants import (
    _CMAP_LIST,
)


class SeriesTabMixin:
    # ─── Series tab ───────────────────────────────────────────────────────────
    def create_series_tab(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(4)

        def row(label_text, widget_obj, stretch=True):
            r = QHBoxLayout()
            r.setSpacing(6)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(90)
            r.addWidget(lbl)
            r.addWidget(widget_obj)
            if stretch: r.addStretch()
            layout.addLayout(r)

        # ── Active subplot selector (shown when n > 1) ───────────────────────
        sc_sp_row = QHBoxLayout()
        sc_sp_row.setSpacing(6)
        sc_sp_row.addWidget(QLabel('Subplot:'))
        self.series_curve_sp_active = QComboBox()
        self.series_curve_sp_active.addItem('Subplot 1')
        self.series_curve_sp_active.currentIndexChanged.connect(self._on_series_curve_sp_changed)
        sc_sp_row.addWidget(self.series_curve_sp_active)
        sc_sp_row.addStretch()
        self._series_curve_sp_row_widget = QWidget()
        self._series_curve_sp_row_widget.setLayout(sc_sp_row)
        self._series_curve_sp_row_widget.setVisible(False)
        layout.addWidget(self._series_curve_sp_row_widget)

        # ── Per-curve ─────────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Per-Curve'))
        self.curve_select = QComboBox()
        self.curve_select.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.curve_select.currentIndexChanged.connect(lambda _: self.load_curve_style())
        self.curve_select.currentIndexChanged.connect(lambda _: self._on_fit_series_changed())
        layout.addWidget(self.curve_select)

        # Line style
        self.curve_linestyle = QComboBox()
        self.curve_linestyle.addItems(['-','--','-.', ':','none'])
        self.curve_linestyle.setCurrentIndex(0)
        self.curve_linestyle.currentTextChanged.connect(lambda _: self.save_curve_style())
        row('Line style:', self.curve_linestyle)

        # Curve color inline
        cr = QHBoxLayout()
        cr.setSpacing(6)
        lbl_cc = QLabel('Color:')
        lbl_cc.setFixedWidth(90)
        cr.addWidget(lbl_cc)
        self.curve_color = '#1f77b4'
        self.curve_color_label = self._color_sw('#1f77b4')
        cr.addWidget(self.curve_color_label)
        btn_cc = QPushButton('…')
        btn_cc.setFixedWidth(28)
        btn_cc.clicked.connect(lambda: self.pick_color('curve'))
        cr.addWidget(btn_cc)
        self.curve_lock_label = QLabel('🔒')
        self.curve_lock_label.setToolTip('Color is manually locked')
        self.curve_lock_label.setVisible(False)
        cr.addWidget(self.curve_lock_label)
        btn_unlock = QPushButton('Unlock')
        btn_unlock.setFixedWidth(56)
        btn_unlock.setToolTip('Remove manual lock — palette color will be used')
        btn_unlock.clicked.connect(self._unlock_curve_color)
        cr.addWidget(btn_unlock)
        cr.addStretch()
        layout.addLayout(cr)

        self.curve_marker = QComboBox()
        self.curve_marker.addItems(['None','o','s','^','v','D','*','+','x'])
        self.curve_marker.setCurrentIndex(0)
        self.curve_marker.currentTextChanged.connect(lambda _: self.save_curve_style())
        row('Marker:', self.curve_marker)

        self.curve_linewidth = QDoubleSpinBox()
        self.curve_linewidth.setRange(0.5, 5.0)
        self.curve_linewidth.setValue(1.5)
        self.curve_linewidth.setSingleStep(0.1)
        self.curve_linewidth.editingFinished.connect(self.save_curve_style)

        self.curve_markersize = QDoubleSpinBox()
        self.curve_markersize.setRange(1, 20)
        self.curve_markersize.setValue(6)
        self.curve_markersize.setSingleStep(0.5)
        self.curve_markersize.editingFinished.connect(self.save_curve_style)

        self.curve_marker_color = '#1f77b4'
        self.curve_marker_color_label = self._color_sw('#1f77b4')
        btn_mc = QPushButton('…')
        btn_mc.setFixedWidth(28)
        btn_mc.clicked.connect(lambda: self.pick_color('curve_marker'))
        cwm = QHBoxLayout()
        cwm.setSpacing(4)
        cwm.addWidget(QLabel('W:'))
        cwm.addWidget(self.curve_linewidth)
        cwm.addWidget(QLabel('Size:'))
        cwm.addWidget(self.curve_markersize)
        cwm.addStretch()
        layout.addLayout(cwm)
        mc_row = QHBoxLayout()
        mc_row.setSpacing(4)
        lbl_mc = QLabel('Marker color:')
        lbl_mc.setFixedWidth(90)
        mc_row.addWidget(lbl_mc)
        mc_row.addWidget(self.curve_marker_color_label)
        mc_row.addWidget(btn_mc)
        mc_row.addStretch()
        layout.addLayout(mc_row)

        def _srow(*widgets):
            h = QHBoxLayout()
            for w in widgets: h.addWidget(w)
            return h

        # Line series options
        self.st_line_group = QWidget()
        stlg = QVBoxLayout(self.st_line_group)
        stlg.setContentsMargins(0, 0, 0, 0)
        stlg.setSpacing(4)
        self.line_drawstyle = QComboBox()
        self.line_drawstyle.addItems(['default', 'steps-pre', 'steps-post', 'steps-mid'])
        self.line_drawstyle.currentTextChanged.connect(self.update_preview)
        stlg.addLayout(_srow(QLabel('Draw style:'), self.line_drawstyle))
        layout.addWidget(self.st_line_group)

        # Scatter series options
        self.st_scatter_group = QWidget()
        stsg = QVBoxLayout(self.st_scatter_group)
        stsg.setContentsMargins(0, 0, 0, 0)
        stsg.setSpacing(4)
        stsg.addLayout(_srow(QLabel('Point size:'), self._make_spin('scatter_size', 1, 500, 20)))
        stsg.addLayout(_srow(QLabel('Alpha:'),       self._make_dbl_spin('scatter_alpha', 0.05, 1.0, 0.7, 0.05)))
        stsg.addLayout(_srow(QLabel('Edge color:'),  self._make_edgecolor_combo('scatter_edgecolor', 'none')))
        stsg.addLayout(_srow(QLabel('Edge width:'),  self._make_dbl_spin('scatter_lw', 0.0, 5.0, 0.5, 0.25)))
        self.scatter_colorby_check = QCheckBox('Color by Z column')
        self.scatter_colorby_check.stateChanged.connect(self.update_preview)
        stsg.addWidget(self.scatter_colorby_check)
        stsg.addLayout(_srow(QLabel('Colormap:'), self._make_cmap_combo('scatter_cmap_combo', _CMAP_LIST, default='rainbow')))
        layout.addWidget(self.st_scatter_group)

        # Bar series options
        self.st_bar_group = QWidget()
        stbg = QVBoxLayout(self.st_bar_group)
        stbg.setContentsMargins(0, 0, 0, 0)
        stbg.setSpacing(4)
        stbg.addLayout(_srow(QLabel('Width:'),      self._make_dbl_spin('bar_width', 0.05, 1.0, 0.8, 0.05)))
        stbg.addLayout(_srow(QLabel('Alpha:'),      self._make_dbl_spin('bar_alpha', 0.05, 1.0, 1.0, 0.05)))
        stbg.addLayout(_srow(QLabel('Edge color:'), self._make_edgecolor_combo('bar_edgecolor', 'none')))
        stbg.addLayout(_srow(QLabel('Edge width:'), self._make_dbl_spin('bar_edge_lw', 0.0, 4.0, 0.5, 0.25)))
        self.bar_colorbyval = QCheckBox('Color bars by value')
        self.bar_colorbyval.stateChanged.connect(self.update_preview)
        stbg.addWidget(self.bar_colorbyval)
        layout.addWidget(self.st_bar_group)

        # Histogram series options
        self.st_hist_group = QWidget()
        sthg = QVBoxLayout(self.st_hist_group)
        sthg.setContentsMargins(0, 0, 0, 0)
        sthg.setSpacing(4)
        sthg.addLayout(_srow(QLabel('Alpha:'),      self._make_dbl_spin('hist_alpha', 0.05, 1.0, 0.7, 0.05)))
        sthg.addLayout(_srow(QLabel('Edge color:'), self._make_edgecolor_combo('hist_edgecolor', 'white')))
        layout.addWidget(self.st_hist_group)

        # Errorbar series options
        self.st_err_group = QWidget()
        steg = QVBoxLayout(self.st_err_group)
        steg.setContentsMargins(0, 0, 0, 0)
        steg.setSpacing(4)
        steg.addLayout(_srow(QLabel('Cap size:'),    self._make_spin('err_capsize', 0, 20, 4)))
        steg.addLayout(_srow(QLabel('Cap thick:'),   self._make_dbl_spin('err_capthick', 0.5, 8.0, 1.5, 0.5)))
        steg.addLayout(_srow(QLabel('Err lw:'),      self._make_dbl_spin('err_elinewidth', 0.5, 8.0, 1.5, 0.5)))
        steg.addLayout(_srow(QLabel('X errors:'),    self._make_combo('err_xerr_combo', ['(none)'])))
        self.err_barsabove = QCheckBox('Bars above line')
        self.err_barsabove.stateChanged.connect(self.update_preview)
        steg.addWidget(self.err_barsabove)
        layout.addWidget(self.st_err_group)

        # Area series options
        self.st_area_group = QWidget()
        stag = QVBoxLayout(self.st_area_group)
        stag.setContentsMargins(0, 0, 0, 0)
        stag.setSpacing(4)
        stag.addLayout(_srow(QLabel('Fill alpha:'), self._make_dbl_spin('area_alpha', 0.05, 1.0, 0.4, 0.05)))
        stag.addLayout(_srow(QLabel('Line width:'), self._make_dbl_spin('area_lw', 0.0, 5.0, 0.8, 0.25)))
        self.area_showline = QCheckBox('Show edge line')
        self.area_showline.setChecked(True)
        self.area_showline.stateChanged.connect(self.update_preview)
        stag.addWidget(self.area_showline)
        layout.addWidget(self.st_area_group)

        # Fill Between series options
        self.st_fill_between_group = QWidget()
        stfbg = QVBoxLayout(self.st_fill_between_group)
        stfbg.setContentsMargins(0, 0, 0, 0)
        stfbg.setSpacing(4)
        stfbg.addLayout(_srow(QLabel('Fill alpha:'), self._make_dbl_spin('fill_between_alpha', 0.05, 1.0, 0.4, 0.05)))
        stfbg.addLayout(_srow(QLabel('Line width:'), self._make_dbl_spin('fill_between_lw', 0.0, 5.0, 0.8, 0.25)))
        self.fill_between_showline = QCheckBox('Show edge lines')
        self.fill_between_showline.setChecked(True)
        self.fill_between_showline.stateChanged.connect(self.update_preview)
        stfbg.addWidget(self.fill_between_showline)
        layout.addWidget(self.st_fill_between_group)

        # Step series options
        self.st_step_group = QWidget()
        ststg = QVBoxLayout(self.st_step_group)
        ststg.setContentsMargins(0, 0, 0, 0)
        ststg.setSpacing(4)
        self.step_fill = QCheckBox('Fill under')
        self.step_fill.stateChanged.connect(self.update_preview)
        ststg.addWidget(self.step_fill)
        ststg.addLayout(_srow(QLabel('Fill alpha:'), self._make_dbl_spin('step_fill_alpha', 0.05, 1.0, 0.2, 0.05)))
        layout.addWidget(self.st_step_group)

        # Bubble series options
        self.st_bubble_group = QWidget()
        stbug = QVBoxLayout(self.st_bubble_group)
        stbug.setContentsMargins(0, 0, 0, 0)
        stbug.setSpacing(4)
        stbug.addLayout(_srow(QLabel('Size col:'),   self._make_col_combo('bubble_size_combo', '(uniform)')))
        stbug.addLayout(_srow(QLabel('Scale:'),      self._make_dbl_spin('bubble_scale', 1, 5000, 200, 50)))
        stbug.addLayout(_srow(QLabel('Alpha:'),      self._make_dbl_spin('bubble_alpha', 0.05, 1.0, 0.6, 0.05)))
        stbug.addLayout(_srow(QLabel('Edge color:'), self._make_edgecolor_combo('bubble_edgecolor', 'none')))
        layout.addWidget(self.st_bubble_group)

        # Polar series options
        self.st_polar_group = QWidget()
        stplg = QVBoxLayout(self.st_polar_group)
        stplg.setContentsMargins(0, 0, 0, 0)
        stplg.setSpacing(4)
        self.polar_fill = QCheckBox('Fill')
        self.polar_fill.stateChanged.connect(self.update_preview)
        stplg.addWidget(self.polar_fill)
        stplg.addLayout(_srow(QLabel('Fill alpha:'), self._make_dbl_spin('polar_fill_alpha', 0.05, 1.0, 0.2, 0.05)))
        layout.addWidget(self.st_polar_group)

        # Radar series options
        self.st_radar_group = QWidget()
        strdr = QVBoxLayout(self.st_radar_group)
        strdr.setContentsMargins(0, 0, 0, 0)
        strdr.setSpacing(4)
        self.radar_fill = QCheckBox('Fill')
        self.radar_fill.setChecked(True)
        self.radar_fill.stateChanged.connect(self.update_preview)
        strdr.addWidget(self.radar_fill)
        strdr.addLayout(_srow(QLabel('Fill alpha:'), self._make_dbl_spin('radar_fill_alpha', 0.05, 1.0, 0.25, 0.05)))
        layout.addWidget(self.st_radar_group)

        # ECDF series options
        self.st_ecdf_group = QWidget()
        stecg = QVBoxLayout(self.st_ecdf_group)
        stecg.setContentsMargins(0, 0, 0, 0)
        stecg.setSpacing(4)
        self.ecdf_markers = QCheckBox('Show markers')
        self.ecdf_markers.stateChanged.connect(self.update_preview)
        stecg.addWidget(self.ecdf_markers)
        stecg.addLayout(_srow(QLabel('Alpha:'),      self._make_dbl_spin('ecdf_alpha', 0.05, 1.0, 1.0, 0.05)))
        layout.addWidget(self.st_ecdf_group)

        layout.addWidget(self._hline())

        # ── Curve Fit ─────────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Curve Fit (Line / Scatter)'))
        lbl_hint = QLabel('Fits the curve selected above.\nUse Per-Curve controls to style the fit curve.')
        lbl_hint.setStyleSheet('color:#888; font-size:10px;')
        layout.addWidget(lbl_hint)

        fr = QHBoxLayout()
        fr.addWidget(QLabel('Model:'))
        self.fit_combo = QComboBox()
        self.fit_combo.addItem('None')
        self.fit_combo.addItems(CurveFitter.MODELS.keys())
        fr.addWidget(self.fit_combo)
        fr.addStretch()
        layout.addLayout(fr)

        btn_fit = QPushButton('▶  Apply Fit')
        btn_fit.clicked.connect(self.apply_fit)
        btn_remove_fit = QPushButton('✕  Remove Fit')
        btn_remove_fit.clicked.connect(self._remove_fit)
        btn_remove_fit.setToolTip('Remove the fitted curve for the currently selected series')
        fit_btn_row = QHBoxLayout()
        fit_btn_row.setSpacing(4)
        fit_btn_row.addWidget(btn_fit)
        fit_btn_row.addWidget(btn_remove_fit)
        layout.addLayout(fit_btn_row)

        # ── Fit-specific controls (disabled when an original series is selected) ──
        self._fit_controls_widget = QWidget()
        fc_lay = QVBoxLayout(self._fit_controls_widget)
        fc_lay.setContentsMargins(0, 0, 0, 0)
        fc_lay.setSpacing(4)

        ci_row = QHBoxLayout()
        ci_row.setSpacing(6)
        ci_row.addWidget(QLabel('Confidence limits:'))
        self.fit_ci_combo = QComboBox()
        self.fit_ci_combo.addItems(['Off', '1σ  (68%)', '2σ  (95%)', '3σ  (99.7%)'])
        self.fit_ci_combo.currentIndexChanged.connect(self._on_ci_changed)
        ci_row.addWidget(self.fit_ci_combo)
        ci_row.addStretch()
        fc_lay.addLayout(ci_row)

        pi_row = QHBoxLayout()
        pi_row.setSpacing(6)
        pi_row.addWidget(QLabel('Prediction band:'))
        self.fit_pi_combo = QComboBox()
        self.fit_pi_combo.addItems(['Off', '1σ  (68%)', '2σ  (95%)', '3σ  (99.7%)'])
        self.fit_pi_combo.currentIndexChanged.connect(self._on_ci_changed)
        pi_row.addWidget(self.fit_pi_combo)
        pi_row.addStretch()
        fc_lay.addLayout(pi_row)

        self.fit_ci_alpha_spin = QDoubleSpinBox()
        self.fit_ci_alpha_spin.setRange(0.05, 1.0)
        self.fit_ci_alpha_spin.setSingleStep(0.05)
        self.fit_ci_alpha_spin.setValue(0.25)
        self.fit_ci_alpha_spin.valueChanged.connect(self.update_preview)
        ci_alpha_row = QHBoxLayout()
        ci_alpha_row.setSpacing(6)
        ci_alpha_row.addWidget(QLabel('Band opacity:'))
        ci_alpha_row.addWidget(self.fit_ci_alpha_spin)
        ci_alpha_row.addStretch()
        fc_lay.addLayout(ci_alpha_row)

        res_box = QGroupBox('Fit Results')
        res_lay = QVBoxLayout(res_box)
        res_lay.setSpacing(2)
        res_lay.setContentsMargins(4, 4, 4, 4)
        self.fit_results_text = QPlainTextEdit()
        self.fit_results_text.setReadOnly(True)
        self.fit_results_text.setMinimumHeight(180)
        self.fit_results_text.setFont(QFont('Courier New' if __import__('sys').platform == 'win32' else 'Menlo' if __import__('sys').platform == 'darwin' else 'monospace', 9))
        self.fit_results_text.setPlainText('Run a fit to see results.')
        # Keep backwards-compat aliases
        self.fit_eq_label = QLabel('')
        self.fit_eq_label.setVisible(False)
        self.fit_r2_label = QLabel('')
        self.fit_r2_label.setVisible(False)
        res_lay.addWidget(self.fit_results_text)
        fc_lay.addWidget(res_box)

        self._fit_controls_widget.setEnabled(False)
        layout.addWidget(self._fit_controls_widget)

        # ── Export row — outside the fit controls, active whenever fits exist ──
        self._fit_export_widget = QWidget()
        exp_row = QHBoxLayout(self._fit_export_widget)
        exp_row.setContentsMargins(0, 0, 0, 0)
        exp_row.setSpacing(6)
        self.fit_export_all_check = QCheckBox('All fits')
        self.fit_export_all_check.setToolTip('Export results for every fitted curve, not just the currently selected one')
        exp_row.addWidget(self.fit_export_all_check)
        btn_export_fit = QPushButton('⬇  Export Results (.txt)')
        btn_export_fit.clicked.connect(self._export_fit_results)
        exp_row.addWidget(btn_export_fit)
        exp_row.addStretch()
        self._fit_export_widget.setEnabled(False)
        layout.addWidget(self._fit_export_widget)

        layout.addStretch()
        scroll.setWidget(content)
        mlay = QVBoxLayout(widget)
        mlay.addWidget(scroll)
        self.plots_inner_tabs.addTab(widget, 'Curves')
