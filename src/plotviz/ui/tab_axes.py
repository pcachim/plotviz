"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_axes.py  –  plotviz
AxesTabMixin: create_axes_tab(): axis labels, scales, limits, ticks, 3D viewpoint.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton, QCheckBox, QScrollArea, QButtonGroup, QRadioButton,
)
from PyQt6.QtCore import Qt
from ui.collapsible import CollapsibleSection
from ui.tab_constants import (
    _FONTS,
)


class AxesTabMixin:
    def _refresh_axes_summaries(self):
        for sec in getattr(self, '_axes_sections', ()):
            sec.refresh_summary()

    def _axis_summary(self, prefix):
        """One-line summary of an axis (label and limits) for its closed section."""
        label = getattr(self, prefix + 'label_input').text() or '(no label)'
        if getattr(self, prefix + '_auto').isChecked():
            lim = 'auto limits'
        else:
            lim = f'{getattr(self, prefix + "_min").value():g} – {getattr(self, prefix + "_max").value():g}'
        return f'{label} · {lim}'

    # ─── Axes tab ─────────────────────────────────────────────────────────────
    def create_axes_tab(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        main = QVBoxLayout(content)
        main.setSpacing(5)
        main.setContentsMargins(6, 6, 6, 6)
        layout = main          # where the rows are added: the open section's body
        sections = []

        def open_section(title, key, expanded, summary):
            """Start a collapsible section; the following rows go into its body."""
            nonlocal layout
            sec = CollapsibleSection(title, key, expanded, summary)
            main.addWidget(sec)
            sections.append(sec)
            layout = sec.body_layout

        # Helper: compact spinbox widths
        _SW = 60   # narrow spinbox (sizes, rotation)
        _LW = 82   # wider spinbox (limits)
        _DW = 65   # direction/format combo

        # ── Subplot selector (hidden when n == 1) ─────────────────────────────
        sp_sel_row = QHBoxLayout()
        sp_sel_row.setSpacing(6)
        sp_sel_row.addWidget(QLabel('Subplot:'))
        self.sp_active = QComboBox()
        self.sp_active.addItem('Subplot 1')
        self.sp_active.currentIndexChanged.connect(self.on_active_subplot_changed)
        sp_sel_row.addWidget(self.sp_active)
        sp_sel_row.addStretch()
        self._axes_sp_row_widget = QWidget()
        self._axes_sp_row_widget.setLayout(sp_sel_row)
        self._axes_sp_row_widget.setVisible(False)
        layout.addWidget(self._axes_sp_row_widget)

        # ── Equal Scale ───────────────────────────────────────────────────────
        self.equal_scale_check = QCheckBox('Equal scale (1:1 aspect ratio)')
        self.equal_scale_check.setToolTip(
            'Force X and Y axes to use the same scale length (ax.set_aspect("equal")).\n'
            'Useful for scatter plots, maps, and any data where distances should be preserved.'
        )
        self.equal_scale_check.stateChanged.connect(self._save_axes_state)
        layout.addWidget(self.equal_scale_check)

        layout.addWidget(self._hline())

        # ══════════════════════════════════════════════════════════════════════
        # ── X Axis ────────────────────────────────────────────────────────────
        open_section('X Axis', 'axes_x', True, lambda: self._axis_summary('x'))

        # Show checkbox
        self.xlabel_show_check = QCheckBox('Show X label')
        self.xlabel_show_check.setChecked(True)
        self.xlabel_show_check.stateChanged.connect(self._on_sp_xlabel_show_changed)
        layout.addWidget(self.xlabel_show_check)

        # Label text
        self.xlabel_input = QLineEdit()
        self.xlabel_input.setPlaceholderText('X label (optional)')
        self.xlabel_input.textChanged.connect(self._on_sp_xlabel_changed)
        layout.addWidget(self.xlabel_input)

        # Font + Size  (row 1 of 2)
        xfont_row1 = QHBoxLayout()
        xfont_row1.setSpacing(4)
        xfont_row1.addWidget(QLabel('Font:'))
        self.xlabel_font = QComboBox()
        self.xlabel_font.addItems(_FONTS)
        self.xlabel_font.currentTextChanged.connect(self.update_preview)
        xfont_row1.addWidget(self.xlabel_font, 1)
        xfont_row1.addWidget(QLabel('Size:'))
        self.xlabel_size = QSpinBox()
        self.xlabel_size.setRange(6, 32)
        self.xlabel_size.setValue(11)
        self.xlabel_size.setFixedWidth(_SW)
        self.xlabel_size.valueChanged.connect(self.update_preview)
        xfont_row1.addWidget(self.xlabel_size)
        layout.addLayout(xfont_row1)

        # Color  (row 2 of 2)
        xfont_row2 = QHBoxLayout()
        xfont_row2.setSpacing(4)
        xfont_row2.addWidget(QLabel('Color:'))
        self.xlabel_color = '#000000'
        self.xlabel_color_label = self._color_sw('#000000')
        xfont_row2.addWidget(self.xlabel_color_label)
        btn_xc = QPushButton('…')
        btn_xc.setFixedWidth(28)
        btn_xc.clicked.connect(lambda: self.pick_color('xlabel'))
        xfont_row2.addWidget(btn_xc)
        xfont_row2.addStretch()
        layout.addLayout(xfont_row2)

        # Rotation + Pad  (label text, not ticks)
        xlabel_pos_row = QHBoxLayout()
        xlabel_pos_row.setSpacing(4)
        xlabel_pos_row.addWidget(QLabel('Rotation:'))
        self.xlabel_rotation = QSpinBox()
        self.xlabel_rotation.setRange(-180, 180)
        self.xlabel_rotation.setValue(0)
        self.xlabel_rotation.setFixedWidth(_SW)
        self.xlabel_rotation.setToolTip('Rotation of the X-axis label text in degrees')
        self.xlabel_rotation.valueChanged.connect(self._save_axes_state)
        xlabel_pos_row.addWidget(self.xlabel_rotation)
        xlabel_pos_row.addWidget(QLabel('Pad:'))
        self.xlabel_labelpad = QSpinBox()
        self.xlabel_labelpad.setRange(0, 50)
        self.xlabel_labelpad.setValue(4)
        self.xlabel_labelpad.setFixedWidth(_SW)
        self.xlabel_labelpad.setToolTip('Distance between the X-axis label and the axis (points)')
        self.xlabel_labelpad.valueChanged.connect(self._save_axes_state)
        xlabel_pos_row.addWidget(self.xlabel_labelpad)
        xlabel_pos_row.addStretch()
        layout.addLayout(xlabel_pos_row)

        # Loc + Align
        xlabel_align_row = QHBoxLayout()
        xlabel_align_row.setSpacing(4)
        xlabel_align_row.addWidget(QLabel('Loc:'))
        self.xlabel_loc = QComboBox()
        self.xlabel_loc.addItems(['center', 'left', 'right'])
        self.xlabel_loc.setFixedWidth(70)
        self.xlabel_loc.setToolTip('Horizontal position of the X-axis label along the axis')
        self.xlabel_loc.currentTextChanged.connect(self._save_axes_state)
        xlabel_align_row.addWidget(self.xlabel_loc)
        xlabel_align_row.addWidget(QLabel('Align:'))
        self.xlabel_ha = QComboBox()
        self.xlabel_ha.addItems(['center', 'left', 'right'])
        self.xlabel_ha.setFixedWidth(70)
        self.xlabel_ha.setToolTip('Horizontal alignment of the X-axis label text anchor')
        self.xlabel_ha.currentTextChanged.connect(self._save_axes_state)
        xlabel_align_row.addWidget(self.xlabel_ha)
        xlabel_align_row.addStretch()
        layout.addLayout(xlabel_align_row)

        # Limits  (min / max on same row, Auto below)
        xlim_row = QHBoxLayout()
        xlim_row.setSpacing(4)
        xlim_row.addWidget(QLabel('X min:'))
        self.x_min = QDoubleSpinBox()
        self.x_min.setRange(-1e10, 1e10)
        self.x_min.setSingleStep(0.1)
        self.x_min.setFixedWidth(_LW)
        self.x_min.setEnabled(False)  # disabled while Auto is checked
        self.x_min.valueChanged.connect(self._on_sp_lim_changed)
        xlim_row.addWidget(self.x_min)
        xlim_row.addWidget(QLabel('max:'))
        self.x_max = QDoubleSpinBox()
        self.x_max.setRange(-1e10, 1e10)
        self.x_max.setValue(1)
        self.x_max.setSingleStep(0.1)
        self.x_max.setFixedWidth(_LW)
        self.x_max.setEnabled(False)  # disabled while Auto is checked
        self.x_max.valueChanged.connect(self._on_sp_lim_changed)
        xlim_row.addWidget(self.x_max)
        xlim_row.addStretch()
        layout.addLayout(xlim_row)

        xauto_row = QHBoxLayout()
        self.x_auto = QCheckBox('Auto limits')
        self.x_auto.setChecked(True)
        self.x_auto.stateChanged.connect(self._on_sp_lim_changed)
        xauto_row.addWidget(self.x_auto)
        xauto_row.addStretch()
        layout.addLayout(xauto_row)

        # Scale radio buttons
        layout.addWidget(QLabel('Scale:'))
        self.xscale_group = QButtonGroup(self)
        xsr = QHBoxLayout()
        xsr.setSpacing(6)
        for lbl, val in [('Linear', 'linear'), ('Log', 'log'), ('Logit', 'logit'), ('Inverted', 'inverted')]:
            rb = QRadioButton(lbl)
            rb.setProperty('scale_value', val)
            if val == 'linear': rb.setChecked(True)
            rb.toggled.connect(self._save_axes_state)
            self.xscale_group.addButton(rb)
            xsr.addWidget(rb)
        xsr.addStretch()
        layout.addLayout(xsr)

        # Tick size + direction
        xtick_row1 = QHBoxLayout()
        xtick_row1.setSpacing(4)
        xtick_row1.addWidget(QLabel('Tick size:'))
        self.xtick_size = QSpinBox()
        self.xtick_size.setRange(4, 24)
        self.xtick_size.setValue(9)
        self.xtick_size.setFixedWidth(_SW)
        self.xtick_size.valueChanged.connect(self._save_axes_state)
        xtick_row1.addWidget(self.xtick_size)
        xtick_row1.addWidget(QLabel('Direction:'))
        self.xtick_dir = QComboBox()
        self.xtick_dir.addItems(['out', 'in', 'inout'])
        self.xtick_dir.setFixedWidth(_DW)
        self.xtick_dir.currentTextChanged.connect(self._save_axes_state)
        xtick_row1.addWidget(self.xtick_dir)
        xtick_row1.addStretch()
        layout.addLayout(xtick_row1)

        # Show ticks + minor ticks
        xtick_row2 = QHBoxLayout()
        self.xticks_show = QCheckBox('Show ticks')
        self.xticks_show.setChecked(True)
        self.xticks_show.stateChanged.connect(self._save_axes_state)
        xtick_row2.addWidget(self.xticks_show)
        self.xtick_minor = QCheckBox('Minor ticks')
        self.xtick_minor.setChecked(False)
        self.xtick_minor.stateChanged.connect(self._save_axes_state)
        xtick_row2.addWidget(self.xtick_minor)
        xtick_row2.addStretch()
        layout.addLayout(xtick_row2)

        # Rotation
        xtick_rot_row = QHBoxLayout()
        xtick_rot_row.setSpacing(4)
        xtick_rot_row.addWidget(QLabel('Rotation:'))
        self.xtick_rotation = QSpinBox()
        self.xtick_rotation.setRange(-90, 90)
        self.xtick_rotation.setValue(0)
        self.xtick_rotation.setFixedWidth(_SW)
        self.xtick_rotation.valueChanged.connect(self._save_axes_state)
        xtick_rot_row.addWidget(self.xtick_rotation)
        xtick_rot_row.addStretch()
        layout.addLayout(xtick_rot_row)

        # Step
        xtick_step_row = QHBoxLayout()
        xtick_step_row.setSpacing(4)
        xtick_step_row.addWidget(QLabel('Step (0 = auto):'))
        self.xtick_step = QDoubleSpinBox()
        self.xtick_step.setRange(0, 1e9)
        self.xtick_step.setValue(0)
        self.xtick_step.setSingleStep(0.1)
        self.xtick_step.setFixedWidth(_LW)
        self.xtick_step.editingFinished.connect(self._save_axes_state)
        xtick_step_row.addWidget(self.xtick_step)
        xtick_step_row.addStretch()
        layout.addLayout(xtick_step_row)

        # Format
        xfmt_row = QHBoxLayout()
        xfmt_row.setSpacing(4)
        xfmt_row.addWidget(QLabel('Format:'))
        self.x_formatter = QComboBox()
        self.x_formatter.addItems(['auto', 'plain', 'sci', 'percent', '{x:.2f}', '{x:.0f}'])
        self.x_formatter.setEditable(True)
        self.x_formatter.currentTextChanged.connect(self._save_axes_state)
        xfmt_row.addWidget(self.x_formatter, 1)
        layout.addLayout(xfmt_row)

        # X-axis position on Y axis
        xpos_row = QHBoxLayout()
        xpos_row.setSpacing(4)
        xpos_row.addWidget(QLabel('Position on Y:'))
        self.xaxis_pos = QComboBox()
        self.xaxis_pos.addItems(['bottom', 'top', 'zero'])
        self.xaxis_pos.setToolTip(
            'Where the X axis line and ticks appear:\n'
            '  bottom — default, along the bottom spine\n'
            '  top    — move axis line and ticks to the top\n'
            '  zero   — anchor the axis line at Y = 0'
        )
        self.xaxis_pos.setFixedWidth(80)
        self.xaxis_pos.currentTextChanged.connect(self._save_axes_state)
        xpos_row.addWidget(self.xaxis_pos)
        xpos_row.addStretch()
        layout.addLayout(xpos_row)

        main.addWidget(self._hline())

        # ══════════════════════════════════════════════════════════════════════
        # ── Y Axis (Left) ─────────────────────────────────────────────────────
        open_section('Y Axis (Left)', 'axes_y', True, lambda: self._axis_summary('y'))

        self.ylabel_show_check = QCheckBox('Show Y label')
        self.ylabel_show_check.setChecked(True)
        self.ylabel_show_check.stateChanged.connect(self._on_sp_ylabel_show_changed)
        layout.addWidget(self.ylabel_show_check)

        self.ylabel_input = QLineEdit()
        self.ylabel_input.setPlaceholderText('Y label (optional)')
        self.ylabel_input.textChanged.connect(self._on_sp_ylabel_changed)
        layout.addWidget(self.ylabel_input)

        yfont_row1 = QHBoxLayout()
        yfont_row1.setSpacing(4)
        yfont_row1.addWidget(QLabel('Font:'))
        self.ylabel_font = QComboBox()
        self.ylabel_font.addItems(_FONTS)
        self.ylabel_font.currentTextChanged.connect(self.update_preview)
        yfont_row1.addWidget(self.ylabel_font, 1)
        yfont_row1.addWidget(QLabel('Size:'))
        self.ylabel_size = QSpinBox()
        self.ylabel_size.setRange(6, 32)
        self.ylabel_size.setValue(11)
        self.ylabel_size.setFixedWidth(_SW)
        self.ylabel_size.valueChanged.connect(self.update_preview)
        yfont_row1.addWidget(self.ylabel_size)
        layout.addLayout(yfont_row1)

        yfont_row2 = QHBoxLayout()
        yfont_row2.setSpacing(4)
        yfont_row2.addWidget(QLabel('Color:'))
        self.ylabel_color = '#000000'
        self.ylabel_color_label = self._color_sw('#000000')
        yfont_row2.addWidget(self.ylabel_color_label)
        btn_yc = QPushButton('…')
        btn_yc.setFixedWidth(28)
        btn_yc.clicked.connect(lambda: self.pick_color('ylabel'))
        yfont_row2.addWidget(btn_yc)
        yfont_row2.addStretch()
        layout.addLayout(yfont_row2)

        # Rotation + Pad  (label text, not ticks)
        ylabel_pos_row = QHBoxLayout()
        ylabel_pos_row.setSpacing(4)
        ylabel_pos_row.addWidget(QLabel('Rotation:'))
        self.ylabel_rotation = QSpinBox()
        self.ylabel_rotation.setRange(-180, 180)
        self.ylabel_rotation.setValue(90)
        self.ylabel_rotation.setFixedWidth(_SW)
        self.ylabel_rotation.setToolTip('Rotation of the Y-axis label text in degrees (90 = vertical, 0 = horizontal)')
        self.ylabel_rotation.valueChanged.connect(self._save_axes_state)
        ylabel_pos_row.addWidget(self.ylabel_rotation)
        ylabel_pos_row.addWidget(QLabel('Pad:'))
        self.ylabel_labelpad = QSpinBox()
        self.ylabel_labelpad.setRange(0, 50)
        self.ylabel_labelpad.setValue(4)
        self.ylabel_labelpad.setFixedWidth(_SW)
        self.ylabel_labelpad.setToolTip('Distance between the Y-axis label and the axis (points)')
        self.ylabel_labelpad.valueChanged.connect(self._save_axes_state)
        ylabel_pos_row.addWidget(self.ylabel_labelpad)
        ylabel_pos_row.addStretch()
        layout.addLayout(ylabel_pos_row)

        # Loc + Align
        ylabel_align_row = QHBoxLayout()
        ylabel_align_row.setSpacing(4)
        ylabel_align_row.addWidget(QLabel('Loc:'))
        self.ylabel_loc = QComboBox()
        self.ylabel_loc.addItems(['center', 'bottom', 'top'])
        self.ylabel_loc.setFixedWidth(70)
        self.ylabel_loc.setToolTip('Vertical position of the Y-axis label along the axis')
        self.ylabel_loc.currentTextChanged.connect(self._save_axes_state)
        ylabel_align_row.addWidget(self.ylabel_loc)
        ylabel_align_row.addWidget(QLabel('Align:'))
        self.ylabel_ha = QComboBox()
        self.ylabel_ha.addItems(['center', 'left', 'right'])
        self.ylabel_ha.setFixedWidth(70)
        self.ylabel_ha.setToolTip('Horizontal alignment of the Y-axis label text anchor')
        self.ylabel_ha.currentTextChanged.connect(self._save_axes_state)
        ylabel_align_row.addWidget(self.ylabel_ha)
        ylabel_align_row.addStretch()
        layout.addLayout(ylabel_align_row)

        ylim_row = QHBoxLayout()
        ylim_row.setSpacing(4)
        ylim_row.addWidget(QLabel('Y min:'))
        self.y_min = QDoubleSpinBox()
        self.y_min.setRange(-1e10, 1e10)
        self.y_min.setSingleStep(0.1)
        self.y_min.setFixedWidth(_LW)
        self.y_min.setEnabled(False)  # disabled while Auto is checked
        self.y_min.valueChanged.connect(self._on_sp_lim_changed)
        ylim_row.addWidget(self.y_min)
        ylim_row.addWidget(QLabel('max:'))
        self.y_max = QDoubleSpinBox()
        self.y_max.setRange(-1e10, 1e10)
        self.y_max.setValue(1)
        self.y_max.setSingleStep(0.1)
        self.y_max.setFixedWidth(_LW)
        self.y_max.setEnabled(False)  # disabled while Auto is checked
        self.y_max.valueChanged.connect(self._on_sp_lim_changed)
        ylim_row.addWidget(self.y_max)
        ylim_row.addStretch()
        layout.addLayout(ylim_row)

        yauto_row = QHBoxLayout()
        self.y_auto = QCheckBox('Auto limits')
        self.y_auto.setChecked(True)
        self.y_auto.stateChanged.connect(self._on_sp_lim_changed)
        yauto_row.addWidget(self.y_auto)
        yauto_row.addStretch()
        layout.addLayout(yauto_row)

        layout.addWidget(QLabel('Scale:'))
        self.yscale_group = QButtonGroup(self)
        ysr = QHBoxLayout()
        ysr.setSpacing(6)
        for lbl, val in [('Linear', 'linear'), ('Log', 'log'), ('Logit', 'logit'), ('Inverted', 'inverted')]:
            rb = QRadioButton(lbl)
            rb.setProperty('scale_value', val)
            if val == 'linear': rb.setChecked(True)
            rb.toggled.connect(self._save_axes_state)
            self.yscale_group.addButton(rb)
            ysr.addWidget(rb)
        ysr.addStretch()
        layout.addLayout(ysr)

        ytick_row1 = QHBoxLayout()
        ytick_row1.setSpacing(4)
        ytick_row1.addWidget(QLabel('Tick size:'))
        self.ytick_size = QSpinBox()
        self.ytick_size.setRange(4, 24)
        self.ytick_size.setValue(9)
        self.ytick_size.setFixedWidth(_SW)
        self.ytick_size.valueChanged.connect(self._save_axes_state)
        ytick_row1.addWidget(self.ytick_size)
        ytick_row1.addWidget(QLabel('Direction:'))
        self.ytick_dir = QComboBox()
        self.ytick_dir.addItems(['out', 'in', 'inout'])
        self.ytick_dir.setFixedWidth(_DW)
        self.ytick_dir.currentTextChanged.connect(self._save_axes_state)
        ytick_row1.addWidget(self.ytick_dir)
        ytick_row1.addStretch()
        layout.addLayout(ytick_row1)

        ytick_row2 = QHBoxLayout()
        self.yticks_show = QCheckBox('Show ticks')
        self.yticks_show.setChecked(True)
        self.yticks_show.stateChanged.connect(self._save_axes_state)
        ytick_row2.addWidget(self.yticks_show)
        self.ytick_minor = QCheckBox('Minor ticks')
        self.ytick_minor.setChecked(False)
        self.ytick_minor.stateChanged.connect(self._save_axes_state)
        ytick_row2.addWidget(self.ytick_minor)
        ytick_row2.addStretch()
        layout.addLayout(ytick_row2)

        ytick_rot_row = QHBoxLayout()
        ytick_rot_row.setSpacing(4)
        ytick_rot_row.addWidget(QLabel('Rotation:'))
        self.ytick_rotation = QSpinBox()
        self.ytick_rotation.setRange(-90, 90)
        self.ytick_rotation.setValue(0)
        self.ytick_rotation.setFixedWidth(_SW)
        self.ytick_rotation.valueChanged.connect(self._save_axes_state)
        ytick_rot_row.addWidget(self.ytick_rotation)
        ytick_rot_row.addStretch()
        layout.addLayout(ytick_rot_row)

        ytick_step_row = QHBoxLayout()
        ytick_step_row.setSpacing(4)
        ytick_step_row.addWidget(QLabel('Step (0 = auto):'))
        self.ytick_step = QDoubleSpinBox()
        self.ytick_step.setRange(0, 1e9)
        self.ytick_step.setValue(0)
        self.ytick_step.setSingleStep(0.1)
        self.ytick_step.setFixedWidth(_LW)
        self.ytick_step.editingFinished.connect(self._save_axes_state)
        ytick_step_row.addWidget(self.ytick_step)
        ytick_step_row.addStretch()
        layout.addLayout(ytick_step_row)

        yfmt_row = QHBoxLayout()
        yfmt_row.setSpacing(4)
        yfmt_row.addWidget(QLabel('Format:'))
        self.y_formatter = QComboBox()
        self.y_formatter.addItems(['auto', 'plain', 'sci', 'percent', '{x:.2f}', '{x:.0f}'])
        self.y_formatter.setEditable(True)
        self.y_formatter.currentTextChanged.connect(self._save_axes_state)
        yfmt_row.addWidget(self.y_formatter, 1)
        layout.addLayout(yfmt_row)

        # Y-axis position on X axis
        ypos_row = QHBoxLayout()
        ypos_row.setSpacing(4)
        ypos_row.addWidget(QLabel('Position on X:'))
        self.yaxis_pos = QComboBox()
        self.yaxis_pos.addItems(['left', 'right', 'zero'])
        self.yaxis_pos.setToolTip(
            'Where the Y axis line and ticks appear:\n'
            '  left  — default, along the left spine\n'
            '  right — move axis line and ticks to the right\n'
            '  zero  — anchor the axis line at X = 0'
        )
        self.yaxis_pos.setFixedWidth(80)
        self.yaxis_pos.currentTextChanged.connect(self._save_axes_state)
        ypos_row.addWidget(self.yaxis_pos)
        ypos_row.addStretch()
        layout.addLayout(ypos_row)

        layout = main
        layout.addWidget(self._hline())

        # ══════════════════════════════════════════════════════════════════════
        # ── Y Axis (Right / Secondary) ────────────────────────────────────────
        open_section('Y Axis (Right / Secondary)', 'axes_y2', False,
                     lambda: self._axis_summary('y2'))
        layout.addWidget(QLabel('(Activate by ticking Y2 in the Series table)'))

        self.y2label_show_check = QCheckBox('Show Y2 label')
        self.y2label_show_check.setChecked(True)
        self.y2label_show_check.stateChanged.connect(self._on_sp_y2label_show_changed)
        layout.addWidget(self.y2label_show_check)

        self.y2label_input = QLineEdit()
        self.y2label_input.setPlaceholderText('Y2 label (optional)')
        self.y2label_input.textChanged.connect(self._on_sp_y2label_changed)
        layout.addWidget(self.y2label_input)

        y2font_row1 = QHBoxLayout()
        y2font_row1.setSpacing(4)
        y2font_row1.addWidget(QLabel('Font:'))
        self.y2label_font = QComboBox()
        self.y2label_font.addItems(_FONTS)
        self.y2label_font.currentTextChanged.connect(self.update_preview)
        y2font_row1.addWidget(self.y2label_font, 1)
        y2font_row1.addWidget(QLabel('Size:'))
        self.y2label_size = QSpinBox()
        self.y2label_size.setRange(6, 32)
        self.y2label_size.setValue(11)
        self.y2label_size.setFixedWidth(_SW)
        self.y2label_size.valueChanged.connect(self.update_preview)
        y2font_row1.addWidget(self.y2label_size)
        layout.addLayout(y2font_row1)

        y2font_row2 = QHBoxLayout()
        y2font_row2.setSpacing(4)
        y2font_row2.addWidget(QLabel('Color:'))
        self.y2label_color = '#000000'
        self.y2label_color_label = self._color_sw('#000000')
        y2font_row2.addWidget(self.y2label_color_label)
        btn_y2c = QPushButton('…')
        btn_y2c.setFixedWidth(28)
        btn_y2c.clicked.connect(lambda: self.pick_color('y2label'))
        y2font_row2.addWidget(btn_y2c)
        y2font_row2.addStretch()
        layout.addLayout(y2font_row2)

        # Rotation + Pad  (label text, not ticks)
        y2label_pos_row = QHBoxLayout()
        y2label_pos_row.setSpacing(4)
        y2label_pos_row.addWidget(QLabel('Rotation:'))
        self.y2label_rotation = QSpinBox()
        self.y2label_rotation.setRange(-180, 180)
        self.y2label_rotation.setValue(90)
        self.y2label_rotation.setFixedWidth(_SW)
        self.y2label_rotation.setToolTip('Rotation of the Y2-axis label text in degrees (90 = vertical, 0 = horizontal)')
        self.y2label_rotation.valueChanged.connect(self.update_preview)
        y2label_pos_row.addWidget(self.y2label_rotation)
        y2label_pos_row.addWidget(QLabel('Pad:'))
        self.y2label_labelpad = QSpinBox()
        self.y2label_labelpad.setRange(0, 50)
        self.y2label_labelpad.setValue(4)
        self.y2label_labelpad.setFixedWidth(_SW)
        self.y2label_labelpad.setToolTip('Distance between the Y2-axis label and the axis (points)')
        self.y2label_labelpad.valueChanged.connect(self.update_preview)
        y2label_pos_row.addWidget(self.y2label_labelpad)
        y2label_pos_row.addStretch()
        layout.addLayout(y2label_pos_row)

        # Loc + Align
        y2label_align_row = QHBoxLayout()
        y2label_align_row.setSpacing(4)
        y2label_align_row.addWidget(QLabel('Loc:'))
        self.y2label_loc = QComboBox()
        self.y2label_loc.addItems(['center', 'bottom', 'top'])
        self.y2label_loc.setFixedWidth(70)
        self.y2label_loc.setToolTip('Vertical position of the Y2-axis label along the axis')
        self.y2label_loc.currentTextChanged.connect(self.update_preview)
        y2label_align_row.addWidget(self.y2label_loc)
        y2label_align_row.addWidget(QLabel('Align:'))
        self.y2label_ha = QComboBox()
        self.y2label_ha.addItems(['center', 'left', 'right'])
        self.y2label_ha.setFixedWidth(70)
        self.y2label_ha.setToolTip('Horizontal alignment of the Y2-axis label text anchor')
        self.y2label_ha.currentTextChanged.connect(self.update_preview)
        y2label_align_row.addWidget(self.y2label_ha)
        y2label_align_row.addStretch()
        layout.addLayout(y2label_align_row)

        y2lim_row = QHBoxLayout()
        y2lim_row.setSpacing(4)
        y2lim_row.addWidget(QLabel('Y2 min:'))
        self.y2_min = QDoubleSpinBox()
        self.y2_min.setRange(-1e10, 1e10)
        self.y2_min.setSingleStep(0.1)
        self.y2_min.setFixedWidth(_LW)
        self.y2_min.setEnabled(False)  # disabled while Auto is checked
        self.y2_min.valueChanged.connect(self._on_sp_lim_changed)
        y2lim_row.addWidget(self.y2_min)
        y2lim_row.addWidget(QLabel('max:'))
        self.y2_max = QDoubleSpinBox()
        self.y2_max.setRange(-1e10, 1e10)
        self.y2_max.setValue(1)
        self.y2_max.setSingleStep(0.1)
        self.y2_max.setFixedWidth(_LW)
        self.y2_max.setEnabled(False)  # disabled while Auto is checked
        self.y2_max.valueChanged.connect(self._on_sp_lim_changed)
        y2lim_row.addWidget(self.y2_max)
        y2lim_row.addStretch()
        layout.addLayout(y2lim_row)

        y2auto_row = QHBoxLayout()
        self.y2_auto = QCheckBox('Auto limits')
        self.y2_auto.setChecked(True)
        self.y2_auto.stateChanged.connect(self._on_sp_lim_changed)
        y2auto_row.addWidget(self.y2_auto)
        y2auto_row.addStretch()
        layout.addLayout(y2auto_row)

        layout = main

        layout.addWidget(self._hline())

        # ══════════════════════════════════════════════════════════════════════
        # ── Z Axis (3D Surface only) ──────────────────────────────────────────
        # The section also holds the 3D viewpoint (built in create_canvas_grid_tab).
        self._z_axis_widget = CollapsibleSection(
            'Z / Color Axis', 'axes_z', True,
            lambda: self.zlabel_input.text() or '(no label)')
        sections.append(self._z_axis_widget)
        _zlay = self._z_axis_widget.body_layout

        self.zlabel_show_check = QCheckBox('Show Z label')
        self.zlabel_show_check.setChecked(True)
        self.zlabel_show_check.stateChanged.connect(self._on_sp_zlabel_show_changed)
        _zlay.addWidget(self.zlabel_show_check)

        self.zlabel_input = QLineEdit()
        self.zlabel_input.setPlaceholderText('Z label (optional)')
        self.zlabel_input.textChanged.connect(self._on_sp_zlabel_changed)
        _zlay.addWidget(self.zlabel_input)

        zfont_row1 = QHBoxLayout()
        zfont_row1.setSpacing(4)
        zfont_row1.addWidget(QLabel('Font:'))
        self.zlabel_font = QComboBox()
        self.zlabel_font.addItems(_FONTS)
        self.zlabel_font.currentTextChanged.connect(self.update_preview)
        zfont_row1.addWidget(self.zlabel_font, 1)
        zfont_row1.addWidget(QLabel('Size:'))
        self.zlabel_size = QSpinBox()
        self.zlabel_size.setRange(6, 32)
        self.zlabel_size.setValue(11)
        self.zlabel_size.setFixedWidth(_SW)
        self.zlabel_size.valueChanged.connect(self.update_preview)
        zfont_row1.addWidget(self.zlabel_size)
        _zlay.addLayout(zfont_row1)

        zfont_row2 = QHBoxLayout()
        zfont_row2.setSpacing(4)
        zfont_row2.addWidget(QLabel('Color:'))
        self.zlabel_color = '#000000'
        self.zlabel_color_label = self._color_sw('#000000')
        zfont_row2.addWidget(self.zlabel_color_label)
        btn_zc = QPushButton('…')
        btn_zc.setFixedWidth(28)
        btn_zc.clicked.connect(lambda: self.pick_color('zlabel'))
        zfont_row2.addWidget(btn_zc)
        zfont_row2.addStretch()
        _zlay.addLayout(zfont_row2)

        zlabel_pos_row = QHBoxLayout()
        zlabel_pos_row.setSpacing(4)
        zlabel_pos_row.addWidget(QLabel('Rotation:'))
        self.zlabel_rotation = QSpinBox()
        self.zlabel_rotation.setRange(-180, 180)
        self.zlabel_rotation.setValue(90)
        self.zlabel_rotation.setFixedWidth(_SW)
        self.zlabel_rotation.setToolTip('Rotation of the Z-axis label in degrees')
        self.zlabel_rotation.valueChanged.connect(self._save_axes_state)
        zlabel_pos_row.addWidget(self.zlabel_rotation)
        zlabel_pos_row.addWidget(QLabel('Pad:'))
        self.zlabel_labelpad = QSpinBox()
        self.zlabel_labelpad.setRange(0, 50)
        self.zlabel_labelpad.setValue(4)
        self.zlabel_labelpad.setFixedWidth(_SW)
        self.zlabel_labelpad.setToolTip('Distance between the Z-axis label and the axis (points)')
        self.zlabel_labelpad.valueChanged.connect(self._save_axes_state)
        zlabel_pos_row.addWidget(self.zlabel_labelpad)
        zlabel_pos_row.addStretch()
        _zlay.addLayout(zlabel_pos_row)

        self._z_axis_widget.setVisible(False)
        layout.addWidget(self._z_axis_widget)
        _zlay.addWidget(self._layout_3d_view_widget)

        layout.addStretch()
        self._axes_sections = sections
        self._refresh_axes_summaries()
        scroll.setWidget(content)
        mlay = QVBoxLayout(widget)
        mlay.addWidget(scroll)
        self.plots_inner_tabs.addTab(widget, 'Axes')
