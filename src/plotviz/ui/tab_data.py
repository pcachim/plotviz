"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_file.py  –  plotviz
FileTabMixin: create_file_tab(): the Data tab (datasets + Generate page); also builds the
subplot-grid, palette and colour-scheme panels that the Figure tab shows.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QPushButton, QListWidget,
    QCheckBox, QScrollArea, QTabWidget,
)
from ui.tab_constants import (
    COLOR_PALETTES,
)


class FileTabMixin:
    def create_file_tab(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(6)

        # Hidden widgets kept for settings persistence (export_format / export_dpi);
        # exporting itself is File > Export Image.
        self._export_fmt_combo = QComboBox()
        self._export_fmt_combo.addItems(['PNG', 'SVG', 'PDF', 'JPEG', 'TIFF', 'EPS'])
        self._export_fmt_combo.setVisible(False)
        layout.addWidget(self._export_fmt_combo)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(36, 1200)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setVisible(False)
        layout.addWidget(self.dpi_spin)

        # ── Subplot Grid ──────────────────────────────────────────────────────
        self._subplot_grid_panel = QWidget()
        pl = QVBoxLayout(self._subplot_grid_panel)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(6)
        pl.addWidget(self._sec_label('Subplot Grid'))
        # sp_rows / sp_cols / sp_sharex / sp_sharey are kept as hidden widgets so
        # serialisation and on_subplot_layout_changed continue to work unchanged.
        self.sp_rows = QSpinBox()
        self.sp_rows.setRange(1, 8)
        self.sp_rows.setValue(1)
        self.sp_rows.valueChanged.connect(lambda _: self.on_subplot_layout_changed())
        self.sp_rows.setVisible(False)
        self.sp_cols = QSpinBox()
        self.sp_cols.setRange(1, 8)
        self.sp_cols.setValue(1)
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
        pl.addWidget(btn_subplot_cfg)


        # ── Datasets ──────────────────────────────────────────────────────────
        layout.addWidget(self._sec_label('Datasets'))
        btn_load = QPushButton('📂  Browse Files  (CSV, Excel, JSON, TXT)')
        btn_load.clicked.connect(self.load_data)
        layout.addWidget(btn_load)
        self.dataset_list = QListWidget()
        self.dataset_list.setMinimumHeight(120)
        self.dataset_list.setMaximumHeight(220)
        self.dataset_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.dataset_list)
        ds_btn_row = QHBoxLayout()
        ds_btn_row.setSpacing(4)
        btn_remove_ds = QPushButton('🗑 Remove selected')
        btn_remove_ds.clicked.connect(self._remove_selected_datasets)
        btn_inspect = QPushButton('🔍 Inspect values')
        btn_inspect.setToolTip('Inspect selected column(s), or all if none selected')
        btn_inspect.clicked.connect(self._inspect_series)
        ds_btn_row.addWidget(btn_remove_ds)
        ds_btn_row.addWidget(btn_inspect)
        layout.addLayout(ds_btn_row)

        # ── Colour palette ────────────────────────────────────────────────────
        self._palette_panel = QWidget()
        pl = QVBoxLayout(self._palette_panel)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(6)
        pl.addWidget(self._sec_label('Colour Palette'))
        pal_row = QHBoxLayout()
        pal_row.setSpacing(6)
        self.palette_combo = QComboBox()
        self.palette_combo.addItems(sorted(COLOR_PALETTES.keys(), key=str.casefold))
        idx = self.palette_combo.findText('Matplotlib')
        if idx >= 0: self.palette_combo.setCurrentIndex(idx)
        self.palette_combo.currentTextChanged.connect(self._on_palette_changed)
        pal_row.addWidget(self.palette_combo)
        pal_row.addStretch()
        pl.addLayout(pal_row)
        self._palette_swatch_row = QHBoxLayout()
        self._palette_swatch_row.setSpacing(2)
        self._palette_swatches = []
        for _ in range(16):
            sw = QLabel()
            sw.setFixedSize(18, 14)
            sw.setStyleSheet('background:#ccc; border:1px solid #aaa;')
            self._palette_swatches.append(sw)
            self._palette_swatch_row.addWidget(sw)
        self._palette_swatch_row.addStretch()
        pl.addLayout(self._palette_swatch_row)
        pal_btn_row = QHBoxLayout()
        pal_btn_row.setSpacing(4)
        btn_edit_pal = QPushButton('✏️ Edit palette…')
        btn_edit_pal.setToolTip('Create or edit a custom colour palette')
        btn_edit_pal.clicked.connect(self._open_palette_editor)
        pal_btn_row.addWidget(btn_edit_pal)
        btn_reset_locks = QPushButton('↺ Reset colors')
        btn_reset_locks.setToolTip('Remove manual color locks from all series and re-apply the active palette')
        btn_reset_locks.clicked.connect(self._reset_all_color_locks)
        pal_btn_row.addWidget(btn_reset_locks)
        pal_btn_row.addStretch()
        pl.addLayout(pal_btn_row)
        pal_io_row = QHBoxLayout()
        pal_io_row.setSpacing(4)
        btn_import_pal = QPushButton('📥 Load palette…')
        btn_import_pal.setToolTip('Load a .pvizp palette bundle')
        btn_import_pal.clicked.connect(self._import_palette_bundle)
        pal_io_row.addWidget(btn_import_pal)
        btn_export_pal = QPushButton('📤 Save palette…')
        btn_export_pal.setToolTip('Save custom palettes as a .pvizp bundle')
        btn_export_pal.clicked.connect(self._export_palette_bundle)
        pal_io_row.addWidget(btn_export_pal)
        pal_io_row.addStretch()
        pl.addLayout(pal_io_row)
        self._refresh_palette_swatches()


        # ── Color Schemes ─────────────────────────────────────────────────────
        self._scheme_panel = QWidget()
        pl = QVBoxLayout(self._scheme_panel)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(6)
        pl.addWidget(self._sec_label('Color Schemes'))

        cs_sel_row = QHBoxLayout()
        cs_sel_row.setSpacing(4)
        self._cs_combo = QComboBox()
        self._cs_combo.setToolTip('Choose a built-in or saved color scheme; it is applied at once')
        cs_sel_row.addWidget(self._cs_combo, 1)
        pl.addLayout(cs_sel_row)

        cs_target_row = QHBoxLayout()
        cs_target_row.setSpacing(4)
        cs_target_row.addWidget(QLabel('Apply to:'))
        self._cs_target = QComboBox()
        self._cs_target.addItems(['All subplots', 'Active subplot only'])
        self._cs_target.setToolTip(
            'Active subplot only changes that subplot\'s plot area, axes colour, borders,\n'
            'grid and title colour. Figure background, palette, fonts and axis-label\n'
            'colours belong to the whole figure and stay as they are.')
        self._cs_target.setEnabled(False)          # needs more than one subplot
        cs_target_row.addWidget(self._cs_target, 1)
        pl.addLayout(cs_target_row)

        cs_btn_row = QHBoxLayout()
        cs_btn_row.setSpacing(4)
        btn_cs_load = QPushButton('📂 Load scheme…')
        btn_cs_load.setToolTip('Load a .pvizc color scheme file')
        btn_cs_load.clicked.connect(self._load_color_scheme)
        cs_btn_row.addWidget(btn_cs_load)
        btn_cs_save = QPushButton('💾 Save scheme…')
        btn_cs_save.setToolTip('Save current colors as a .pvizc color scheme')
        btn_cs_save.clicked.connect(self._save_color_scheme)
        cs_btn_row.addWidget(btn_cs_save)
        cs_btn_row.addStretch()
        pl.addLayout(cs_btn_row)

        # Populate built-in schemes and set initial swatch
        self._init_color_schemes()


        layout.addStretch()
        scroll.setWidget(content)
        mlay = QVBoxLayout(widget)
        mlay.addWidget(scroll)

        # Data tab = the loaded datasets, and the generators that create new ones
        self.data_inner_tabs = QTabWidget()
        self.data_inner_tabs.addTab(widget, 'Datasets')
        self.data_inner_tabs.addTab(self._advanced_panel, 'Generate')
        self.tabs.addTab(self.data_inner_tabs, 'Data')
