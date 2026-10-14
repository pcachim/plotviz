"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_style.py  –  plotviz
StyleTabMixin: create_style_tab(): fonts, colours and figure styling.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton, QCheckBox, QScrollArea,
)
from ui.tab_constants import (
    _FONTS,
)


class StyleTabMixin:
    # ─── Style tab ────────────────────────────────────────────────────────────
    def create_style_tab(self):
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

        def color_row(label_text, attr_name, default_hex, pick_target=None):
            r = QHBoxLayout()
            r.setSpacing(6)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(90)
            r.addWidget(lbl)
            sw = self._color_sw(default_hex)
            setattr(self, attr_name + '_swatch', sw)
            r.addWidget(sw)
            setattr(self, attr_name, default_hex)
            btn = QPushButton('…')
            btn.setFixedWidth(28)
            target = pick_target or attr_name
            btn.clicked.connect(lambda _=False, t=target: self.pick_color(t))
            r.addWidget(btn)
            r.addStretch()
            layout.addLayout(r)

        # ── Chart Title ───────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Chart Title'))
        title_row = QHBoxLayout()
        self.title_check = QCheckBox('Show Title')
        self.title_check.setChecked(True)
        self.title_check.stateChanged.connect(self.update_preview)
        title_row.addWidget(self.title_check)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText('Main title')
        self.title_input.editingFinished.connect(self.update_preview)
        title_row.addWidget(self.title_input)
        layout.addLayout(title_row)
        tfont_row = QHBoxLayout()
        tfont_row.addWidget(QLabel('Font:'))
        self.title_font = QComboBox()
        self.title_font.addItems(_FONTS)
        self.title_font.currentTextChanged.connect(self.update_preview)
        tfont_row.addWidget(self.title_font)
        tfont_row.addWidget(QLabel('Size:'))
        self.title_size = QSpinBox()
        self.title_size.setRange(6,32)
        self.title_size.setValue(14)
        self.title_size.valueChanged.connect(self.update_preview)
        tfont_row.addWidget(self.title_size)
        tfont_row.addStretch()
        layout.addLayout(tfont_row)
        tcolor_row = QHBoxLayout()
        tcolor_row.setSpacing(6)
        tcolor_row.addWidget(QLabel('Color:'))
        self.title_color_swatch = self._color_sw('#000000')
        tcolor_row.addWidget(self.title_color_swatch)
        self.title_color = '#000000'
        tbtn = QPushButton('…')
        tbtn.setFixedWidth(28)
        tbtn.clicked.connect(lambda: self.pick_color('title'))
        tcolor_row.addWidget(tbtn)
        tcolor_row.addStretch()
        layout.addLayout(tcolor_row)

        # Chart title X / Y position, shown in physical units (fig_unit) but stored as
        # fractions of the figure (self._title_frac). _refresh_geometry_widgets (called
        # once all the size widgets exist) fills in range, decimals and value.
        _DEFAULT_W_CM, _DEFAULT_H_CM = 20.0, 15.0
        tpos_row = QHBoxLayout()
        tpos_row.setSpacing(4)
        tpos_row.addWidget(QLabel('X:'))
        self.title_x = QDoubleSpinBox()
        self.title_x.setRange(0.0, _DEFAULT_W_CM)
        self.title_x.setSingleStep(0.1)
        self.title_x.setDecimals(1)
        self.title_x.setFixedWidth(66)
        self.title_x.valueChanged.connect(lambda v: self._on_title_pos_edited(0, v))
        self.title_x.setToolTip('Horizontal position of title (physical units, 0 = left edge)')
        tpos_row.addWidget(self.title_x)
        tpos_row.addWidget(QLabel('Y:'))
        self.title_y = QDoubleSpinBox()
        self.title_y.setRange(0.0, _DEFAULT_H_CM)
        self.title_y.setSingleStep(0.1)
        self.title_y.setDecimals(1)
        self.title_y.setFixedWidth(66)
        self.title_y.valueChanged.connect(lambda v: self._on_title_pos_edited(1, v))
        self.title_y.setToolTip('Vertical position of title (physical units, 0 = bottom edge)')
        tpos_row.addWidget(self.title_y)
        tpos_row.addStretch()
        layout.addLayout(tpos_row)
        # Keep title_y_offset as hidden alias for serialization compat
        self.title_y_offset = self.title_y

        # ── Title extra: rotation + alignment ────────────────────────────────
        textra_row = QHBoxLayout()
        textra_row.setSpacing(4)
        textra_row.addWidget(QLabel('Rot:'))
        self.title_rotation = QSpinBox()
        self.title_rotation.setRange(-180, 180)
        self.title_rotation.setValue(0)
        self.title_rotation.setFixedWidth(52)
        self.title_rotation.setToolTip('Rotation of the title text in degrees')
        self.title_rotation.valueChanged.connect(self.update_preview)
        textra_row.addWidget(self.title_rotation)
        textra_row.addWidget(QLabel('Align:'))
        self.title_ha = QComboBox()
        self.title_ha.addItems(['center', 'left', 'right'])
        self.title_ha.setFixedWidth(70)
        self.title_ha.setToolTip('Horizontal alignment of the title text')
        self.title_ha.currentTextChanged.connect(self.update_preview)
        textra_row.addWidget(self.title_ha)
        textra_row.addStretch()
        layout.addLayout(textra_row)

        layout.addWidget(self._hline())

        # ── Figure size ───────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Figure Size'))

        # Presets row
        pr = QHBoxLayout()
        pr.setSpacing(6)
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
        pr.addWidget(self.fig_preset_combo)
        pr.addStretch()
        layout.addLayout(pr)

        # Units + W + H on one row
        sz_row = QHBoxLayout()
        sz_row.setSpacing(6)
        sz_row.addWidget(QLabel('Units:'))
        self.fig_unit = QComboBox()
        self.fig_unit.addItems(['cm', 'inches', 'pixels'])
        self.fig_unit.setFixedWidth(70)
        self.fig_unit.currentTextChanged.connect(self._on_fig_unit_changed)
        sz_row.addWidget(self.fig_unit)
        sz_row.addWidget(QLabel('W:'))
        self.fig_width = QDoubleSpinBox()
        self.fig_width.setDecimals(1)
        self.fig_width.setRange(2, 200)
        self.fig_width.setValue(20.0)
        self.fig_width.setSingleStep(0.5)
        self.fig_width.valueChanged.connect(self._on_figsize_manual_change)
        sz_row.addWidget(self.fig_width)
        sz_row.addWidget(QLabel('H:'))
        self.fig_height = QDoubleSpinBox()
        self.fig_height.setDecimals(1)
        self.fig_height.setRange(2, 200)
        self.fig_height.setValue(15.0)
        self.fig_height.setSingleStep(0.5)
        self.fig_height.valueChanged.connect(self._on_figsize_manual_change)
        sz_row.addWidget(self.fig_height)
        sz_row.addStretch()
        layout.addLayout(sz_row)

        # ── Margins (2-column layout) ─────────────────────────────────────────
        layout.addWidget(self._sec_label('Margins'))
        margins_grid = QHBoxLayout()
        margins_grid.setSpacing(10)
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()
        # Shown in physical units (fig_unit) but stored as fractions of the figure
        # (self._fig_margins); the defaults are 0.10 / 0.95 / 0.10 / 0.95, i.e.
        # 2 / 19 / 1.5 / 14.25 cm on the default 20 × 15 cm figure.
        for idx, (attr, label, col) in enumerate([
            ('fig_left',   'Left',   left_col),
            ('fig_right',  'Right',  right_col),
            ('fig_bottom', 'Bottom', left_col),
            ('fig_top',    'Top',    right_col),
        ]):
            mr = QHBoxLayout()
            mr.setSpacing(4)
            lbl = QLabel(label)
            lbl.setFixedWidth(44)
            mr.addWidget(lbl)
            sp = QDoubleSpinBox()
            sp.setFixedWidth(66)
            # Range, decimals and value come from _refresh_geometry_widgets below.
            sp.valueChanged.connect(lambda v, i=idx: self._on_margin_edited(i, v))
            setattr(self, attr, sp)
            mr.addWidget(sp)
            col.addLayout(mr)
        margins_grid.addLayout(left_col)
        margins_grid.addLayout(right_col)
        margins_grid.addStretch()
        layout.addLayout(margins_grid)

        # All size, margin and title widgets now exist: start from the default
        # fractions and let them fill in the spinboxes.
        self._fig_margins = list(self._DEFAULT_MARGINS)
        self._title_frac = list(self._DEFAULT_TITLE_FRAC)
        self._refresh_geometry_widgets()

        # Subplot spacing (hspace / wspace)
        sp_row = QHBoxLayout()
        sp_row.setSpacing(6)
        sp_row.addWidget(QLabel('H spacing:'))
        self.sp_hspace = QDoubleSpinBox()
        self.sp_hspace.setRange(0.0, 1.0)
        self.sp_hspace.setSingleStep(0.05)
        self.sp_hspace.setDecimals(2)
        self.sp_hspace.setValue(0.35)
        self.sp_hspace.setFixedWidth(66)
        self.sp_hspace.setToolTip('Vertical gap between subplot rows')
        self.sp_hspace.valueChanged.connect(self.update_preview)
        sp_row.addWidget(self.sp_hspace)
        sp_row.addWidget(QLabel('W spacing:'))
        self.sp_wspace = QDoubleSpinBox()
        self.sp_wspace.setRange(0.0, 1.0)
        self.sp_wspace.setSingleStep(0.05)
        self.sp_wspace.setDecimals(2)
        self.sp_wspace.setValue(0.35)
        self.sp_wspace.setFixedWidth(66)
        self.sp_wspace.setToolTip('Horizontal gap between subplot columns')
        self.sp_wspace.valueChanged.connect(self.update_preview)
        sp_row.addWidget(self.sp_wspace)
        sp_row.addStretch()
        layout.addLayout(sp_row)

        # Dummy preset_combo to keep _collect_settings/_apply_settings happy
        self.preset_combo = QComboBox()
        self.preset_combo.setVisible(False)
        layout.addWidget(self.preset_combo)

        layout.addWidget(self._hline())

        # ── Colors ────────────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Colors'))
        color_row('Background:',  'chart_bg_color', '#ffffff', 'chart_bg')
        color_row('Foreground:',  'chart_fg_color', '#000000', 'chart_fg')

        layout.addStretch()
        scroll.setWidget(content)
        mlay = QVBoxLayout(widget)
        mlay.addWidget(scroll)
        self.tabs.addTab(widget,'Style')
