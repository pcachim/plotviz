"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_statistics.py  –  plotviz
StatisticsTabMixin: the Statistics page of the Data tab (summary table of the loaded series,
and their correlation matrix).
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QApplication, QAbstractItemView,
)

from core.dates import format_date, is_date
from data.descriptive import STAT_COLUMNS, describe_all, correlation_matrix
from ui.mixin_base import MixinBase


_DATE_STATS = ('mean', 'min', '25%', 'median', '75%', 'max')    # dates; std is in days


def _fmt(v, as_date=False):
    if v is None:
        return ''
    if as_date:
        return format_date(v)
    return f'{v:d}' if isinstance(v, int) else f'{v:.6g}'


class StatisticsTabMixin(MixinBase):
    def create_statistics_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(6)

        layout.addWidget(self._sec_label('Summary'))
        hint = QLabel('Series selected in the Datasets list, or all of them if none is selected.')
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#777;font-size:11px;')
        layout.addWidget(hint)
        self.stats_table = QTableWidget()
        self._stats_table_setup(self.stats_table)
        layout.addWidget(self.stats_table, 3)

        layout.addWidget(self._sec_label('Correlation'))
        row = QHBoxLayout()
        row.setSpacing(4)
        row.addWidget(QLabel('Method:'))
        self.stats_corr_method = QComboBox()
        self.stats_corr_method.addItems(['pearson', 'spearman'])
        self.stats_corr_method.currentIndexChanged.connect(self._refresh_statistics)
        row.addWidget(self.stats_corr_method)
        row.addStretch()
        btn_refresh = QPushButton('↻ Refresh')
        btn_refresh.clicked.connect(self._refresh_statistics)
        btn_copy = QPushButton('📋 Copy summary')
        btn_copy.setToolTip('Copy the summary table to the clipboard (tab-separated)')
        btn_copy.clicked.connect(self._copy_statistics)
        row.addWidget(btn_refresh)
        row.addWidget(btn_copy)
        layout.addLayout(row)
        self.corr_table = QTableWidget()
        self._stats_table_setup(self.corr_table)
        layout.addWidget(self.corr_table, 3)
        self.stats_note = QLabel('')
        self.stats_note.setWordWrap(True)
        self.stats_note.setStyleSheet('color:#777;font-size:11px;')
        layout.addWidget(self.stats_note)
        return page

    @staticmethod
    def _stats_table_setup(table):
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setDefaultSectionSize(22)

    def _stats_names(self):
        picked = [i.text() for i in self.dataset_list.selectedItems()]
        return picked or sorted(self.datasets)

    def _refresh_statistics(self, *_):
        names = self._stats_names()
        rows = describe_all(self.datasets, names)
        t = self.stats_table                       # one column per series, one row per statistic
        t.clear()
        t.setRowCount(len(STAT_COLUMNS))
        t.setColumnCount(len(rows))
        t.setVerticalHeaderLabels(STAT_COLUMNS)
        t.setHorizontalHeaderLabels(list(rows))
        for c, (name, stats) in enumerate(rows.items()):
            for r, key in enumerate(STAT_COLUMNS):
                item = QTableWidgetItem(_fmt(stats[key], is_date(self.datasets[name]) and key in _DATE_STATS))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                t.setItem(r, c, item)
        t.resizeColumnsToContents()

        used, mat = correlation_matrix(self.datasets, names, self.stats_corr_method.currentText())
        ct = self.corr_table
        ct.clear()
        ct.setColumnCount(len(used))
        ct.setRowCount(len(used))
        ct.setHorizontalHeaderLabels(used)
        ct.setVerticalHeaderLabels(used)
        for i in range(len(used)):
            for j in range(len(used)):
                v = mat[i, j]
                item = QTableWidgetItem('' if v != v else f'{v:.3f}')
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if v == v:                                   # blue (negative) to red (positive)
                    a = int(110 * abs(v))
                    item.setBackground(QColor(220, 60, 60, a) if v > 0 else QColor(60, 90, 220, a))
                ct.setItem(i, j, item)
        ct.resizeColumnsToContents()
        skipped = len(names) - len(used)
        self.stats_note.setText(
            (f'{skipped} text series left out of the correlation. ' if skipped else '') +
            'Blank cells: series of different length, a constant series, or fewer than 3 common points.')

    def _copy_statistics(self):
        t = self.stats_table
        header = [t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]
        lines = ['\t'.join([''] + header)]
        for r in range(t.rowCount()):
            cells = [t.verticalHeaderItem(r).text()]
            cells += [t.item(r, c).text() for c in range(t.columnCount())]
            lines.append('\t'.join(cells))
        QApplication.clipboard().setText('\n'.join(lines))
