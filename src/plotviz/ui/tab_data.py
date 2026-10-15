"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_data.py  –  plotviz
DataTabMixin: create_data_tab(): the Data tab (Datasets page, plus the Generate page).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QSpinBox, QPushButton, QListWidget,
    QScrollArea, QTabWidget,
)


class DataTabMixin:
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
        btn_inspect = QPushButton('🔍 Inspect values')
        btn_inspect.setToolTip('Inspect selected column(s), or all if none selected')
        btn_inspect.clicked.connect(self._inspect_series)
        ds_btn_row.addWidget(btn_remove_ds)
        ds_btn_row.addWidget(btn_inspect)
        layout.addLayout(ds_btn_row)

        layout.addStretch()
        scroll.setWidget(content)
        mlay = QVBoxLayout(widget)
        mlay.addWidget(scroll)

        # Data tab = the loaded datasets, and the generators that create new ones
        self.data_inner_tabs = QTabWidget()
        self.data_inner_tabs.addTab(widget, 'Datasets')
        self.data_inner_tabs.addTab(self._advanced_panel, 'Generate')
        self.tabs.addTab(self.data_inner_tabs, 'Data')
