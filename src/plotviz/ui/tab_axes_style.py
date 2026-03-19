"""
Copyright (c) 2026 Paulo Cachim
ui/tab_axes_style.py  –  plotviz
TabStyleMixin: create_style_tab()
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton, QScrollArea, QGroupBox,
    QCheckBox, QButtonGroup, QRadioButton,
)

_FONTS = ['sans-serif', 'serif', 'monospace']


class TabStyleMixin:
    def create_style_tab(self):
        widget = QWidget(); scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); layout = QVBoxLayout(content)
        layout.setSpacing(4)

        def row(label_text, widget_obj, stretch=True):
            r = QHBoxLayout(); r.setSpacing(6)
            lbl = QLabel(label_text); lbl.setFixedWidth(90)
            r.addWidget(lbl); r.addWidget(widget_obj)
            if stretch: r.addStretch()
            layout.addLayout(r)

        def color_row(label_text, attr_name, default_hex, pick_target=None):
            r = QHBoxLayout(); r.setSpacing(6)
            lbl = QLabel(label_text); lbl.setFixedWidth(90); r.addWidget(lbl)
            swatch = QLabel('■'); swatch.setStyleSheet(f'color:{default_hex};font-size:18px;')
            setattr(self, attr_name + '_swatch', swatch); r.addWidget(swatch)
            hex_lbl = QLabel(default_hex); hex_lbl.setFixedWidth(58)
            setattr(self, attr_name + '_hex', hex_lbl); r.addWidget(hex_lbl)
            setattr(self, attr_name, default_hex)
            btn = QPushButton('…'); btn.setFixedWidth(28)
            target = pick_target or attr_name
            btn.clicked.connect(lambda _=False, t=target: self.pick_color(t))
            r.addWidget(btn); r.addStretch(); layout.addLayout(r)

        # ── Chart Title ───────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Chart Title'))
        title_row = QHBoxLayout()
        self.title_check = QCheckBox('Show Title'); self.title_check.setChecked(True)
        self.title_check.stateChanged.connect(self.update_preview); title_row.addWidget(self.title_check)
        self.title_input = QLineEdit(); self.title_input.setPlaceholderText('Main title')
        self.title_input.editingFinished.connect(self.update_preview)
        title_row.addWidget(self.title_input); layout.addLayout(title_row)
        tfont_row = QHBoxLayout(); tfont_row.addWidget(QLabel('Font:'))
        self.title_font = QComboBox(); self.title_font.addItems(_FONTS)
        self.title_font.currentTextChanged.connect(self.update_preview); tfont_row.addWidget(self.title_font)
        tfont_row.addWidget(QLabel('Size:'))
        self.title_size = QSpinBox(); self.title_size.setRange(6,32); self.title_size.setValue(14)
        self.title_size.valueChanged.connect(self.update_preview); tfont_row.addWidget(self.title_size)
        tbtn = QPushButton('Color'); tbtn.clicked.connect(lambda: self.pick_color('title')); tfont_row.addWidget(tbtn)
        self.title_color_label = QLabel('■'); self.title_color_label.setStyleSheet('color:#000000;font-size:16px;')
        tfont_row.addWidget(self.title_color_label); self.title_color = '#000000'
        tfont_row.addStretch(); layout.addLayout(tfont_row)

        # Chart title X / Y position (figure-normalised coords)
        tpos_row = QHBoxLayout(); tpos_row.setSpacing(4)
        tpos_row.addWidget(QLabel('X:'))
        self.title_x = QDoubleSpinBox(); self.title_x.setRange(0.0, 1.0)
        self.title_x.setSingleStep(0.01); self.title_x.setDecimals(2); self.title_x.setValue(0.5)
        self.title_x.setFixedWidth(66); self.title_x.valueChanged.connect(self.update_preview)
        self.title_x.setToolTip('Horizontal position (0=left, 0.5=centre, 1=right)')
        tpos_row.addWidget(self.title_x)
        tpos_row.addWidget(QLabel('Y:'))
        self.title_y = QDoubleSpinBox(); self.title_y.setRange(0.50, 1.00)
        self.title_y.setSingleStep(0.01); self.title_y.setDecimals(2); self.title_y.setValue(0.97)
        self.title_y.setFixedWidth(66); self.title_y.valueChanged.connect(self.update_preview)
        self.title_y.setToolTip('Vertical position in figure (0.97 = near top, inside drawing zone)')
        tpos_row.addWidget(self.title_y)
        tpos_row.addStretch(); layout.addLayout(tpos_row)
        # Keep title_y_offset as hidden alias for serialization compat
        self.title_y_offset = self.title_y

        layout.addWidget(self._hline())

        # ── Figure size ───────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Figure Size'))

        # Presets row
        pr = QHBoxLayout(); pr.setSpacing(6)
        pr.addWidget(QLabel('Preset:'))
        self.fig_preset_combo = QComboBox()
        self._fig_presets = [
            ('20 × 10 cm',   20.0, 10.0),
            ('20 × 12.5 cm', 20.0, 12.5),
            ('20 × 15 cm',   20.0, 15.0),
            ('20 × 17.5 cm', 20.0, 17.5),
            ('20 × 20 cm',   20.0, 20.0),
            ('Custom',        None, None),
        ]
        self.fig_preset_combo.addItems([p[0] for p in self._fig_presets])
        self.fig_preset_combo.setCurrentIndex(2)   # default: 20 × 15 cm
        self.fig_preset_combo.currentIndexChanged.connect(self._on_fig_preset_changed)
        pr.addWidget(self.fig_preset_combo); pr.addStretch()
        layout.addLayout(pr)

        # Units + W + H on one row
        sz_row = QHBoxLayout(); sz_row.setSpacing(6)
        sz_row.addWidget(QLabel('Units:'))
        self.fig_unit = QComboBox(); self.fig_unit.addItems(['cm', 'inches', 'pixels'])
        self.fig_unit.setFixedWidth(70)
        self.fig_unit.currentTextChanged.connect(self._on_fig_unit_changed)
        sz_row.addWidget(self.fig_unit)
        sz_row.addWidget(QLabel('W:'))
        self.fig_width = QDoubleSpinBox(); self.fig_width.setDecimals(1)
        self.fig_width.setRange(2, 200); self.fig_width.setValue(20.0)
        self.fig_width.setSingleStep(0.5)
        self.fig_width.valueChanged.connect(self._on_figsize_manual_change)
        sz_row.addWidget(self.fig_width)
        sz_row.addWidget(QLabel('H:'))
        self.fig_height = QDoubleSpinBox(); self.fig_height.setDecimals(1)
        self.fig_height.setRange(2, 200); self.fig_height.setValue(15.0)
        self.fig_height.setSingleStep(0.5)
        self.fig_height.valueChanged.connect(self._on_figsize_manual_change)
        sz_row.addWidget(self.fig_height); sz_row.addStretch()
        layout.addLayout(sz_row)

        # ── Margins (2-column layout) ─────────────────────────────────────────
        layout.addWidget(self._sec_label('Margins'))
        margins_grid = QHBoxLayout(); margins_grid.setSpacing(10)
        left_col = QVBoxLayout(); right_col = QVBoxLayout()
        for attr, label, default, col in [
            ('fig_left',   'Left',   0.10, left_col),
            ('fig_right',  'Right',  0.95, right_col),
            ('fig_bottom', 'Bottom', 0.10, left_col),
            ('fig_top',    'Top',    0.95, right_col),
        ]:
            mr = QHBoxLayout(); mr.setSpacing(4)
            lbl = QLabel(label); lbl.setFixedWidth(44); mr.addWidget(lbl)
            sp = QDoubleSpinBox(); sp.setRange(0.0, 1.0); sp.setSingleStep(0.01)
            sp.setDecimals(2); sp.setValue(default); sp.setFixedWidth(62)
            sp.valueChanged.connect(self.update_preview)
            setattr(self, attr, sp)
            mr.addWidget(sp); col.addLayout(mr)
        margins_grid.addLayout(left_col); margins_grid.addLayout(right_col)
        margins_grid.addStretch(); layout.addLayout(margins_grid)

        # Subplot spacing (hspace / wspace)
        sp_row = QHBoxLayout(); sp_row.setSpacing(6)
        sp_row.addWidget(QLabel('H spacing:'))
        self.sp_hspace = QDoubleSpinBox(); self.sp_hspace.setRange(0.0, 1.0)
        self.sp_hspace.setSingleStep(0.05); self.sp_hspace.setDecimals(2); self.sp_hspace.setValue(0.35)
        self.sp_hspace.setFixedWidth(66); self.sp_hspace.setToolTip('Vertical gap between subplot rows')
        self.sp_hspace.valueChanged.connect(self.update_preview); sp_row.addWidget(self.sp_hspace)
        sp_row.addWidget(QLabel('W spacing:'))
        self.sp_wspace = QDoubleSpinBox(); self.sp_wspace.setRange(0.0, 1.0)
        self.sp_wspace.setSingleStep(0.05); self.sp_wspace.setDecimals(2); self.sp_wspace.setValue(0.35)
        self.sp_wspace.setFixedWidth(66); self.sp_wspace.setToolTip('Horizontal gap between subplot columns')
        self.sp_wspace.valueChanged.connect(self.update_preview); sp_row.addWidget(self.sp_wspace)
        sp_row.addStretch(); layout.addLayout(sp_row)

        layout.addWidget(self._hline())

        # Dummy preset_combo to keep _collect_settings/_apply_settings happy
        self.preset_combo = QComboBox(); self.preset_combo.setVisible(False)
        layout.addWidget(self.preset_combo)

        # ── Chart background / foreground / borders ───────────────────────────
        layout.addWidget(self._sec_label('Chart Canvas'))
        color_row('BG color:', 'chart_bg_color',  '#ffffff', 'chart_bg')
        color_row('FG color:', 'chart_fg_color',  '#000000', 'chart_fg')
        color_row('Plot area:', 'plot_bg_color', '#ffffff', 'plot_bg')

        br = QHBoxLayout(); br.setSpacing(6)
        self.border_top    = QCheckBox('Top');    self.border_top.setChecked(True)
        self.border_bottom = QCheckBox('Bottom'); self.border_bottom.setChecked(True)
        self.border_left   = QCheckBox('Left');   self.border_left.setChecked(True)
        self.border_right  = QCheckBox('Right');  self.border_right.setChecked(True)
        lbl_b = QLabel('Borders:'); lbl_b.setFixedWidth(90); br.addWidget(lbl_b)
        for chk in (self.border_top, self.border_bottom, self.border_left, self.border_right):
            chk.stateChanged.connect(self.update_preview); br.addWidget(chk)
        br.addStretch(); layout.addLayout(br)

        layout.addWidget(self._hline())

        # ── Per-curve ─────────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Per-Curve'))
        self.curve_select = QComboBox()
        self.curve_select.currentIndexChanged.connect(self.load_curve_style)
        row('Curve:', self.curve_select)

        # Line style
        self.curve_linestyle = QComboBox(); self.curve_linestyle.addItems(['-','--','-.', ':','none'])
        self.curve_linestyle.setCurrentIndex(0)
        self.curve_linestyle.currentTextChanged.connect(lambda _: self.save_curve_style())
        row('Line style:', self.curve_linestyle)

        # Curve color inline
        cr = QHBoxLayout(); cr.setSpacing(6)
        lbl_cc = QLabel('Color:'); lbl_cc.setFixedWidth(90); cr.addWidget(lbl_cc)
        self.curve_color_label = QLabel('■ #1f77b4'); cr.addWidget(self.curve_color_label)
        self.curve_color = '#1f77b4'
        btn_cc = QPushButton('…'); btn_cc.setFixedWidth(28)
        btn_cc.clicked.connect(lambda: self.pick_color('curve')); cr.addWidget(btn_cc)
        self.curve_lock_label = QLabel('🔒'); self.curve_lock_label.setToolTip('Color is manually locked')
        self.curve_lock_label.setVisible(False); cr.addWidget(self.curve_lock_label)
        btn_unlock = QPushButton('Unlock'); btn_unlock.setFixedWidth(56)
        btn_unlock.setToolTip('Remove manual lock — palette color will be used')
        btn_unlock.clicked.connect(self._unlock_curve_color); cr.addWidget(btn_unlock)
        cr.addStretch(); layout.addLayout(cr)

        self.curve_marker = QComboBox()
        self.curve_marker.addItems(['None','o','s','^','v','D','*','+','x'])
        self.curve_marker.setCurrentIndex(0)
        self.curve_marker.currentTextChanged.connect(lambda _: self.save_curve_style())
        row('Marker:', self.curve_marker)

        self.curve_linewidth = QDoubleSpinBox(); self.curve_linewidth.setRange(0.5,5.0)
        self.curve_linewidth.setValue(1.5); self.curve_linewidth.setSingleStep(0.1)
        self.curve_linewidth.editingFinished.connect(self.save_curve_style)

        self.curve_markersize = QDoubleSpinBox(); self.curve_markersize.setRange(1,20)
        self.curve_markersize.setValue(6); self.curve_markersize.setSingleStep(0.5)
        self.curve_markersize.editingFinished.connect(self.save_curve_style)

        # W + Size (renamed) + Mkr Color (renamed, same line)
        self.curve_marker_color_label = QLabel('■ #1f77b4')
        self.curve_marker_color = '#1f77b4'
        btn_mc = QPushButton('…'); btn_mc.setFixedWidth(28)
        btn_mc.clicked.connect(lambda: self.pick_color('curve_marker'))
        cwm = QHBoxLayout(); cwm.setSpacing(4)
        cwm.addWidget(QLabel('W:')); cwm.addWidget(self.curve_linewidth)
        cwm.addWidget(QLabel('Size:')); cwm.addWidget(self.curve_markersize)
        cwm.addWidget(QLabel('Color:')); cwm.addWidget(self.curve_marker_color_label)
        cwm.addWidget(btn_mc)
        cwm.addStretch(); layout.addLayout(cwm)

        layout.addWidget(self._hline())

        # ── Grid (major | minor side by side) ─────────────────────────────────
        layout.addWidget(self._sec_label('Grid'))
        grid_row = QHBoxLayout(); grid_row.setSpacing(6)

        # --- Major ---
        maj_box = QGroupBox('Major')
        maj_lay = QVBoxLayout(maj_box); maj_lay.setSpacing(3)
        self.grid_check = QCheckBox('Enable'); self.grid_check.setChecked(True)
        self.grid_check.stateChanged.connect(self.update_preview)
        maj_lay.addWidget(self.grid_check)
        # color
        c1 = QHBoxLayout(); c1.setSpacing(3)
        self.grid_color = '#cccccc'
        self.grid_color_sw = QLabel('■'); self.grid_color_sw.setStyleSheet('color:#cccccc;font-size:15px;')
        g_btn = QPushButton('…'); g_btn.setFixedWidth(22)
        g_btn.clicked.connect(lambda: self._pick_grid_color('major'))
        c1.addWidget(self.grid_color_sw); c1.addWidget(g_btn); c1.addStretch()
        maj_lay.addLayout(c1)
        # style
        self.grid_linestyle = QComboBox(); self.grid_linestyle.addItems(['-','--','-.', ':'])
        self.grid_linestyle.setCurrentText('--')
        self.grid_linestyle.currentTextChanged.connect(self.update_preview)
        maj_lay.addWidget(self.grid_linestyle)
        # width
        wl1 = QHBoxLayout(); wl1.setSpacing(3); wl1.addWidget(QLabel('W:'))
        self.grid_linewidth = QDoubleSpinBox(); self.grid_linewidth.setRange(0.1,4.0)
        self.grid_linewidth.setValue(0.5); self.grid_linewidth.setSingleStep(0.1)
        self.grid_linewidth.valueChanged.connect(self.update_preview)
        wl1.addWidget(self.grid_linewidth); maj_lay.addLayout(wl1)
        # alpha
        al1 = QHBoxLayout(); al1.setSpacing(3); al1.addWidget(QLabel('α:'))
        self.grid_alpha = QDoubleSpinBox(); self.grid_alpha.setRange(0.0,1.0)
        self.grid_alpha.setValue(0.4); self.grid_alpha.setSingleStep(0.05)
        self.grid_alpha.valueChanged.connect(self.update_preview)
        al1.addWidget(self.grid_alpha); maj_lay.addLayout(al1)
        grid_row.addWidget(maj_box)

        # --- Minor ---
        min_box = QGroupBox('Minor')
        min_lay = QVBoxLayout(min_box); min_lay.setSpacing(3)
        self.minor_grid_check = QCheckBox('Enable')
        self.minor_grid_check.stateChanged.connect(self.update_preview)
        min_lay.addWidget(self.minor_grid_check)
        # color
        c2 = QHBoxLayout(); c2.setSpacing(3)
        self.minor_grid_color = '#e8e8e8'
        self.minor_grid_color_sw = QLabel('■'); self.minor_grid_color_sw.setStyleSheet('color:#e8e8e8;font-size:15px;')
        sg_btn = QPushButton('…'); sg_btn.setFixedWidth(22)
        sg_btn.clicked.connect(lambda: self._pick_grid_color('minor'))
        c2.addWidget(self.minor_grid_color_sw); c2.addWidget(sg_btn); c2.addStretch()
        min_lay.addLayout(c2)
        # style
        self.minor_grid_linestyle = QComboBox(); self.minor_grid_linestyle.addItems(['-','--','-.', ':'])
        self.minor_grid_linestyle.setCurrentText(':')
        self.minor_grid_linestyle.currentTextChanged.connect(self.update_preview)
        min_lay.addWidget(self.minor_grid_linestyle)
        # width
        wl2 = QHBoxLayout(); wl2.setSpacing(3); wl2.addWidget(QLabel('W:'))
        self.minor_grid_linewidth = QDoubleSpinBox(); self.minor_grid_linewidth.setRange(0.1,4.0)
        self.minor_grid_linewidth.setValue(0.3); self.minor_grid_linewidth.setSingleStep(0.1)
        self.minor_grid_linewidth.valueChanged.connect(self.update_preview)
        wl2.addWidget(self.minor_grid_linewidth); min_lay.addLayout(wl2)
        # alpha
        al2 = QHBoxLayout(); al2.setSpacing(3); al2.addWidget(QLabel('α:'))
        self.minor_grid_alpha = QDoubleSpinBox(); self.minor_grid_alpha.setRange(0.0,1.0)
        self.minor_grid_alpha.setValue(0.2); self.minor_grid_alpha.setSingleStep(0.05)
        self.minor_grid_alpha.valueChanged.connect(self.update_preview)
        al2.addWidget(self.minor_grid_alpha); min_lay.addLayout(al2)
        grid_row.addWidget(min_box)

        layout.addLayout(grid_row)

        layout.addStretch()
        scroll.setWidget(content); mlay = QVBoxLayout(widget); mlay.addWidget(scroll)
        self.tabs.addTab(widget,'Style')

    # ─── Annotations tab ──────────────────────────────────────────────────────
