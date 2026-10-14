"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_data.py  –  plotviz
DataTabMixin: create_data_tab(): dataset table and import controls.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QListWidget,
    QScrollArea, QTableWidget, QHeaderView,
)
from PyQt6.QtCore import Qt
from ui.tab_constants import (
    ALL_CHART_TYPES,
    PLOT_MODE_GROUPS,
    _ClampWidth,
)


class DataTabMixin:
    def create_data_tab(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)

        # ── Active subplot selector (shown when n > 1) ───────────────────────
        sp_sel_row = QHBoxLayout()
        sp_sel_row.setSpacing(6)
        sp_sel_row.addWidget(QLabel('Subplot:'))
        self.series_sp_active = QComboBox()
        self.series_sp_active.addItem('Subplot 1')
        self.series_sp_active.currentIndexChanged.connect(self._on_series_subplot_changed)
        sp_sel_row.addWidget(self.series_sp_active)
        sp_sel_row.addStretch()
        self._series_sp_row_widget = QWidget()
        self._series_sp_row_widget.setLayout(sp_sel_row)
        self._series_sp_row_widget.setVisible(False)
        layout.addWidget(self._series_sp_row_widget)

        # ── Plot Mode selector ───────────────────────────────────────────────
        layout.addWidget(self._hline())
        layout.addWidget(self._sec_label('Plot Mode'))
        self.plot_mode_combo = QComboBox()
        self.plot_mode_combo.addItems(list(PLOT_MODE_GROUPS.keys()))
        self.plot_mode_combo.setToolTip('Sets what types of series can be drawn on this subplot')
        self.plot_mode_combo.currentTextChanged.connect(self._on_plot_mode_changed)
        layout.addWidget(self.plot_mode_combo)

        layout.addWidget(self._hline())

        # ── Series table: X, Y, Label, Type, Plot, Y2 ────────────────────────
        layout.addWidget(self._sec_label('Series'))
        self.series_table = QTableWidget(0, 6)
        self.series_table.setHorizontalHeaderLabels(['X column', 'Y column', 'Label', 'Type', 'Plot', 'Y2'])
        hh = self.series_table.horizontalHeader()
        hh.setStretchLastSection(False)
        # Stretch X, Y, Label, Type proportionally; keep Plot and Y2 fixed-width
        for _ci in (0, 1, 2, 3):
            hh.setSectionResizeMode(_ci, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        hh.resizeSection(4, 38)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        hh.resizeSection(5, 32)
        self.series_table.setMinimumHeight(140)
        self.series_table.setSizePolicy(
            __import__('PyQt6.QtWidgets', fromlist=['QSizePolicy']).QSizePolicy.Policy.Expanding,
            __import__('PyQt6.QtWidgets', fromlist=['QSizePolicy']).QSizePolicy.Policy.Expanding,
        )
        self.series_table.itemChanged.connect(self._on_series_item_changed)
        self.series_table.itemSelectionChanged.connect(self._on_series_selection_changed)
        self.series_table.itemDoubleClicked.connect(self._on_series_label_double_click)
        layout.addWidget(self.series_table)

        sr = QHBoxLayout()
        sr.setSpacing(4)
        btn_add_row = QPushButton('➕ Add series')
        btn_add_row.clicked.connect(self._add_series_row)
        btn_del_row = QPushButton('➖ Remove selected')
        btn_del_row.clicked.connect(self._del_series_row)
        sr.addWidget(btn_add_row)
        sr.addWidget(btn_del_row)
        layout.addLayout(sr)

        # Hidden chart_type_combo — kept for backward-compat with plot_engine,
        # chart_export, plot_decorators etc. Always reflects the active series type.
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.setVisible(False)
        self.chart_type_combo.addItems(ALL_CHART_TYPES)
        layout.addWidget(self.chart_type_combo)

        # Hidden combo_x / y_list kept for compat
        self.combo_x = QComboBox()
        self.combo_x.setVisible(False)
        self.y_list  = QListWidget()
        self.y_list.setVisible(False)
        self.y_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.y_list.itemSelectionChanged.connect(self.on_y_selection_changed)
        layout.addWidget(self.combo_x)
        layout.addWidget(self.y_list)

        # ── Series-selection-driven extras (Z col, Err col, option groups) ─────
        # These are wrapped so they can be shown/hidden based on the selected
        # series row's type rather than the (now hidden) chart_type_combo.
        layout.addWidget(self._hline())

        self._combo_z_widget = QWidget()
        _zl = QVBoxLayout(self._combo_z_widget)
        _zl.setContentsMargins(0,0,0,0)
        _zl.setSpacing(2)
        _zl.addWidget(QLabel('Z / Color column  (Heatmap, Contour, Tricontour, 3D):'))
        self.combo_z = QComboBox()
        self.combo_z.addItem('(none)')
        self.combo_z.currentIndexChanged.connect(self.update_preview)
        _zl.addWidget(self.combo_z)
        self._combo_z_widget.setVisible(False)
        layout.addWidget(self._combo_z_widget)

        self._combo_err_widget = QWidget()
        _el = QVBoxLayout(self._combo_err_widget)
        _el.setContentsMargins(0,0,0,0)
        _el.setSpacing(2)
        _el.addWidget(QLabel('Error column  (Errorbar):'))
        self.combo_err = QComboBox()
        self.combo_err.addItem('(none)')
        self.combo_err.currentIndexChanged.connect(self.update_preview)
        _el.addWidget(self.combo_err)
        self._combo_err_widget.setVisible(False)
        layout.addWidget(self._combo_err_widget)

        self._combo_fill_y2_widget = QWidget()
        _fy2l = QVBoxLayout(self._combo_fill_y2_widget)
        _fy2l.setContentsMargins(0,0,0,0)
        _fy2l.setSpacing(2)
        _fy2l.addWidget(QLabel('Y2 column  (Fill Between):'))
        self.combo_fill_y2 = QComboBox()
        self.combo_fill_y2.addItem('(none)')
        self.combo_fill_y2.currentIndexChanged.connect(self.update_preview)
        _fy2l.addWidget(self.combo_fill_y2)
        self._combo_fill_y2_widget.setVisible(False)
        layout.addWidget(self._combo_fill_y2_widget)

        layout.addWidget(self._hline())

        # ── Selected series indicator ─────────────────────────────────────────
        self._selected_series_label = QLabel('▶  No series selected')
        self._selected_series_label.setStyleSheet(
            'font-weight:bold; color:#555; font-size:11px; padding:2px 0;')
        layout.addWidget(self._selected_series_label)

        # ── Chart-type option groups (visible one at a time) ──────────────────
        self._build_chart_option_groups(layout)

        layout.addStretch()
        scroll.setWidget(content)
        _cw = _ClampWidth(content, scroll)
        scroll.viewport().installEventFilter(_cw)
        mlay = QVBoxLayout(widget)
        mlay.setContentsMargins(0,0,0,0)
        mlay.addWidget(scroll)
        self.plots_inner_tabs.addTab(widget, 'Data')
        self._on_plot_mode_changed('Standard')

        # Dummy sp_chart_type — kept for compat
        self.sp_chart_type = QComboBox()
        self.sp_chart_type.setVisible(False)
        self.sp_chart_type.addItems(ALL_CHART_TYPES)
