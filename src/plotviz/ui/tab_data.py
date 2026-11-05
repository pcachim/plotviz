"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_data.py  –  plotviz
DataTabMixin: create_data_tab(): the Data tab (Datasets page, plus the Generate, Statistics and Transform pages).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QSpinBox, QPushButton, QListWidget,
    QScrollArea, QTabWidget,
)
from ui.mixin_base import MixinBase
from ui.tab_constants import make_compact_tabs


class DataTabMixin(MixinBase):
    def create_data_tab(self):
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
        btn_reload_ds = QPushButton('⟳ Reload')
        btn_reload_ds.setToolTip('Read the selected columns (all of them if none is selected) again from '
                                 'their files; the chart follows.  File → Reload Data Files does the same')
        btn_reload_ds.clicked.connect(lambda: self._reload_datasets(self._selected_dataset_names()))
        btn_inspect = QPushButton('🔍 Inspect values')
        btn_inspect.setToolTip('Inspect selected column(s), or all if none selected')
        btn_inspect.clicked.connect(self._inspect_series)
        ds_btn_row.addWidget(btn_remove_ds)
        ds_btn_row.addWidget(btn_reload_ds)
        ds_btn_row.addWidget(btn_inspect)
        layout.addLayout(ds_btn_row)

        layout.addStretch()
        scroll.setWidget(content)
        mlay = QVBoxLayout(widget)
        mlay.addWidget(scroll)

        # Data tab, in working order: get data (load, generate), look at it, derive new series
        self.data_inner_tabs = QTabWidget()
        make_compact_tabs(self.data_inner_tabs.tabBar())
        self.data_inner_tabs.addTab(widget, 'Datasets')
        self.data_inner_tabs.addTab(self._advanced_panel, 'Generate')
        self.data_inner_tabs.addTab(self.create_statistics_page(), 'Statistics')
        self.data_inner_tabs.addTab(self.create_transform_page(), 'Transform')
        self.data_inner_tabs.currentChanged.connect(self._on_data_page_changed)
        self.tabs.addTab(self.data_inner_tabs, 'Data')
        self.tabs.currentChanged.connect(self._on_outer_tab_changed)

    def _on_outer_tab_changed(self, index):
        """Coming back to the Data tab: the open page's preview may be out of date."""
        if self.tabs.tabText(index) == 'Data':
            self._on_data_page_changed(self.data_inner_tabs.currentIndex())

    def _on_data_page_changed(self, index):
        if self.data_inner_tabs.tabText(index) == 'Statistics':
            self._refresh_statistics()
        elif self.data_inner_tabs.tabText(index) == 'Transform':
            self.tf_preview.schedule()
        elif self.data_inner_tabs.tabText(index) == 'Generate':
            self._schedule_generate_previews()
