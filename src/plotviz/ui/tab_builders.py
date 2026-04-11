"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.


ui/tab_builders.py  –  plotviz
Mixin that provides all create_*_tab() methods for PlotVizApp.
"""
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton, QFileDialog, QListWidget,
    QCheckBox, QScrollArea, QColorDialog, QButtonGroup, QRadioButton,
    QFrame, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QSizePolicy, QPlainTextEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from data.scientific import CurveFitter

ALL_CHART_TYPES = [
    # ── Per-series mixable ────────────────────────────────────────────
    'Line', 'Scatter', 'Bar', 'Errorbar', 'Area', 'Fill Between',
    'Step', 'Stem', 'Bubble', 'Waterfall',
    # ── Whole-chart / specialised ─────────────────────────────────────
    'Histogram', 'Hist2D', 'Hexbin',
    'Boxplot', 'Violin',
    'Pie', 'Polar', 'Radar',
    'Heatmap', 'Contour', '3D Surface',
    'ECDF', 'Quiver', 'Barbs', 'Streamplot',
]

# Types available per-series in the table Type column (all types)
PER_SERIES_TYPES = ALL_CHART_TYPES

# Types that take over the whole chart (no per-series mixing)
WHOLE_CHART_TYPES = {
    'Histogram', 'Hist2D', 'Hexbin',
    'Boxplot', 'Violin',
    'Pie', 'Polar', 'Radar',
    'Heatmap', 'Contour', '3D Surface',
    'ECDF', 'Quiver', 'Barbs', 'Streamplot',
}

_NO_X_TYPES = {'Histogram', 'Boxplot', 'Violin', 'Pie', 'ECDF',
}

# Master colormap list — sorted alphabetically (case-insensitive).
_CMAP_LIST = sorted([
    'viridis', 'plasma', 'inferno', 'magma', 'cividis', 'turbo',
    'Blues', 'Greens', 'Reds', 'Purples', 'Oranges', 'Greys',
    'YlOrRd', 'YlGnBu', 'BuPu', 'RdPu', 'PuBu',
    'hot', 'cool', 'copper', 'bone', 'gray',
    'coolwarm', 'RdBu', 'RdYlBu', 'RdYlGn', 'Spectral',
    'PiYG', 'PRGn', 'BrBG', 'PuOr', 'bwr', 'seismic',
    'twilight', 'hsv',
    'rainbow', 'nipy_spectral',
], key=str.casefold)

# ── Plot-mode groups ──────────────────────────────────────────────────────────
# "Standard" covers all freely-mixable per-series types. The remaining modes
# are for whole-chart exclusive types that can't be mixed with anything else.
PLOT_MODE_GROUPS = {
    'Standard':          ['Line', 'Scatter', 'Bar', 'Area', 'Fill Between',
                          'Errorbar', 'Step', 'Stem', 'Bubble', 'Waterfall'],
    'Histogram':         ['Histogram'],
    'Statistical':       ['Boxplot', 'Violin', 'ECDF'],
    'Heatmap & Contour': ['Heatmap', 'Contour', 'Hist2D', 'Hexbin', '3D Surface'],
    'Polar & Radar':     ['Polar', 'Radar'],
    'Pie':               ['Pie'],
    'Quiver':            ['Quiver', 'Barbs', 'Streamplot'],
}

# Reverse: given a series type, which plot mode contains it?
TYPE_TO_PLOT_MODE = {t: m for m, types in PLOT_MODE_GROUPS.items() for t in types}

# ── Named colour palettes available in the Data tab (16 colours = Qt custom slots)
COLOR_PALETTES = {
    'Matplotlib':  ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd',
                    '#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf',
                    '#aec7e8','#ffbb78','#98df8a','#ff9896','#c5b0d5',
                    '#c49c94'],
    'Pastel':      ['#aec6cf','#ffb347','#b5ead7','#ff9aa2','#c7ceea',
                    '#ffdac1','#e2f0cb','#f8c8d4','#d4a5c9','#b5d8cc',
                    '#a8d8ea','#f9e4b7','#c8e6c9','#f8bbd0','#d1c4e9',
                    '#ffe0b2'],
    'Bold':        ['#e6194b','#3cb44b','#4363d8','#f58231','#911eb4',
                    '#42d4f4','#f032e6','#bfef45','#fabed4','#469990',
                    '#9a6324','#fffac8','#800000','#aaffc3','#808000',
                    '#ffd8b1'],
    'Earth':       ['#8b4513','#cd853f','#556b2f','#6b8e23','#8fbc8f',
                    '#bc8f5f','#a0522d','#deb887','#696969','#808000',
                    '#d2691e','#f4a460','#228b22','#90ee90','#a9a9a9',
                    '#c8a882'],
    'Ocean':       ['#003f5c','#2f4b7c','#665191','#a05195','#d45087',
                    '#f95d6a','#ff7c43','#ffa600','#488f8f','#2b9999',
                    '#005f73','#0a9396','#94d2bd','#e9d8a6','#ee9b00',
                    '#ca6702'],
    'Warm':        ['#d62728','#ff7f0e','#e377c2','#bcbd22','#f7b731',
                    '#e55039','#f39c12','#c0392b','#e74c3c','#d35400',
                    '#f1c40f','#e67e22','#e91e63','#ff5722','#ffc107',
                    '#ff6b6b'],
    'Cool':        ['#1f77b4','#17becf','#2ca02c','#9467bd','#4169e1',
                    '#00ced1','#3cb371','#6a5acd','#20b2aa','#1e90ff',
                    '#5c85d6','#4fc3f7','#81c784','#ba68c8','#4dd0e1',
                    '#26c6da'],
    'Colorblind':  ['#0077bb','#ee7733','#009988','#cc3311','#33bbee',
                    '#ee3377','#bbbbbb','#000000','#994455','#ddaa33',
                    '#004488','#bb5566','#6699cc','#eecc66','#997700',
                    '#44bb99'],
    'Nature':      ['#4e9a8d','#f4a261','#e76f51','#264653','#2a9d8f',
                    '#e9c46a','#a8dadc','#457b9d','#1d3557','#f1faee',
                    '#606c38','#dda15e','#bc6c25','#283618','#fefae0',
                    '#588157'],
    'Publication': ['#000000','#e41a1c','#377eb8','#4daf4a','#984ea3',
                    '#ff7f00','#a65628','#f781bf','#999999','#ffff33',
                    '#66c2a5','#fc8d62','#8da0cb','#e78ac3','#a6d854',
                    '#ffd92f'],
    'Grayscale':   ['#000000','#111111','#222222','#404040','#606060',
                    '#808080','#909090','#999999','#b0b0b0','#c0c0c0',
                    '#c8c8c8','#d0d0d0','#d8d8d8','#e0e0e0','#e8e8e8',
                    '#f0f0f0'],
}

# Runtime-added custom palettes (loaded from palette.json in .pvizp or user prefs)
_CUSTOM_PALETTES: dict = {}


def get_all_palettes() -> dict:
    """Return built-in + custom palettes merged."""
    return {**COLOR_PALETTES, **_CUSTOM_PALETTES}


def add_custom_palette(name: str, colors: list):
    """Register a custom palette at runtime."""
    _CUSTOM_PALETTES[name] = colors[:16]

_FONTS = ['sans-serif', 'serif', 'monospace']


class TabBuildersMixin:
    def create_file_tab(self):
        widget = QWidget(); scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); layout = QVBoxLayout(content); layout.setSpacing(6)

        # ── Open row ──────────────────────────────────────────────────────────
        open_row = QHBoxLayout(); open_row.setSpacing(4)
        self._open_combo = QComboBox()
        self._open_combo.addItems(['Open Chart  (.pviz)', 'Load Template  (.pvizt)'])
        open_row.addWidget(self._open_combo, 1)
        btn_open_go = QPushButton('📂 Open')
        btn_open_go.setFixedWidth(80)
        def _do_open():
            if self._open_combo.currentIndex() == 0: self._load_project()
            else: self._load_template()
        btn_open_go.clicked.connect(_do_open)
        open_row.addWidget(btn_open_go)
        layout.addLayout(open_row)

        # ── Recent files ──────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Recent Files'))
        self._recent_list = QListWidget()
        self._recent_list.setMaximumHeight(110)
        self._recent_list.setToolTip('Double-click to open')
        self._recent_list.itemDoubleClicked.connect(self._open_recent_file)
        layout.addWidget(self._recent_list)

        # ── Save row ──────────────────────────────────────────────────────────
        save_row = QHBoxLayout(); save_row.setSpacing(4)
        self._save_combo = QComboBox()
        self._save_combo.addItems(['Save Chart  (.pviz)', 'Save Template  (.pvizt)'])
        save_row.addWidget(self._save_combo, 1)
        btn_save_go = QPushButton('💾 Save')
        btn_save_go.setFixedWidth(80)
        def _do_save():
            if self._save_combo.currentIndex() == 0: self._save_project()
            else: self._save_template()
        btn_save_go.clicked.connect(_do_save)
        save_row.addWidget(btn_save_go)
        layout.addLayout(save_row)

        # ── Export row ────────────────────────────────────────────────────────
        exp_row = QHBoxLayout(); exp_row.setSpacing(4)
        self._export_fmt_combo = QComboBox()
        self._export_fmt_combo.addItems(['PNG', 'SVG', 'PDF', 'JPEG'])
        exp_row.addWidget(self._export_fmt_combo)
        exp_row.addWidget(QLabel('DPI:'))
        self.dpi_spin = QSpinBox(); self.dpi_spin.setRange(72, 600); self.dpi_spin.setValue(300)
        self.dpi_spin.setFixedWidth(62)
        exp_row.addWidget(self.dpi_spin)
        btn_export_go = QPushButton('⬆ Export')
        btn_export_go.setFixedWidth(80)
        btn_export_go.clicked.connect(
            lambda: self.export_chart(self._export_fmt_combo.currentText().lower()))
        exp_row.addWidget(btn_export_go)
        layout.addLayout(exp_row)

        layout.addWidget(self._hline())

        # ── Subplot Grid ──────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Subplot Grid'))
        # sp_rows / sp_cols / sp_sharex / sp_sharey are kept as hidden widgets so
        # serialisation and on_subplot_layout_changed continue to work unchanged.
        self.sp_rows = QSpinBox(); self.sp_rows.setRange(1, 8); self.sp_rows.setValue(1)
        self.sp_rows.valueChanged.connect(lambda _: self.on_subplot_layout_changed())
        self.sp_rows.setVisible(False)
        self.sp_cols = QSpinBox(); self.sp_cols.setRange(1, 8); self.sp_cols.setValue(1)
        self.sp_cols.valueChanged.connect(lambda _: self.on_subplot_layout_changed())
        self.sp_cols.setVisible(False)
        self.sp_sharex = QCheckBox('Share X')
        self.sp_sharex.stateChanged.connect(self.update_preview)
        self.sp_sharex.setVisible(False)
        self.sp_sharey = QCheckBox('Share Y')
        self.sp_sharey.stateChanged.connect(self.update_preview)
        self.sp_sharey.setVisible(False)
        btn_subplot_cfg = QPushButton('⚙️  Configure Subplot Layout…')
        btn_subplot_cfg.setToolTip('Pick a preset or draw a custom mosaic layout')
        btn_subplot_cfg.clicked.connect(self._open_subplot_config_dialog)
        layout.addWidget(btn_subplot_cfg)

        layout.addWidget(self._hline())

        # ── Datasets ──────────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Datasets'))
        btn_load = QPushButton('📂  Browse Files  (CSV, Excel, JSON, TXT)')
        btn_load.clicked.connect(self.load_data); layout.addWidget(btn_load)
        self.dataset_list = QListWidget(); self.dataset_list.setMinimumHeight(120); self.dataset_list.setMaximumHeight(220)
        self.dataset_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.dataset_list)
        ds_btn_row = QHBoxLayout(); ds_btn_row.setSpacing(4)
        btn_remove_ds = QPushButton('🗑 Remove selected')
        btn_remove_ds.clicked.connect(self._remove_selected_datasets)
        btn_inspect = QPushButton('🔍 Inspect values')
        btn_inspect.setToolTip('Inspect selected column(s), or all if none selected')
        btn_inspect.clicked.connect(self._inspect_series)
        ds_btn_row.addWidget(btn_remove_ds); ds_btn_row.addWidget(btn_inspect)
        layout.addLayout(ds_btn_row)

        layout.addWidget(self._hline())

        # ── Colour palette ────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Colour Palette'))
        pal_row = QHBoxLayout(); pal_row.setSpacing(6)
        self.palette_combo = QComboBox()
        self.palette_combo.addItems(sorted(COLOR_PALETTES.keys(), key=str.casefold))
        idx = self.palette_combo.findText('Matplotlib')
        if idx >= 0: self.palette_combo.setCurrentIndex(idx)
        self.palette_combo.currentTextChanged.connect(self._on_palette_changed)
        pal_row.addWidget(self.palette_combo)
        pal_row.addStretch()
        layout.addLayout(pal_row)
        self._palette_swatch_row = QHBoxLayout(); self._palette_swatch_row.setSpacing(2)
        self._palette_swatches = []
        for _ in range(16):
            sw = QLabel()
            sw.setFixedSize(18, 14)
            sw.setStyleSheet('background:#ccc; border:1px solid #aaa;')
            self._palette_swatches.append(sw)
            self._palette_swatch_row.addWidget(sw)
        self._palette_swatch_row.addStretch()
        layout.addLayout(self._palette_swatch_row)
        pal_btn_row = QHBoxLayout(); pal_btn_row.setSpacing(4)
        btn_edit_pal = QPushButton('✏️ Edit palette…')
        btn_edit_pal.setToolTip('Create or edit a custom colour palette')
        btn_edit_pal.clicked.connect(self._open_palette_editor)
        pal_btn_row.addWidget(btn_edit_pal)
        btn_reset_locks = QPushButton('↺ Reset colors')
        btn_reset_locks.setToolTip('Remove manual color locks from all series and re-apply the active palette')
        btn_reset_locks.clicked.connect(self._reset_all_color_locks)
        pal_btn_row.addWidget(btn_reset_locks)
        pal_btn_row.addStretch()
        layout.addLayout(pal_btn_row)
        pal_io_row = QHBoxLayout(); pal_io_row.setSpacing(4)
        btn_import_pal = QPushButton('📥 Load palette…')
        btn_import_pal.setToolTip('Load a .pvizp palette bundle')
        btn_import_pal.clicked.connect(self._import_palette_bundle)
        pal_io_row.addWidget(btn_import_pal)
        btn_export_pal = QPushButton('📤 Save palette…')
        btn_export_pal.setToolTip('Save custom palettes as a .pvizp bundle')
        btn_export_pal.clicked.connect(self._export_palette_bundle)
        pal_io_row.addWidget(btn_export_pal)
        pal_io_row.addStretch()
        layout.addLayout(pal_io_row)
        self._refresh_palette_swatches()

        layout.addWidget(self._hline())

        # ── Color Schemes ─────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Color Schemes'))

        cs_sel_row = QHBoxLayout(); cs_sel_row.setSpacing(4)
        self._cs_combo = QComboBox()
        self._cs_combo.setToolTip('Select a built-in or saved color scheme')
        cs_sel_row.addWidget(self._cs_combo, 1)
        btn_cs_apply = QPushButton('Apply')
        btn_cs_apply.setFixedWidth(54)
        btn_cs_apply.setToolTip('Apply selected color scheme to the chart')
        btn_cs_apply.clicked.connect(self._apply_color_scheme_selected)
        cs_sel_row.addWidget(btn_cs_apply)
        layout.addLayout(cs_sel_row)

        # Swatch row — 5 colored squares showing bg / fg / plot / grid / accent
        self._cs_swatches = []
        sw_row = QHBoxLayout(); sw_row.setSpacing(3)
        for _ in range(5):
            sw = QLabel()
            sw.setFixedSize(22, 16)
            sw.setStyleSheet('background:#ccc; border:1px solid #888; border-radius:2px;')
            self._cs_swatches.append(sw)
            sw_row.addWidget(sw)
        sw_labels = [QLabel(t) for t in ('BG', 'Plot', 'FG', 'Grid', 'Title')]
        for lbl in sw_labels:
            lbl.setStyleSheet('font-size:9px; color:#888;')
        sw_detail = QHBoxLayout(); sw_detail.setSpacing(3)
        for i, lbl in enumerate(sw_labels):
            pair = QVBoxLayout(); pair.setSpacing(1)
            pair.addWidget(self._cs_swatches[i], alignment=Qt.AlignmentFlag.AlignHCenter)
            pair.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignHCenter)
            sw_detail.addLayout(pair)
        sw_detail.addStretch()
        layout.addLayout(sw_detail)

        cs_btn_row = QHBoxLayout(); cs_btn_row.setSpacing(4)
        btn_cs_load = QPushButton('📂 Load scheme…')
        btn_cs_load.setToolTip('Load a .pvizc color scheme file')
        btn_cs_load.clicked.connect(self._load_color_scheme)
        cs_btn_row.addWidget(btn_cs_load)
        btn_cs_save = QPushButton('💾 Save scheme…')
        btn_cs_save.setToolTip('Save current colors as a .pvizc color scheme')
        btn_cs_save.clicked.connect(self._save_color_scheme)
        cs_btn_row.addWidget(btn_cs_save)
        cs_btn_row.addStretch()
        layout.addLayout(cs_btn_row)

        # Populate built-in schemes and set initial swatch
        self._init_color_schemes()

        layout.addWidget(self._hline())

        layout.addStretch()
        scroll.setWidget(content); mlay = QVBoxLayout(widget); mlay.addWidget(scroll)
        self.tabs.addTab(widget, 'Chart')
    def create_data_tab(self):
        widget = QWidget()
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        # ── Active subplot selector (shown when n > 1) ───────────────────────
        sp_sel_row = QHBoxLayout(); sp_sel_row.setSpacing(6)
        sp_sel_row.addWidget(QLabel('Subplot:'))
        self.series_sp_active = QComboBox(); self.series_sp_active.addItem('Subplot 1')
        self.series_sp_active.currentIndexChanged.connect(self._on_series_subplot_changed)
        sp_sel_row.addWidget(self.series_sp_active); sp_sel_row.addStretch()
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
        hh.resizeSection(0, 90); hh.resizeSection(1, 90); hh.resizeSection(2, 80)
        hh.resizeSection(3, 75); hh.resizeSection(4, 36); hh.resizeSection(5, 30)
        self.series_table.setMinimumHeight(140)
        self.series_table.setSizePolicy(
            __import__('PyQt6.QtWidgets', fromlist=['QSizePolicy']).QSizePolicy.Policy.Expanding,
            __import__('PyQt6.QtWidgets', fromlist=['QSizePolicy']).QSizePolicy.Policy.Expanding,
        )
        self.series_table.itemChanged.connect(self._on_series_item_changed)
        self.series_table.itemSelectionChanged.connect(self._on_series_selection_changed)
        self.series_table.itemDoubleClicked.connect(self._on_series_label_double_click)
        layout.addWidget(self.series_table)

        sr = QHBoxLayout(); sr.setSpacing(4)
        btn_add_row = QPushButton('➕ Add series')
        btn_add_row.clicked.connect(self._add_series_row)
        btn_del_row = QPushButton('➖ Remove selected')
        btn_del_row.clicked.connect(self._del_series_row)
        sr.addWidget(btn_add_row); sr.addWidget(btn_del_row)
        layout.addLayout(sr)

        # Hidden chart_type_combo — kept for backward-compat with plot_engine,
        # chart_export, plot_decorators etc. Always reflects the active series type.
        self.chart_type_combo = QComboBox(); self.chart_type_combo.setVisible(False)
        self.chart_type_combo.addItems(ALL_CHART_TYPES)
        layout.addWidget(self.chart_type_combo)

        # Hidden combo_x / y_list kept for compat
        self.combo_x = QComboBox(); self.combo_x.setVisible(False)
        self.y_list  = QListWidget(); self.y_list.setVisible(False)
        self.y_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.y_list.itemSelectionChanged.connect(self.on_y_selection_changed)
        layout.addWidget(self.combo_x); layout.addWidget(self.y_list)

        # ── Series-selection-driven extras (Z col, Err col, option groups) ─────
        # These are wrapped so they can be shown/hidden based on the selected
        # series row's type rather than the (now hidden) chart_type_combo.
        layout.addWidget(self._hline())

        self._combo_z_widget = QWidget()
        _zl = QVBoxLayout(self._combo_z_widget); _zl.setContentsMargins(0,0,0,0); _zl.setSpacing(2)
        _zl.addWidget(QLabel('Z / Color column  (Heatmap, Contour, 3D):'))
        self.combo_z = QComboBox(); self.combo_z.addItem('(none)')
        self.combo_z.currentIndexChanged.connect(self.update_preview)
        _zl.addWidget(self.combo_z)
        self._combo_z_widget.setVisible(False)
        layout.addWidget(self._combo_z_widget)

        self._combo_err_widget = QWidget()
        _el = QVBoxLayout(self._combo_err_widget); _el.setContentsMargins(0,0,0,0); _el.setSpacing(2)
        _el.addWidget(QLabel('Error column  (Errorbar):'))
        self.combo_err = QComboBox(); self.combo_err.addItem('(none)')
        self.combo_err.currentIndexChanged.connect(self.update_preview)
        _el.addWidget(self.combo_err)
        self._combo_err_widget.setVisible(False)
        layout.addWidget(self._combo_err_widget)

        self._combo_fill_y2_widget = QWidget()
        _fy2l = QVBoxLayout(self._combo_fill_y2_widget); _fy2l.setContentsMargins(0,0,0,0); _fy2l.setSpacing(2)
        _fy2l.addWidget(QLabel('Y2 column  (Fill Between):'))
        self.combo_fill_y2 = QComboBox(); self.combo_fill_y2.addItem('(none)')
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
        mlay = QVBoxLayout(widget); mlay.addWidget(scroll)
        self.plots_inner_tabs.addTab(widget, 'Data')
        self._on_plot_mode_changed('Standard')

        # Dummy sp_chart_type — kept for compat
        self.sp_chart_type = QComboBox(); self.sp_chart_type.setVisible(False)
        self.sp_chart_type.addItems(ALL_CHART_TYPES)

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
        hgb.addLayout(_row(QLabel('Colormap:'), self._make_combo('cmap_combo', _CMAP_LIST, default='rainbow')))
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

        # ── Fill Between (no chart-mode options; Y2 column is in the dedicated
        #    column-picker widget above; per-series options live in the Series tab)
        self.fill_between_group = QGroupBox('Fill Between Options')
        fbg = QVBoxLayout(self.fill_between_group)
        _fb_hint = QLabel('Select a Y2 column above.\nStyle options are in the Series tab.')
        _fb_hint.setStyleSheet('color:#888; font-size:10px;')
        fbg.addWidget(_fb_hint)
        layout.addWidget(self.fill_between_group)

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
        h2g.addLayout(_row(QLabel('Colormap:'), self._make_combo('hist2d_cmap_combo', _CMAP_LIST, default='rainbow')))
        self.hist2d_colorbar = QCheckBox('Show colorbar'); self.hist2d_colorbar.setChecked(True); self.hist2d_colorbar.stateChanged.connect(self.update_preview); h2g.addWidget(self.hist2d_colorbar)
        self.hist2d_log      = QCheckBox('Log color scale'); self.hist2d_log.stateChanged.connect(self.update_preview); h2g.addWidget(self.hist2d_log)
        layout.addWidget(self.hist2d_group)

        # ── Hexbin ────────────────────────────────────────────────────────────
        self.hexbin_group = QGroupBox('Hexbin Options')
        hxg = QVBoxLayout(self.hexbin_group)
        hxg.addLayout(_row(QLabel('Grid size:'), self._make_spin('hexbin_gridsize', 5, 100, 20)))
        hxg.addLayout(_row(QLabel('Alpha:'),     self._make_dbl_spin('hexbin_alpha', 0.05, 1.0, 1.0, 0.05)))
        hxg.addLayout(_row(QLabel('Colormap:'),  self._make_combo('hexbin_cmap_combo', _CMAP_LIST, default='rainbow')))
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
        qvg.addLayout(_row(QLabel('Colormap:'), self._make_combo('quiver_cmap_combo', _CMAP_LIST, default='rainbow')))
        layout.addWidget(self.quiver_group)

        # ── Barbs ─────────────────────────────────────────────────────────────
        self.barbs_group = QGroupBox('Barbs (Wind Barb) Options')
        brg = QVBoxLayout(self.barbs_group)
        brg.addLayout(_row(QLabel('U col (dx):'), self._make_col_combo('barbs_u_combo', '(none)')))
        brg.addLayout(_row(QLabel('V col (dy):'), self._make_col_combo('barbs_v_combo', '(none)')))
        brg.addLayout(_row(QLabel('Length:'),     self._make_dbl_spin('barbs_length', 1.0, 30.0, 7.0, 0.5)))
        brg.addLayout(_row(QLabel('Pivot:'),      self._make_combo('barbs_pivot_combo', ['tip', 'middle', 'tail'])))
        brg.addLayout(_row(QLabel('Alpha:'),      self._make_dbl_spin('barbs_alpha', 0.05, 1.0, 0.85, 0.05)))
        self.barbs_color_by_mag = QCheckBox('Color by magnitude'); self.barbs_color_by_mag.stateChanged.connect(self.update_preview); brg.addWidget(self.barbs_color_by_mag)
        brg.addLayout(_row(QLabel('Colormap:'),   self._make_combo('barbs_cmap_combo', _CMAP_LIST, default='rainbow')))
        layout.addWidget(self.barbs_group)

        # ── Streamplot ────────────────────────────────────────────────────────
        self.streamplot_group = QGroupBox('Streamplot Options')
        spg = QVBoxLayout(self.streamplot_group)
        spg.addLayout(_row(QLabel('U col (dx):'), self._make_col_combo('stream_u_combo', '(none)')))
        spg.addLayout(_row(QLabel('V col (dy):'), self._make_col_combo('stream_v_combo', '(none)')))
        spg.addLayout(_row(QLabel('Density:'),    self._make_dbl_spin('stream_density', 0.1, 10.0, 1.0, 0.1)))
        spg.addLayout(_row(QLabel('Arrow size:'), self._make_dbl_spin('stream_arrowsize', 0.1, 5.0, 1.0, 0.1)))
        spg.addLayout(_row(QLabel('Line width:'), self._make_dbl_spin('stream_linewidth', 0.2, 5.0, 1.5, 0.1)))
        self.stream_color_by_mag = QCheckBox('Color by magnitude'); self.stream_color_by_mag.stateChanged.connect(self.update_preview); spg.addWidget(self.stream_color_by_mag)
        spg.addLayout(_row(QLabel('Colormap:'),   self._make_combo('stream_cmap_combo', _CMAP_LIST, default='rainbow')))
        layout.addWidget(self.streamplot_group)

    # ── Widget factory helpers ─────────────────────────────────────────────────
    def _make_spin(self, attr, lo, hi, val):
        w = QSpinBox(); w.setRange(lo, hi); w.setValue(val)
        setattr(self, attr, w); w.valueChanged.connect(self.update_preview); return w

    def _make_dbl_spin(self, attr, lo, hi, val, step, decimals=None):
        w = QDoubleSpinBox(); w.setRange(lo, hi); w.setValue(val); w.setSingleStep(step)
        if decimals is not None: w.setDecimals(decimals)
        setattr(self, attr, w); w.valueChanged.connect(self.update_preview); return w

    def _make_combo(self, attr, items, default=None):
        w = QComboBox(); w.addItems(items)
        if default is not None:
            idx = w.findText(default)
            if idx >= 0: w.setCurrentIndex(idx)
        setattr(self, attr, w); w.currentTextChanged.connect(self.update_preview); return w

    def _make_linestyle_combo(self, attr, default='-'):
        w = QComboBox(); w.addItems(['-', '--', '-.', ':', 'none'])
        idx = w.findText(default); w.setCurrentIndex(max(idx, 0))
        setattr(self, attr, w); w.currentTextChanged.connect(self.update_preview); return w

    def _make_marker_combo(self, attr, default='None'):
        items = ['None','o','s','^','v','<','>','D','P','X','*','+','x','|','_','h','H','1','2','3','4']
        w = QComboBox(); w.addItems(items)
        idx = w.findText(default); w.setCurrentIndex(max(idx, 0))
        setattr(self, attr, w); w.currentTextChanged.connect(self.update_preview); return w

    def _make_edgecolor_combo(self, attr, default='none'):
        items = ['none','black','white','gray','auto']
        w = QComboBox(); w.addItems(items)
        idx = w.findText(default); w.setCurrentIndex(max(idx, 0))
        setattr(self, attr, w); w.currentTextChanged.connect(self.update_preview); return w

    def _make_col_combo(self, attr, sentinel='(none)'):
        w = QComboBox(); w.addItem(sentinel)
        setattr(self, attr, w); w.currentTextChanged.connect(self.update_preview); return w

    # ── Shared color-picker helpers ───────────────────────────────────────────
    _SW_CSS = 'background-color:{};border:1px solid #888;border-radius:2px;'

    def _color_sw(self, hex_color='#000000'):
        """Create a 22×22 solid-square swatch QLabel."""
        sw = QLabel()
        sw.setFixedSize(22, 22)
        sw.setStyleSheet(self._SW_CSS.format(hex_color))
        return sw

    def _make_color_btn(self, attr, default_hex):
        """Return a QWidget [■ swatch | … btn] for attr; swatch stored as self.<attr>_sw.

        Does NOT overwrite self.<attr> if it is already set — prevents widget
        construction from clobbering a colour restored from a saved file.
        """
        from PyQt6.QtWidgets import QPushButton
        from PyQt6.QtGui import QColor
        from ui.helpers import _show_color_dialog
        if not getattr(self, attr, None):
            setattr(self, attr, default_hex)
        current = getattr(self, attr, default_hex)
        sw = self._color_sw(current)
        setattr(self, attr + '_sw', sw)
        btn = QPushButton('…')
        btn.setFixedWidth(28)
        def _pick():
            pal = self._active_palette_colors() if hasattr(self, '_active_palette_colors') else None
            col = _show_color_dialog(QColor(getattr(self, attr)), self, pal)
            if col.isValid():
                setattr(self, attr, col.name())
                sw.setStyleSheet(self._SW_CSS.format(col.name()))
                self.update_preview()
        btn.clicked.connect(_pick)
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0); h.setSpacing(4)
        h.addWidget(sw); h.addWidget(btn); h.addStretch()
        return container

    # ─── Axes tab ─────────────────────────────────────────────────────────────
    def create_axes_tab(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(5)
        layout.setContentsMargins(6, 6, 6, 6)

        # Helper: compact spinbox widths
        _SW = 60   # narrow spinbox (sizes, rotation)
        _LW = 82   # wider spinbox (limits)
        _DW = 65   # direction/format combo

        # ── Subplot selector (hidden when n == 1) ─────────────────────────────
        sp_sel_row = QHBoxLayout(); sp_sel_row.setSpacing(6)
        sp_sel_row.addWidget(QLabel('Subplot:'))
        self.sp_active = QComboBox(); self.sp_active.addItem('Subplot 1')
        self.sp_active.currentIndexChanged.connect(self.on_active_subplot_changed)
        sp_sel_row.addWidget(self.sp_active); sp_sel_row.addStretch()
        self._axes_sp_row_widget = QWidget()
        self._axes_sp_row_widget.setLayout(sp_sel_row)
        self._axes_sp_row_widget.setVisible(False)
        layout.addWidget(self._axes_sp_row_widget)

        layout.addWidget(self._hline())

        # ══════════════════════════════════════════════════════════════════════
        # ── X Axis ────────────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('X Axis'))

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
        xfont_row1 = QHBoxLayout(); xfont_row1.setSpacing(4)
        xfont_row1.addWidget(QLabel('Font:'))
        self.xlabel_font = QComboBox(); self.xlabel_font.addItems(_FONTS)
        self.xlabel_font.currentTextChanged.connect(self.update_preview)
        xfont_row1.addWidget(self.xlabel_font, 1)
        xfont_row1.addWidget(QLabel('Size:'))
        self.xlabel_size = QSpinBox(); self.xlabel_size.setRange(6, 32); self.xlabel_size.setValue(11)
        self.xlabel_size.setFixedWidth(_SW)
        self.xlabel_size.valueChanged.connect(self.update_preview)
        xfont_row1.addWidget(self.xlabel_size)
        layout.addLayout(xfont_row1)

        # Color  (row 2 of 2)
        xfont_row2 = QHBoxLayout(); xfont_row2.setSpacing(4)
        xfont_row2.addWidget(QLabel('Color:'))
        self.xlabel_color = '#000000'
        self.xlabel_color_label = self._color_sw('#000000')
        xfont_row2.addWidget(self.xlabel_color_label)
        btn_xc = QPushButton('…'); btn_xc.setFixedWidth(28)
        btn_xc.clicked.connect(lambda: self.pick_color('xlabel'))
        xfont_row2.addWidget(btn_xc)
        xfont_row2.addStretch()
        layout.addLayout(xfont_row2)

        # Limits  (min / max on same row, Auto below)
        xlim_row = QHBoxLayout(); xlim_row.setSpacing(4)
        xlim_row.addWidget(QLabel('X min:'))
        self.x_min = QDoubleSpinBox(); self.x_min.setRange(-1e10, 1e10); self.x_min.setSingleStep(0.1)
        self.x_min.setFixedWidth(_LW)
        self.x_min.editingFinished.connect(self._on_sp_lim_changed)
        xlim_row.addWidget(self.x_min)
        xlim_row.addWidget(QLabel('max:'))
        self.x_max = QDoubleSpinBox(); self.x_max.setRange(-1e10, 1e10); self.x_max.setValue(1); self.x_max.setSingleStep(0.1)
        self.x_max.setFixedWidth(_LW)
        self.x_max.editingFinished.connect(self._on_sp_lim_changed)
        xlim_row.addWidget(self.x_max)
        xlim_row.addStretch()
        layout.addLayout(xlim_row)

        xauto_row = QHBoxLayout()
        self.x_auto = QCheckBox('Auto limits'); self.x_auto.setChecked(True)
        self.x_auto.stateChanged.connect(self._on_sp_lim_changed)
        xauto_row.addWidget(self.x_auto); xauto_row.addStretch()
        layout.addLayout(xauto_row)

        # Scale radio buttons
        layout.addWidget(QLabel('Scale:'))
        self.xscale_group = QButtonGroup(self)
        xsr = QHBoxLayout(); xsr.setSpacing(6)
        for lbl, val in [('Linear', 'linear'), ('Log', 'log'), ('Logit', 'logit'), ('Inverted', 'inverted')]:
            rb = QRadioButton(lbl); rb.setProperty('scale_value', val)
            if val == 'linear': rb.setChecked(True)
            rb.toggled.connect(self._save_axes_state)
            self.xscale_group.addButton(rb); xsr.addWidget(rb)
        xsr.addStretch()
        layout.addLayout(xsr)

        # Tick size + direction
        xtick_row1 = QHBoxLayout(); xtick_row1.setSpacing(4)
        xtick_row1.addWidget(QLabel('Tick size:'))
        self.xtick_size = QSpinBox(); self.xtick_size.setRange(4, 24); self.xtick_size.setValue(9)
        self.xtick_size.setFixedWidth(_SW)
        self.xtick_size.valueChanged.connect(self._save_axes_state)
        xtick_row1.addWidget(self.xtick_size)
        xtick_row1.addWidget(QLabel('Direction:'))
        self.xtick_dir = QComboBox(); self.xtick_dir.addItems(['out', 'in', 'inout'])
        self.xtick_dir.setFixedWidth(_DW)
        self.xtick_dir.currentTextChanged.connect(self._save_axes_state)
        xtick_row1.addWidget(self.xtick_dir)
        xtick_row1.addStretch()
        layout.addLayout(xtick_row1)

        # Show ticks + minor ticks
        xtick_row2 = QHBoxLayout()
        self.xticks_show = QCheckBox('Show ticks'); self.xticks_show.setChecked(True)
        self.xticks_show.stateChanged.connect(self._save_axes_state)
        xtick_row2.addWidget(self.xticks_show)
        self.xtick_minor = QCheckBox('Minor ticks'); self.xtick_minor.setChecked(False)
        self.xtick_minor.stateChanged.connect(self._save_axes_state)
        xtick_row2.addWidget(self.xtick_minor)
        xtick_row2.addStretch()
        layout.addLayout(xtick_row2)

        # Rotation
        xtick_rot_row = QHBoxLayout(); xtick_rot_row.setSpacing(4)
        xtick_rot_row.addWidget(QLabel('Rotation:'))
        self.xtick_rotation = QSpinBox(); self.xtick_rotation.setRange(-90, 90); self.xtick_rotation.setValue(0)
        self.xtick_rotation.setFixedWidth(_SW)
        self.xtick_rotation.valueChanged.connect(self._save_axes_state)
        xtick_rot_row.addWidget(self.xtick_rotation)
        xtick_rot_row.addStretch()
        layout.addLayout(xtick_rot_row)

        # Step
        xtick_step_row = QHBoxLayout(); xtick_step_row.setSpacing(4)
        xtick_step_row.addWidget(QLabel('Step (0 = auto):'))
        self.xtick_step = QDoubleSpinBox(); self.xtick_step.setRange(0, 1e9); self.xtick_step.setValue(0); self.xtick_step.setSingleStep(0.1)
        self.xtick_step.setFixedWidth(_LW)
        self.xtick_step.editingFinished.connect(self._save_axes_state)
        xtick_step_row.addWidget(self.xtick_step)
        xtick_step_row.addStretch()
        layout.addLayout(xtick_step_row)

        # Format
        xfmt_row = QHBoxLayout(); xfmt_row.setSpacing(4)
        xfmt_row.addWidget(QLabel('Format:'))
        self.x_formatter = QComboBox()
        self.x_formatter.addItems(['auto', 'plain', 'sci', 'percent', '{x:.2f}', '{x:.0f}'])
        self.x_formatter.setEditable(True)
        self.x_formatter.currentTextChanged.connect(self._save_axes_state)
        xfmt_row.addWidget(self.x_formatter, 1)
        layout.addLayout(xfmt_row)

        layout.addWidget(self._hline())

        # ══════════════════════════════════════════════════════════════════════
        # ── Y Axis (Left) ─────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Y Axis (Left)'))

        self.ylabel_show_check = QCheckBox('Show Y label')
        self.ylabel_show_check.setChecked(True)
        self.ylabel_show_check.stateChanged.connect(self._on_sp_ylabel_show_changed)
        layout.addWidget(self.ylabel_show_check)

        self.ylabel_input = QLineEdit()
        self.ylabel_input.setPlaceholderText('Y label (optional)')
        self.ylabel_input.textChanged.connect(self._on_sp_ylabel_changed)
        layout.addWidget(self.ylabel_input)

        yfont_row1 = QHBoxLayout(); yfont_row1.setSpacing(4)
        yfont_row1.addWidget(QLabel('Font:'))
        self.ylabel_font = QComboBox(); self.ylabel_font.addItems(_FONTS)
        self.ylabel_font.currentTextChanged.connect(self.update_preview)
        yfont_row1.addWidget(self.ylabel_font, 1)
        yfont_row1.addWidget(QLabel('Size:'))
        self.ylabel_size = QSpinBox(); self.ylabel_size.setRange(6, 32); self.ylabel_size.setValue(11)
        self.ylabel_size.setFixedWidth(_SW)
        self.ylabel_size.valueChanged.connect(self.update_preview)
        yfont_row1.addWidget(self.ylabel_size)
        layout.addLayout(yfont_row1)

        yfont_row2 = QHBoxLayout(); yfont_row2.setSpacing(4)
        yfont_row2.addWidget(QLabel('Color:'))
        self.ylabel_color = '#000000'
        self.ylabel_color_label = self._color_sw('#000000')
        yfont_row2.addWidget(self.ylabel_color_label)
        btn_yc = QPushButton('…'); btn_yc.setFixedWidth(28)
        btn_yc.clicked.connect(lambda: self.pick_color('ylabel'))
        yfont_row2.addWidget(btn_yc)
        yfont_row2.addStretch()
        layout.addLayout(yfont_row2)

        ylim_row = QHBoxLayout(); ylim_row.setSpacing(4)
        ylim_row.addWidget(QLabel('Y min:'))
        self.y_min = QDoubleSpinBox(); self.y_min.setRange(-1e10, 1e10); self.y_min.setSingleStep(0.1)
        self.y_min.setFixedWidth(_LW)
        self.y_min.editingFinished.connect(self._on_sp_lim_changed)
        ylim_row.addWidget(self.y_min)
        ylim_row.addWidget(QLabel('max:'))
        self.y_max = QDoubleSpinBox(); self.y_max.setRange(-1e10, 1e10); self.y_max.setValue(1); self.y_max.setSingleStep(0.1)
        self.y_max.setFixedWidth(_LW)
        self.y_max.editingFinished.connect(self._on_sp_lim_changed)
        ylim_row.addWidget(self.y_max)
        ylim_row.addStretch()
        layout.addLayout(ylim_row)

        yauto_row = QHBoxLayout()
        self.y_auto = QCheckBox('Auto limits'); self.y_auto.setChecked(True)
        self.y_auto.stateChanged.connect(self._on_sp_lim_changed)
        yauto_row.addWidget(self.y_auto); yauto_row.addStretch()
        layout.addLayout(yauto_row)

        layout.addWidget(QLabel('Scale:'))
        self.yscale_group = QButtonGroup(self)
        ysr = QHBoxLayout(); ysr.setSpacing(6)
        for lbl, val in [('Linear', 'linear'), ('Log', 'log'), ('Logit', 'logit'), ('Inverted', 'inverted')]:
            rb = QRadioButton(lbl); rb.setProperty('scale_value', val)
            if val == 'linear': rb.setChecked(True)
            rb.toggled.connect(self._save_axes_state)
            self.yscale_group.addButton(rb); ysr.addWidget(rb)
        ysr.addStretch()
        layout.addLayout(ysr)

        ytick_row1 = QHBoxLayout(); ytick_row1.setSpacing(4)
        ytick_row1.addWidget(QLabel('Tick size:'))
        self.ytick_size = QSpinBox(); self.ytick_size.setRange(4, 24); self.ytick_size.setValue(9)
        self.ytick_size.setFixedWidth(_SW)
        self.ytick_size.valueChanged.connect(self._save_axes_state)
        ytick_row1.addWidget(self.ytick_size)
        ytick_row1.addWidget(QLabel('Direction:'))
        self.ytick_dir = QComboBox(); self.ytick_dir.addItems(['out', 'in', 'inout'])
        self.ytick_dir.setFixedWidth(_DW)
        self.ytick_dir.currentTextChanged.connect(self._save_axes_state)
        ytick_row1.addWidget(self.ytick_dir)
        ytick_row1.addStretch()
        layout.addLayout(ytick_row1)

        ytick_row2 = QHBoxLayout()
        self.yticks_show = QCheckBox('Show ticks'); self.yticks_show.setChecked(True)
        self.yticks_show.stateChanged.connect(self._save_axes_state)
        ytick_row2.addWidget(self.yticks_show)
        self.ytick_minor = QCheckBox('Minor ticks'); self.ytick_minor.setChecked(False)
        self.ytick_minor.stateChanged.connect(self._save_axes_state)
        ytick_row2.addWidget(self.ytick_minor)
        ytick_row2.addStretch()
        layout.addLayout(ytick_row2)

        ytick_rot_row = QHBoxLayout(); ytick_rot_row.setSpacing(4)
        ytick_rot_row.addWidget(QLabel('Rotation:'))
        self.ytick_rotation = QSpinBox(); self.ytick_rotation.setRange(-90, 90); self.ytick_rotation.setValue(0)
        self.ytick_rotation.setFixedWidth(_SW)
        self.ytick_rotation.valueChanged.connect(self._save_axes_state)
        ytick_rot_row.addWidget(self.ytick_rotation)
        ytick_rot_row.addStretch()
        layout.addLayout(ytick_rot_row)

        ytick_step_row = QHBoxLayout(); ytick_step_row.setSpacing(4)
        ytick_step_row.addWidget(QLabel('Step (0 = auto):'))
        self.ytick_step = QDoubleSpinBox(); self.ytick_step.setRange(0, 1e9); self.ytick_step.setValue(0); self.ytick_step.setSingleStep(0.1)
        self.ytick_step.setFixedWidth(_LW)
        self.ytick_step.editingFinished.connect(self._save_axes_state)
        ytick_step_row.addWidget(self.ytick_step)
        ytick_step_row.addStretch()
        layout.addLayout(ytick_step_row)

        yfmt_row = QHBoxLayout(); yfmt_row.setSpacing(4)
        yfmt_row.addWidget(QLabel('Format:'))
        self.y_formatter = QComboBox()
        self.y_formatter.addItems(['auto', 'plain', 'sci', 'percent', '{x:.2f}', '{x:.0f}'])
        self.y_formatter.setEditable(True)
        self.y_formatter.currentTextChanged.connect(self._save_axes_state)
        yfmt_row.addWidget(self.y_formatter, 1)
        layout.addLayout(yfmt_row)

        layout.addWidget(self._hline())

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
        # ── Y Axis (Right / Secondary) ────────────────────────────────────────
        layout.addWidget(self._sec_label('Y Axis (Right / Secondary)'))
        layout.addWidget(QLabel('(Activate by ticking Y2 in the Series table)'))

        self.y2label_show_check = QCheckBox('Show Y2 label')
        self.y2label_show_check.setChecked(True)
        self.y2label_show_check.stateChanged.connect(self._on_sp_y2label_show_changed)
        layout.addWidget(self.y2label_show_check)

        self.y2label_input = QLineEdit()
        self.y2label_input.setPlaceholderText('Y2 label (optional)')
        self.y2label_input.textChanged.connect(self._on_sp_y2label_changed)
        layout.addWidget(self.y2label_input)

        y2font_row1 = QHBoxLayout(); y2font_row1.setSpacing(4)
        y2font_row1.addWidget(QLabel('Font:'))
        self.y2label_font = QComboBox(); self.y2label_font.addItems(_FONTS)
        self.y2label_font.currentTextChanged.connect(self.update_preview)
        y2font_row1.addWidget(self.y2label_font, 1)
        y2font_row1.addWidget(QLabel('Size:'))
        self.y2label_size = QSpinBox(); self.y2label_size.setRange(6, 32); self.y2label_size.setValue(11)
        self.y2label_size.setFixedWidth(_SW)
        self.y2label_size.valueChanged.connect(self.update_preview)
        y2font_row1.addWidget(self.y2label_size)
        layout.addLayout(y2font_row1)

        y2font_row2 = QHBoxLayout(); y2font_row2.setSpacing(4)
        y2font_row2.addWidget(QLabel('Color:'))
        self.y2label_color = '#000000'
        self.y2label_color_label = self._color_sw('#000000')
        y2font_row2.addWidget(self.y2label_color_label)
        btn_y2c = QPushButton('…'); btn_y2c.setFixedWidth(28)
        btn_y2c.clicked.connect(lambda: self.pick_color('y2label'))
        y2font_row2.addWidget(btn_y2c)
        y2font_row2.addStretch()
        layout.addLayout(y2font_row2)

        y2lim_row = QHBoxLayout(); y2lim_row.setSpacing(4)
        y2lim_row.addWidget(QLabel('Y2 min:'))
        self.y2_min = QDoubleSpinBox(); self.y2_min.setRange(-1e10, 1e10); self.y2_min.setSingleStep(0.1)
        self.y2_min.setFixedWidth(_LW)
        self.y2_min.editingFinished.connect(self._on_sp_lim_changed)
        y2lim_row.addWidget(self.y2_min)
        y2lim_row.addWidget(QLabel('max:'))
        self.y2_max = QDoubleSpinBox(); self.y2_max.setRange(-1e10, 1e10); self.y2_max.setValue(1); self.y2_max.setSingleStep(0.1)
        self.y2_max.setFixedWidth(_LW)
        self.y2_max.editingFinished.connect(self._on_sp_lim_changed)
        y2lim_row.addWidget(self.y2_max)
        y2lim_row.addStretch()
        layout.addLayout(y2lim_row)

        y2auto_row = QHBoxLayout()
        self.y2_auto = QCheckBox('Auto limits'); self.y2_auto.setChecked(True)
        self.y2_auto.stateChanged.connect(self._on_sp_lim_changed)
        y2auto_row.addWidget(self.y2_auto); y2auto_row.addStretch()
        layout.addLayout(y2auto_row)

        layout.addWidget(self._hline())

        layout.addStretch()
        scroll.setWidget(content)
        mlay = QVBoxLayout(widget); mlay.addWidget(scroll)
        self.plots_inner_tabs.addTab(widget, 'Axes')


    # ─── Style tab ────────────────────────────────────────────────────────────
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
            sw = self._color_sw(default_hex)
            setattr(self, attr_name + '_swatch', sw); r.addWidget(sw)
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
        tfont_row.addStretch(); layout.addLayout(tfont_row)
        tcolor_row = QHBoxLayout(); tcolor_row.setSpacing(6)
        tcolor_row.addWidget(QLabel('Color:'))
        self.title_color_label = self._color_sw('#000000')
        tcolor_row.addWidget(self.title_color_label)
        self.title_color = '#000000'
        tbtn = QPushButton('…'); tbtn.setFixedWidth(28)
        tbtn.clicked.connect(lambda: self.pick_color('title'))
        tcolor_row.addWidget(tbtn); tcolor_row.addStretch(); layout.addLayout(tcolor_row)

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
        c1 = QHBoxLayout(); c1.setSpacing(4)
        c1.addWidget(QLabel('Color:'))
        self.grid_color = '#cccccc'
        self.grid_color_sw = self._color_sw('#cccccc')
        g_btn = QPushButton('…'); g_btn.setFixedWidth(28)
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
        c2 = QHBoxLayout(); c2.setSpacing(4)
        c2.addWidget(QLabel('Color:'))
        self.minor_grid_color = '#e8e8e8'
        self.minor_grid_color_sw = self._color_sw('#e8e8e8')
        sg_btn = QPushButton('…'); sg_btn.setFixedWidth(28)
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

    # ─── Series tab ───────────────────────────────────────────────────────────
    def create_series_tab(self):
        widget = QWidget(); scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); layout = QVBoxLayout(content)
        layout.setSpacing(4)

        def row(label_text, widget_obj, stretch=True):
            r = QHBoxLayout(); r.setSpacing(6)
            lbl = QLabel(label_text); lbl.setFixedWidth(90)
            r.addWidget(lbl); r.addWidget(widget_obj)
            if stretch: r.addStretch()
            layout.addLayout(r)

        # ── Active subplot selector (shown when n > 1) ───────────────────────
        sc_sp_row = QHBoxLayout(); sc_sp_row.setSpacing(6)
        sc_sp_row.addWidget(QLabel('Subplot:'))
        self.series_curve_sp_active = QComboBox(); self.series_curve_sp_active.addItem('Subplot 1')
        self.series_curve_sp_active.currentIndexChanged.connect(self._on_series_curve_sp_changed)
        sc_sp_row.addWidget(self.series_curve_sp_active); sc_sp_row.addStretch()
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
        self.curve_linestyle = QComboBox(); self.curve_linestyle.addItems(['-','--','-.', ':','none'])
        self.curve_linestyle.setCurrentIndex(0)
        self.curve_linestyle.currentTextChanged.connect(lambda _: self.save_curve_style())
        row('Line style:', self.curve_linestyle)

        # Curve color inline
        cr = QHBoxLayout(); cr.setSpacing(6)
        lbl_cc = QLabel('Color:'); lbl_cc.setFixedWidth(90); cr.addWidget(lbl_cc)
        self.curve_color = '#1f77b4'
        self.curve_color_label = self._color_sw('#1f77b4')
        cr.addWidget(self.curve_color_label)
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

        self.curve_linewidth = QDoubleSpinBox(); self.curve_linewidth.setRange(0.5, 5.0)
        self.curve_linewidth.setValue(1.5); self.curve_linewidth.setSingleStep(0.1)
        self.curve_linewidth.editingFinished.connect(self.save_curve_style)

        self.curve_markersize = QDoubleSpinBox(); self.curve_markersize.setRange(1, 20)
        self.curve_markersize.setValue(6); self.curve_markersize.setSingleStep(0.5)
        self.curve_markersize.editingFinished.connect(self.save_curve_style)

        self.curve_marker_color = '#1f77b4'
        self.curve_marker_color_label = self._color_sw('#1f77b4')
        btn_mc = QPushButton('…'); btn_mc.setFixedWidth(28)
        btn_mc.clicked.connect(lambda: self.pick_color('curve_marker'))
        cwm = QHBoxLayout(); cwm.setSpacing(4)
        cwm.addWidget(QLabel('W:')); cwm.addWidget(self.curve_linewidth)
        cwm.addWidget(QLabel('Size:')); cwm.addWidget(self.curve_markersize)
        cwm.addStretch(); layout.addLayout(cwm)
        mc_row = QHBoxLayout(); mc_row.setSpacing(4)
        lbl_mc = QLabel('Marker color:'); lbl_mc.setFixedWidth(90); mc_row.addWidget(lbl_mc)
        mc_row.addWidget(self.curve_marker_color_label)
        mc_row.addWidget(btn_mc)
        mc_row.addStretch(); layout.addLayout(mc_row)

        def _srow(*widgets):
            h = QHBoxLayout()
            for w in widgets: h.addWidget(w)
            return h

        # Line series options
        self.st_line_group = QWidget()
        stlg = QVBoxLayout(self.st_line_group); stlg.setContentsMargins(0, 0, 0, 0); stlg.setSpacing(4)
        self.line_drawstyle = QComboBox()
        self.line_drawstyle.addItems(['default', 'steps-pre', 'steps-post', 'steps-mid'])
        self.line_drawstyle.currentTextChanged.connect(self.update_preview)
        stlg.addLayout(_srow(QLabel('Draw style:'), self.line_drawstyle))
        layout.addWidget(self.st_line_group)

        # Scatter series options
        self.st_scatter_group = QWidget()
        stsg = QVBoxLayout(self.st_scatter_group); stsg.setContentsMargins(0, 0, 0, 0); stsg.setSpacing(4)
        stsg.addLayout(_srow(QLabel('Point size:'), self._make_spin('scatter_size', 1, 500, 20)))
        stsg.addLayout(_srow(QLabel('Alpha:'),       self._make_dbl_spin('scatter_alpha', 0.05, 1.0, 0.7, 0.05)))
        stsg.addLayout(_srow(QLabel('Edge color:'),  self._make_edgecolor_combo('scatter_edgecolor', 'none')))
        stsg.addLayout(_srow(QLabel('Edge width:'),  self._make_dbl_spin('scatter_lw', 0.0, 5.0, 0.5, 0.25)))
        self.scatter_colorby_check = QCheckBox('Color by Z column')
        self.scatter_colorby_check.stateChanged.connect(self.update_preview)
        stsg.addWidget(self.scatter_colorby_check)
        stsg.addLayout(_srow(QLabel('Colormap:'), self._make_combo('scatter_cmap_combo', _CMAP_LIST, default='rainbow')))
        layout.addWidget(self.st_scatter_group)

        # Bar series options
        self.st_bar_group = QWidget()
        stbg = QVBoxLayout(self.st_bar_group); stbg.setContentsMargins(0, 0, 0, 0); stbg.setSpacing(4)
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
        sthg = QVBoxLayout(self.st_hist_group); sthg.setContentsMargins(0, 0, 0, 0); sthg.setSpacing(4)
        sthg.addLayout(_srow(QLabel('Alpha:'),      self._make_dbl_spin('hist_alpha', 0.05, 1.0, 0.7, 0.05)))
        sthg.addLayout(_srow(QLabel('Edge color:'), self._make_edgecolor_combo('hist_edgecolor', 'white')))
        layout.addWidget(self.st_hist_group)

        # Errorbar series options
        self.st_err_group = QWidget()
        steg = QVBoxLayout(self.st_err_group); steg.setContentsMargins(0, 0, 0, 0); steg.setSpacing(4)
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
        stag = QVBoxLayout(self.st_area_group); stag.setContentsMargins(0, 0, 0, 0); stag.setSpacing(4)
        stag.addLayout(_srow(QLabel('Fill alpha:'), self._make_dbl_spin('area_alpha', 0.05, 1.0, 0.4, 0.05)))
        stag.addLayout(_srow(QLabel('Line width:'), self._make_dbl_spin('area_lw', 0.0, 5.0, 0.8, 0.25)))
        self.area_showline = QCheckBox('Show edge line')
        self.area_showline.setChecked(True)
        self.area_showline.stateChanged.connect(self.update_preview)
        stag.addWidget(self.area_showline)
        layout.addWidget(self.st_area_group)

        # Fill Between series options
        self.st_fill_between_group = QWidget()
        stfbg = QVBoxLayout(self.st_fill_between_group); stfbg.setContentsMargins(0, 0, 0, 0); stfbg.setSpacing(4)
        stfbg.addLayout(_srow(QLabel('Fill alpha:'), self._make_dbl_spin('fill_between_alpha', 0.05, 1.0, 0.4, 0.05)))
        stfbg.addLayout(_srow(QLabel('Line width:'), self._make_dbl_spin('fill_between_lw', 0.0, 5.0, 0.8, 0.25)))
        self.fill_between_showline = QCheckBox('Show edge lines')
        self.fill_between_showline.setChecked(True)
        self.fill_between_showline.stateChanged.connect(self.update_preview)
        stfbg.addWidget(self.fill_between_showline)
        layout.addWidget(self.st_fill_between_group)

        # Step series options
        self.st_step_group = QWidget()
        ststg = QVBoxLayout(self.st_step_group); ststg.setContentsMargins(0, 0, 0, 0); ststg.setSpacing(4)
        self.step_fill = QCheckBox('Fill under')
        self.step_fill.stateChanged.connect(self.update_preview)
        ststg.addWidget(self.step_fill)
        ststg.addLayout(_srow(QLabel('Fill alpha:'), self._make_dbl_spin('step_fill_alpha', 0.05, 1.0, 0.2, 0.05)))
        layout.addWidget(self.st_step_group)

        # Bubble series options
        self.st_bubble_group = QWidget()
        stbug = QVBoxLayout(self.st_bubble_group); stbug.setContentsMargins(0, 0, 0, 0); stbug.setSpacing(4)
        stbug.addLayout(_srow(QLabel('Size col:'),   self._make_col_combo('bubble_size_combo', '(uniform)')))
        stbug.addLayout(_srow(QLabel('Scale:'),      self._make_dbl_spin('bubble_scale', 1, 5000, 200, 50)))
        stbug.addLayout(_srow(QLabel('Alpha:'),      self._make_dbl_spin('bubble_alpha', 0.05, 1.0, 0.6, 0.05)))
        stbug.addLayout(_srow(QLabel('Edge color:'), self._make_edgecolor_combo('bubble_edgecolor', 'none')))
        layout.addWidget(self.st_bubble_group)

        # Polar series options
        self.st_polar_group = QWidget()
        stplg = QVBoxLayout(self.st_polar_group); stplg.setContentsMargins(0, 0, 0, 0); stplg.setSpacing(4)
        self.polar_fill = QCheckBox('Fill')
        self.polar_fill.stateChanged.connect(self.update_preview)
        stplg.addWidget(self.polar_fill)
        stplg.addLayout(_srow(QLabel('Fill alpha:'), self._make_dbl_spin('polar_fill_alpha', 0.05, 1.0, 0.2, 0.05)))
        layout.addWidget(self.st_polar_group)

        # Radar series options
        self.st_radar_group = QWidget()
        strdr = QVBoxLayout(self.st_radar_group); strdr.setContentsMargins(0, 0, 0, 0); strdr.setSpacing(4)
        self.radar_fill = QCheckBox('Fill')
        self.radar_fill.setChecked(True)
        self.radar_fill.stateChanged.connect(self.update_preview)
        strdr.addWidget(self.radar_fill)
        strdr.addLayout(_srow(QLabel('Fill alpha:'), self._make_dbl_spin('radar_fill_alpha', 0.05, 1.0, 0.25, 0.05)))
        layout.addWidget(self.st_radar_group)

        # ECDF series options
        self.st_ecdf_group = QWidget()
        stecg = QVBoxLayout(self.st_ecdf_group); stecg.setContentsMargins(0, 0, 0, 0); stecg.setSpacing(4)
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

        fr = QHBoxLayout(); fr.addWidget(QLabel('Model:'))
        self.fit_combo = QComboBox(); self.fit_combo.addItem('None')
        self.fit_combo.addItems(CurveFitter.MODELS.keys())
        fr.addWidget(self.fit_combo); fr.addStretch(); layout.addLayout(fr)

        btn_fit = QPushButton('▶  Apply Fit')
        btn_fit.clicked.connect(self.apply_fit)
        btn_remove_fit = QPushButton('✕  Remove Fit')
        btn_remove_fit.clicked.connect(self._remove_fit)
        btn_remove_fit.setToolTip('Remove the fitted curve for the currently selected series')
        fit_btn_row = QHBoxLayout(); fit_btn_row.setSpacing(4)
        fit_btn_row.addWidget(btn_fit); fit_btn_row.addWidget(btn_remove_fit)
        layout.addLayout(fit_btn_row)

        # ── Fit-specific controls (disabled when an original series is selected) ──
        self._fit_controls_widget = QWidget()
        fc_lay = QVBoxLayout(self._fit_controls_widget)
        fc_lay.setContentsMargins(0, 0, 0, 0); fc_lay.setSpacing(4)

        ci_row = QHBoxLayout(); ci_row.setSpacing(6); ci_row.addWidget(QLabel('Confidence limits:'))
        self.fit_ci_combo = QComboBox()
        self.fit_ci_combo.addItems(['Off', '1σ  (68%)', '2σ  (95%)', '3σ  (99.7%)'])
        self.fit_ci_combo.currentIndexChanged.connect(self._on_ci_changed)
        ci_row.addWidget(self.fit_ci_combo); ci_row.addStretch(); fc_lay.addLayout(ci_row)

        pi_row = QHBoxLayout(); pi_row.setSpacing(6); pi_row.addWidget(QLabel('Prediction band:'))
        self.fit_pi_combo = QComboBox()
        self.fit_pi_combo.addItems(['Off', '1σ  (68%)', '2σ  (95%)', '3σ  (99.7%)'])
        self.fit_pi_combo.currentIndexChanged.connect(self._on_ci_changed)
        pi_row.addWidget(self.fit_pi_combo); pi_row.addStretch(); fc_lay.addLayout(pi_row)

        self.fit_ci_alpha_spin = QDoubleSpinBox()
        self.fit_ci_alpha_spin.setRange(0.05, 1.0); self.fit_ci_alpha_spin.setSingleStep(0.05); self.fit_ci_alpha_spin.setValue(0.25)
        self.fit_ci_alpha_spin.valueChanged.connect(self.update_preview)
        ci_alpha_row = QHBoxLayout(); ci_alpha_row.setSpacing(6)
        ci_alpha_row.addWidget(QLabel('Band opacity:')); ci_alpha_row.addWidget(self.fit_ci_alpha_spin)
        ci_alpha_row.addStretch(); fc_lay.addLayout(ci_alpha_row)

        res_box = QGroupBox('Fit Results')
        res_lay = QVBoxLayout(res_box); res_lay.setSpacing(2); res_lay.setContentsMargins(4, 4, 4, 4)
        self.fit_results_text = QPlainTextEdit()
        self.fit_results_text.setReadOnly(True)
        self.fit_results_text.setMinimumHeight(180)
        self.fit_results_text.setFont(QFont('Courier New' if __import__('sys').platform == 'win32' else 'Menlo' if __import__('sys').platform == 'darwin' else 'monospace', 9))
        self.fit_results_text.setPlainText('Run a fit to see results.')
        # Keep backwards-compat aliases
        self.fit_eq_label = QLabel(''); self.fit_eq_label.setVisible(False)
        self.fit_r2_label = QLabel(''); self.fit_r2_label.setVisible(False)
        res_lay.addWidget(self.fit_results_text)
        fc_lay.addWidget(res_box)

        self._fit_controls_widget.setEnabled(False)
        layout.addWidget(self._fit_controls_widget)

        # ── Export row — outside the fit controls, active whenever fits exist ──
        self._fit_export_widget = QWidget()
        exp_row = QHBoxLayout(self._fit_export_widget)
        exp_row.setContentsMargins(0, 0, 0, 0); exp_row.setSpacing(6)
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
        scroll.setWidget(content); mlay = QVBoxLayout(widget); mlay.addWidget(scroll)
        self.plots_inner_tabs.addTab(widget, 'Series')

    # ─── Annotations tab ──────────────────────────────────────────────────────
    def create_annotations_tab(self):
        widget = QWidget(); scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); layout = QVBoxLayout(content)
        layout.setSpacing(4)

        def irow(*widgets):
            r = QHBoxLayout(); r.setSpacing(4)
            for w in widgets: r.addWidget(w)
            r.addStretch(); layout.addLayout(r)

        def lrow(label, *widgets):
            r = QHBoxLayout(); r.setSpacing(4)
            lb = QLabel(label); lb.setFixedWidth(76); r.addWidget(lb)
            for w in widgets: r.addWidget(w)
            r.addStretch(); layout.addLayout(r)

        def color_btn(attr, default):
            sw = self._color_sw(default)
            setattr(self, attr, default)
            setattr(self, attr + '_sw', sw)
            btn = QPushButton('…'); btn.setFixedWidth(28)
            btn.clicked.connect(lambda _=False, a=attr: self._pick_ann_color_attr(a))
            return sw, btn

        # ── Subplot selector ─────────────────────────────────────────────────
        ann_sp_row = QHBoxLayout(); ann_sp_row.setSpacing(6)
        ann_sp_row.addWidget(QLabel('Subplot:'))
        self.ann_sp_active = QComboBox(); self.ann_sp_active.addItem('Subplot 1')
        self.ann_sp_active.currentIndexChanged.connect(self._on_ann_subplot_changed)
        ann_sp_row.addWidget(self.ann_sp_active); ann_sp_row.addStretch()
        self._ann_sp_row_widget = QWidget()
        self._ann_sp_row_widget.setLayout(ann_sp_row)
        self._ann_sp_row_widget.setVisible(False)
        layout.addWidget(self._ann_sp_row_widget)

        layout.addWidget(self._hline())

        # ── Subplot Title (moved from Axes; hidden when n==1) ─────────────────
        self._axes_title_section = QWidget()
        _ts_lay = QVBoxLayout(self._axes_title_section)
        _ts_lay.setContentsMargins(0, 0, 0, 0); _ts_lay.setSpacing(4)
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
        self.sp_title_color_label = self._color_sw('#000000')
        btn_sp_tc = QPushButton('…'); btn_sp_tc.setFixedWidth(28)
        btn_sp_tc.clicked.connect(lambda: self._pick_sp_title_color())
        sp_tf_row.addWidget(QLabel('Color:'))
        sp_tf_row.addWidget(self.sp_title_color_label); sp_tf_row.addWidget(btn_sp_tc)
        sp_tf_row.addStretch(); _ts_lay.addLayout(sp_tf_row)
        _ts_lay.addWidget(self._hline())
        layout.addWidget(self._axes_title_section)
        self._axes_title_section.setVisible(False)  # shown only when n > 1

        # ── Legend (moved from Axes; full styling) ────────────────────────────
        layout.addWidget(self._sec_label('Legend'))

        leg_check_row = QHBoxLayout(); leg_check_row.setSpacing(6)
        self.legend_show_check = QCheckBox('Show legend'); self.legend_show_check.setChecked(True)
        self.legend_show_check.stateChanged.connect(self._on_sp_legend_changed)
        leg_check_row.addWidget(self.legend_show_check); leg_check_row.addStretch()
        layout.addLayout(leg_check_row)

        # Location dropdown + fine X/Y position
        leg_loc_row = QHBoxLayout(); leg_loc_row.setSpacing(4)
        leg_loc_row.addWidget(QLabel('Position:'))
        self.legend_pos = QComboBox()
        self.legend_pos.addItems(['best', 'upper right', 'upper left', 'upper center',
                                  'lower right', 'lower left', 'lower center',
                                  'center right', 'center left', 'center', 'manual'])
        self.legend_pos.currentTextChanged.connect(self._on_sp_legend_changed)
        leg_loc_row.addWidget(self.legend_pos)
        leg_loc_row.addWidget(QLabel('X:'))
        self.legend_x = QDoubleSpinBox(); self.legend_x.setRange(0.0, 1.5)
        self.legend_x.setSingleStep(0.01); self.legend_x.setDecimals(2)
        self.legend_x.setValue(0.01); self.legend_x.setFixedWidth(60)
        self.legend_x.setToolTip('Fine X position (figure fraction); active for all positions except "best"')
        self.legend_x.valueChanged.connect(self._on_sp_legend_changed)
        leg_loc_row.addWidget(self.legend_x)
        leg_loc_row.addWidget(QLabel('Y:'))
        self.legend_y = QDoubleSpinBox(); self.legend_y.setRange(0.0, 1.5)
        self.legend_y.setSingleStep(0.01); self.legend_y.setDecimals(2)
        self.legend_y.setValue(0.99); self.legend_y.setFixedWidth(60)
        self.legend_y.setToolTip('Fine Y position (figure fraction); active for all positions except "best"')
        self.legend_y.valueChanged.connect(self._on_sp_legend_changed)
        leg_loc_row.addWidget(self.legend_y)
        leg_loc_row.addStretch(); layout.addLayout(leg_loc_row)

        # Font size + columns
        leg_style_row = QHBoxLayout(); leg_style_row.setSpacing(4)
        leg_style_row.addWidget(QLabel('Font sz:'))
        self.legend_fontsize = QSpinBox(); self.legend_fontsize.setRange(5, 24)
        self.legend_fontsize.setValue(9); self.legend_fontsize.setFixedWidth(46)
        self.legend_fontsize.valueChanged.connect(self._on_sp_legend_changed)
        leg_style_row.addWidget(self.legend_fontsize)
        leg_style_row.addWidget(QLabel('Cols:'))
        self.legend_ncols = QSpinBox(); self.legend_ncols.setRange(1, 8)
        self.legend_ncols.setValue(1); self.legend_ncols.setFixedWidth(42)
        self.legend_ncols.valueChanged.connect(self._on_sp_legend_changed)
        leg_style_row.addWidget(self.legend_ncols)
        self.legend_frameon = QCheckBox('Frame')
        self.legend_frameon.setChecked(True)
        self.legend_frameon.stateChanged.connect(self._on_sp_legend_changed)
        leg_style_row.addWidget(self.legend_frameon)
        leg_style_row.addStretch(); layout.addLayout(leg_style_row)

        # Colors — text, background, edge (one row each, using lrow like annotations)
        self.legend_color = '#000000'
        self.legend_color_sw = self._color_sw('#000000')
        btn_leg_tc = QPushButton('…'); btn_leg_tc.setFixedWidth(28)
        btn_leg_tc.clicked.connect(lambda: self._pick_legend_color('text'))
        lrow('Text color:', self.legend_color_sw, btn_leg_tc)

        self.legend_facecolor = '#ffffff'
        self.legend_facecolor_sw = self._color_sw('#ffffff')
        btn_leg_bg = QPushButton('…'); btn_leg_bg.setFixedWidth(28)
        btn_leg_bg.clicked.connect(lambda: self._pick_legend_color('bg'))
        self.legend_alpha = QDoubleSpinBox(); self.legend_alpha.setRange(0.0, 1.0)
        self.legend_alpha.setSingleStep(0.05); self.legend_alpha.setValue(0.8)
        self.legend_alpha.setFixedWidth(54)
        self.legend_alpha.valueChanged.connect(self._on_sp_legend_changed)
        lrow('BG color:', self.legend_facecolor_sw, btn_leg_bg, QLabel('α:'), self.legend_alpha)

        self.legend_edgecolor = '#cccccc'
        self.legend_edgecolor_sw = self._color_sw('#cccccc')
        btn_leg_ec = QPushButton('…'); btn_leg_ec.setFixedWidth(28)
        btn_leg_ec.clicked.connect(lambda: self._pick_legend_color('edge'))
        lrow('Edge color:', self.legend_edgecolor_sw, btn_leg_ec)

        layout.addWidget(self._hline())

        # ── Show/hide annotations for current subplot ─────────────────────────
        vis_row = QHBoxLayout(); vis_row.setSpacing(6)
        self.ann_subplot_visible = QCheckBox('Show annotations on this subplot')
        self.ann_subplot_visible.setChecked(True)
        self.ann_subplot_visible.stateChanged.connect(self._on_ann_subplot_visibility_changed)
        vis_row.addWidget(self.ann_subplot_visible); vis_row.addStretch()
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
        r_mode1 = QHBoxLayout(); r_mode1.setSpacing(3)
        r_mode1.addWidget(self.ann_none_btn); r_mode1.addWidget(self.ann_text_btn)
        layout.addLayout(r_mode1)
        r_mode2 = QHBoxLayout(); r_mode2.setSpacing(3)
        r_mode2.addWidget(self.ann_arrow_btn); r_mode2.addWidget(self.ann_image_btn)
        layout.addLayout(r_mode2)

        self.ann_image_zoom = QDoubleSpinBox(); self.ann_image_zoom.setRange(0.01, 5.0)
        self.ann_image_zoom.setValue(0.15); self.ann_image_zoom.setSingleStep(0.01)
        lrow('Img zoom:', self.ann_image_zoom)

        layout.addWidget(self._hline())
        layout.addWidget(QLabel('Style for new annotations:'))

        self.ann_font = QComboBox(); self.ann_font.addItems(_FONTS)
        self.ann_font.setFixedWidth(110)
        self.ann_font.currentTextChanged.connect(self._sync_ann_style)
        self.ann_fontsize = QSpinBox(); self.ann_fontsize.setRange(6, 48); self.ann_fontsize.setValue(10)
        self.ann_fontsize.setFixedWidth(52)
        self.ann_fontsize.valueChanged.connect(self._sync_ann_style)
        lrow('Font:', self.ann_font, QLabel('Sz:'), self.ann_fontsize)

        self.ann_fontcolor = '#000000'
        fc_sw, fc_btn = color_btn('ann_fontcolor', '#000000')
        lrow('Font color:', fc_sw, fc_btn)

        self.ann_bgcolor = '#ffffcc'
        bg_sw, bg_btn = color_btn('ann_bgcolor', '#ffffcc')
        self.ann_bg_alpha = QDoubleSpinBox(); self.ann_bg_alpha.setRange(0, 1)
        self.ann_bg_alpha.setSingleStep(0.05); self.ann_bg_alpha.setValue(0.9)
        self.ann_bg_alpha.setFixedWidth(58)
        self.ann_bg_alpha.valueChanged.connect(self._sync_ann_style)
        lrow('BG:', bg_sw, bg_btn, QLabel('α:'), self.ann_bg_alpha)

        self.ann_edgecolor = '#aaaaaa'
        ec_sw, ec_btn = color_btn('ann_edgecolor', '#aaaaaa')
        lrow('Border:', ec_sw, ec_btn)

        layout.addWidget(self._hline())

        # Manual position + place
        self.ann_x_override = QLineEdit(); self.ann_x_override.setPlaceholderText('X')
        self.ann_x_override.setFixedWidth(60)
        self.ann_y_override = QLineEdit(); self.ann_y_override.setPlaceholderText('Y')
        self.ann_y_override.setFixedWidth(60)
        btn_place = QPushButton('📍 Place'); btn_place.setFixedWidth(64)
        btn_place.clicked.connect(self._place_at_override)
        lrow('Position:', self.ann_x_override, self.ann_y_override, btn_place)

        btn_undo  = QPushButton('↩ Undo last')
        btn_clear = QPushButton('🗑 Clear all')
        btn_clear.clicked.connect(lambda: self.canvas.clear_annotations())
        btn_undo.clicked.connect(lambda: self.canvas.remove_last_annotation())
        irow(btn_undo, btn_clear)

        layout.addWidget(self._hline())
        layout.addWidget(QLabel('Annotations — double-click to edit:'))
        self.ann_list_widget = QListWidget(); self.ann_list_widget.setMaximumHeight(120)
        self.ann_list_widget.itemDoubleClicked.connect(self._edit_selected_annotation)
        layout.addWidget(self.ann_list_widget)

        btn_edit = QPushButton('✏️ Edit selected')
        btn_del  = QPushButton('🗑 Delete selected')
        btn_edit.clicked.connect(self._edit_selected_annotation)
        btn_del.clicked.connect(self._delete_selected_annotation)
        irow(btn_edit, btn_del)

        layout.addStretch()
        scroll.setWidget(content); mlay = QVBoxLayout(widget); mlay.addWidget(scroll)
        self.plots_inner_tabs.addTab(widget, 'Annotations')

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
        _gsp_lay.addWidget(QLabel('Active Subplot:'))
        self.global_sp_active = QComboBox()
        self.global_sp_active.addItem('Subplot 1')
        self.global_sp_active.setMinimumWidth(110)
        self.global_sp_active.setToolTip(
            'Active subplot — affects Data, Axes, Series and Annotation tabs')
        self.global_sp_active.currentIndexChanged.connect(self._on_global_sp_changed)
        _gsp_lay.addWidget(self.global_sp_active)
        _gsp_lay.addStretch()
        self._global_sp_container.setVisible(False)
        outer_lay.addWidget(self._global_sp_container)

        # ── Inner tab widget ──────────────────────────────────────────────────
        self.plots_inner_tabs = QTabWidget()
        self.create_data_tab()
        self.create_series_tab()
        self.create_axes_tab()
        self.create_annotations_tab()
        outer_lay.addWidget(self.plots_inner_tabs)

        self.tabs.addTab(outer, 'Plots')

    # ─── Advanced tab ─────────────────────────────────────────────────────────
    def create_advanced_tab(self):
        # Outer scroll wraps everything so the whole tab is scrollable
        outer_widget = QWidget()
        outer_scroll = QScrollArea(); outer_scroll.setWidgetResizable(True)
        outer_content = QWidget()
        outer_lay = QVBoxLayout(outer_content)
        outer_lay.setContentsMargins(6, 6, 6, 6); outer_lay.setSpacing(8)

        # ── Section title ──────────────────────────────────────────────────────
        title_lbl = QLabel('DATASET GENERATION')
        title_lbl.setStyleSheet('font-weight:bold; font-size:11px; color:#888; letter-spacing:1px;')
        outer_lay.addWidget(title_lbl)

        # ── Top: compact inner QTabWidget for f(x) and Data Table ─────────────
        inner_tabs = QTabWidget()
        inner_tabs.setDocumentMode(True)
        inner_tabs.setTabPosition(QTabWidget.TabPosition.North)
        inner_tabs.setMaximumWidth(420)
        inner_tabs.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        # ── Inner tab 1 — Function Generator ──────────────────────────────────
        fg_content = QWidget()
        fg_lay = QVBoxLayout(fg_content); fg_lay.setSpacing(5); fg_lay.setContentsMargins(8,8,8,8)

        fg_lay.addWidget(self._sec_label('Function Generator'))

        mode_row = QHBoxLayout(); mode_row.setSpacing(4)
        mode_row.addWidget(QLabel('Input:'))
        self._adv_mode_range = QRadioButton('x range')
        self._adv_mode_col   = QRadioButton('column')
        self._adv_mode_range.setChecked(True)
        mode_row.addWidget(self._adv_mode_range); mode_row.addWidget(self._adv_mode_col)
        mode_row.addStretch(); fg_lay.addLayout(mode_row)

        self._adv_range_widget = QWidget()
        rw_lay = QVBoxLayout(self._adv_range_widget); rw_lay.setContentsMargins(0,0,0,0); rw_lay.setSpacing(3)
        xr = QHBoxLayout(); xr.setSpacing(4)
        xr.addWidget(QLabel('x:'))
        self.gen_x_min = QDoubleSpinBox(); self.gen_x_min.setRange(-1e9,1e9); self.gen_x_min.setValue(0); self.gen_x_min.setDecimals(3); self.gen_x_min.setFixedWidth(72)
        xr.addWidget(self.gen_x_min); xr.addWidget(QLabel('→'))
        self.gen_x_max = QDoubleSpinBox(); self.gen_x_max.setRange(-1e9,1e9); self.gen_x_max.setValue(10); self.gen_x_max.setDecimals(3); self.gen_x_max.setFixedWidth(72)
        xr.addWidget(self.gen_x_max); xr.addWidget(QLabel('n:'))
        self.gen_x_n = QSpinBox(); self.gen_x_n.setRange(2,100000); self.gen_x_n.setValue(200); self.gen_x_n.setFixedWidth(60)
        xr.addWidget(self.gen_x_n); xr.addStretch(); rw_lay.addLayout(xr)
        sp_row = QHBoxLayout(); sp_row.setSpacing(4)
        sp_row.addWidget(QLabel('spacing:'))
        self.gen_x_spacing = QComboBox()
        self.gen_x_spacing.addItems(['linspace', 'logspace', 'geomspace', 'random', 'uniform'])
        self.gen_x_spacing.setToolTip(
            'linspace  — evenly spaced in linear scale\n'
            'logspace  — evenly spaced in log₁₀ scale (start/stop are exponents)\n'
            'geomspace — evenly spaced in log scale (start/stop must be > 0)\n'
            'random    — Normal(μ=mid, σ=(max−min)/6), sorted ascending\n'
            'uniform   — Uniform(start, stop), sorted ascending')
        self.gen_x_spacing.setFixedWidth(100)
        sp_row.addWidget(self.gen_x_spacing); sp_row.addStretch()
        rw_lay.addLayout(sp_row)
        nr = QHBoxLayout(); nr.setSpacing(4); nr.addWidget(QLabel('x col:'))
        self.gen_x_name = QLineEdit('x'); self.gen_x_name.setFixedWidth(70); nr.addWidget(self.gen_x_name)
        nr.addStretch(); rw_lay.addLayout(nr)
        fg_lay.addWidget(self._adv_range_widget)

        self._adv_col_widget = QWidget()
        cw_lay = QVBoxLayout(self._adv_col_widget); cw_lay.setContentsMargins(0,0,0,0); cw_lay.setSpacing(3)
        src_row = QHBoxLayout(); src_row.setSpacing(4); src_row.addWidget(QLabel('Col:'))
        self.fn_source_combo = QComboBox(); self.fn_source_combo.setMinimumWidth(90); src_row.addWidget(self.fn_source_combo)
        src_row.addWidget(QLabel('as:'))
        self.fn_var_name = QLineEdit('x'); self.fn_var_name.setFixedWidth(40); src_row.addWidget(self.fn_var_name)
        src_row.addStretch(); cw_lay.addLayout(src_row)
        fg_lay.addWidget(self._adv_col_widget); self._adv_col_widget.setVisible(False)

        fg_lay.addWidget(QLabel('expr (np, sin, cos, exp, log, pi …):'))
        self.gen_expr = QLineEdit('sin(x)'); fg_lay.addWidget(self.gen_expr)
        self.fn_expr = self.gen_expr
        out_row = QHBoxLayout(); out_row.setSpacing(4); out_row.addWidget(QLabel('y col:'))
        self.gen_y_name = QLineEdit('y'); self.gen_y_name.setFixedWidth(70); out_row.addWidget(self.gen_y_name)
        self.fn_out_name = self.gen_y_name; out_row.addStretch(); fg_lay.addLayout(out_row)

        btn_gen = QPushButton('▶  Generate / Apply')
        btn_gen.clicked.connect(self._adv_generate_or_apply); fg_lay.addWidget(btn_gen)
        self.gen_status = QLabel(''); self.gen_status.setStyleSheet('color:#555;font-size:11px;')
        self.fn_status = self.gen_status; fg_lay.addWidget(self.gen_status)

        def _on_mode_toggle():
            use_range = self._adv_mode_range.isChecked()
            self._adv_range_widget.setVisible(use_range)
            self._adv_col_widget.setVisible(not use_range)
        self._adv_mode_range.toggled.connect(_on_mode_toggle)
        fg_lay.addStretch()
        inner_tabs.addTab(fg_content, 'y=f(x)')

        # ── Inner tab 2 — z = f(x, y) generator ──────────────────────────────────────
        fxy_content = QWidget()
        fxy_lay = QVBoxLayout(fxy_content); fxy_lay.setSpacing(4); fxy_lay.setContentsMargins(8,8,8,8)
        fxy_lay.addWidget(self._sec_label('z = f(x, y)  Generator'))
        _sp_tip = ('linspace  — evenly spaced in linear scale\n'
                   'logspace  — evenly spaced in log₁₀ scale (start/stop are exponents)\n'
                   'geomspace — evenly spaced in log scale (start/stop must be > 0)\n'
                   'random    — Normal(μ=mid, σ=(max−min)/6), sorted ascending\n'
                   'uniform   — Uniform(start, stop), sorted ascending')
        # ─ X series ─
        fxy_lay.addWidget(self._sec_label('x series'))
        _fxm = QHBoxLayout(); _fxm.setSpacing(4); _fxm.addWidget(QLabel('Input:'))
        self.fxy_x_mode_range = QRadioButton('range'); self.fxy_x_mode_range.setChecked(True)
        self.fxy_x_mode_col   = QRadioButton('column')
        _fxm.addWidget(self.fxy_x_mode_range); _fxm.addWidget(self.fxy_x_mode_col); _fxm.addStretch(); fxy_lay.addLayout(_fxm)
        self._fxy_x_range_widget = QWidget()
        _xrw = QVBoxLayout(self._fxy_x_range_widget); _xrw.setContentsMargins(0,0,0,0); _xrw.setSpacing(2)
        _xr = QHBoxLayout(); _xr.setSpacing(4); _xr.addWidget(QLabel('x:'))
        self.fxy_x_min = QDoubleSpinBox(); self.fxy_x_min.setRange(-1e9,1e9); self.fxy_x_min.setValue(0); self.fxy_x_min.setDecimals(3); self.fxy_x_min.setFixedWidth(68)
        _xr.addWidget(self.fxy_x_min); _xr.addWidget(QLabel('→'))
        self.fxy_x_max = QDoubleSpinBox(); self.fxy_x_max.setRange(-1e9,1e9); self.fxy_x_max.setValue(10); self.fxy_x_max.setDecimals(3); self.fxy_x_max.setFixedWidth(68)
        _xr.addWidget(self.fxy_x_max); _xr.addWidget(QLabel('n:'))
        self.fxy_x_n = QSpinBox(); self.fxy_x_n.setRange(2,100000); self.fxy_x_n.setValue(50); self.fxy_x_n.setFixedWidth(56)
        _xr.addWidget(self.fxy_x_n); _xr.addStretch(); _xrw.addLayout(_xr)
        _xsp = QHBoxLayout(); _xsp.setSpacing(4); _xsp.addWidget(QLabel('spacing:'))
        self.fxy_x_spacing = QComboBox(); self.fxy_x_spacing.addItems(['linspace','logspace','geomspace','random','uniform'])
        self.fxy_x_spacing.setToolTip(_sp_tip); self.fxy_x_spacing.setFixedWidth(96)
        _xsp.addWidget(self.fxy_x_spacing); _xsp.addStretch(); _xrw.addLayout(_xsp)
        _xcn = QHBoxLayout(); _xcn.setSpacing(4); _xcn.addWidget(QLabel('x col:'))
        self.fxy_x_col_name = QLineEdit('x'); self.fxy_x_col_name.setFixedWidth(60)
        _xcn.addWidget(self.fxy_x_col_name); _xcn.addStretch(); _xrw.addLayout(_xcn)
        fxy_lay.addWidget(self._fxy_x_range_widget)
        self._fxy_x_col_widget = QWidget()
        _xcw = QHBoxLayout(self._fxy_x_col_widget); _xcw.setContentsMargins(0,0,0,0); _xcw.setSpacing(4)
        _xcw.addWidget(QLabel('x col:')); self.fxy_x_combo = QComboBox(); self.fxy_x_combo.setMinimumWidth(90)
        _xcw.addWidget(self.fxy_x_combo); _xcw.addWidget(QLabel('as:'))
        self.fxy_x_var = QLineEdit('x'); self.fxy_x_var.setFixedWidth(36)
        _xcw.addWidget(self.fxy_x_var); _xcw.addStretch()
        fxy_lay.addWidget(self._fxy_x_col_widget); self._fxy_x_col_widget.setVisible(False)
        # ─ Y series ─
        fxy_lay.addWidget(self._sec_label('y series'))
        _fym = QHBoxLayout(); _fym.setSpacing(4); _fym.addWidget(QLabel('Input:'))
        self.fxy_y_mode_range = QRadioButton('range'); self.fxy_y_mode_range.setChecked(True)
        self.fxy_y_mode_col   = QRadioButton('column')
        _fym.addWidget(self.fxy_y_mode_range); _fym.addWidget(self.fxy_y_mode_col); _fym.addStretch(); fxy_lay.addLayout(_fym)
        self._fxy_y_range_widget = QWidget()
        _yrw = QVBoxLayout(self._fxy_y_range_widget); _yrw.setContentsMargins(0,0,0,0); _yrw.setSpacing(2)
        _yr = QHBoxLayout(); _yr.setSpacing(4); _yr.addWidget(QLabel('y:'))
        self.fxy_y_min = QDoubleSpinBox(); self.fxy_y_min.setRange(-1e9,1e9); self.fxy_y_min.setValue(0); self.fxy_y_min.setDecimals(3); self.fxy_y_min.setFixedWidth(68)
        _yr.addWidget(self.fxy_y_min); _yr.addWidget(QLabel('→'))
        self.fxy_y_max = QDoubleSpinBox(); self.fxy_y_max.setRange(-1e9,1e9); self.fxy_y_max.setValue(10); self.fxy_y_max.setDecimals(3); self.fxy_y_max.setFixedWidth(68)
        _yr.addWidget(self.fxy_y_max); _yr.addWidget(QLabel('n:'))
        self.fxy_y_n = QSpinBox(); self.fxy_y_n.setRange(2,100000); self.fxy_y_n.setValue(50); self.fxy_y_n.setFixedWidth(56)
        _yr.addWidget(self.fxy_y_n); _yr.addStretch(); _yrw.addLayout(_yr)
        _ysp = QHBoxLayout(); _ysp.setSpacing(4); _ysp.addWidget(QLabel('spacing:'))
        self.fxy_y_spacing = QComboBox(); self.fxy_y_spacing.addItems(['linspace','logspace','geomspace','random','uniform'])
        self.fxy_y_spacing.setToolTip(_sp_tip); self.fxy_y_spacing.setFixedWidth(96)
        _ysp.addWidget(self.fxy_y_spacing); _ysp.addStretch(); _yrw.addLayout(_ysp)
        _ycn = QHBoxLayout(); _ycn.setSpacing(4); _ycn.addWidget(QLabel('y col:'))
        self.fxy_y_col_name = QLineEdit('y'); self.fxy_y_col_name.setFixedWidth(60)
        _ycn.addWidget(self.fxy_y_col_name); _ycn.addStretch(); _yrw.addLayout(_ycn)
        fxy_lay.addWidget(self._fxy_y_range_widget)
        self._fxy_y_col_widget = QWidget()
        _ycw = QHBoxLayout(self._fxy_y_col_widget); _ycw.setContentsMargins(0,0,0,0); _ycw.setSpacing(4)
        _ycw.addWidget(QLabel('y col:')); self.fxy_y_combo = QComboBox(); self.fxy_y_combo.setMinimumWidth(90)
        _ycw.addWidget(self.fxy_y_combo); _ycw.addWidget(QLabel('as:'))
        self.fxy_y_var = QLineEdit('y'); self.fxy_y_var.setFixedWidth(36)
        _ycw.addWidget(self.fxy_y_var); _ycw.addStretch()
        fxy_lay.addWidget(self._fxy_y_col_widget); self._fxy_y_col_widget.setVisible(False)
        # ─ Meshgrid ─
        self.fxy_meshgrid = QCheckBox('Meshgrid  (expand x × y → n² points)')
        self.fxy_meshgrid.setToolTip(
            'When checked, a full meshgrid is created (every x_i × y_j combination).\n'
            'x, y, and z columns are all flattened to length nx * ny.\n'
            'Ideal for Heatmap, Contour, 3D Surface, or Scatter with Z colour.')
        fxy_lay.addWidget(self.fxy_meshgrid)
        # ─ Expression & output ─
        fxy_lay.addWidget(QLabel('z = expr (np, sin, cos, exp, log, pi …):'))
        self.fxy_expr = QLineEdit('x**2 + sin(y)'); fxy_lay.addWidget(self.fxy_expr)
        _zn = QHBoxLayout(); _zn.setSpacing(4); _zn.addWidget(QLabel('z col:'))
        self.fxy_z_name = QLineEdit('z'); self.fxy_z_name.setFixedWidth(60)
        _zn.addWidget(self.fxy_z_name); _zn.addStretch(); fxy_lay.addLayout(_zn)
        btn_fxy = QPushButton('▶  Generate z')
        btn_fxy.clicked.connect(self._generate_fxy); fxy_lay.addWidget(btn_fxy)
        self.fxy_status = QLabel(''); self.fxy_status.setStyleSheet('color:#555;font-size:11px;')
        fxy_lay.addWidget(self.fxy_status); fxy_lay.addStretch()
        def _fxy_xtog(): r = self.fxy_x_mode_range.isChecked(); self._fxy_x_range_widget.setVisible(r); self._fxy_x_col_widget.setVisible(not r)
        def _fxy_ytog(): r = self.fxy_y_mode_range.isChecked(); self._fxy_y_range_widget.setVisible(r); self._fxy_y_col_widget.setVisible(not r)
        self.fxy_x_mode_range.toggled.connect(_fxy_xtog)
        self.fxy_y_mode_range.toggled.connect(_fxy_ytog)
        inner_tabs.addTab(fxy_content, 'z=f(x,y)')

        # ── Inner tab 3 — Manual Data Table ───────────────────────────────────
        dt_widget = QWidget()
        dt_lay = QVBoxLayout(dt_widget); dt_lay.setSpacing(5); dt_lay.setContentsMargins(8,8,8,8)

        tc = QHBoxLayout(); tc.setSpacing(3)
        tc.addWidget(QLabel('Cols:'))
        self.table_cols_spin = QSpinBox(); self.table_cols_spin.setRange(1,20); self.table_cols_spin.setValue(2); self.table_cols_spin.setFixedWidth(46); tc.addWidget(self.table_cols_spin)
        tc.addWidget(QLabel('Rows:'))
        self.table_rows_spin = QSpinBox(); self.table_rows_spin.setRange(1,10000); self.table_rows_spin.setValue(5); self.table_rows_spin.setFixedWidth(55); tc.addWidget(self.table_rows_spin)
        btn_new_table = QPushButton('New'); btn_new_table.setFixedWidth(46); btn_new_table.clicked.connect(self._new_data_table); tc.addWidget(btn_new_table)
        tc.addStretch(); dt_lay.addLayout(tc)

        self.data_table = QTableWidget(5, 2)
        self.data_table.setHorizontalHeaderLabels(['col_1', 'col_2'])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.data_table.horizontalHeader().sectionDoubleClicked.connect(self._rename_table_col)
        dt_lay.addWidget(self.data_table, stretch=1)

        tr = QHBoxLayout(); tr.setSpacing(3)
        for label, slot in [('＋R', self._table_add_row), ('－R', self._table_del_row),
                             ('＋C', self._table_add_col), ('－C', self._table_del_col)]:
            b = QPushButton(label); b.setFixedWidth(34); b.clicked.connect(slot); tr.addWidget(b)
        btn_clr   = QPushButton('🗑'); btn_clr.setFixedWidth(34);   btn_clr.clicked.connect(self._table_clear);     tr.addWidget(btn_clr)
        btn_paste = QPushButton('📋'); btn_paste.setFixedWidth(34); btn_paste.clicked.connect(self._table_paste_csv); tr.addWidget(btn_paste)
        tr.addStretch(); dt_lay.addLayout(tr)

        load_row = QHBoxLayout(); load_row.setSpacing(4)
        btn_load_table = QPushButton('📥 Load'); btn_load_table.clicked.connect(self._load_table_data)
        btn_copy_csv   = QPushButton('📤 CSV');  btn_copy_csv.clicked.connect(self._table_copy_csv)
        load_row.addWidget(btn_load_table); load_row.addWidget(btn_copy_csv); load_row.addStretch()
        dt_lay.addLayout(load_row)
        self.table_status = QLabel(''); self.table_status.setStyleSheet('color:#555;font-size:11px;')
        dt_lay.addWidget(self.table_status)
        inner_tabs.addTab(dt_widget, '📋 Table')

        # Size inner tabs to their content (no forced stretch)
        inner_tabs.adjustSize()
        outer_lay.addWidget(inner_tabs)

        outer_lay.addStretch()
        outer_scroll.setWidget(outer_content)
        mlay = QVBoxLayout(outer_widget); mlay.setContentsMargins(0,0,0,0); mlay.addWidget(outer_scroll)
        self.tabs.addTab(outer_widget, 'Advanced')


