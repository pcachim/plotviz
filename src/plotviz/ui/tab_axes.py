"""
Copyright (c) 2026 Paulo Cachim
ui/tab_axes.py  –  plotviz
TabAxesMixin: create_axes_tab()
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton, QScrollArea, QButtonGroup,
    QRadioButton, QCheckBox,
)

_FONTS = ['sans-serif', 'serif', 'monospace']


class TabAxesMixin:
    def create_axes_tab(self):
        widget = QWidget()
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); layout = QVBoxLayout(content); layout.setSpacing(5)

        # ── Subplot selector (hidden when n == 1) ─────────────────────────────
        sp_sel_row = QHBoxLayout(); sp_sel_row.setSpacing(6)
        sp_sel_row.addWidget(QLabel('Subplot:'))
        self.sp_active = QComboBox(); self.sp_active.addItem('Subplot 1')
        self.sp_active.currentIndexChanged.connect(self.on_active_subplot_changed)
        sp_sel_row.addWidget(self.sp_active); sp_sel_row.addStretch()
        self._axes_sp_row_widget = QWidget()
        self._axes_sp_row_widget.setLayout(sp_sel_row)
        self._axes_sp_row_widget.setVisible(False)   # shown only when n > 1
        layout.addWidget(self._axes_sp_row_widget)

        layout.addWidget(self._hline())

        # ── Title (hidden when n==1 — chart title is controlled from Style tab) ──
        self._axes_title_section = QWidget()
        _ts_lay = QVBoxLayout(self._axes_title_section); _ts_lay.setContentsMargins(0,0,0,0); _ts_lay.setSpacing(4)
        _ts_lay.addWidget(self._sec_label('Subplot Title'))
        title_row = QHBoxLayout()
        self.title_show_check = QCheckBox('Show title'); self.title_show_check.setChecked(True)
        self.title_show_check.stateChanged.connect(self._on_sp_title_show_changed)
        title_row.addWidget(self.title_show_check); title_row.addStretch()
        _ts_lay.addLayout(title_row)
        self.sp_title_input = QLineEdit(); self.sp_title_input.setPlaceholderText('Subplot 1')
        self.sp_title_input.editingFinished.connect(self._on_sp_title_changed)
        _ts_lay.addWidget(self.sp_title_input)
        sp_tf_row = QHBoxLayout(); sp_tf_row.setSpacing(4)
        self.sp_title_font = QComboBox(); self.sp_title_font.addItems(_FONTS)
        self.sp_title_font.currentTextChanged.connect(lambda _: self._on_sp_title_changed())
        sp_tf_row.addWidget(self.sp_title_font)
        self.sp_title_size = QSpinBox(); self.sp_title_size.setRange(6, 32); self.sp_title_size.setValue(11)
        self.sp_title_size.setFixedWidth(46)
        self.sp_title_size.valueChanged.connect(lambda _: self._on_sp_title_changed())
        sp_tf_row.addWidget(self.sp_title_size)
        self.sp_title_color = '#000000'
        self.sp_title_color_label = QLabel('■'); self.sp_title_color_label.setStyleSheet('color:#000000;font-size:16px;')
        btn_sp_tc = QPushButton('Color'); btn_sp_tc.setFixedWidth(46)
        btn_sp_tc.clicked.connect(lambda: self._pick_sp_title_color())
        sp_tf_row.addWidget(self.sp_title_color_label); sp_tf_row.addWidget(btn_sp_tc)
        sp_tf_row.addStretch(); _ts_lay.addLayout(sp_tf_row)
        _ts_lay.addWidget(self._hline())
        layout.addWidget(self._axes_title_section)
        self._axes_title_section.setVisible(False)  # shown only when n > 1

        # ── X Axis ───────────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('X Axis'))
        xlabel_vis_row = QHBoxLayout()
        self.xlabel_show_check = QCheckBox('Show X label'); self.xlabel_show_check.setChecked(True)
        self.xlabel_show_check.stateChanged.connect(self._on_sp_xlabel_show_changed)
        xlabel_vis_row.addWidget(self.xlabel_show_check); xlabel_vis_row.addStretch()
        layout.addLayout(xlabel_vis_row)
        self.xlabel_input = QLineEdit(); self.xlabel_input.setPlaceholderText('X label (optional)')
        self.xlabel_input.editingFinished.connect(self._on_sp_xlabel_changed)
        layout.addWidget(self.xlabel_input)

        xfont_row = QHBoxLayout(); xfont_row.setSpacing(4)
        xfont_row.addWidget(QLabel('Font:'))
        self.xlabel_font = QComboBox(); self.xlabel_font.addItems(_FONTS)
        self.xlabel_font.currentTextChanged.connect(self.update_preview)
        xfont_row.addWidget(self.xlabel_font)
        xfont_row.addWidget(QLabel('Sz:'))
        self.xlabel_size = QSpinBox(); self.xlabel_size.setRange(6, 32); self.xlabel_size.setValue(11)
        self.xlabel_size.valueChanged.connect(self.update_preview); xfont_row.addWidget(self.xlabel_size)
        btn_xc = QPushButton('Color'); btn_xc.clicked.connect(lambda: self.pick_color('xlabel'))
        xfont_row.addWidget(btn_xc)
        self.xlabel_color_label = QLabel('■'); self.xlabel_color_label.setStyleSheet('color:black;font-size:16px;')
        xfont_row.addWidget(self.xlabel_color_label); self.xlabel_color = '#000000'
        xfont_row.addStretch(); layout.addLayout(xfont_row)

        xlim_row = QHBoxLayout(); xlim_row.setSpacing(4)
        xlim_row.addWidget(QLabel('X min:'))
        self.x_min = QDoubleSpinBox(); self.x_min.setRange(-1e10, 1e10); self.x_min.setSingleStep(0.1)
        self.x_min.editingFinished.connect(self._on_sp_lim_changed); xlim_row.addWidget(self.x_min)
        xlim_row.addWidget(QLabel('max:'))
        self.x_max = QDoubleSpinBox(); self.x_max.setRange(-1e10, 1e10); self.x_max.setValue(1); self.x_max.setSingleStep(0.1)
        self.x_max.editingFinished.connect(self._on_sp_lim_changed); xlim_row.addWidget(self.x_max)
        self.x_auto = QCheckBox('Auto'); self.x_auto.setChecked(True)
        self.x_auto.stateChanged.connect(self._on_sp_lim_changed); xlim_row.addWidget(self.x_auto)
        xlim_row.addStretch(); layout.addLayout(xlim_row)

        layout.addWidget(QLabel('Scale:'))
        self.xscale_group = QButtonGroup(self)
        xsr = QHBoxLayout()
        for lbl, val in [('Linear', 'linear'), ('Log', 'log'), ('Logit', 'logit'), ('Inverted', 'inverted')]:
            rb = QRadioButton(lbl); rb.setProperty('scale_value', val)
            if val == 'linear': rb.setChecked(True)
            rb.toggled.connect(self._save_axes_state)
            self.xscale_group.addButton(rb); xsr.addWidget(rb)
        layout.addLayout(xsr)

        tick_x_row = QHBoxLayout()
        tick_x_row.addWidget(QLabel('Tick size:'))
        self.xtick_size = QSpinBox(); self.xtick_size.setRange(4, 24); self.xtick_size.setValue(9)
        self.xtick_size.valueChanged.connect(self._save_axes_state)
        tick_x_row.addWidget(self.xtick_size)
        tick_x_row.addWidget(QLabel('Direction:'))
        self.xtick_dir = QComboBox(); self.xtick_dir.addItems(['out', 'in', 'inout'])
        self.xtick_dir.currentTextChanged.connect(self._save_axes_state)
        tick_x_row.addWidget(self.xtick_dir); tick_x_row.addStretch()
        layout.addLayout(tick_x_row)

        xtick_row2 = QHBoxLayout()
        self.xticks_show = QCheckBox('Show ticks'); self.xticks_show.setChecked(True)
        self.xticks_show.stateChanged.connect(self._save_axes_state)
        xtick_row2.addWidget(self.xticks_show)
        self.xtick_minor = QCheckBox('Minor ticks'); self.xtick_minor.setChecked(False)
        self.xtick_minor.stateChanged.connect(self._save_axes_state)
        xtick_row2.addWidget(self.xtick_minor); xtick_row2.addStretch()
        layout.addLayout(xtick_row2)

        xtick_row3 = QHBoxLayout()
        xtick_row3.addWidget(QLabel('Rotation:'))
        self.xtick_rotation = QSpinBox(); self.xtick_rotation.setRange(-90, 90); self.xtick_rotation.setValue(0)
        self.xtick_rotation.valueChanged.connect(self._save_axes_state)
        xtick_row3.addWidget(self.xtick_rotation)
        xtick_row3.addWidget(QLabel('Step (0=auto):'))
        self.xtick_step = QDoubleSpinBox(); self.xtick_step.setRange(0, 1e9); self.xtick_step.setValue(0); self.xtick_step.setSingleStep(0.1)
        self.xtick_step.editingFinished.connect(self._save_axes_state)
        xtick_row3.addWidget(self.xtick_step); xtick_row3.addStretch()
        layout.addLayout(xtick_row3)

        xfmt_row = QHBoxLayout()
        xfmt_row.addWidget(QLabel('Format:'))
        self.x_formatter = QComboBox()
        self.x_formatter.addItems(['auto', 'plain', 'sci', 'percent', '{x:.2f}', '{x:.0f}'])
        self.x_formatter.setEditable(True)
        self.x_formatter.currentTextChanged.connect(self._save_axes_state)
        xfmt_row.addWidget(self.x_formatter); xfmt_row.addStretch()
        layout.addLayout(xfmt_row)

        layout.addWidget(self._hline())

        # ── Y Axis (Left) ─────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Y Axis (Left)'))
        ylabel_vis_row = QHBoxLayout()
        self.ylabel_show_check = QCheckBox('Show Y label'); self.ylabel_show_check.setChecked(True)
        self.ylabel_show_check.stateChanged.connect(self._on_sp_ylabel_show_changed)
        ylabel_vis_row.addWidget(self.ylabel_show_check); ylabel_vis_row.addStretch()
        layout.addLayout(ylabel_vis_row)
        self.ylabel_input = QLineEdit(); self.ylabel_input.setPlaceholderText('Y label (optional)')
        self.ylabel_input.editingFinished.connect(self._on_sp_ylabel_changed)
        layout.addWidget(self.ylabel_input)

        yfont_row = QHBoxLayout(); yfont_row.setSpacing(4)
        yfont_row.addWidget(QLabel('Font:'))
        self.ylabel_font = QComboBox(); self.ylabel_font.addItems(_FONTS)
        self.ylabel_font.currentTextChanged.connect(self.update_preview)
        yfont_row.addWidget(self.ylabel_font)
        yfont_row.addWidget(QLabel('Sz:'))
        self.ylabel_size = QSpinBox(); self.ylabel_size.setRange(6, 32); self.ylabel_size.setValue(11)
        self.ylabel_size.valueChanged.connect(self.update_preview); yfont_row.addWidget(self.ylabel_size)
        btn_yc = QPushButton('Color'); btn_yc.clicked.connect(lambda: self.pick_color('ylabel'))
        yfont_row.addWidget(btn_yc)
        self.ylabel_color_label = QLabel('■'); self.ylabel_color_label.setStyleSheet('color:black;font-size:16px;')
        yfont_row.addWidget(self.ylabel_color_label); self.ylabel_color = '#000000'
        yfont_row.addStretch(); layout.addLayout(yfont_row)

        ylim_row = QHBoxLayout(); ylim_row.setSpacing(4)
        ylim_row.addWidget(QLabel('Y min:'))
        self.y_min = QDoubleSpinBox(); self.y_min.setRange(-1e10, 1e10); self.y_min.setSingleStep(0.1)
        self.y_min.editingFinished.connect(self._on_sp_lim_changed); ylim_row.addWidget(self.y_min)
        ylim_row.addWidget(QLabel('max:'))
        self.y_max = QDoubleSpinBox(); self.y_max.setRange(-1e10, 1e10); self.y_max.setValue(1); self.y_max.setSingleStep(0.1)
        self.y_max.editingFinished.connect(self._on_sp_lim_changed); ylim_row.addWidget(self.y_max)
        self.y_auto = QCheckBox('Auto'); self.y_auto.setChecked(True)
        self.y_auto.stateChanged.connect(self._on_sp_lim_changed); ylim_row.addWidget(self.y_auto)
        ylim_row.addStretch(); layout.addLayout(ylim_row)

        layout.addWidget(QLabel('Scale:'))
        self.yscale_group = QButtonGroup(self)
        ysr = QHBoxLayout()
        for lbl, val in [('Linear', 'linear'), ('Log', 'log'), ('Logit', 'logit'), ('Inverted', 'inverted')]:
            rb = QRadioButton(lbl); rb.setProperty('scale_value', val)
            if val == 'linear': rb.setChecked(True)
            rb.toggled.connect(self._save_axes_state)
            self.yscale_group.addButton(rb); ysr.addWidget(rb)
        layout.addLayout(ysr)

        tick_y_row = QHBoxLayout()
        tick_y_row.addWidget(QLabel('Tick size:'))
        self.ytick_size = QSpinBox(); self.ytick_size.setRange(4, 24); self.ytick_size.setValue(9)
        self.ytick_size.valueChanged.connect(self._save_axes_state)
        tick_y_row.addWidget(self.ytick_size)
        tick_y_row.addWidget(QLabel('Direction:'))
        self.ytick_dir = QComboBox(); self.ytick_dir.addItems(['out', 'in', 'inout'])
        self.ytick_dir.currentTextChanged.connect(self._save_axes_state)
        tick_y_row.addWidget(self.ytick_dir); tick_y_row.addStretch()
        layout.addLayout(tick_y_row)

        ytick_row2 = QHBoxLayout()
        self.yticks_show = QCheckBox('Show ticks'); self.yticks_show.setChecked(True)
        self.yticks_show.stateChanged.connect(self._save_axes_state)
        ytick_row2.addWidget(self.yticks_show)
        self.ytick_minor = QCheckBox('Minor ticks'); self.ytick_minor.setChecked(False)
        self.ytick_minor.stateChanged.connect(self._save_axes_state)
        ytick_row2.addWidget(self.ytick_minor); ytick_row2.addStretch()
        layout.addLayout(ytick_row2)

        ytick_row3 = QHBoxLayout()
        ytick_row3.addWidget(QLabel('Rotation:'))
        self.ytick_rotation = QSpinBox(); self.ytick_rotation.setRange(-90, 90); self.ytick_rotation.setValue(0)
        self.ytick_rotation.valueChanged.connect(self._save_axes_state)
        ytick_row3.addWidget(self.ytick_rotation)
        ytick_row3.addWidget(QLabel('Step (0=auto):'))
        self.ytick_step = QDoubleSpinBox(); self.ytick_step.setRange(0, 1e9); self.ytick_step.setValue(0); self.ytick_step.setSingleStep(0.1)
        self.ytick_step.editingFinished.connect(self._save_axes_state)
        ytick_row3.addWidget(self.ytick_step); ytick_row3.addStretch()
        layout.addLayout(ytick_row3)

        yfmt_row = QHBoxLayout()
        yfmt_row.addWidget(QLabel('Format:'))
        self.y_formatter = QComboBox()
        self.y_formatter.addItems(['auto', 'plain', 'sci', 'percent', '{x:.2f}', '{x:.0f}'])
        self.y_formatter.setEditable(True)
        self.y_formatter.currentTextChanged.connect(self._save_axes_state)
        yfmt_row.addWidget(self.y_formatter); yfmt_row.addStretch()
        layout.addLayout(yfmt_row)

        layout.addWidget(self._hline())

        # ── Y Axis (Right / Secondary) ────────────────────────────────────────
        layout.addWidget(self._sec_label('Y Axis (Right / Secondary)'))
        layout.addWidget(QLabel('(Activate by ticking Y2 in the Series table)'))
        y2label_vis_row = QHBoxLayout()
        self.y2label_show_check = QCheckBox('Show Y2 label'); self.y2label_show_check.setChecked(True)
        self.y2label_show_check.stateChanged.connect(self._on_sp_y2label_show_changed)
        y2label_vis_row.addWidget(self.y2label_show_check); y2label_vis_row.addStretch()
        layout.addLayout(y2label_vis_row)
        self.y2label_input = QLineEdit(); self.y2label_input.setPlaceholderText('Y2 label (optional)')
        self.y2label_input.editingFinished.connect(self._on_sp_y2label_changed)
        layout.addWidget(self.y2label_input)

        y2font_row = QHBoxLayout(); y2font_row.setSpacing(4)
        y2font_row.addWidget(QLabel('Font:'))
        self.y2label_font = QComboBox(); self.y2label_font.addItems(_FONTS)
        self.y2label_font.currentTextChanged.connect(self.update_preview)
        y2font_row.addWidget(self.y2label_font)
        y2font_row.addWidget(QLabel('Sz:'))
        self.y2label_size = QSpinBox(); self.y2label_size.setRange(6, 32); self.y2label_size.setValue(11)
        self.y2label_size.valueChanged.connect(self.update_preview); y2font_row.addWidget(self.y2label_size)
        btn_y2c = QPushButton('Color'); btn_y2c.clicked.connect(lambda: self.pick_color('y2label'))
        y2font_row.addWidget(btn_y2c)
        self.y2label_color_label = QLabel('■'); self.y2label_color_label.setStyleSheet('color:black;font-size:16px;')
        y2font_row.addWidget(self.y2label_color_label); self.y2label_color = '#000000'
        y2font_row.addStretch(); layout.addLayout(y2font_row)

        y2lim_row = QHBoxLayout(); y2lim_row.setSpacing(4)
        y2lim_row.addWidget(QLabel('Y2 min:'))
        self.y2_min = QDoubleSpinBox(); self.y2_min.setRange(-1e10, 1e10); self.y2_min.setSingleStep(0.1)
        self.y2_min.editingFinished.connect(self._on_sp_lim_changed); y2lim_row.addWidget(self.y2_min)
        y2lim_row.addWidget(QLabel('max:'))
        self.y2_max = QDoubleSpinBox(); self.y2_max.setRange(-1e10, 1e10); self.y2_max.setValue(1); self.y2_max.setSingleStep(0.1)
        self.y2_max.editingFinished.connect(self._on_sp_lim_changed); y2lim_row.addWidget(self.y2_max)
        self.y2_auto = QCheckBox('Auto'); self.y2_auto.setChecked(True)
        self.y2_auto.stateChanged.connect(self._on_sp_lim_changed); y2lim_row.addWidget(self.y2_auto)
        y2lim_row.addStretch(); layout.addLayout(y2lim_row)

        layout.addWidget(self._hline())

        # ── Legend ────────────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Legend'))
        leg_row = QHBoxLayout()
        self.legend_show_check = QCheckBox('Show legend'); self.legend_show_check.setChecked(True)
        self.legend_show_check.stateChanged.connect(self._on_sp_legend_changed)
        leg_row.addWidget(self.legend_show_check)
        self.legend_pos = QComboBox()
        self.legend_pos.addItems(['best', 'upper right', 'upper left', 'upper center',
                                  'lower right', 'lower left', 'lower center',
                                  'center right', 'center left', 'center'])
        self.legend_pos.currentTextChanged.connect(self._on_sp_legend_changed)
        leg_row.addWidget(self.legend_pos); leg_row.addStretch()
        layout.addLayout(leg_row)

        layout.addStretch()
        scroll.setWidget(content); mlay = QVBoxLayout(widget); mlay.addWidget(scroll)
        self.tabs.addTab(widget, 'Axes')


    # ─── Style tab ────────────────────────────────────────────────────────────
