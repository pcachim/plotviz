"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_annotations.py  –  plotviz
AnnotationsTabMixin: create_annotations_tab(): text/arrow/image annotations.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton, QListWidget,
    QCheckBox, QScrollArea,
)
from ui.tab_constants import (
    _FONTS,
)


class AnnotationsTabMixin:
    # ─── Annotations tab ──────────────────────────────────────────────────────
    def create_annotations_tab(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(4)

        def irow(*widgets):
            r = QHBoxLayout()
            r.setSpacing(4)
            for w in widgets: r.addWidget(w)
            r.addStretch()
            layout.addLayout(r)

        def lrow(label, *widgets):
            r = QHBoxLayout()
            r.setSpacing(4)
            lb = QLabel(label)
            lb.setFixedWidth(76)
            r.addWidget(lb)
            for w in widgets: r.addWidget(w)
            r.addStretch()
            layout.addLayout(r)

        def color_btn(attr, default):
            sw = self._color_sw(default)
            setattr(self, attr, default)
            setattr(self, attr + '_sw', sw)
            btn = QPushButton('…')
            btn.setFixedWidth(28)
            btn.clicked.connect(lambda _=False, a=attr: self._pick_ann_color_attr(a))
            return sw, btn

        # ── Subplot selector ─────────────────────────────────────────────────
        ann_sp_row = QHBoxLayout()
        ann_sp_row.setSpacing(6)
        ann_sp_row.addWidget(QLabel('Subplot:'))
        self.ann_sp_active = QComboBox()
        self.ann_sp_active.addItem('Subplot 1')
        self.ann_sp_active.currentIndexChanged.connect(self._on_ann_subplot_changed)
        ann_sp_row.addWidget(self.ann_sp_active)
        ann_sp_row.addStretch()
        self._ann_sp_row_widget = QWidget()
        self._ann_sp_row_widget.setLayout(ann_sp_row)
        self._ann_sp_row_widget.setVisible(False)
        layout.addWidget(self._ann_sp_row_widget)

        layout.addWidget(self._hline())

        # ── Subplot Title (moved from Axes; hidden when n==1) ─────────────────
        self._axes_title_section = QWidget()
        _ts_lay = QVBoxLayout(self._axes_title_section)
        _ts_lay.setContentsMargins(0, 0, 0, 0)
        _ts_lay.setSpacing(4)
        _ts_lay.addWidget(self._sec_label('Subplot Title'))
        title_row = QHBoxLayout()
        self.title_show_check = QCheckBox('Show title')
        self.title_show_check.setChecked(True)
        self.title_show_check.stateChanged.connect(self._on_sp_title_show_changed)
        title_row.addWidget(self.title_show_check)
        title_row.addStretch()
        _ts_lay.addLayout(title_row)
        self.sp_title_input = QLineEdit()
        self.sp_title_input.setPlaceholderText('Subplot 1')
        self.sp_title_input.editingFinished.connect(self._on_sp_title_changed)
        _ts_lay.addWidget(self.sp_title_input)
        sp_tf_row = QHBoxLayout()
        sp_tf_row.setSpacing(4)
        self.sp_title_font = QComboBox()
        self.sp_title_font.addItems(_FONTS)
        self.sp_title_font.currentTextChanged.connect(lambda _: self._on_sp_title_changed())
        sp_tf_row.addWidget(self.sp_title_font)
        self.sp_title_size = QSpinBox()
        self.sp_title_size.setRange(6, 32)
        self.sp_title_size.setValue(11)
        self.sp_title_size.setFixedWidth(46)
        self.sp_title_size.valueChanged.connect(lambda _: self._on_sp_title_changed())
        sp_tf_row.addWidget(self.sp_title_size)
        self.sp_title_color = '#000000'
        self.sp_title_color_label = self._color_sw('#000000')
        btn_sp_tc = QPushButton('…')
        btn_sp_tc.setFixedWidth(28)
        btn_sp_tc.clicked.connect(lambda: self._pick_sp_title_color())
        sp_tf_row.addWidget(QLabel('Color:'))
        sp_tf_row.addWidget(self.sp_title_color_label)
        sp_tf_row.addWidget(btn_sp_tc)
        sp_tf_row.addStretch()
        _ts_lay.addLayout(sp_tf_row)

        # ── Subplot title extra: pad + rotation + alignment ──────────────────
        sp_textra_row = QHBoxLayout()
        sp_textra_row.setSpacing(4)
        sp_textra_row.addWidget(QLabel('Pad:'))
        self.sp_title_pad = QSpinBox()
        self.sp_title_pad.setRange(0, 50)
        self.sp_title_pad.setValue(6)
        self.sp_title_pad.setFixedWidth(46)
        self.sp_title_pad.setToolTip('Distance between subplot title and top of axes (points)')
        self.sp_title_pad.valueChanged.connect(lambda _: self._on_sp_title_changed())
        sp_textra_row.addWidget(self.sp_title_pad)
        sp_textra_row.addWidget(QLabel('Rot:'))
        self.sp_title_rotation = QSpinBox()
        self.sp_title_rotation.setRange(-180, 180)
        self.sp_title_rotation.setValue(0)
        self.sp_title_rotation.setFixedWidth(52)
        self.sp_title_rotation.setToolTip('Rotation of the subplot title text in degrees')
        self.sp_title_rotation.valueChanged.connect(lambda _: self._on_sp_title_changed())
        sp_textra_row.addWidget(self.sp_title_rotation)
        sp_textra_row.addWidget(QLabel('Align:'))
        self.sp_title_ha = QComboBox()
        self.sp_title_ha.addItems(['center', 'left', 'right'])
        self.sp_title_ha.setFixedWidth(70)
        self.sp_title_ha.setToolTip('Horizontal alignment of the subplot title text')
        self.sp_title_ha.currentTextChanged.connect(lambda _: self._on_sp_title_changed())
        sp_textra_row.addWidget(self.sp_title_ha)
        sp_textra_row.addStretch()
        _ts_lay.addLayout(sp_textra_row)

        _ts_lay.addWidget(self._hline())
        layout.addWidget(self._axes_title_section)
        self._axes_title_section.setVisible(False)  # shown only when n > 1

        # ── Legend (moved from Axes; full styling) ────────────────────────────
        layout.addWidget(self._sec_label('Legend'))

        leg_check_row = QHBoxLayout()
        leg_check_row.setSpacing(6)
        self.legend_show_check = QCheckBox('Show legend')
        self.legend_show_check.setChecked(True)
        self.legend_show_check.stateChanged.connect(self._on_sp_legend_changed)
        leg_check_row.addWidget(self.legend_show_check)
        leg_check_row.addSpacing(12)
        self.legend_auto_pos = QCheckBox('Auto position')
        self.legend_auto_pos.setChecked(True)
        self.legend_auto_pos.setToolTip('Let matplotlib pick the best legend position automatically')
        self.legend_auto_pos.stateChanged.connect(self._on_sp_legend_changed)
        self.legend_auto_pos.stateChanged.connect(self._update_legend_pos_enabled)
        leg_check_row.addWidget(self.legend_auto_pos)
        leg_check_row.addStretch()
        layout.addLayout(leg_check_row)

        # Location dropdown + fine X/Y position
        leg_loc_row = QHBoxLayout()
        leg_loc_row.setSpacing(4)
        leg_loc_row.addWidget(QLabel('Position:'))
        self.legend_pos = QComboBox()
        self.legend_pos.addItems(['upper left', 'upper center', 'upper right',
                                  'center left', 'center', 'center right',
                                  'lower left', 'lower center', 'lower right'])
        self.legend_pos.currentTextChanged.connect(self._on_sp_legend_changed)
        leg_loc_row.addWidget(self.legend_pos)
        self._legend_x_label = QLabel('X:')
        leg_loc_row.addWidget(self._legend_x_label)
        self.legend_x = QDoubleSpinBox()
        self.legend_x.setRange(0.0, 1.5)
        self.legend_x.setSingleStep(0.01)
        self.legend_x.setDecimals(2)
        self.legend_x.setValue(0.01)
        self.legend_x.setFixedWidth(60)
        self.legend_x.setToolTip('Fine X position (figure fraction); used when Auto position is off')
        self.legend_x.valueChanged.connect(self._on_sp_legend_changed)
        leg_loc_row.addWidget(self.legend_x)
        self._legend_y_label = QLabel('Y:')
        leg_loc_row.addWidget(self._legend_y_label)
        self.legend_y = QDoubleSpinBox()
        self.legend_y.setRange(0.0, 1.5)
        self.legend_y.setSingleStep(0.01)
        self.legend_y.setDecimals(2)
        self.legend_y.setValue(0.99)
        self.legend_y.setFixedWidth(60)
        self.legend_y.setToolTip('Fine Y position (figure fraction); used when Auto position is off')
        self.legend_y.valueChanged.connect(self._on_sp_legend_changed)
        leg_loc_row.addWidget(self.legend_y)
        leg_loc_row.addStretch()
        layout.addLayout(leg_loc_row)
        # Reflect the initial auto-on state (combo + X/Y start disabled)
        self._update_legend_pos_enabled()

        # Font size + columns
        leg_style_row = QHBoxLayout()
        leg_style_row.setSpacing(4)
        leg_style_row.addWidget(QLabel('Font sz:'))
        self.legend_fontsize = QSpinBox()
        self.legend_fontsize.setRange(5, 24)
        self.legend_fontsize.setValue(9)
        self.legend_fontsize.setFixedWidth(46)
        self.legend_fontsize.valueChanged.connect(self._on_sp_legend_changed)
        leg_style_row.addWidget(self.legend_fontsize)
        leg_style_row.addWidget(QLabel('Cols:'))
        self.legend_ncols = QSpinBox()
        self.legend_ncols.setRange(1, 8)
        self.legend_ncols.setValue(1)
        self.legend_ncols.setFixedWidth(42)
        self.legend_ncols.valueChanged.connect(self._on_sp_legend_changed)
        leg_style_row.addWidget(self.legend_ncols)
        self.legend_frameon = QCheckBox('Frame')
        self.legend_frameon.setChecked(True)
        self.legend_frameon.stateChanged.connect(self._on_sp_legend_changed)
        leg_style_row.addWidget(self.legend_frameon)
        leg_style_row.addStretch()
        layout.addLayout(leg_style_row)

        # Colors — text, background, edge (one row each, using lrow like annotations)
        self.legend_color = '#000000'
        self.legend_color_sw = self._color_sw('#000000')
        btn_leg_tc = QPushButton('…')
        btn_leg_tc.setFixedWidth(28)
        btn_leg_tc.clicked.connect(lambda: self._pick_legend_color('text'))
        lrow('Text color:', self.legend_color_sw, btn_leg_tc)

        self.legend_facecolor = '#ffffff'
        self.legend_facecolor_sw = self._color_sw('#ffffff')
        btn_leg_bg = QPushButton('…')
        btn_leg_bg.setFixedWidth(28)
        btn_leg_bg.clicked.connect(lambda: self._pick_legend_color('bg'))
        self.legend_alpha = QDoubleSpinBox()
        self.legend_alpha.setRange(0.0, 1.0)
        self.legend_alpha.setSingleStep(0.05)
        self.legend_alpha.setValue(0.8)
        self.legend_alpha.setFixedWidth(54)
        self.legend_alpha.valueChanged.connect(self._on_sp_legend_changed)
        lrow('BG color:', self.legend_facecolor_sw, btn_leg_bg, QLabel('α:'), self.legend_alpha)

        self.legend_edgecolor = '#cccccc'
        self.legend_edgecolor_sw = self._color_sw('#cccccc')
        btn_leg_ec = QPushButton('…')
        btn_leg_ec.setFixedWidth(28)
        btn_leg_ec.clicked.connect(lambda: self._pick_legend_color('edge'))
        lrow('Edge color:', self.legend_edgecolor_sw, btn_leg_ec)

        layout.addWidget(self._hline())

        # ── Show/hide annotations for current subplot ─────────────────────────
        vis_row = QHBoxLayout()
        vis_row.setSpacing(6)
        self.ann_subplot_visible = QCheckBox('Show annotations on this subplot')
        self.ann_subplot_visible.setChecked(True)
        self.ann_subplot_visible.stateChanged.connect(self._on_ann_subplot_visibility_changed)
        vis_row.addWidget(self.ann_subplot_visible)
        vis_row.addStretch()
        layout.addLayout(vis_row)

        # ── Mode buttons ──────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Place Annotation'))
        self.ann_none_btn  = QPushButton('🖱 Normal/Drag')
        self.ann_text_btn  = QPushButton('📝 Text')
        self.ann_arrow_btn = QPushButton('➡ Arrow')
        self.ann_image_btn = QPushButton('🖼 Image')
        for btn in (self.ann_none_btn, self.ann_text_btn,
                    self.ann_arrow_btn, self.ann_image_btn):
            btn.setCheckable(True)
        self.ann_none_btn.setChecked(True)
        self.ann_none_btn.clicked.connect(lambda: self.set_annotation_mode(None))
        self.ann_text_btn.clicked.connect(lambda: self.set_annotation_mode('text'))
        self.ann_arrow_btn.clicked.connect(lambda: self.set_annotation_mode('arrow'))
        self.ann_image_btn.clicked.connect(self._start_image_annotation)
        r_mode1 = QHBoxLayout()
        r_mode1.setSpacing(3)
        r_mode1.addWidget(self.ann_none_btn)
        r_mode1.addWidget(self.ann_text_btn)
        layout.addLayout(r_mode1)
        r_mode2 = QHBoxLayout()
        r_mode2.setSpacing(3)
        r_mode2.addWidget(self.ann_arrow_btn)
        r_mode2.addWidget(self.ann_image_btn)
        layout.addLayout(r_mode2)

        self.ann_image_zoom = QDoubleSpinBox()
        self.ann_image_zoom.setRange(0.01, 5.0)
        self.ann_image_zoom.setValue(0.15)
        self.ann_image_zoom.setSingleStep(0.01)
        lrow('Img zoom:', self.ann_image_zoom)

        layout.addWidget(self._hline())
        layout.addWidget(QLabel('Style for new annotations:'))

        self.ann_font = QComboBox()
        self.ann_font.addItems(_FONTS)
        self.ann_font.setFixedWidth(110)
        self.ann_font.currentTextChanged.connect(self._sync_ann_style)
        self.ann_fontsize = QSpinBox()
        self.ann_fontsize.setRange(6, 48)
        self.ann_fontsize.setValue(10)
        self.ann_fontsize.setFixedWidth(52)
        self.ann_fontsize.valueChanged.connect(self._sync_ann_style)
        lrow('Font:', self.ann_font, QLabel('Sz:'), self.ann_fontsize)

        self.ann_fontcolor = '#000000'
        fc_sw, fc_btn = color_btn('ann_fontcolor', '#000000')
        lrow('Font color:', fc_sw, fc_btn)

        self.ann_bgcolor = '#ffffcc'
        bg_sw, bg_btn = color_btn('ann_bgcolor', '#ffffcc')
        self.ann_bg_alpha = QDoubleSpinBox()
        self.ann_bg_alpha.setRange(0, 1)
        self.ann_bg_alpha.setSingleStep(0.05)
        self.ann_bg_alpha.setValue(0.9)
        self.ann_bg_alpha.setFixedWidth(58)
        self.ann_bg_alpha.valueChanged.connect(self._sync_ann_style)
        lrow('BG:', bg_sw, bg_btn, QLabel('α:'), self.ann_bg_alpha)

        self.ann_edgecolor = '#aaaaaa'
        ec_sw, ec_btn = color_btn('ann_edgecolor', '#aaaaaa')
        lrow('Border:', ec_sw, ec_btn)

        layout.addWidget(self._hline())

        # Manual position + place
        self.ann_x_override = QLineEdit()
        self.ann_x_override.setPlaceholderText('X')
        self.ann_x_override.setFixedWidth(60)
        self.ann_y_override = QLineEdit()
        self.ann_y_override.setPlaceholderText('Y')
        self.ann_y_override.setFixedWidth(60)
        btn_place = QPushButton('📍 Place')
        btn_place.setFixedWidth(64)
        btn_place.clicked.connect(self._place_at_override)
        lrow('Position:', self.ann_x_override, self.ann_y_override, btn_place)

        btn_undo  = QPushButton('↩ Undo last')
        btn_clear = QPushButton('🗑 Clear all')
        btn_clear.clicked.connect(lambda: self.canvas.clear_annotations())
        btn_undo.clicked.connect(lambda: self.canvas.remove_last_annotation())
        irow(btn_undo, btn_clear)

        layout.addWidget(self._hline())
        layout.addWidget(QLabel('Annotations — double-click to edit:'))
        self.ann_list_widget = QListWidget()
        self.ann_list_widget.setMaximumHeight(120)
        self.ann_list_widget.itemDoubleClicked.connect(self._edit_selected_annotation)
        layout.addWidget(self.ann_list_widget)

        btn_edit = QPushButton('✏️ Edit selected')
        btn_del  = QPushButton('🗑 Delete selected')
        btn_edit.clicked.connect(self._edit_selected_annotation)
        btn_del.clicked.connect(self._delete_selected_annotation)
        irow(btn_edit, btn_del)

        layout.addStretch()
        scroll.setWidget(content)
        mlay = QVBoxLayout(widget)
        mlay.addWidget(scroll)
        self.plots_inner_tabs.addTab(widget, 'Annotations')
