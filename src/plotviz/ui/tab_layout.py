"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_layout.py  –  plotviz
LayoutTabMixin: create_layout_tab() and create_plots_tab(): figure size, subplots and plot-mode selection.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton, QCheckBox, QGroupBox, QTabWidget, QSlider,
)
from PyQt6.QtCore import Qt


class LayoutTabMixin:
    # ─── Canvas + grid panel (per subplot; shown inside the Axes tab) ─────────
    def create_layout_tab(self):
        """Build the per-subplot canvas, border, grid and 3D-viewpoint controls.

        They are not a tab of their own: the panel is kept in
        ``self._canvas_grid_panel`` and create_axes_tab() adds it to the Axes tab.
        """
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Subplot selector (shown only when n > 1) ──────────────────────────
        sp_sel_row = QHBoxLayout()
        sp_sel_row.setSpacing(6)
        sp_sel_row.addWidget(QLabel('Subplot:'))
        self.layout_sp_active = QComboBox()
        self.layout_sp_active.addItem('Subplot 1')
        self.layout_sp_active.currentIndexChanged.connect(self._on_layout_sp_changed)
        sp_sel_row.addWidget(self.layout_sp_active)
        sp_sel_row.addStretch()
        self._layout_sp_row_widget = QWidget()
        self._layout_sp_row_widget.setLayout(sp_sel_row)
        self._layout_sp_row_widget.setVisible(False)
        layout.addWidget(self._layout_sp_row_widget)

        # ── Chart Canvas ──────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Chart Canvas'))

        def _color_row(label_text, attr_name, default_hex, pick_target):
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
            btn.clicked.connect(lambda _=False, t=pick_target: self.pick_color(t))
            r.addWidget(btn)
            r.addStretch()
            layout.addLayout(r)

        _color_row('Plot area:', 'plot_bg_color',  '#ffffff', 'plot_bg')

        br = QHBoxLayout()
        br.setSpacing(6)
        self.border_top    = QCheckBox('Top')
        self.border_top.setChecked(True)
        self.border_bottom = QCheckBox('Bottom')
        self.border_bottom.setChecked(True)
        self.border_left   = QCheckBox('Left')
        self.border_left.setChecked(True)
        self.border_right  = QCheckBox('Right')
        self.border_right.setChecked(True)
        lbl_b = QLabel('Borders:')
        lbl_b.setFixedWidth(90)
        br.addWidget(lbl_b)
        for chk in (self.border_top, self.border_bottom, self.border_left, self.border_right):
            chk.stateChanged.connect(self.update_preview)
            br.addWidget(chk)
        br.addStretch()
        layout.addLayout(br)

        layout.addWidget(self._hline())

        # ── Grid (major | minor side by side) ─────────────────────────────────
        layout.addWidget(self._sec_label('Grid'))
        grid_row = QHBoxLayout()
        grid_row.setSpacing(6)

        # --- Major ---
        maj_box = QGroupBox('Major')
        maj_lay = QVBoxLayout(maj_box)
        maj_lay.setSpacing(3)
        self.grid_check = QCheckBox('Enable')
        self.grid_check.setChecked(True)
        self.grid_check.stateChanged.connect(self.update_preview)
        maj_lay.addWidget(self.grid_check)
        c1 = QHBoxLayout(); c1.setSpacing(4); c1.addWidget(QLabel('Color:'))
        self.grid_color    = '#cccccc'
        self.grid_color_sw = self._color_sw('#cccccc')
        g_btn = QPushButton('…'); g_btn.setFixedWidth(28)
        g_btn.clicked.connect(lambda: self._pick_grid_color('major'))
        c1.addWidget(self.grid_color_sw); c1.addWidget(g_btn); c1.addStretch()
        maj_lay.addLayout(c1)
        self.grid_linestyle = QComboBox()
        self.grid_linestyle.addItems(['-', '--', '-.', ':'])
        self.grid_linestyle.setCurrentText('--')
        self.grid_linestyle.currentTextChanged.connect(self.update_preview)
        maj_lay.addWidget(self.grid_linestyle)
        wl1 = QHBoxLayout(); wl1.setSpacing(3); wl1.addWidget(QLabel('W:'))
        self.grid_linewidth = QDoubleSpinBox()
        self.grid_linewidth.setRange(0.1, 4.0); self.grid_linewidth.setValue(0.5)
        self.grid_linewidth.setSingleStep(0.1)
        self.grid_linewidth.valueChanged.connect(self.update_preview)
        wl1.addWidget(self.grid_linewidth); maj_lay.addLayout(wl1)
        al1 = QHBoxLayout(); al1.setSpacing(3); al1.addWidget(QLabel('α:'))
        self.grid_alpha = QDoubleSpinBox()
        self.grid_alpha.setRange(0.0, 1.0); self.grid_alpha.setValue(0.4)
        self.grid_alpha.setSingleStep(0.05)
        self.grid_alpha.valueChanged.connect(self.update_preview)
        al1.addWidget(self.grid_alpha); maj_lay.addLayout(al1)
        grid_row.addWidget(maj_box)

        # --- Minor ---
        min_box = QGroupBox('Minor')
        min_lay = QVBoxLayout(min_box)
        min_lay.setSpacing(3)
        self.minor_grid_check = QCheckBox('Enable')
        self.minor_grid_check.stateChanged.connect(self.update_preview)
        min_lay.addWidget(self.minor_grid_check)
        c2 = QHBoxLayout(); c2.setSpacing(4); c2.addWidget(QLabel('Color:'))
        self.minor_grid_color    = '#e8e8e8'
        self.minor_grid_color_sw = self._color_sw('#e8e8e8')
        sg_btn = QPushButton('…'); sg_btn.setFixedWidth(28)
        sg_btn.clicked.connect(lambda: self._pick_grid_color('minor'))
        c2.addWidget(self.minor_grid_color_sw); c2.addWidget(sg_btn); c2.addStretch()
        min_lay.addLayout(c2)
        self.minor_grid_linestyle = QComboBox()
        self.minor_grid_linestyle.addItems(['-', '--', '-.', ':'])
        self.minor_grid_linestyle.setCurrentText(':')
        self.minor_grid_linestyle.currentTextChanged.connect(self.update_preview)
        min_lay.addWidget(self.minor_grid_linestyle)
        wl2 = QHBoxLayout(); wl2.setSpacing(3); wl2.addWidget(QLabel('W:'))
        self.minor_grid_linewidth = QDoubleSpinBox()
        self.minor_grid_linewidth.setRange(0.1, 4.0); self.minor_grid_linewidth.setValue(0.3)
        self.minor_grid_linewidth.setSingleStep(0.1)
        self.minor_grid_linewidth.valueChanged.connect(self.update_preview)
        wl2.addWidget(self.minor_grid_linewidth); min_lay.addLayout(wl2)
        al2 = QHBoxLayout(); al2.setSpacing(3); al2.addWidget(QLabel('α:'))
        self.minor_grid_alpha = QDoubleSpinBox()
        self.minor_grid_alpha.setRange(0.0, 1.0); self.minor_grid_alpha.setValue(0.2)
        self.minor_grid_alpha.setSingleStep(0.05)
        self.minor_grid_alpha.valueChanged.connect(self.update_preview)
        al2.addWidget(self.minor_grid_alpha); min_lay.addLayout(al2)
        grid_row.addWidget(min_box)

        layout.addLayout(grid_row)

        # ── 3D Viewpoint (shown only for 3D Surface charts) ───────────────────
        layout.addWidget(self._hline())
        self._layout_3d_view_widget = QGroupBox('3D Viewpoint')
        _3dv_lay = QVBoxLayout(self._layout_3d_view_widget)
        _3dv_lay.setSpacing(5)

        def _make_angle_row(label_text, slider_attr, spin_attr, lo, hi, default):
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(72)
            row.addWidget(lbl)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(lo, hi)
            slider.setValue(default)
            row.addWidget(slider, 1)
            spin = QSpinBox()
            spin.setRange(lo, hi)
            spin.setValue(default)
            spin.setSuffix('°')
            spin.setFixedWidth(62)
            row.addWidget(spin)
            # Keep slider and spinbox in sync (value equality prevents loops)
            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)
            # Trigger preview on change
            slider.valueChanged.connect(self.update_preview)
            setattr(self, slider_attr, slider)
            setattr(self, spin_attr, spin)
            _3dv_lay.addLayout(row)

        _make_angle_row('Elevation:', 'view3d_elev_slider', 'view3d_elev_spin',
                        -90, 90, 30)
        _make_angle_row('Azimuth:', 'view3d_azim_slider', 'view3d_azim_spin',
                        -180, 180, -60)

        _reset_3d_btn = QPushButton('Reset View')
        _reset_3d_btn.setFixedWidth(100)
        def _reset_3d_view():
            for sl, sp, val in [
                (self.view3d_elev_slider, self.view3d_elev_spin, 30),
                (self.view3d_azim_slider, self.view3d_azim_spin, -60),
            ]:
                sl.blockSignals(True); sp.blockSignals(True)
                sl.setValue(val);       sp.setValue(val)
                sl.blockSignals(False); sp.blockSignals(False)
            self.update_preview()
        _reset_3d_btn.clicked.connect(_reset_3d_view)
        _3dv_btn_row = QHBoxLayout()
        _3dv_btn_row.addWidget(_reset_3d_btn)
        _3dv_btn_row.addStretch()
        _3dv_lay.addLayout(_3dv_btn_row)

        self._layout_3d_view_widget.setVisible(False)
        layout.addWidget(self._layout_3d_view_widget)

        self._canvas_grid_panel = content

    # ─── Plots tab (container for subplot selector + inner tabs) ──────────────
    def create_plots_tab(self):
        outer = QWidget()
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(4, 4, 4, 4)
        outer_lay.setSpacing(4)

        # ── Subplot selector (shown only when n > 1) ──────────────────────────
        self._global_sp_container = QWidget()
        _gsp_lay = QHBoxLayout(self._global_sp_container)
        _gsp_lay.setContentsMargins(4, 2, 4, 2)
        _gsp_lay.setSpacing(4)
        _gsp_lay.addWidget(QLabel('Editing:'))
        self.global_sp_active = QComboBox()
        self.global_sp_active.addItem('Subplot 1')
        self.global_sp_active.setMinimumWidth(110)
        self.global_sp_active.setToolTip(
            'The subplot that the Data, Series, Axes and Annotations tabs edit')
        self.global_sp_active.currentIndexChanged.connect(self._on_global_sp_changed)
        _gsp_lay.addWidget(self.global_sp_active)
        _gsp_lay.addStretch()
        self.global_sp_active.setEnabled(False)       # one subplot: nothing to choose
        outer_lay.addWidget(self._global_sp_container)

        # ── Inner tab widget ──────────────────────────────────────────────────
        self.plots_inner_tabs = QTabWidget()
        self.create_data_tab()
        self.create_layout_tab()
        self.create_series_tab()
        self.create_axes_tab()
        self.create_annotations_tab()
        outer_lay.addWidget(self.plots_inner_tabs)

        self.tabs.addTab(outer, 'Plots')
