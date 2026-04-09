"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.

ui/main_window.py  –  plotviz
Core application class. Tab UI, helpers, and event handlers.
Tab building, plot engine and serialization live in their own mixin modules.
"""

import os
import sys

# ── Path bootstrap ────────────────────────────────────────────────────────────
# Ensure src/plotviz/ is on sys.path regardless of how this module is loaded.
# main.py does this first when launching normally; this guard covers every other
# case (pytest, direct `python ui/main_window.py`, PyInstaller, etc.).
_HERE = os.path.dirname(os.path.abspath(__file__))   # …/ui/
_PKG  = os.path.dirname(_HERE)                       # …/src/plotviz/
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)
# ─────────────────────────────────────────────────────────────────────────────

import csv
import io
import json
import shutil
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QFileDialog,
    QMessageBox, QListWidget, QListWidgetItem, QCheckBox, QSplitter, QScrollArea,
    QButtonGroup, QRadioButton, QFrame, QGroupBox, QDialog,
    QDialogButtonBox, QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QShortcut, QKeySequence
from PyQt6.QtWidgets import QApplication
try:
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
except ImportError:
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

from ui.canvas import CanvasPlotter
from ui.tab_builders import (
    TabBuildersMixin, COLOR_PALETTES, get_all_palettes, add_custom_palette,
    PER_SERIES_TYPES, _CUSTOM_PALETTES,
    PLOT_MODE_GROUPS, TYPE_TO_PLOT_MODE,
)
from ui.plot_engine import PlotEngineMixin
from ui.serialization import SerializationMixin
from ui.python_export import PythonExportMixin
from ui.seaborn_explorer import SeabornExplorer
from ui.code_runner import CodeRunnerDialog


import config.settings as settings
from ui.helpers import _get_dir, _remember_dir, _show_color_dialog
from ui.dialogs import AnnotationEditDialog, DataImportDialog

from data.scientific import CurveFitter
from styling.presets import ChartPresets


# class AnnotationEditDialog(QDialog):
#     """Edit a single annotation's position, label, style, and image zoom."""

#     def __init__(self, ann, parent=None):
#         super().__init__(parent)
#         self.ann = ann
#         self.setWindowTitle('Edit Annotation')
#         layout = QVBoxLayout(self)
#         form   = QFormLayout()

#         atype = ann['type']
#         self.fields = {}

#         if atype == 'text':
#             self.fields['label'] = QLineEdit(ann.get('label',''))
#             form.addRow('Label:', self.fields['label'])
#             self.fields['x'] = QDoubleSpinBox()
#             self.fields['x'].setRange(-1e9, 1e9); self.fields['x'].setDecimals(6)
#             self.fields['x'].setValue(ann['x'])
#             form.addRow('X:', self.fields['x'])
#             self.fields['y'] = QDoubleSpinBox()
#             self.fields['y'].setRange(-1e9, 1e9); self.fields['y'].setDecimals(6)
#             self.fields['y'].setValue(ann['y'])
#             form.addRow('Y:', self.fields['y'])

#             s = ann.get('style', {})
#             self.fields['fontsize'] = QSpinBox()
#             self.fields['fontsize'].setRange(6,72)
#             self.fields['fontsize'].setValue(s.get('fontsize',10))
#             form.addRow('Font size:', self.fields['fontsize'])

#             self.fields['fontcolor'] = QLineEdit(s.get('fontcolor','#000000'))
#             btn_fc = QPushButton('…')
#             btn_fc.setFixedWidth(28)
#             btn_fc.clicked.connect(lambda: self._pick_color('fontcolor'))
#             row = QHBoxLayout(); row.addWidget(self.fields['fontcolor']); row.addWidget(btn_fc)
#             w = QWidget(); w.setLayout(row)
#             form.addRow('Font color:', w)

#             self.fields['bg_alpha'] = QDoubleSpinBox()
#             self.fields['bg_alpha'].setRange(0,1); self.fields['bg_alpha'].setSingleStep(0.05)
#             self.fields['bg_alpha'].setValue(s.get('bg_alpha',0.9))
#             form.addRow('BG opacity:', self.fields['bg_alpha'])

#             self.fields['bg_color'] = QLineEdit(s.get('bg_color','#ffffcc'))
#             btn_bg = QPushButton('…')
#             btn_bg.setFixedWidth(28)
#             btn_bg.clicked.connect(lambda: self._pick_color('bg_color'))
#             row2 = QHBoxLayout(); row2.addWidget(self.fields['bg_color']); row2.addWidget(btn_bg)
#             w2 = QWidget(); w2.setLayout(row2)
#             form.addRow('BG color:', w2)

#         elif atype == 'arrow':
#             for k, label in [('x0','Tail X'),('y0','Tail Y'),('x1','Tip X'),('y1','Tip Y')]:
#                 sb = QDoubleSpinBox()
#                 sb.setRange(-1e9,1e9); sb.setDecimals(6)
#                 sb.setValue(ann[k])
#                 self.fields[k] = sb
#                 form.addRow(label+':', sb)
#             self.fields['label'] = QLineEdit(ann.get('label',''))
#             form.addRow('Label:', self.fields['label'])
#             s = ann.get('style', {})
#             self.fields['fontcolor'] = QLineEdit(s.get('fontcolor','#000000'))
#             btn_fc2 = QPushButton('…'); btn_fc2.setFixedWidth(28)
#             btn_fc2.clicked.connect(lambda: self._pick_color('fontcolor'))
#             row3 = QHBoxLayout(); row3.addWidget(self.fields['fontcolor']); row3.addWidget(btn_fc2)
#             w3 = QWidget(); w3.setLayout(row3)
#             form.addRow('Arrow color:', w3)

#         elif atype == 'image':
#             self.fields['x'] = QDoubleSpinBox()
#             self.fields['x'].setRange(-1e9,1e9); self.fields['x'].setDecimals(6)
#             self.fields['x'].setValue(ann['x'])
#             form.addRow('X:', self.fields['x'])
#             self.fields['y'] = QDoubleSpinBox()
#             self.fields['y'].setRange(-1e9,1e9); self.fields['y'].setDecimals(6)
#             self.fields['y'].setValue(ann['y'])
#             form.addRow('Y:', self.fields['y'])
#             self.fields['zoom'] = QDoubleSpinBox()
#             self.fields['zoom'].setRange(0.01,5.0); self.fields['zoom'].setSingleStep(0.05)
#             self.fields['zoom'].setValue(ann.get('zoom',0.15))
#             form.addRow('Zoom:', self.fields['zoom'])

#         layout.addLayout(form)
#         btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
#                                 QDialogButtonBox.StandardButton.Cancel)
#         btns.accepted.connect(self.accept)
#         btns.rejected.connect(self.reject)
#         layout.addWidget(btns)

#     def _pick_color(self, field_key):
#         cur = self.fields[field_key].text() if field_key in self.fields else '#000000'
#         # Pull active palette from main window if available
#         mw = QApplication.activeWindow()
#         pal_colors = (mw._active_palette_colors()
#                       if mw and hasattr(mw, '_active_palette_colors') else None)
#         color = _show_color_dialog(QColor(cur), self, palette_colors=pal_colors)
#         if color.isValid():
#             self.fields[field_key].setText(color.name())

#     def apply(self):
#         """Write edited values back into self.ann."""
#         ann   = self.ann
#         atype = ann['type']
#         if atype == 'text':
#             ann['label'] = self.fields['label'].text()
#             ann['x']     = self.fields['x'].value()
#             ann['y']     = self.fields['y'].value()
#             ann.setdefault('style', {})
#             ann['style']['fontsize']  = self.fields['fontsize'].value()
#             ann['style']['fontcolor'] = self.fields['fontcolor'].text()
#             ann['style']['bg_alpha']  = self.fields['bg_alpha'].value()
#             ann['style']['bg_color']  = self.fields['bg_color'].text()
#             # Preserve edge_color if already set
#             ann['style'].setdefault('edge_color', '#aaaaaa')
#             ann['style'].setdefault('fontfamily', 'sans-serif')
#         elif atype == 'arrow':
#             for k in ('x0','y0','x1','y1'):
#                 ann[k] = self.fields[k].value()
#             ann['label'] = self.fields['label'].text()
#             ann.setdefault('style', {})
#             ann['style']['fontcolor'] = self.fields['fontcolor'].text()
#             ann['style'].setdefault('fontsize', 10)
#             ann['style'].setdefault('fontfamily', 'sans-serif')
#         elif atype == 'image':
#             ann['x']    = self.fields['x'].value()
#             ann['y']    = self.fields['y'].value()
#             ann['zoom'] = self.fields['zoom'].value()


# ═══════════════════════════════════════════════════════════════════════════════
# DATA IMPORT DIALOG
# ═══════════════════════════════════════════════════════════════════════════════
# class DataImportDialog(QDialog):
#     """
#     Per-file import wizard.  Lets the user:
#       • choose sheet (Excel), separator (CSV/TXT), or JSON orientation
#       • set header row & skip rows
#       • preview the raw table
#       • select / deselect / rename individual columns
#     """

#     # ── supported separators for CSV / TXT ───────────────────────────────────
#     _SEP_LABELS = ['Auto-detect', 'Comma  (,)', 'Semicolon  (;)',
#                    'Tab  (\\t)', 'Space / whitespace', 'Pipe  (|)', 'Custom…']
#     _SEP_CHARS  = [None, ',', ';', '\t', r'\s+', '|', None]

#     def __init__(self, filepath: str, parent=None):
#         super().__init__(parent)
#         self.filepath  = filepath
#         self.ext       = os.path.splitext(filepath)[1].lower()
#         self._raw_df   = None        # full DataFrame from last parse
#         self._col_data = {}          # col_name → np.ndarray after dtype inference
#         self._col_checks  = {}       # col_name → QCheckBox
#         self._col_renames = {}       # col_name → QLineEdit
#         self._building = False       # guard against recursive refresh

#         self.setWindowTitle(f'Import — {os.path.basename(filepath)}')
#         self.setMinimumSize(860, 620)
#         self._build_ui()
#         self._refresh()

#     # ─── UI construction ─────────────────────────────────────────────────────
#     def _build_ui(self):
#         root = QVBoxLayout(self)
#         root.setSpacing(6)

#         # ── top bar: file path label ──────────────────────────────────────────
#         path_lbl = QLabel(f'<b>File:</b> {self.filepath}')
#         path_lbl.setWordWrap(True)
#         root.addWidget(path_lbl)

#         # ── format-specific options ───────────────────────────────────────────
#         opt_box = QGroupBox('Parse options')
#         opt_lay = QHBoxLayout(opt_box)
#         opt_lay.setSpacing(12)

#         # Sheet selector (Excel only)
#         self._sheet_label = QLabel('Sheet:')
#         self._sheet_combo = QComboBox(); self._sheet_combo.setMinimumWidth(120)
#         self._sheet_combo.currentTextChanged.connect(self._refresh)
#         opt_lay.addWidget(self._sheet_label)
#         opt_lay.addWidget(self._sheet_combo)
#         is_excel = self.ext in ('.xlsx', '.xls')
#         self._sheet_label.setVisible(is_excel)
#         self._sheet_combo.setVisible(is_excel)
#         if is_excel:
#             try:
#                 import openpyxl
#                 wb = openpyxl.load_workbook(self.filepath, read_only=True, data_only=True)
#                 self._sheet_combo.blockSignals(True)
#                 self._sheet_combo.addItems(wb.sheetnames)
#                 self._sheet_combo.blockSignals(False)
#                 wb.close()
#             except Exception:
#                 try:
#                     xl = pd.ExcelFile(self.filepath)
#                     self._sheet_combo.blockSignals(True)
#                     self._sheet_combo.addItems(xl.sheet_names)
#                     self._sheet_combo.blockSignals(False)
#                 except Exception:
#                     pass

#         # Separator (CSV / TXT only)
#         self._sep_label = QLabel('Separator:')
#         self._sep_combo = QComboBox()
#         self._sep_combo.addItems(self._SEP_LABELS)
#         self._sep_combo.currentIndexChanged.connect(self._on_sep_changed)
#         self._sep_custom = QLineEdit(); self._sep_custom.setPlaceholderText('regex / char')
#         self._sep_custom.setFixedWidth(80); self._sep_custom.setVisible(False)
#         self._sep_custom.editingFinished.connect(self._refresh)
#         opt_lay.addWidget(self._sep_label)
#         opt_lay.addWidget(self._sep_combo)
#         opt_lay.addWidget(self._sep_custom)
#         is_text = self.ext in ('.csv', '.txt')
#         self._sep_label.setVisible(is_text)
#         self._sep_combo.setVisible(is_text)
#         if is_text:
#             # default: comma for csv, whitespace for txt
#             self._sep_combo.blockSignals(True)
#             self._sep_combo.setCurrentIndex(1 if self.ext == '.csv' else 4)
#             self._sep_combo.blockSignals(False)

#         # JSON orientation
#         self._json_label = QLabel('Orientation:')
#         self._json_combo = QComboBox()
#         self._json_combo.addItems(['columns (default)', 'records', 'index', 'split', 'values'])
#         self._json_combo.currentTextChanged.connect(self._refresh)
#         opt_lay.addWidget(self._json_label)
#         opt_lay.addWidget(self._json_combo)
#         is_json = self.ext == '.json'
#         self._json_label.setVisible(is_json)
#         self._json_combo.setVisible(is_json)

#         # Header row & skip rows (always visible)
#         opt_lay.addWidget(QLabel('Header row:'))
#         self._header_spin = QSpinBox(); self._header_spin.setRange(0, 100)
#         self._header_spin.setValue(0); self._header_spin.setFixedWidth(55)
#         self._header_spin.valueChanged.connect(self._refresh)
#         opt_lay.addWidget(self._header_spin)

#         opt_lay.addWidget(QLabel('Skip rows:'))
#         self._skip_spin = QSpinBox(); self._skip_spin.setRange(0, 1000)
#         self._skip_spin.setValue(0); self._skip_spin.setFixedWidth(55)
#         self._skip_spin.valueChanged.connect(self._refresh)
#         opt_lay.addWidget(self._skip_spin)

#         opt_lay.addStretch()
#         root.addWidget(opt_box)

#         # ── splitter: preview (top) + column picker (bottom) ─────────────────
#         splitter = QSplitter(Qt.Orientation.Vertical)

#         # Preview table
#         preview_w = QWidget(); preview_lay = QVBoxLayout(preview_w); preview_lay.setContentsMargins(0,0,0,0)
#         hdr_row = QHBoxLayout()
#         hdr_row.addWidget(QLabel('<b>Data preview</b> (first 100 rows):'))
#         self._shape_lbl = QLabel('')
#         self._shape_lbl.setStyleSheet('color:#555;font-size:11px;')
#         hdr_row.addWidget(self._shape_lbl); hdr_row.addStretch()
#         preview_lay.addLayout(hdr_row)
#         self._preview_table = QTableWidget()
#         self._preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
#         self._preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectColumns)
#         self._preview_table.horizontalHeader().setStretchLastSection(False)
#         self._preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
#         self._preview_table.setMinimumHeight(180)
#         preview_lay.addWidget(self._preview_table)
#         splitter.addWidget(preview_w)

#         # Column picker
#         picker_w = QWidget(); picker_lay = QVBoxLayout(picker_w); picker_lay.setContentsMargins(0,0,0,0)
#         pick_hdr = QHBoxLayout()
#         pick_hdr.addWidget(QLabel('<b>Columns to import</b> (✔ = include, edit name to rename):'))
#         btn_all  = QPushButton('Select all');   btn_all.setFixedWidth(90)
#         btn_none = QPushButton('Select none');  btn_none.setFixedWidth(90)
#         btn_all.clicked.connect(lambda: self._set_all_checks(True))
#         btn_none.clicked.connect(lambda: self._set_all_checks(False))
#         pick_hdr.addStretch(); pick_hdr.addWidget(btn_all); pick_hdr.addWidget(btn_none)
#         picker_lay.addLayout(pick_hdr)

#         scroll = QScrollArea(); scroll.setWidgetResizable(True)
#         self._col_picker_widget = QWidget()
#         self._col_picker_lay = QVBoxLayout(self._col_picker_widget)
#         self._col_picker_lay.setSpacing(3); self._col_picker_lay.setContentsMargins(4,4,4,4)
#         scroll.setWidget(self._col_picker_widget)
#         picker_lay.addWidget(scroll)
#         splitter.addWidget(picker_w)

#         splitter.setSizes([280, 200])
#         root.addWidget(splitter, 1)

#         # ── status / error label ──────────────────────────────────────────────
#         self._status_lbl = QLabel('')
#         self._status_lbl.setStyleSheet('color:#b00;font-size:11px;')
#         self._status_lbl.setWordWrap(True)
#         root.addWidget(self._status_lbl)

#         # ── dialog buttons ────────────────────────────────────────────────────
#         btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
#                                 QDialogButtonBox.StandardButton.Cancel)
#         btns.accepted.connect(self._on_accept)
#         btns.rejected.connect(self.reject)
#         self._ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
#         self._ok_btn.setText('Import selected columns')
#         root.addWidget(btns)

#     # ─── separator combo ─────────────────────────────────────────────────────
#     def _on_sep_changed(self, idx):
#         is_custom = (idx == len(self._SEP_LABELS) - 1)
#         self._sep_custom.setVisible(is_custom)
#         if not is_custom:
#             self._refresh()

#     def _current_sep(self):
#         idx = self._sep_combo.currentIndex()
#         if idx == len(self._SEP_CHARS) - 1:          # Custom
#             return self._sep_custom.text() or ','
#         return self._SEP_CHARS[idx]                   # may be None (auto)

#     # ─── core parse / refresh ────────────────────────────────────────────────
#     def _refresh(self):
#         if self._building:
#             return
#         self._building = True
#         try:
#             self._raw_df = self._parse()
#             if self._raw_df is not None:
#                 self._status_lbl.setText('')
#                 self._populate_preview(self._raw_df)
#                 self._infer_col_data(self._raw_df)
#                 self._rebuild_col_picker(self._raw_df)
#                 self._shape_lbl.setText(
#                     f'{len(self._raw_df):,} rows × {len(self._raw_df.columns):,} columns')
#         except Exception as e:
#             self._status_lbl.setText(f'Parse error: {e}')
#             self._preview_table.setRowCount(0)
#             self._preview_table.setColumnCount(0)
#             self._shape_lbl.setText('')
#         finally:
#             self._building = False

#     def _parse(self):
#         import pandas as pd
#         ext  = self.ext
#         hdr  = self._header_spin.value()
#         skip = self._skip_spin.value()

#         if ext in ('.xlsx', '.xls'):
#             sheet = self._sheet_combo.currentText() or 0
#             return pd.read_excel(self.filepath, sheet_name=sheet,
#                                  header=hdr, skiprows=skip or None)

#         if ext == '.json':
#             orient_map = {
#                 'columns (default)': None, 'records': 'records',
#                 'index': 'index', 'split': 'split', 'values': 'values',
#             }
#             orient = orient_map.get(self._json_combo.currentText())
#             with open(self.filepath) as f:
#                 import json as _json
#                 raw = _json.load(f)
#             if isinstance(raw, list):
#                 return pd.DataFrame(raw)
#             kw = {'orient': orient} if orient else {}
#             return pd.read_json(self.filepath, **kw)

#         # CSV / TXT
#         sep = self._current_sep()
#         if sep is None:                       # auto-detect
#             try:
#                 with open(self.filepath, newline='') as f:
#                     dialect = csv.Sniffer().sniff(f.read(4096))
#                 sep = dialect.delimiter
#             except Exception:
#                 sep = ','
#         kw = dict(header=hdr, skiprows=skip or None)
#         if sep == r'\s+':
#             return pd.read_csv(self.filepath, sep=r'\s+', engine='python', **kw)
#         return pd.read_csv(self.filepath, sep=sep, **kw)

#     # ─── preview table ───────────────────────────────────────────────────────
#     def _populate_preview(self, df):
#         preview = df.head(100)
#         self._preview_table.blockSignals(True)
#         self._preview_table.setRowCount(len(preview))
#         self._preview_table.setColumnCount(len(preview.columns))
#         self._preview_table.setHorizontalHeaderLabels([str(c) for c in preview.columns])
#         for ri, row in enumerate(preview.itertuples(index=False)):
#             for ci, val in enumerate(row):
#                 self._preview_table.setItem(ri, ci, QTableWidgetItem(str(val)))
#         self._preview_table.blockSignals(False)

#     # ─── dtype inference ─────────────────────────────────────────────────────
#     def _infer_col_data(self, df):
#         import numpy as np, pandas as pd
#         self._col_data = {}
#         for col in df.columns:
#             series = df[col]
#             numeric = pd.to_numeric(series, errors='coerce')
#             non_null = series.notna().sum()
#             if non_null > 0 and numeric.notna().sum() == non_null:
#                 self._col_data[str(col)] = numeric.to_numpy(dtype=float, na_value=np.nan)
#             else:
#                 self._col_data[str(col)] = series.fillna('').astype(str).to_numpy()

#     # ─── column picker ───────────────────────────────────────────────────────
#     def _rebuild_col_picker(self, df):
#         # Save existing check states + rename text before wiping
#         prev_checks  = {col: cb.isChecked()  for col, cb in self._col_checks.items()}
#         prev_renames = {col: le.text()        for col, le in self._col_renames.items()}

#         # Clear layout
#         while self._col_picker_lay.count():
#             item = self._col_picker_lay.takeAt(0)
#             if item.widget(): item.widget().deleteLater()
#         self._col_checks.clear()
#         self._col_renames.clear()

#         cols = [str(c) for c in df.columns]
#         dtype_icons = {'float': '🔢', 'str': '🔤'}

#         # Header row
#         hdr_w = QWidget()
#         hdr_l = QHBoxLayout(hdr_w); hdr_l.setContentsMargins(0,0,0,0); hdr_l.setSpacing(6)
#         lbl_inc  = QLabel('Include'); lbl_inc.setFixedWidth(56); lbl_inc.setStyleSheet('font-weight:bold;')
#         lbl_orig = QLabel('Original name'); lbl_orig.setFixedWidth(180); lbl_orig.setStyleSheet('font-weight:bold;')
#         lbl_type = QLabel('Type'); lbl_type.setFixedWidth(42); lbl_type.setStyleSheet('font-weight:bold;')
#         lbl_imp  = QLabel('Import as (rename)'); lbl_imp.setStyleSheet('font-weight:bold;')
#         hdr_l.addWidget(lbl_inc); hdr_l.addWidget(lbl_orig)
#         hdr_l.addWidget(lbl_type); hdr_l.addWidget(lbl_imp); hdr_l.addStretch()
#         self._col_picker_lay.addWidget(hdr_w)

#         # One row per column
#         for col in cols:
#             arr = self._col_data.get(col)
#             dtype_icon = dtype_icons['float'] if (arr is not None and arr.dtype != object) else dtype_icons['str']

#             row_w = QWidget()
#             row_l = QHBoxLayout(row_w); row_l.setContentsMargins(0,0,0,0); row_l.setSpacing(6)

#             chk = QCheckBox()
#             chk.setChecked(prev_checks.get(col, True))
#             chk.setFixedWidth(56)
#             self._col_checks[col] = chk

#             orig_lbl = QLabel(col); orig_lbl.setFixedWidth(180)
#             orig_lbl.setToolTip(col)

#             type_lbl = QLabel(dtype_icon); type_lbl.setFixedWidth(42)
#             type_lbl.setToolTip('Numeric' if dtype_icon == dtype_icons['float'] else 'Text/categorical')

#             rename_edit = QLineEdit(prev_renames.get(col, col))
#             rename_edit.setMinimumWidth(160)
#             rename_edit.setPlaceholderText(col)
#             self._col_renames[col] = rename_edit

#             # Grey out rename when unchecked
#             def _on_check(state, le=rename_edit):
#                 le.setEnabled(bool(state))
#             chk.stateChanged.connect(_on_check)
#             rename_edit.setEnabled(chk.isChecked())

#             row_l.addWidget(chk)
#             row_l.addWidget(orig_lbl)
#             row_l.addWidget(type_lbl)
#             row_l.addWidget(rename_edit)
#             row_l.addStretch()
#             self._col_picker_lay.addWidget(row_w)

#         self._col_picker_lay.addStretch()

#     def _set_all_checks(self, state: bool):
#         for chk in self._col_checks.values():
#             chk.setChecked(state)

#     # ─── accept / collect ─────────────────────────────────────────────────────
#     def _on_accept(self):
#         selected = {col for col, chk in self._col_checks.items() if chk.isChecked()}
#         if not selected:
#             QMessageBox.warning(self, 'No columns', 'Select at least one column to import.')
#             return
#         self.accept()

#     def get_selected_data(self) -> dict:
#         """Return {import_name: np.ndarray} for all checked columns."""
#         result = {}
#         for col, chk in self._col_checks.items():
#             if not chk.isChecked():
#                 continue
#             new_name = self._col_renames[col].text().strip() or col
#             arr = self._col_data.get(col)
#             if arr is not None:
#                 result[new_name] = arr
#         return result


class PlotVizApp(TabBuildersMixin, PlotEngineMixin, SerializationMixin, PythonExportMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        from config._version import __version__
        self.setWindowTitle(f'plotviz {__version__}')

        # ── Restore window geometry from settings ──────────────────────────────
        geom = settings.get('window_geometry')   # [x, y, w, h]
        if isinstance(geom, (list, tuple)) and len(geom) == 4:
            self.setGeometry(*geom)
        else:
            self.setGeometry(100, 100, 1400, 900)
        if settings.get('window_maximised'):
            self.showMaximized()

        self.datasets      = {}
        self.curve_styles  = {}
        self._last_fit     = None
        self.subplot_rows  = 1
        self.subplot_cols  = 1
        self.subplot_chart_types  = {0: 'Line'}
        self.subplot_plot_modes   = {0: 'Standard'}
        self.subplot_chart_opts   = {}      # {subplot_idx: {opt_key: value}}
        self.sp_titles            = {0: ''}
        self.subplot_title_show   = {0: True}
        self.subplot_title_font   = {0: 'sans-serif'}
        self.subplot_title_size   = {0: 11}
        self.subplot_title_color  = {0: '#000000'}
        self.subplot_xlabels      = {0: ''}
        self.subplot_xlabel_show  = {0: True}
        self.subplot_ylabels      = {0: ''}
        self.subplot_ylabel_show  = {0: True}
        self.subplot_y2labels     = {0: ''}
        self.subplot_y2label_show = {0: True}
        self.subplot_legends      = {0: True}
        self.subplot_legend_locs  = {0: 'best'}
        self.subplot_legend_x     = {0: 0.01}
        self.subplot_legend_y     = {0: 0.99}
        self.subplot_legend_fontsize = {0: 9}
        self.subplot_legend_ncols = {0: 1}
        self.subplot_legend_frameon = {0: True}
        self.subplot_legend_color   = {0: '#000000'}
        self.subplot_legend_facecolor = {0: '#ffffff'}
        self.subplot_legend_alpha   = {0: 0.8}
        self.subplot_legend_edgecolor = {0: '#cccccc'}
        self.subplot_xlims        = {0: None}
        self.subplot_ylims        = {0: None}
        self.subplot_y2lims       = {0: None}
        self.subplot_xscales      = {0: 'linear'}
        self.subplot_yscales      = {0: 'linear'}
        self.subplot_xtick_sizes  = {0: 9}
        self.subplot_ytick_sizes  = {0: 9}
        # Tick formatting (new per-subplot state)
        self.subplot_xtick_dir      = {0: 'out'}
        self.subplot_ytick_dir      = {0: 'out'}
        self.subplot_xtick_minor    = {0: False}
        self.subplot_ytick_minor    = {0: False}
        self.subplot_xtick_rotation = {0: 0}
        self.subplot_ytick_rotation = {0: 0}
        self.subplot_xtick_step     = {0: 0.0}   # 0 = auto
        self.subplot_ytick_step     = {0: 0.0}
        self.subplot_x_formatter    = {0: 'auto'}
        self.subplot_y_formatter    = {0: 'auto'}
        self.subplot_xticks_show    = {0: True}
        self.subplot_yticks_show    = {0: True}
        self._subplot_mosaic = None  # None = regular grid; list-of-lists = mosaic
        self._colour_mode  = 'system'  # track current scheme for serialization
        self._color_palette = settings.get('color_palette', 'Matplotlib')
        self.subplot_ann_visible  = {0: True}   # per-subplot annotation visibility
        self.subplot_equal_aspect = {0: False}  # per-subplot equal-scale (set_aspect('equal'))
        # fit_color / fit_linestyle / fit_linewidth removed in 2.0.0 —
        # fit curves are now styled via curve_styles like any other series.

        self.init_ui()

        # ── Dirty-state tracking (unsaved changes) ────────────────────────────
        self._is_dirty = False

        # ── Undo/redo stack ────────────────────────────────────────────────────
        self._undo_stack   = []   # list of (settings_dict, series_meta_dict, datasets_copy)
        self._redo_stack   = []
        self._undo_suspended = False  # set True while applying a snapshot
        self._MAX_UNDO = 50

        # ── Current open file (used as Save default name) ─────────────────────
        self._current_filepath = None

        # ── Keyboard shortcuts ────────────────────────────────────────────────
        QShortcut(QKeySequence('Ctrl+Z'), self).activated.connect(self._undo)
        QShortcut(QKeySequence('Ctrl+Y'), self).activated.connect(self._redo)
        QShortcut(QKeySequence('Ctrl+Shift+Z'), self).activated.connect(self._redo)

        # Undo/redo buttons start disabled
        self._update_undo_buttons()

        # ── Apply saved preferences to freshly-built widgets ──────────────────
        self._restore_prefs_from_settings()

        # Only enable LaTeX rendering if a LaTeX installation is present.
        # In a frozen .app bundle (or any machine without LaTeX) kpsewhich
        # does not exist, so usetex must stay False or every render call fails.
        if not getattr(__import__('sys'), 'frozen', False) and shutil.which('latex'):
            try:
                plt.rcParams['text.usetex'] = True
                plt.rcParams['text.latex.preamble'] = r'\usepackage{amsmath}\usepackage{amssymb}'
            except Exception:
                pass

        # ── Load last chart (or sample) once the event loop is running ─────────
        # Connect per-series option widgets AFTER all tab builders have run so
        # every widget attribute is guaranteed to exist.
        self._loading_series_options = False
        self._connect_series_option_signals()

        # Auto-select a series table row whenever one of its embedded cell widgets
        # (X/Y combos, type combo, subplot spin) gains keyboard focus.  Without this,
        # clicking directly on a cell widget bypasses the table's selection model, so
        # _save_series_options would still target the previously-selected row.
        QApplication.instance().focusChanged.connect(self._on_cell_widget_focused)

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._load_on_startup)

    # ═══════════════════════════════════════════════════════════════════════════
    # WINDOW TITLE
    # ═══════════════════════════════════════════════════════════════════════════
    def _update_window_title(self):
        """Set the title bar to 'plotviz <version>' or 'plotviz <version> - <stem>'."""
        from config._version import __version__
        fp = getattr(self, '_current_filepath', None)
        if fp:
            import os as _os
            stem = _os.path.splitext(_os.path.basename(fp))[0]
            self.setWindowTitle(f'plotviz {__version__} - {stem}')
        else:
            self.setWindowTitle(f'plotviz {__version__}')

    # ═══════════════════════════════════════════════════════════════════════════
    # STARTUP LOAD
    # ═══════════════════════════════════════════════════════════════════════════
    def _load_on_startup(self):
        """After the window is shown, silently load the last-used chart.
        If no recent file exists (first launch or cleared history) load a
        built-in sample chart so the canvas is never blank on first open.
        """
        import config.settings as _cfg
        recent = _cfg.get_recent_files()
        if recent:
            fp = recent[0]
            try:
                self._load_project_inner(fp, silent=True)
                self._current_filepath = fp
                self._update_window_title()
                return
            except Exception:
                pass  # File unreadable — fall through to sample

        self._load_sample_chart()

    def _load_sample_chart(self):
        """Populate a sample sine/cosine chart directly into the app state.
        Follows the same pattern as _reset_app so the canvas always renders.
        """
        import numpy as np

        # ── 1. Clear any existing state ───────────────────────────────────────
        self._current_filepath = None
        self._update_window_title()
        self._is_dirty = False
        if hasattr(self, '_undo_stack'):
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._update_undo_buttons()
        self.datasets.clear()
        self.curve_styles.clear()
        if hasattr(self.canvas, 'annotations'):
            self.canvas.annotations.clear()
        self._subplot_mosaic = None
        self.series_table.setRowCount(0)
        if hasattr(self, '_refresh_curve_select'):
            self._refresh_curve_select()

        # ── 2. Load sample data ───────────────────────────────────────────────
        x = np.linspace(0, 4 * np.pi, 60)
        self.datasets['x']     = x
        self.datasets['sin_x'] = np.sin(x)
        self.datasets['cos_x'] = np.cos(x)

        # ── 3. Apply default settings then override title / grid ──────────────
        sample_settings = self._default_settings()
        sample_settings.update({
            'title_show':    True,
            'title_text':    'Welcome to plotviz',
            'title_size':    14,
            'title_color':   '#222222',
            'grid_on':       True,
            'grid_color':    '#cccccc',
            'grid_linestyle': '-',
            'grid_linewidth': 0.8,
            'grid_alpha':    0.6,
        })

        self._undo_suspended = True
        self._applying_settings = True
        try:
            self._apply_settings(sample_settings)
        finally:
            self._applying_settings = False
            self._undo_suspended = False

        # ── 4. Populate combos then add series rows ───────────────────────────
        self.update_lists()
        self.on_subplot_layout_changed()

        # Add sin_x and cos_x series using the standard add-row mechanism
        for x_col, y_col, label in [
            ('x', 'sin_x', 'sin(x)'),
            ('x', 'cos_x', 'cos(x)'),
        ]:
            self._add_series_row()
            row = self.series_table.rowCount() - 1
            for col_idx, col_name in [(0, x_col), (1, y_col)]:
                cb = self.series_table.cellWidget(row, col_idx)
                if cb is not None:
                    i = cb.findText(col_name)
                    if i >= 0:
                        cb.blockSignals(True)
                        cb.setCurrentIndex(i)
                        cb.blockSignals(False)
            lbl_item = self.series_table.item(row, 2)
            if lbl_item is not None:
                lbl_item.setText(label)

        # ── 5. Draw ───────────────────────────────────────────────────────────
        self.update_preview()
        if hasattr(self, 'refresh_annotation_list'):
            self.refresh_annotation_list()
        self._notify_sns_explorer()

    # ═══════════════════════════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════════════════════
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._on_canvas_resized()

    def _on_canvas_resized(self):
        """Debounced redraw triggered by splitter moves or window resize."""
        if not hasattr(self, '_resize_timer'):
            from PyQt6.QtCore import QTimer
            self._resize_timer = QTimer(self)
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self.update_preview)
        self._resize_timer.start(80)   # 80 ms debounce

    # ── Seaborn Explorer ──────────────────────────────────────────────────────
    def _open_seaborn_explorer(self):
        """Open (or restore) the Seaborn Explorer window."""
        palette = [self._palette_color(i) for i in range(10)]
        if self._sns_explorer is None:
            self._sns_explorer = SeabornExplorer(
                datasets=self.datasets,
                palette=palette,
                parent=self,
            )
            self._sns_explorer.setWindowModality(Qt.WindowModality.NonModal)
        else:
            self._sns_explorer.refresh_datasets(self.datasets, palette)
        self._sns_explorer.show()
        self._sns_explorer.raise_()
        self._sns_explorer.activateWindow()

    def _notify_sns_explorer(self):
        """Called whenever datasets change so the explorer stays in sync."""
        if self._sns_explorer is not None and self._sns_explorer.isVisible():
            palette = [self._palette_color(i) for i in range(10)]
            self._sns_explorer.refresh_datasets(self.datasets, palette)
        if self._code_runner is not None and self._code_runner.isVisible():
            self._code_runner.refresh_datasets(self.datasets)

    # ── Python Code Runner ────────────────────────────────────────────────────
    def _open_code_runner(self):
        """Open (or restore) the Python Code Runner window."""
        if self._code_runner is None:
            self._code_runner = CodeRunnerDialog(
                datasets=self.datasets,
                parent=self,
            )
            self._code_runner.setWindowModality(Qt.WindowModality.NonModal)
        else:
            self._code_runner.refresh_datasets(self.datasets)
        self._code_runner.show()
        self._code_runner.raise_()
        self._code_runner.activateWindow()

    def _open_pvizx_in_code_runner(self, fp: str):
        """Open the Code Runner, load fp (.pvizx) into it, and run it."""
        self._open_code_runner()
        self._code_runner.load_pvizx(fp)

    def closeEvent(self, event):
        """Persist window state and prefs before closing."""
        geo = self.geometry()
        settings.set('window_geometry', [geo.x(), geo.y(), geo.width(), geo.height()])
        settings.set('window_maximised', self.isMaximized())
        settings.set('color_palette', getattr(self, '_color_palette', 'Matplotlib'))
        settings.set('theme', self.colour_scheme_combo.currentText()
                     if hasattr(self, 'colour_scheme_combo') else 'System')
        if hasattr(self, '_export_fmt_combo'):
            settings.set('export_format', self._export_fmt_combo.currentText())
        if hasattr(self, 'dpi_spin'):
            settings.set('export_dpi', self.dpi_spin.value())
        if hasattr(self, 'fig_preset_combo'):
            settings.set('fig_preset', self.fig_preset_combo.currentText())
        # Persist any custom palettes to settings
        settings.set('custom_palettes', dict(_CUSTOM_PALETTES))
        event.accept()

    def _restore_prefs_from_settings(self):
        """Apply persisted preferences to UI widgets after init_ui() has run."""
        # Theme
        theme = settings.get('theme') or 'System'
        idx = self.colour_scheme_combo.findText(theme)
        if idx >= 0:
            self.colour_scheme_combo.blockSignals(True)
            self.colour_scheme_combo.setCurrentIndex(idx)
            self.colour_scheme_combo.blockSignals(False)
        self._apply_colour_scheme(theme)

        # Colour palette
        pal = settings.get('color_palette') or 'Matplotlib'
        # Register any saved custom palettes first
        custom = settings.get('custom_palettes') or {}
        if custom:
            for name, colors in custom.items():
                add_custom_palette(name, colors)
                if self.palette_combo.findText(name) < 0:
                    self.palette_combo.addItem(name)
        pal_idx = self.palette_combo.findText(pal)
        if pal_idx >= 0:
            self.palette_combo.blockSignals(True)
            self.palette_combo.setCurrentIndex(pal_idx)
            self.palette_combo.blockSignals(False)
        self._color_palette = pal
        self._refresh_palette_swatches()

        # Export format + DPI
        fmt = settings.get('export_format') or 'PNG'
        fmt_idx = self._export_fmt_combo.findText(fmt)
        if fmt_idx >= 0:
            self._export_fmt_combo.setCurrentIndex(fmt_idx)
        self.dpi_spin.setValue(int(settings.get('export_dpi') or 300))

        # Figure size preset
        fig_preset = settings.get('fig_preset') or ''
        if fig_preset:
            fp_idx = self.fig_preset_combo.findText(fig_preset)
            if fp_idx >= 0:
                self.fig_preset_combo.blockSignals(True)
                self.fig_preset_combo.setCurrentIndex(fp_idx)
                self.fig_preset_combo.blockSignals(False)

        # Populate recent files list
        self._rebuild_recent_files_ui()

    # ═══════════════════════════════════════════════════════════════════════════
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        self.tabs = QTabWidget()
        self.create_file_tab()
        self.create_style_tab()      # figure size, margins, colours, grid
        self.create_data_tab()       # series table + chart-type options
        self.create_series_tab()     # per-curve style
        self.create_axes_tab()       # per-subplot selector + titles, labels, limits, legend
        self.create_annotations_tab()
        self.create_advanced_tab()

        # ── Menu bar — File ───────────────────────────────────────────────────
        from PyQt6.QtWidgets import QMenuBar
        from PyQt6.QtGui import QAction
        menubar = self.menuBar()

        file_menu = menubar.addMenu('File')

        def _go_chart_tab():
            self.tabs.setCurrentIndex(0)   # Chart / File tab

        def _go_data_tab():
            self.tabs.setCurrentIndex(2)   # Data tab

        # ── New ───────────────────────────────────────────────────────────────
        act_new = QAction('New Plot', self)
        act_new.setShortcut('Ctrl+N')
        act_new.triggered.connect(lambda: (_go_chart_tab(), self._reset_app()))
        file_menu.addAction(act_new)

        # ── Open / Load ───────────────────────────────────────────────────────
        file_menu.addSeparator()

        act_open = QAction('Open Chart (.pviz)…', self)
        act_open.setShortcut('Ctrl+O')
        act_open.triggered.connect(lambda: (_go_chart_tab(), self._load_project()))
        file_menu.addAction(act_open)

        act_open_tpl = QAction('Load Template (.pvizt)…', self)
        act_open_tpl.triggered.connect(lambda: (_go_chart_tab(), self._load_template()))
        file_menu.addAction(act_open_tpl)

        act_load_pal = QAction('Load Palette (.pvizp)…', self)
        act_load_pal.triggered.connect(
            lambda: (_go_chart_tab(), self._import_palette_bundle()))
        file_menu.addAction(act_load_pal)

        act_load_scheme = QAction('Load Scheme (.pvizc)…', self)
        act_load_scheme.triggered.connect(
            lambda: (_go_chart_tab(), self._load_color_scheme()))
        file_menu.addAction(act_load_scheme)

        # ── Load Data ─────────────────────────────────────────────────────────
        file_menu.addSeparator()

        act_load_data = QAction('Load Data…', self)
        act_load_data.setShortcut('Ctrl+L')
        act_load_data.triggered.connect(lambda: (_go_data_tab(), self.load_data()))
        file_menu.addAction(act_load_data)

        # ── Save ──────────────────────────────────────────────────────────────
        file_menu.addSeparator()

        act_save = QAction('Save Chart (.pviz)…', self)
        act_save.setShortcut('Ctrl+S')
        act_save.triggered.connect(lambda: (_go_chart_tab(), self._save_project()))
        file_menu.addAction(act_save)

        act_save_tpl = QAction('Save Template (.pvizt)…', self)
        act_save_tpl.triggered.connect(lambda: (_go_chart_tab(), self._save_template()))
        file_menu.addAction(act_save_tpl)

        act_save_pal = QAction('Save Palette (.pvizp)…', self)
        act_save_pal.triggered.connect(
            lambda: (_go_chart_tab(), self._export_palette_bundle()))
        file_menu.addAction(act_save_pal)

        act_save_scheme = QAction('Save Scheme (.pvizc)…', self)
        act_save_scheme.triggered.connect(
            lambda: (_go_chart_tab(), self._save_color_scheme()))
        file_menu.addAction(act_save_scheme)

        # ── Export ────────────────────────────────────────────────────────────
        file_menu.addSeparator()

        act_export_img = QAction('Export Image…', self)
        act_export_img.setShortcut('Ctrl+E')
        act_export_img.triggered.connect(
            lambda: (_go_chart_tab(),
                     self.export_chart(self._export_fmt_combo.currentText().lower())))
        file_menu.addAction(act_export_img)

        act_export_py = QAction('Export Python Bundle (.pvizx)…', self)
        act_export_py.setShortcut('Ctrl+Shift+E')
        act_export_py.triggered.connect(
            lambda: (_go_chart_tab(), self._export_python_bundle()))
        file_menu.addAction(act_export_py)

        self._file_menu = file_menu

        # ── Menu bar — View ───────────────────────────────────────────────────
        view_menu = menubar.addMenu('View')
        for i in range(self.tabs.count()):
            name = self.tabs.tabText(i)
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(i == 0)
            action.triggered.connect(lambda checked, idx=i: self.tabs.setCurrentIndex(idx))
            view_menu.addAction(action)
            # Keep checkmarks in sync when tab changes
            self.tabs.currentChanged.connect(
                lambda cur, a=action, idx=i: a.setChecked(cur == idx))
        self._view_menu = view_menu

        # ── Tools menu ────────────────────────────────────────────────────────
        from PyQt6.QtGui import QAction
        tools_menu = menubar.addMenu('Tools')
        sns_action = QAction('Seaborn Explorer…', self)
        sns_action.setShortcut('Ctrl+Shift+S')
        sns_action.setStatusTip('Open the Seaborn statistical chart explorer')
        sns_action.triggered.connect(self._open_seaborn_explorer)
        tools_menu.addAction(sns_action)

        code_action = QAction('Python Code Runner…', self)
        code_action.setShortcut('Ctrl+Shift+P')
        code_action.setStatusTip('Write or load Python code to draw a matplotlib/seaborn chart')
        code_action.triggered.connect(self._open_code_runner)
        tools_menu.addAction(code_action)

        self._tools_menu = tools_menu
        self._sns_explorer  = None   # lazily created
        self._code_runner   = None   # lazily created

        # ── Configurations menu ───────────────────────────────────────────────
        config_menu = menubar.addMenu('Configurations')

        _prefs_label = 'Preferences…' if sys.platform == 'darwin' else 'Settings…'
        act_prefs = QAction(_prefs_label, self)
        act_prefs.setShortcut('Ctrl+,' if sys.platform == 'darwin' else 'Ctrl+Alt+S')
        act_prefs.setStatusTip('Open application settings / preferences')
        act_prefs.triggered.connect(self._open_app_settings_dialog)
        config_menu.addAction(act_prefs)

        config_menu.addSeparator()

        act_about_cfg = QAction('About plotviz…', self)
        act_about_cfg.setStatusTip('About this application')
        act_about_cfg.triggered.connect(self._show_about)
        config_menu.addAction(act_about_cfg)

        self._config_menu = config_menu

        # ── macOS application menu (plotviz / python) ─────────────────────────
        # On macOS Qt maps QMenu with the same name as the app to the system
        # application menu that appears left of "File". We add Preferences and
        # About there so they appear in the native location.
        if sys.platform == 'darwin':
            app_menu = menubar.addMenu('plotviz')

            act_about_app = QAction('About plotviz', self)
            act_about_app.triggered.connect(self._show_about)
            app_menu.addAction(act_about_app)

            app_menu.addSeparator()

            act_prefs_app = QAction('Preferences…', self)
            act_prefs_app.setShortcut('Ctrl+,')
            act_prefs_app.triggered.connect(self._open_app_settings_dialog)
            app_menu.addAction(act_prefs_app)

        # Tooltips
        for i, tip in enumerate([
            'Chart — open/save/export, subplot layout, colour palette',
            'Style — figure size, margins, colours, grid',
            'Data — load datasets, series table, chart type options',
            'Series — per-curve line style, colour, marker and curve fitting',
            'Axes — per-subplot titles, labels, axis limits and legend',
            'Annotations — subplot title, legend, text/arrow/image annotations',
            'Advanced — function generator and manual data table',
        ]):
            self.tabs.setTabToolTip(i, tip)

        self.canvas = CanvasPlotter()
        self.canvas.main_window = self
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        cv_layout = QVBoxLayout()
        cv_layout.addWidget(self.toolbar)
        cv_layout.addWidget(self.canvas)
        cv_widget = QWidget()
        cv_widget.setLayout(cv_layout)

        # ── Left panel: top action bar + tabs ─────────────────────────────────
        left_panel = QWidget()
        left_vbox = QVBoxLayout(left_panel)
        left_vbox.setContentsMargins(0, 0, 0, 0)
        left_vbox.setSpacing(0)

        # Top action bar (above tabs): New Plot | Undo | Redo
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(6, 4, 6, 4)
        top_bar_layout.setSpacing(4)

        btn_new = QPushButton('＋ New Plot')
        btn_new.setToolTip('Start a new blank plot (Ctrl+N)')
        btn_new.clicked.connect(lambda: (self.tabs.setCurrentIndex(0), self._reset_app()))
        top_bar_layout.addWidget(btn_new)

        # ── Global subplot selector (hidden when n == 1) ──────────────────────
        self._global_sp_container = QWidget()
        _gsp_lay = QHBoxLayout(self._global_sp_container)
        _gsp_lay.setContentsMargins(8, 0, 0, 0); _gsp_lay.setSpacing(4)
        _gsp_lay.addWidget(QLabel('Subplot:'))
        self.global_sp_active = QComboBox()
        self.global_sp_active.addItem('Subplot 1')
        self.global_sp_active.setMinimumWidth(100)
        self.global_sp_active.setToolTip('Active subplot — affects Data, Axes, Series and Annotation tabs')
        self.global_sp_active.currentIndexChanged.connect(self._on_global_sp_changed)
        _gsp_lay.addWidget(self.global_sp_active)
        self._global_sp_container.setVisible(False)
        top_bar_layout.addWidget(self._global_sp_container)

        top_bar_layout.addStretch()

        btn_undo = QPushButton('↩ Undo')
        btn_undo.setToolTip('Undo last change (Ctrl+Z)')
        btn_undo.clicked.connect(self._undo)
        btn_undo.setFixedWidth(72)
        top_bar_layout.addWidget(btn_undo)
        self._btn_undo = btn_undo

        btn_redo = QPushButton('↪ Redo')
        btn_redo.setToolTip('Redo (Ctrl+Y)')
        btn_redo.clicked.connect(self._redo)
        btn_redo.setFixedWidth(72)
        top_bar_layout.addWidget(btn_redo)
        self._btn_redo = btn_redo

        # Separator line below top bar
        top_sep = QFrame(); top_sep.setFrameShape(QFrame.Shape.HLine)
        top_sep.setFrameShadow(QFrame.Shadow.Sunken)

        left_vbox.addWidget(top_bar)
        left_vbox.addWidget(top_sep)
        left_vbox.addWidget(self.tabs)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(cv_widget)
        splitter.setSizes([520, 1480])
        splitter.splitterMoved.connect(lambda: self._on_canvas_resized())
        self._main_splitter = splitter
        main_layout.addWidget(splitter)

        self._sync_ann_style()
        # Draw the initial blank layout so the canvas is never empty on startup
        self.update_preview()

    # ─── File tab ─────────────────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════════
    # DARK MODE
    # ═══════════════════════════════════════════════════════════════════════════
    def _apply_colour_scheme(self, scheme: str = None):
        """Apply Light / Dark / System colour scheme using Qt's native API."""
        app = QApplication.instance()

        if scheme is None:
            scheme = getattr(self, 'colour_scheme_combo',
                             None) and self.colour_scheme_combo.currentText() or 'System'

        self._colour_mode = scheme.lower()
        settings.set('theme', scheme)

        try:
            # Qt 6.5+ native path — lets the platform handle the palette
            hints = app.styleHints()
            mapping = {
                'Light':  Qt.ColorScheme.Light,
                'Dark':   Qt.ColorScheme.Dark,
                'System': Qt.ColorScheme.Unknown,
            }
            hints.setColorScheme(mapping.get(scheme, Qt.ColorScheme.Unknown))
        except AttributeError:
            # Fallback for Qt < 6.5: manual palette
            from PyQt6.QtGui import QColor, QPalette
            if scheme == 'Dark':
                p = QPalette()
                p.setColor(QPalette.ColorRole.Window,          QColor(30, 30, 30))
                p.setColor(QPalette.ColorRole.WindowText,      QColor(220, 220, 220))
                p.setColor(QPalette.ColorRole.Base,            QColor(45, 45, 45))
                p.setColor(QPalette.ColorRole.AlternateBase,   QColor(55, 55, 55))
                p.setColor(QPalette.ColorRole.Text,            QColor(220, 220, 220))
                p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 255, 255))
                p.setColor(QPalette.ColorRole.Button,          QColor(55, 55, 55))
                p.setColor(QPalette.ColorRole.ButtonText,      QColor(220, 220, 220))
                p.setColor(QPalette.ColorRole.Highlight,       QColor(42, 130, 218))
                p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
                p.setColor(QPalette.ColorRole.Link,            QColor(42, 130, 218))
                p.setColor(QPalette.ColorRole.Mid,             QColor(70, 70, 70))
                p.setColor(QPalette.ColorRole.Shadow,          QColor(20, 20, 20))
                p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(45, 45, 45))
                p.setColor(QPalette.ColorRole.ToolTipText,     QColor(220, 220, 220))
                app.setPalette(p)
            elif scheme == 'Light':
                app.setPalette(QPalette())
            else:
                app.setPalette(app.style().standardPalette())

        self.update_preview()

    # ═══════════════════════════════════════════════════════════════════════════
    # CHART TYPE VISIBILITY
    # ═══════════════════════════════════════════════════════════════════════════
    def _update_option_group_visibility(self, ct):
        """Show/hide chart-type option groups (Data tab) and series-type option
        groups (Series tab) for the given chart type."""
        if not hasattr(self, 'hist_group'):
            return

        # ── Data tab: chart-mode groups ───────────────────────────────────────
        data_vis = {
            self.bar_group:          ct == 'Bar',
            self.hist_group:         ct == 'Histogram',
            self.heat_group:         ct in ('Heatmap', 'Contour', '3D Surface'),
            self.pie_group:          ct == 'Pie',
            self.area_group:         ct == 'Area',
            self.fill_between_group: ct == 'Fill Between',
            self.violin_group:       ct == 'Violin',
            self.boxplot_group:      ct == 'Boxplot',
            self.step_group:         ct == 'Step',
            self.stem_group:         ct == 'Stem',
            self.waterfall_group:    ct == 'Waterfall',
            self.hist2d_group:       ct == 'Hist2D',
            self.hexbin_group:       ct == 'Hexbin',
            self.radar_group:        ct == 'Radar',
            self.ecdf_group:         ct == 'ECDF',
            self.quiver_group:       ct == 'Quiver',
            self.barbs_group:        ct == 'Barbs',
            self.streamplot_group:   ct == 'Streamplot',
        }
        for grp, show in data_vis.items():
            grp.setVisible(show)

        # ── Series tab: per-series type groups ────────────────────────────────
        for attr, show in [
            ('st_line_group',         ct == 'Line'),
            ('st_scatter_group',      ct == 'Scatter'),
            ('st_bar_group',          ct == 'Bar'),
            ('st_hist_group',         ct == 'Histogram'),
            ('st_err_group',          ct == 'Errorbar'),
            ('st_area_group',         ct == 'Area'),
            ('st_fill_between_group', ct == 'Fill Between'),
            ('st_step_group',         ct == 'Step'),
            ('st_bubble_group',       ct == 'Bubble'),
            ('st_polar_group',        ct == 'Polar'),
            ('st_radar_group',        ct == 'Radar'),
            ('st_ecdf_group',         ct == 'ECDF'),
        ]:
            grp = getattr(self, attr, None)
            if grp is not None:
                grp.setVisible(show)

        # ── Column-picker visibility ───────────────────────────────────────────
        if hasattr(self, '_combo_z_widget'):
            self._combo_z_widget.setVisible(ct in ('Heatmap', 'Contour', '3D Surface'))
        if hasattr(self, '_combo_err_widget'):
            self._combo_err_widget.setVisible(ct == 'Errorbar')
        if hasattr(self, '_combo_fill_y2_widget'):
            self._combo_fill_y2_widget.setVisible(ct == 'Fill Between')

    def _on_chart_type_changed(self, ct):
        """Hidden chart_type_combo changed — update subplot_chart_types and option groups.
        No longer pushes to series table rows; that is now _on_plot_mode_changed's job.
        """
        from ui.tab_builders import WHOLE_CHART_TYPES
        if hasattr(self, 'series_sp_active'):
            n = self.subplot_rows * self.subplot_cols
            active_sp = (self.series_sp_active.currentIndex() + 1) if n > 1 else 1
            active_idx = active_sp - 1
            if ct in WHOLE_CHART_TYPES:
                self.subplot_chart_types[active_idx] = ct
            else:
                if self.subplot_chart_types.get(active_idx) in WHOLE_CHART_TYPES:
                    self.subplot_chart_types[active_idx] = ct
        self._update_option_group_visibility(ct)
        if hasattr(self, 'datasets'):
            self.update_preview()

    def _on_plot_mode_changed(self, mode):
        """Plot Mode combo changed — repopulate type cells in the active subplot's rows
        to only contain the types that belong to this mode, then update option groups.
        """
        from ui.tab_builders import PLOT_MODE_GROUPS, WHOLE_CHART_TYPES
        allowed = PLOT_MODE_GROUPS.get(mode, [])
        if not allowed:
            return
        n = self.subplot_rows * self.subplot_cols
        active_sp = (self.series_sp_active.currentIndex() + 1) if (n > 1 and hasattr(self, 'series_sp_active')) else 1
        active_idx = active_sp - 1
        # Persist the mode for this subplot
        self.subplot_plot_modes[active_idx] = mode
        # Repopulate every visible type combo for the active subplot
        if hasattr(self, 'series_table'):
            for row in range(self.series_table.rowCount()):
                spin = self.series_table.cellWidget(row, 4)
                row_sp = spin.value() if (spin and n > 1) else 1
                if row_sp != active_sp:
                    continue
                type_cb = self.series_table.cellWidget(row, 3)
                if type_cb:
                    current = type_cb.currentText()
                    type_cb.blockSignals(True)
                    type_cb.clear()
                    type_cb.addItems(allowed)
                    new_idx = type_cb.findText(current) if current in allowed else 0
                    type_cb.setCurrentIndex(new_idx)
                    type_cb.blockSignals(False)
        first_type = allowed[0]
        # Sync the hidden chart_type_combo
        if hasattr(self, 'chart_type_combo'):
            self.chart_type_combo.blockSignals(True)
            i = self.chart_type_combo.findText(first_type)
            if i >= 0:
                self.chart_type_combo.setCurrentIndex(i)
            self.chart_type_combo.blockSignals(False)
        # Update subplot_chart_types for whole-chart projections
        if first_type in WHOLE_CHART_TYPES:
            self.subplot_chart_types[active_idx] = first_type
        else:
            if self.subplot_chart_types.get(active_idx) in WHOLE_CHART_TYPES:
                self.subplot_chart_types[active_idx] = first_type
        self._update_option_group_visibility(first_type)
        if hasattr(self, 'datasets'):
            self.update_preview()

    # ── Per-subplot chart-option fields ──────────────────────────────────────
    # Each entry: (widget_attr, storage_key, default_value, widget_kind)
    # widget_kind: 'spin' | 'dbl' | 'check' | 'combo' | 'color'
    # These are the Data-tab chart-level option groups; each subplot stores its
    # own copy in self.subplot_chart_opts[subplot_idx].
    CHART_OPT_FIELDS = [
        # Bar
        ('bar_stacked',         'bar_stacked',         False,     'check'),
        ('bar_horizontal',      'bar_horizontal',       False,     'check'),
        # Histogram
        ('hist_bins',           'hist_bins',            20,        'spin'),
        ('hist_density',        'hist_density',         False,     'check'),
        ('hist_cumulative',     'hist_cumulative',      False,     'check'),
        ('hist_histtype',       'hist_histtype',        'bar',     'combo'),
        ('hist_orientation',    'hist_orientation',     'vertical','combo'),
        # Heatmap / Contour / 3D
        ('cmap_combo',          'cmap',                 'viridis', 'combo'),
        ('contour_levels',      'contour_levels',       10,        'spin'),
        ('heat_alpha',          'heat_alpha',           1.0,       'dbl'),
        ('heat_interpolation',  'heat_interpolation',   'nearest', 'combo'),
        ('heat_colorbar',       'heat_colorbar',        True,      'check'),
        ('heat_filled_contour', 'heat_filled_contour',  True,      'check'),
        ('heat_contour_lines',  'heat_contour_lines',   True,      'check'),
        ('surf_stride',         'surf_stride',          1,         'spin'),
        ('surf_wireframe',      'surf_wireframe',       False,     'check'),
        # Pie
        ('pie_autopct',         'pie_autopct',          True,      'check'),
        ('pie_shadow',          'pie_shadow',           False,     'check'),
        ('pie_donut',           'pie_donut',            False,     'check'),
        ('pie_explode_first',   'pie_explode_first',    False,     'check'),
        ('pie_startangle',      'pie_startangle',       90.0,      'dbl'),
        ('pie_labeldistance',   'pie_labeldistance',    1.1,       'dbl'),
        ('pie_pctdistance',     'pie_pctdistance',      0.6,       'dbl'),
        # Area
        ('area_stacked',        'area_stacked',         False,     'check'),
        ('area_baseline',       'area_baseline',        0.0,       'dbl'),
        # Violin
        ('violin_show_means',   'violin_show_means',    True,      'check'),
        ('violin_show_medians', 'violin_show_medians',  True,      'check'),
        ('violin_show_extrema', 'violin_show_extrema',  False,     'check'),
        ('violin_points',       'violin_points',        '100',     'combo'),
        ('violin_bw',           'violin_bw',            'scott',   'combo'),
        ('violin_vert',         'violin_vert',          True,      'check'),
        # Boxplot
        ('box_show_means',      'box_show_means',       False,     'check'),
        ('box_show_medians',    'box_show_medians',     True,      'check'),
        ('box_notch',           'box_notch',            False,     'check'),
        ('box_showfliers',      'box_showfliers',       True,      'check'),
        ('box_vert',            'box_vert',             True,      'check'),
        ('box_whis',            'box_whis',             1.5,       'dbl'),
        ('box_alpha',           'box_alpha',            0.7,       'dbl'),
        # Step
        ('step_where',          'step_where',           'pre',     'combo'),
        # Stem
        ('stem_baseline',       'stem_baseline',        0.0,       'dbl'),
        # Waterfall
        ('waterfall_connector', 'waterfall_connector',  True,      'check'),
        ('waterfall_width',     'waterfall_width',      0.6,       'dbl'),
        ('waterfall_alpha',     'waterfall_alpha',      1.0,       'dbl'),
        ('waterfall_pos_color', 'waterfall_pos_color',  '#2ecc71', 'color'),
        ('waterfall_neg_color', 'waterfall_neg_color',  '#e74c3c', 'color'),
        # Hist2D
        ('hist2d_bins_x',       'hist2d_bins_x',        20,        'spin'),
        ('hist2d_bins_y',       'hist2d_bins_y',        20,        'spin'),
        ('hist2d_alpha',        'hist2d_alpha',         1.0,       'dbl'),
        ('hist2d_cmap_combo',   'hist2d_cmap',          'viridis', 'combo'),
        ('hist2d_colorbar',     'hist2d_colorbar',      True,      'check'),
        ('hist2d_log',          'hist2d_log',           False,     'check'),
        # Hexbin
        ('hexbin_gridsize',     'hexbin_gridsize',      20,        'spin'),
        ('hexbin_alpha',        'hexbin_alpha',         1.0,       'dbl'),
        ('hexbin_cmap_combo',   'hexbin_cmap',          'viridis', 'combo'),
        ('hexbin_colorbar',     'hexbin_colorbar',      True,      'check'),
        ('hexbin_log',          'hexbin_log',           False,     'check'),
        # Radar
        ('radar_gridlevels',    'radar_gridlevels',     5,         'spin'),
        # ECDF
        ('ecdf_complementary',  'ecdf_complementary',   False,     'check'),
        # Quiver
        ('quiver_scale',        'quiver_scale',         1.0,       'dbl'),
        ('quiver_width',        'quiver_width',         0.005,     'dbl'),
        ('quiver_color_by_mag', 'quiver_color_by_mag',  False,     'check'),
        ('quiver_cmap_combo',   'quiver_cmap',          'viridis', 'combo'),
        # Barbs
        ('barbs_length',        'barbs_length',         7.0,       'dbl'),
        ('barbs_pivot_combo',   'barbs_pivot',          'tip',     'combo'),
        ('barbs_alpha',         'barbs_alpha',          0.85,      'dbl'),
        ('barbs_color_by_mag',  'barbs_color_by_mag',   False,     'check'),
        ('barbs_cmap_combo',    'barbs_cmap',           'viridis', 'combo'),
        # Streamplot
        ('stream_density',      'stream_density',       1.0,       'dbl'),
        ('stream_arrowsize',    'stream_arrowsize',     1.0,       'dbl'),
        ('stream_linewidth',    'stream_linewidth',     1.5,       'dbl'),
        ('stream_color_by_mag', 'stream_color_by_mag',  False,     'check'),
        ('stream_cmap_combo',   'stream_cmap',          'viridis', 'combo'),
    ]

    def _default_chart_opts(self):
        """Return a dict of chart option defaults for a fresh subplot."""
        return {key: default for _, key, default, _ in self.CHART_OPT_FIELDS}

    def _save_chart_opts(self, idx):
        """Read all chart option widgets and persist to subplot_chart_opts[idx]."""
        opts = self.subplot_chart_opts.setdefault(idx, self._default_chart_opts())
        for attr, key, default, kind in self.CHART_OPT_FIELDS:
            w = getattr(self, attr, None)
            if w is None:
                continue
            if kind == 'spin':
                opts[key] = w.value()
            elif kind == 'dbl':
                opts[key] = w.value()
            elif kind == 'check':
                opts[key] = w.isChecked()
            elif kind == 'combo':
                opts[key] = w.currentText()
            elif kind == 'color':
                opts[key] = getattr(self, attr, default)

    def _load_chart_opts(self, idx):
        """Load subplot_chart_opts[idx] values into the chart option widgets."""
        opts = self.subplot_chart_opts.get(idx, self._default_chart_opts())
        for attr, key, default, kind in self.CHART_OPT_FIELDS:
            w = getattr(self, attr, None)
            val = opts.get(key, default)
            if w is None:
                if kind == 'color':
                    setattr(self, attr, val)
                continue
            if kind == 'spin':
                w.blockSignals(True); w.setValue(int(val)); w.blockSignals(False)
            elif kind == 'dbl':
                w.blockSignals(True); w.setValue(float(val)); w.blockSignals(False)
            elif kind == 'check':
                w.blockSignals(True); w.setChecked(bool(val)); w.blockSignals(False)
            elif kind == 'combo':
                w.blockSignals(True)
                i = w.findText(str(val))
                if i >= 0: w.setCurrentIndex(i)
                w.blockSignals(False)
            elif kind == 'color':
                setattr(self, attr, val)
                btn = getattr(self, attr + '_btn', None)
                if btn: btn.setStyleSheet(f'background-color:{val};border:1px solid #888;')

    # ── Per-series option fields ──────────────────────────────────────────────
    # Each entry: (widget_attr, storage_key, default_value, widget_kind)
    # widget_kind: 'spin' | 'dbl' | 'check' | 'combo'
    # Only per-series visual params live here (Series tab groups).
    # Chart-mode params (bar_stacked, hist_bins, etc.) are now per-subplot
    # via subplot_chart_opts / _save_chart_opts / _load_chart_opts.
    _SERIES_OPTION_FIELDS = [
        # Line (per-series visual) — linestyle/lw/marker/markersize from Per-Curve
        ('line_drawstyle',          'line_drawstyle',   'default', 'combo'),
        # Scatter (per-series visual) — marker from Per-Curve
        ('scatter_size',            'sc_size',          20,        'spin'),
        ('scatter_alpha',           'sc_alpha',         0.7,       'dbl'),
        ('scatter_edgecolor',       'sc_edgecolor',     'none',    'combo'),
        ('scatter_lw',              'sc_lw',            0.5,       'dbl'),
        ('scatter_colorby_check',   'sc_colorby',       False,     'check'),
        ('scatter_cmap_combo',      'sc_cmap',          'viridis', 'combo'),
        # Bar (per-series visual only; stacked/horizontal saved at chart level)
        ('bar_width',               'bar_width',        0.8,       'dbl'),
        ('bar_alpha',               'bar_alpha',        1.0,       'dbl'),
        ('bar_edgecolor',           'bar_edgecolor',    'none',    'combo'),
        ('bar_edge_lw',             'bar_edge_lw',      0.5,       'dbl'),
        ('bar_colorbyval',          'bar_colorbyval',   False,     'check'),
        # Histogram (per-series visual only; bins/density/etc. saved at chart level)
        ('hist_alpha',              'hist_alpha',       0.7,       'dbl'),
        ('hist_edgecolor',          'hist_edgecolor',   'white',   'combo'),
        # Errorbar (per-series visual) — marker/linewidth from Per-Curve
        ('err_capsize',             'err_capsize',      4,         'spin'),
        ('err_capthick',            'err_capthick',     1.5,       'dbl'),
        ('err_elinewidth',          'err_elinewidth',   1.5,       'dbl'),
        ('err_barsabove',           'err_barsabove',    False,     'check'),
        # Area (per-series visual only; stacked/baseline saved at chart level)
        ('area_alpha',              'area_alpha',       0.4,       'dbl'),
        ('area_lw',                 'area_lw',          0.8,       'dbl'),
        ('area_showline',           'area_showline',    True,      'check'),
        # Fill Between (per-series visual; Y2 column is saved separately via _save_fill_y2)
        ('fill_between_alpha',      'fill_between_alpha',   0.4,   'dbl'),
        ('fill_between_lw',         'fill_between_lw',      0.8,   'dbl'),
        ('fill_between_showline',   'fill_between_showline', True,  'check'),
        # Step (per-series visual only; where saved at chart level) — lw from Per-Curve
        ('step_fill',               'step_fill',        False,     'check'),
        ('step_fill_alpha',         'step_fill_alpha',  0.2,       'dbl'),
        # Stem — marker/lw/markersize all from Per-Curve; no type-specific opts
        # Bubble (per-series visual) — marker from Per-Curve
        ('bubble_scale',            'bubble_scale',     200.0,     'dbl'),
        ('bubble_alpha',            'bubble_alpha',     0.6,       'dbl'),
        ('bubble_edgecolor',        'bubble_edgecolor', 'none',    'combo'),
        # Polar (per-series visual) — linestyle/lw/marker from Per-Curve
        ('polar_fill',              'pol_fill',         False,     'check'),
        ('polar_fill_alpha',        'pol_fill_alpha',   0.2,       'dbl'),
        # Radar (per-series visual only; gridlevels saved at chart level) — lw from Per-Curve
        ('radar_fill',              'rad_fill',         True,      'check'),
        ('radar_fill_alpha',        'rad_fill_alpha',   0.25,      'dbl'),
        # ECDF (per-series visual only; complementary saved at chart level) — lw from Per-Curve
        ('ecdf_markers',            'ecdf_markers',     False,     'check'),
        ('ecdf_alpha',              'ecdf_alpha',       1.0,       'dbl'),
        # Quiver params are chart-mode — saved at chart level, not per-series
    ]

    def _series_opts_key(self, row):
        """Return the curve_styles label for a series table row, or None."""
        lbl_item = self.series_table.item(row, 2)
        if lbl_item and lbl_item.text():
            return lbl_item.text()
        ycb = self.series_table.cellWidget(row, 1)
        return ycb.currentText() if ycb else None

    def _save_series_options(self):
        """Persist the current option-group widget values into curve_styles for
        whichever series is currently selected in the Per-Curve combo (curve_select).
        The Series tab is self-contained — no dependency on the Data tab table.

        IMPORTANT: always ends with update_preview() so the chart reflects the
        new values.  Some option widgets (e.g. radar_fill) also have a direct
        stateChanged→update_preview connection that fires *before* this method
        (Qt delivers signals in connection order).  Without the call here the
        chart would render with the old stored value and only update on the next
        external event, making the checkbox appear inverted."""
        if getattr(self, '_loading_series_options', False):
            return
        cs = getattr(self, 'curve_select', None)
        label = cs.currentText() if cs else None
        if not label:
            return
        entry = self.curve_styles.setdefault(label, {})
        opts = entry.setdefault('opts', {})
        for attr, key, _default, kind in self._SERIES_OPTION_FIELDS:
            w = getattr(self, attr, None)
            if w is None:
                continue
            if kind == 'spin':
                opts[key] = w.value()
            elif kind == 'dbl':
                opts[key] = w.value()
            elif kind == 'check':
                opts[key] = w.isChecked()
            elif kind == 'combo':
                opts[key] = w.currentText()
            elif kind == 'color':
                # w is the hex string stored directly on self (not a Qt widget)
                opts[key] = w if isinstance(w, str) else _default
        # Redraw *after* saving so the chart always reflects the current widget
        # state, not the stale stored value from the earlier direct signal.
        if hasattr(self, 'datasets'):
            self.update_preview()

    def _load_series_options_by_label(self, label):
        """Push stored per-series option values into the option-group widgets for
        the given series label.  The Series tab calls this directly; the Data tab
        wrapper (_load_series_options) resolves a row to a label first."""
        entry = self.curve_styles.setdefault(label, {}) if label else {}
        stored = entry.get('opts', {}) if label else {}
        opts = {key: stored.get(key, default)
                for _, key, default, _ in self._SERIES_OPTION_FIELDS}
        if label:
            entry['opts'] = opts  # persist so plot_engine always finds full opts

        self._loading_series_options = True
        try:
            for attr, key, default, kind in self._SERIES_OPTION_FIELDS:
                w = getattr(self, attr, None)
                if w is None:
                    continue
                val = opts.get(key, default)
                if kind == 'color':
                    setattr(self, attr, val)
                    btn = getattr(self, attr + '_btn', None)
                    if btn:
                        btn.setStyleSheet(f'background-color:{val};border:1px solid #888;')
                    continue
                w.blockSignals(True)
                try:
                    if kind in ('spin', 'dbl'):
                        w.setValue(val)
                    elif kind == 'check':
                        w.setChecked(bool(val))
                    elif kind == 'combo':
                        i = w.findText(str(val))
                        if i >= 0:
                            w.setCurrentIndex(i)
                finally:
                    w.blockSignals(False)
        finally:
            self._loading_series_options = False

    def _load_series_options(self, row):
        """Row-based wrapper — resolves label from the series table then delegates."""
        label = self._series_opts_key(row)
        self._load_series_options_by_label(label)

    def _connect_series_option_signals(self):
        """Connect every option-group widget to _save_series_options so that any
        change is immediately persisted to the selected series.  Called once after
        all tab builders have run (end of __init__)."""
        for attr, _key, _default, kind in self._SERIES_OPTION_FIELDS:
            w = getattr(self, attr, None)
            if w is None:
                continue
            if kind in ('spin', 'dbl'):
                w.valueChanged.connect(self._save_series_options)
            elif kind == 'check':
                w.stateChanged.connect(self._save_series_options)
            elif kind == 'combo':
                w.currentTextChanged.connect(self._save_series_options)
            elif kind == 'color':
                # attr is a hex string on self; the button is at attr + '_btn'
                btn = getattr(self, attr + '_btn', None)
                if btn:
                    btn.clicked.connect(self._save_series_options)

    def _on_cell_widget_focused(self, old_widget, new_widget):
        """Called whenever application focus changes.  If the newly focused widget
        is a cell widget embedded inside the series table, select that row so that
        _save_series_options always targets the correct series."""
        if new_widget is None:
            return
        if getattr(self, '_loading_series_options', False):
            return
        if not hasattr(self, 'series_table'):
            return
        for r in range(self.series_table.rowCount()):
            if self.series_table.isRowHidden(r):
                continue
            for c in range(self.series_table.columnCount()):
                if self.series_table.cellWidget(r, c) is new_widget:
                    self.series_table.selectRow(r)
                    return

    def _on_series_selection_changed(self):
        """Series table row selected — update the selected-series label, load that
        series' stored option values into the option-group widgets, sync the hidden
        chart_type_combo and option group visibility.
        When no visible row is selected, hide all option groups.
        """
        if not hasattr(self, 'chart_type_combo'):
            return
        # Only consider visible (non-hidden) rows — hidden rows from other subplots
        # can remain in Qt's selection model after setRowHidden.
        selected_rows = set(
            idx.row() for idx in self.series_table.selectedIndexes()
            if not self.series_table.isRowHidden(idx.row())
        )
        lbl_widget = getattr(self, '_selected_series_label', None)
        if not selected_rows:
            if lbl_widget:
                lbl_widget.setText('▶  No series selected')
                lbl_widget.setStyleSheet('font-weight:bold; color:#aaa; font-size:11px; padding:2px 0;')
            if hasattr(self, 'hist_group'):
                # Data tab chart-mode groups
                for grp in (self.bar_group, self.hist_group, self.heat_group,
                            self.pie_group, self.area_group, self.fill_between_group,
                            self.violin_group, self.boxplot_group, self.step_group,
                            self.stem_group, self.waterfall_group, self.hist2d_group,
                            self.hexbin_group, self.radar_group, self.ecdf_group,
                            self.quiver_group, self.barbs_group, self.streamplot_group):
                    grp.setVisible(False)
                # Series tab per-series groups
                for _attr in ('st_line_group','st_scatter_group','st_bar_group',
                              'st_hist_group','st_err_group','st_area_group',
                              'st_fill_between_group','st_step_group','st_stem_group',
                              'st_bubble_group','st_polar_group','st_radar_group',
                              'st_ecdf_group'):
                    _g = getattr(self, _attr, None)
                    if _g: _g.setVisible(False)
            if hasattr(self, '_combo_z_widget'):        self._combo_z_widget.setVisible(False)
            if hasattr(self, '_combo_err_widget'):      self._combo_err_widget.setVisible(False)
            if hasattr(self, '_combo_fill_y2_widget'):  self._combo_fill_y2_widget.setVisible(False)
            return
        row = min(selected_rows)
        # Update the selected-series label
        lbl_item = self.series_table.item(row, 2)
        series_name = lbl_item.text() if lbl_item and lbl_item.text() else f'Series {row+1}'
        if lbl_widget:
            lbl_widget.setText(f'▶  {series_name}')
            lbl_widget.setStyleSheet('font-weight:bold; color:#1a6fc4; font-size:11px; padding:2px 0;')
        type_cb = self.series_table.cellWidget(row, 3)
        if not type_cb:
            return
        ct = type_cb.currentText()
        # Sync hidden chart_type_combo and option group visibility
        self._sync_combo_from_type(ct)
        # Sync plot_mode_combo silently — must NOT fire _on_plot_mode_changed
        if hasattr(self, 'plot_mode_combo'):
            mode = TYPE_TO_PLOT_MODE.get(ct, 'Standard')
            self.plot_mode_combo.blockSignals(True)
            i = self.plot_mode_combo.findText(mode)
            if i >= 0:
                self.plot_mode_combo.setCurrentIndex(i)
            self.plot_mode_combo.blockSignals(False)
        # Series type options are driven by curve_select on the Series tab, not
        # by data-tab row selection — see load_curve_style / _save_series_options.

    def _on_series_label_double_click(self, item):
        """Explicitly start in-place editing when the user double-clicks the
        Label column (col 2) in the series table.  This is a belt-and-suspenders
        fix for PyQt6 environments where the default DoubleClicked edit trigger
        is not reliably firing for items inside a QScrollArea."""
        if item is not None and item.column() == 2:
            self.series_table.editItem(item)

    def _sync_combo_from_type(self, ct):
        """Sync the hidden chart_type_combo and option groups to the given type.
        Called whenever a series row's Type cell changes or a row is selected.
        """
        if not hasattr(self, 'chart_type_combo'):
            return
        from ui.tab_builders import WHOLE_CHART_TYPES
        self.chart_type_combo.blockSignals(True)
        i = self.chart_type_combo.findText(ct)
        if i >= 0:
            self.chart_type_combo.setCurrentIndex(i)
        self.chart_type_combo.blockSignals(False)
        self._update_option_group_visibility(ct)
        # Keep subplot_chart_types correct for whole-chart projections
        if ct in WHOLE_CHART_TYPES and hasattr(self, 'series_sp_active'):
            n = self.subplot_rows * self.subplot_cols
            active_sp = (self.series_sp_active.currentIndex() + 1) if n > 1 else 1
            self.subplot_chart_types[active_sp - 1] = ct

    def _on_series_row_type_changed(self, ct):
        """A Type combo inside the series table was changed directly by the user.
        Sync combos/option-group visibility for the new type.  Only update the
        Series tab option widgets if the changed row matches curve_select — the
        Series tab is self-contained around curve_select and we must not push
        a different series' opts into the widgets while curve_select shows another.
        """
        self._sync_combo_from_type(ct)
        selected_rows = set(idx.row() for idx in self.series_table.selectedIndexes())
        if selected_rows:
            row = min(selected_rows)
            changed_label = self._series_opts_key(row)
            cs = getattr(self, 'curve_select', None)
            if cs and cs.currentText() == changed_label:
                self._load_series_options_by_label(changed_label)
        if hasattr(self, 'datasets'):
            self.update_preview()

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    def _hline(self):
        ln = QFrame(); ln.setFrameShape(QFrame.Shape.HLine); ln.setFrameShadow(QFrame.Shadow.Sunken)
        return ln

    @staticmethod
    def _sec_label(txt):
        """Section header label styled like the DATASETS label."""
        lbl = QLabel(txt.upper())
        lbl.setStyleSheet('font-weight:bold; color:#888; font-size:10px;')
        return lbl

    def _get_xscale(self):
        for b in self.xscale_group.buttons():
            if b.isChecked(): return b.property('scale_value')
        return 'linear'

    def _get_yscale(self):
        for b in self.yscale_group.buttons():
            if b.isChecked(): return b.property('scale_value')
        return 'linear'

    def _set_scale_rb(self, group, value):
        """Check the radio button whose scale_value matches value."""
        for b in group.buttons():
            b.blockSignals(True)
            b.setChecked(b.property('scale_value') == value)
            b.blockSignals(False)

    def _apply_scale(self, ax, xs, ys):
        for scale, inv_fn, set_fn in [(xs, ax.invert_xaxis, ax.set_xscale),
                                       (ys, ax.invert_yaxis, ax.set_yscale)]:
            if scale == 'inverted':
                set_fn('linear'); inv_fn()
            else:
                try: set_fn(scale)
                except Exception: set_fn('linear')

    def _tab10(self, n):
        """Legacy shim — returns n colors from the active palette (cycling if needed)."""
        return [self._palette_color(i) for i in range(n)]

    def _palette_color(self, idx):
        """Return the hex color for series index `idx` using the active palette."""
        all_pals = get_all_palettes()
        pal_name = getattr(self, '_color_palette', 'Matplotlib')
        colors = all_pals.get(pal_name, COLOR_PALETTES['Matplotlib'])
        return colors[idx % len(colors)]

    def _refresh_palette_swatches(self):
        """Update the 16 swatch squares in the Data tab to show the active palette."""
        all_pals = get_all_palettes()
        pal_name = getattr(self, '_color_palette', 'Matplotlib')
        colors = all_pals.get(pal_name, COLOR_PALETTES['Matplotlib'])
        for i, sw in enumerate(getattr(self, '_palette_swatches', [])):
            c = colors[i % len(colors)]
            sw.setStyleSheet(f'background:{c}; border:1px solid #888;')

    def _on_palette_changed(self, name):
        """Called when the palette combo changes. Updates state and re-colors unlocked series."""
        self._color_palette = name
        settings.set('color_palette', name)
        self._refresh_palette_swatches()
        # Re-assign auto-colors to every series row that has no manually locked color.
        for row in range(self.series_table.rowCount()):
            lbl = self._resolve_series_label(row)
            s = self.curve_styles.get(lbl, {})
            if not s.get('color_locked', False):
                new_color = self._palette_color(self._local_palette_index(row))
                s['color'] = new_color
                s['marker_color'] = new_color
                self.curve_styles[lbl] = s
                # For Pie subplots, also update per-wedge entries keyed by x-value
                self._recolor_pie_wedges(row, self._local_palette_index(row))
        self._refresh_lock_indicator()
        # Refresh the curve colour swatches visible in the Style tab
        self.load_curve_style()
        self.update_preview()

    def _resolve_series_label(self, row):
        """Return the label string for a series table row — same logic as _get_series."""
        lbl_item = self.series_table.item(row, 2)
        ycb = self.series_table.cellWidget(row, 1)
        cell_text = lbl_item.text() if lbl_item else ''
        y_col = ycb.currentText() if ycb else ''
        return cell_text if cell_text else (y_col if y_col else f'Series {row+1}')

    def _local_palette_index(self, global_row):
        """Return how many valid series rows before `global_row` share the same subplot.
        This is the local colour index — so every subplot restarts at 0."""
        n = self.subplot_rows * self.subplot_cols
        plot_spin_target = self.series_table.cellWidget(global_row, 4)
        if plot_spin_target is None:
            return global_row  # fallback
        target_subplot = (plot_spin_target.value() - 1) if n > 1 else 0
        local_idx = 0
        for r in range(global_row):
            xcb = self.series_table.cellWidget(r, 0)
            ycb = self.series_table.cellWidget(r, 1)
            if xcb is None or ycb is None:
                continue
            ps = self.series_table.cellWidget(r, 4)
            row_subplot = (ps.value() - 1) if (ps and n > 1) else 0
            if row_subplot == target_subplot:
                xc = xcb.currentText()
                yc = ycb.currentText()
                if xc in self.datasets and yc in self.datasets:
                    local_idx += 1
        return local_idx

    def _reset_all_color_locks(self):
        """Remove color_locked from every series and re-apply the active palette."""
        for row in range(self.series_table.rowCount()):
            lbl = self._resolve_series_label(row)
            s = self.curve_styles.get(lbl, {})
            s.pop('color_locked', None)
            new_color = self._palette_color(self._local_palette_index(row))
            s['color'] = new_color
            s['marker_color'] = new_color
            self.curve_styles[lbl] = s
            # For Pie subplots, also update per-wedge entries keyed by x-value
            self._recolor_pie_wedges(row, self._local_palette_index(row))
        self._refresh_lock_indicator()
        self.update_preview()

    def _recolor_pie_wedges(self, row, palette_offset):
        """If the series at `row` belongs to a Pie subplot, assign palette colors
        to each x-value entry in curve_styles (one color per wedge).
        `palette_offset` is the local palette index for the first wedge."""
        n_subplots = self.subplot_rows * self.subplot_cols
        ps = self.series_table.cellWidget(row, 4)
        subplot_idx = (ps.value() - 1) if (ps and n_subplots > 1) else 0
        if self.subplot_chart_types.get(subplot_idx, 'Line') != 'Pie':
            return
        xcb = self.series_table.cellWidget(row, 0)
        if xcb is None:
            return
        xc = xcb.currentText()
        x_vals = list(self.datasets.get(xc, []))
        for i, seg in enumerate(x_vals):
            key = str(seg)
            s = self.curve_styles.get(key, {})
            if not s.get('color_locked', False):
                c = self._palette_color(palette_offset + i)
                s['color'] = c
                s['marker_color'] = c
                self.curve_styles[key] = s

    # ═══════════════════════════════════════════════════════════════════════════
    # RECENT FILES
    # ═══════════════════════════════════════════════════════════════════════════
    def _rebuild_recent_files_ui(self):
        """Refresh the recent-files list widget in the File tab."""
        if not hasattr(self, '_recent_list'):
            return
        self._recent_list.clear()
        for fp in settings.get_recent_files():
            self._recent_list.addItem(os.path.basename(fp))
            item = self._recent_list.item(self._recent_list.count() - 1)
            item.setToolTip(fp)
            item.setData(Qt.ItemDataRole.UserRole, fp)

    def _open_recent_file(self, item):
        """Open a recently used chart file chosen from the list."""
        fp = item.data(Qt.ItemDataRole.UserRole)
        if not fp or not os.path.isfile(fp):
            QMessageBox.warning(self, 'Not found', f'File no longer exists:\n{fp}')
            settings.prune_recent_files()
            self._rebuild_recent_files_ui()
            return
        self._load_project_from_path(fp)

    # ═══════════════════════════════════════════════════════════════════════════
    # CUSTOM PALETTE EDITOR
    # ═══════════════════════════════════════════════════════════════════════════
    def _open_palette_editor(self):
        """Open a dialog to create or edit a custom colour palette."""

        dlg = QDialog(self)
        dlg.setWindowTitle('Palette Editor')
        dlg.setMinimumWidth(420)
        vlay = QVBoxLayout(dlg)

        # ── Palette name ──────────────────────────────────────────────────────
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel('Name:'))
        name_edit = QLineEdit('My Palette')
        name_row.addWidget(name_edit)
        vlay.addLayout(name_row)

        # ── 16 colour swatches ────────────────────────────────────────────────
        vlay.addWidget(QLabel('Colours (click to change):'))
        swatch_grid = QHBoxLayout(); swatch_grid.setSpacing(4)

        default_colors = list(self._active_palette_colors())
        # Pad or trim to 16
        while len(default_colors) < 16:
            default_colors.append('#cccccc')
        default_colors = default_colors[:16]
        edit_colors = list(default_colors)

        swatch_btns = []
        def _make_swatch(i):
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(f'background:{edit_colors[i]};border:1px solid #666;border-radius:3px;')
            btn.setToolTip(edit_colors[i])
            def _pick(checked=False, idx=i):
                c = _show_color_dialog(QColor(edit_colors[idx]), dlg)
                if c.isValid():
                    edit_colors[idx] = c.name()
                    swatch_btns[idx].setStyleSheet(
                        f'background:{c.name()};border:1px solid #666;border-radius:3px;')
                    swatch_btns[idx].setToolTip(c.name())
            btn.clicked.connect(_pick)
            return btn

        for i in range(16):
            btn = _make_swatch(i)
            swatch_btns.append(btn)
            swatch_grid.addWidget(btn)
        vlay.addLayout(swatch_grid)

        # ── Load from existing palette ─────────────────────────────────────────
        load_row = QHBoxLayout()
        load_row.addWidget(QLabel('Load from:'))
        from PyQt6.QtWidgets import QComboBox as _QCB
        base_combo = _QCB()
        base_combo.addItems(list(get_all_palettes().keys()))
        load_row.addWidget(base_combo)
        def _load_base():
            all_p = get_all_palettes()
            cols = list(all_p.get(base_combo.currentText(), []))
            while len(cols) < 16: cols.append('#cccccc')
            for i, c in enumerate(cols[:16]):
                edit_colors[i] = c
                swatch_btns[i].setStyleSheet(
                    f'background:{c};border:1px solid #666;border-radius:3px;')
                swatch_btns[i].setToolTip(c)
        btn_load_base = QPushButton('Load')
        btn_load_base.clicked.connect(_load_base)
        load_row.addWidget(btn_load_base)
        load_row.addStretch()
        vlay.addLayout(load_row)

        # ── OK / Cancel ────────────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        vlay.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        pal_name = name_edit.text().strip()
        if not pal_name:
            QMessageBox.warning(self, 'Name required', 'Please enter a palette name.')
            return

        add_custom_palette(pal_name, list(edit_colors))

        # Refresh combo and select the new palette
        self.palette_combo.blockSignals(True)
        if self.palette_combo.findText(pal_name) < 0:
            self.palette_combo.addItem(pal_name)
        self.palette_combo.setCurrentText(pal_name)
        self.palette_combo.blockSignals(False)
        self._on_palette_changed(pal_name)

    def _custom_palettes_json(self):
        """Return _CUSTOM_PALETTES as a JSON string for saving."""
        return json.dumps(_CUSTOM_PALETTES, indent=2)

    def _load_custom_palettes_json(self, json_str):
        """Load custom palettes from a JSON string."""
        try:
            data = json.loads(json_str)
            for name, colors in data.items():
                add_custom_palette(name, colors)
            # Rebuild combo
            self.palette_combo.blockSignals(True)
            from ui.tab_builders import get_all_palettes
            existing = [self.palette_combo.itemText(i)
                        for i in range(self.palette_combo.count())]
            for name in get_all_palettes():
                if name not in existing:
                    self.palette_combo.addItem(name)
            self.palette_combo.blockSignals(False)
        except Exception as e:
            pass  # silently ignore corrupt palette data

    def _unlock_curve_color(self):
        """Remove the color lock from the currently selected curve."""
        curve = self.curve_select.currentText()
        if curve and curve in self.curve_styles:
            s = self.curve_styles[curve]
            s.pop('color_locked', None)
            # Find the row index for this label and re-assign palette color
            for row in range(self.series_table.rowCount()):
                lbl_item = self.series_table.item(row, 2)
                if lbl_item and lbl_item.text() == curve:
                    new_color = self._palette_color(self._local_palette_index(row))
                    s['color'] = new_color
                    s['marker_color'] = new_color
                    self.curve_color = new_color
                    self.curve_marker_color = new_color
                    self.curve_color_label.setStyleSheet(f'color:{new_color};font-size:16px;')
                    self.curve_marker_color_label.setStyleSheet(f'color:{new_color};font-size:16px;')
                    break
            self.curve_styles[curve] = s
        self._refresh_lock_indicator()
        self.update_preview()

    def _refresh_lock_indicator(self):
        """Show/hide the 🔒 label next to the curve color based on lock state."""
        if not hasattr(self, 'curve_lock_label'):
            return
        curve = self.curve_select.currentText()
        locked = self.curve_styles.get(curve, {}).get('color_locked', False)
        self.curve_lock_label.setVisible(locked)

    # ═══════════════════════════════════════════════════════════════════════════
    # COLORS
    # ═══════════════════════════════════════════════════════════════════════════
    def _active_palette_colors(self):
        """Return the list of hex colors for the current palette."""
        all_pals = get_all_palettes()
        pal = getattr(self, '_color_palette', 'Matplotlib')
        return all_pals.get(pal, COLOR_PALETTES['Matplotlib'])

    def pick_color(self, target):
        # Determine current color for initial value
        _cur = {
            'chart_bg':     getattr(self, 'chart_bg_color',    '#ffffff'),
            'chart_fg':     getattr(self, 'chart_fg_color',    '#000000'),
            'plot_bg':      getattr(self, 'plot_bg_color',     '#ffffff'),
            'title':        getattr(self, 'title_color',       '#000000'),
            'xlabel':       getattr(self, 'xlabel_color',      '#000000'),
            'ylabel':       getattr(self, 'ylabel_color',      '#000000'),
            'y2label':      getattr(self, 'y2label_color',     '#000000'),
            'curve':        getattr(self, 'curve_color',       '#1f77b4'),
            'curve_marker': getattr(self, 'curve_marker_color','#1f77b4'),
        }.get(target, '#000000')
        color = _show_color_dialog(
            QColor(_cur), self, palette_colors=self._active_palette_colors())
        if not color.isValid(): return
        hx = color.name()
        # Chart-canvas colors
        if target in ('chart_bg', 'chart_fg', 'plot_bg'):
            attr = target + '_color'
            setattr(self, attr, hx)
            getattr(self, attr + '_swatch').setStyleSheet(f'color:{hx};font-size:18px;')
            getattr(self, attr + '_hex').setText(hx)
            self.update_preview()
            return
        mapping = {
            'title':        ('title_color',        'title_color_label',        'style'),
            'xlabel':       ('xlabel_color',        'xlabel_color_label',       'style'),
            'ylabel':       ('ylabel_color',        'ylabel_color_label',       'style'),
            'y2label':      ('y2label_color',       'y2label_color_label',      'style'),
            'curve':        ('curve_color',         'curve_color_label',        'swatch'),
            'curve_marker': ('curve_marker_color',  'curve_marker_color_label', 'swatch'),
        }
        attr, lbl_attr, mode = mapping[target]
        setattr(self, attr, hx)
        lbl = getattr(self, lbl_attr)
        if mode == 'style':
            lbl.setStyleSheet(f'color:{hx};font-size:16px;')
        else:  # swatch — force the square to render in the chosen color
            lbl.setText('■')
            lbl.setStyleSheet(f'color:{hx};font-size:16px;')
        if target in ('curve', 'curve_marker'):
            self.save_curve_style(lock_color=True)
        self.update_preview()

    def _sync_ann_style(self):
        if not hasattr(self,'canvas'): return
        self.canvas.ann_style = {
            'fontsize':   self.ann_fontsize.value(),
            'fontcolor':  self.ann_fontcolor,
            'fontfamily': self.ann_font.currentText(),
            'bg_color':   self.ann_bgcolor,
            'bg_alpha':   self.ann_bg_alpha.value(),
            'edge_color': self.ann_edgecolor,
        }

    def _fig_size_in_inches(self):
        """Convert current fig_width/fig_height spinbox values to inches."""
        w, h = self.fig_width.value(), self.fig_height.value()
        unit = self.fig_unit.currentText()
        if unit == 'cm':
            return w / 2.54, h / 2.54
        elif unit == 'pixels':
            dpi = self.dpi_spin.value()
            return w / dpi, h / dpi
        return w, h   # already inches

    def _on_fig_preset_changed(self, idx):
        """Apply a size preset (values are always in cm; convert to current unit)."""
        _, w_cm, h_cm = self._fig_presets[idx]
        if w_cm is None: return  # Custom — don't touch spinboxes
        unit = self.fig_unit.currentText()
        self.fig_width.blockSignals(True); self.fig_height.blockSignals(True)
        if unit == 'cm':
            self.fig_width.setValue(w_cm); self.fig_height.setValue(h_cm)
        elif unit == 'inches':
            self.fig_width.setValue(round(w_cm / 2.54, 2))
            self.fig_height.setValue(round(h_cm / 2.54, 2))
        elif unit == 'pixels':
            dpi = self.dpi_spin.value()
            self.fig_width.setValue(round(w_cm / 2.54 * dpi))
            self.fig_height.setValue(round(h_cm / 2.54 * dpi))
        self.fig_width.blockSignals(False); self.fig_height.blockSignals(False)
        self.update_preview()

    def _on_figsize_manual_change(self):
        """When user edits W/H manually, switch preset combo to 'Custom'."""
        self.fig_preset_combo.blockSignals(True)
        self.fig_preset_combo.setCurrentText('Custom')
        self.fig_preset_combo.blockSignals(False)
        self.update_preview()

    def _on_fig_unit_changed(self, unit):
        """When unit changes, convert current displayed values to the new unit."""
        # First read current inches value
        wi, hi = self._fig_size_in_inches()
        self.fig_width.blockSignals(True); self.fig_height.blockSignals(True)
        if unit == 'cm':
            self.fig_width.setRange(2, 500); self.fig_height.setRange(2, 500)
            self.fig_width.setDecimals(1); self.fig_height.setDecimals(1)
            self.fig_width.setSingleStep(0.5); self.fig_height.setSingleStep(0.5)
            self.fig_width.setValue(round(wi * 2.54, 1))
            self.fig_height.setValue(round(hi * 2.54, 1))
        elif unit == 'inches':
            self.fig_width.setRange(1, 200); self.fig_height.setRange(1, 200)
            self.fig_width.setDecimals(2); self.fig_height.setDecimals(2)
            self.fig_width.setSingleStep(0.25); self.fig_height.setSingleStep(0.25)
            self.fig_width.setValue(round(wi, 2))
            self.fig_height.setValue(round(hi, 2))
        elif unit == 'pixels':
            dpi = self.dpi_spin.value()
            self.fig_width.setRange(50, 20000); self.fig_height.setRange(50, 20000)
            self.fig_width.setDecimals(0); self.fig_height.setDecimals(0)
            self.fig_width.setSingleStep(10); self.fig_height.setSingleStep(10)
            self.fig_width.setValue(round(wi * dpi))
            self.fig_height.setValue(round(hi * dpi))
        self.fig_width.blockSignals(False); self.fig_height.blockSignals(False)
        self.update_preview()

    def _pick_grid_color(self, which):
        cur = self.grid_color if which == 'major' else self.minor_grid_color
        color = _show_color_dialog(
            QColor(cur), self, palette_colors=self._active_palette_colors())
        if not color.isValid(): return
        hx = color.name()
        if which == 'major':
            self.grid_color = hx
            self.grid_color_sw.setStyleSheet(f'color:{hx};font-size:16px;')
        else:
            self.minor_grid_color = hx
            self.minor_grid_color_sw.setStyleSheet(f'color:{hx};font-size:16px;')
        self.update_preview()

    def _pick_ann_color_attr(self, attr):
        """Generic color picker that writes to self.<attr> and updates <attr>_sw swatch."""
        cur = getattr(self, attr, '#000000')
        color = _show_color_dialog(
            QColor(cur), self, palette_colors=self._active_palette_colors())
        if not color.isValid(): return
        hx = color.name()
        setattr(self, attr, hx)
        sw = getattr(self, attr + '_sw', None)
        if sw: sw.setStyleSheet(f'color:{hx};font-size:16px;')
        self._sync_ann_style()

    def _pick_ann_color(self, target):
        """Legacy shim — routes to the generic attr picker."""
        mapping = {'font': 'ann_fontcolor', 'bg': 'ann_bgcolor', 'edge': 'ann_edgecolor'}
        if target in mapping:
            self._pick_ann_color_attr(mapping[target])

    def _place_at_override(self):
        try: x,y = float(self.ann_x_override.text()), float(self.ann_y_override.text())
        except ValueError:
            QMessageBox.warning(self,'Invalid','Enter numeric X and Y.'); return
        if not self.canvas.axes_list: return
        self._sync_ann_style()
        self.canvas._place_text_annotation(self.canvas.axes_list[0], 0, x, y)

    # ═══════════════════════════════════════════════════════════════════════════
    # ANNOTATION MODES & EDIT
    # ═══════════════════════════════════════════════════════════════════════════
    def set_annotation_mode(self, mode):
        self.canvas.annotation_mode = mode
        self.canvas._arrow_start    = None
        for btn, m in [(self.ann_none_btn, None),(self.ann_text_btn,'text'),
                       (self.ann_arrow_btn,'arrow'),(self.ann_image_btn,'image')]:
            btn.setChecked(mode == m)

    def _start_image_annotation(self):
        fp, _ = QFileDialog.getOpenFileName(
            self,'Select Image',_get_dir(),
            'Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff);;All (*)')
        if not fp:
            self.ann_image_btn.setChecked(False); return
        _remember_dir(fp)
        self.canvas._pending_image_path = fp
        self.canvas.ann_image_zoom      = self.ann_image_zoom.value()
        self.set_annotation_mode('image')

    def refresh_annotation_list(self):
        if not hasattr(self,'ann_list_widget'): return
        self.ann_list_widget.clear()
        # Filter to current subplot shown in annotations tab
        filter_idx = self.ann_sp_active.currentIndex() if hasattr(self, 'ann_sp_active') else -1
        for i, ann in enumerate(self.canvas.annotations):
            if filter_idx >= 0 and ann.get('axes_index', 0) != filter_idx:
                continue
            if ann['type']=='text':
                self.ann_list_widget.addItem(f"📝 \"{ann['label']}\"  @ ({ann['x']:.3g},{ann['y']:.3g})")
            elif ann['type']=='arrow':
                self.ann_list_widget.addItem(
                    f"➡  ({ann['x0']:.3g},{ann['y0']:.3g})→({ann['x1']:.3g},{ann['y1']:.3g})")
            elif ann['type']=='image':
                self.ann_list_widget.addItem(
                    f"🖼 {os.path.basename(ann['filepath'])}  zoom={ann.get('zoom',0.15):.2f}  @ ({ann['x']:.3g},{ann['y']:.3g})")

    def _selected_ann_index(self):
        """Return the index into canvas.annotations for the selected list item."""
        rows = self.ann_list_widget.selectedItems()
        if not rows: return -1
        list_row = self.ann_list_widget.row(rows[0])
        # Map list row back to canvas.annotations index (accounting for subplot filter)
        filter_idx = self.ann_sp_active.currentIndex() if hasattr(self, 'ann_sp_active') else -1
        count = 0
        for i, ann in enumerate(self.canvas.annotations):
            if filter_idx >= 0 and ann.get('axes_index', 0) != filter_idx:
                continue
            if count == list_row:
                return i
            count += 1
        return -1

    def _edit_selected_annotation(self):
        idx = self._selected_ann_index()
        if idx < 0:
            QMessageBox.information(self,'Edit','Select an annotation from the list first.'); return
        ann = self.canvas.annotations[idx]
        dlg = AnnotationEditDialog(ann, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.apply()
            # update_preview will clear figure, re-plot, then redraw_annotations
            self.update_preview()
            self.refresh_annotation_list()

    def _delete_selected_annotation(self):
        idx = self._selected_ann_index()
        if idx < 0:
            QMessageBox.information(self,'Delete','Select an annotation first.'); return
        self.canvas.remove_annotation_at(idx)


    # ═══════════════════════════════════════════════════════════════════════════
    # COLOR SCHEMES
    # ═══════════════════════════════════════════════════════════════════════════

    # Keys extracted from a full settings dict that constitute a "color scheme".
    # Anything not in this list is left untouched when a scheme is applied.
    _COLOR_SCHEME_KEYS = [
        'chart_bg_color', 'chart_fg_color', 'plot_bg_color',
        'grid_color', 'grid_on', 'grid_linestyle', 'grid_linewidth', 'grid_alpha',
        'minor_grid_color', 'minor_grid_on',
        'minor_grid_linestyle', 'minor_grid_linewidth', 'minor_grid_alpha',
        'title_color', 'xlabel_color', 'ylabel_color', 'y2label_color',
        'title_font', 'xlabel_font', 'ylabel_font',
        'title_size', 'xlabel_size', 'ylabel_size',
        'border_top', 'border_bottom', 'border_left', 'border_right',
        'color_palette',
        'ann_fontcolor', 'ann_bgcolor', 'ann_edgecolor',
    ]

    # Built-in named schemes: name → partial settings dict
    _BUILTIN_COLOR_SCHEMES = {
        'Default (white)': {
            'chart_bg_color': '#ffffff', 'chart_fg_color': '#000000', 'plot_bg_color': '#ffffff',
            'grid_color': '#cccccc', 'grid_on': True, 'grid_linestyle': '--',
            'grid_linewidth': 0.5, 'grid_alpha': 0.4,
            'minor_grid_color': '#e8e8e8', 'minor_grid_on': False,
            'title_color': '#000000', 'xlabel_color': '#000000', 'ylabel_color': '#000000',
            'color_palette': 'Matplotlib',
        },
        'Dark (charcoal)': {
            'chart_bg_color': '#1e1e2e', 'chart_fg_color': '#cdd6f4', 'plot_bg_color': '#181825',
            'grid_color': '#45475a', 'grid_on': True, 'grid_linestyle': '--',
            'grid_linewidth': 0.5, 'grid_alpha': 0.5,
            'minor_grid_color': '#313244', 'minor_grid_on': False,
            'title_color': '#cdd6f4', 'xlabel_color': '#a6adc8', 'ylabel_color': '#a6adc8',
            'border_top': False, 'border_right': False,
            'color_palette': 'Bold',
        },
        'Dark (slate)': {
            'chart_bg_color': '#0f172a', 'chart_fg_color': '#e2e8f0', 'plot_bg_color': '#1e293b',
            'grid_color': '#334155', 'grid_on': True, 'grid_linestyle': ':',
            'grid_linewidth': 0.6, 'grid_alpha': 0.6,
            'minor_grid_color': '#1e293b', 'minor_grid_on': False,
            'title_color': '#f8fafc', 'xlabel_color': '#94a3b8', 'ylabel_color': '#94a3b8',
            'border_top': False, 'border_right': False,
            'color_palette': 'Bold',
        },
        'Scientific (minimal)': {
            'chart_bg_color': '#ffffff', 'chart_fg_color': '#000000', 'plot_bg_color': '#ffffff',
            'grid_color': '#dddddd', 'grid_on': True, 'grid_linestyle': '--',
            'grid_linewidth': 0.4, 'grid_alpha': 0.3,
            'minor_grid_color': '#eeeeee', 'minor_grid_on': False,
            'title_color': '#111111', 'xlabel_color': '#333333', 'ylabel_color': '#333333',
            'border_top': False, 'border_right': False,
            'color_palette': 'Matplotlib',
        },
        'Nature / print': {
            'chart_bg_color': '#ffffff', 'chart_fg_color': '#000000', 'plot_bg_color': '#ffffff',
            'grid_color': '#cccccc', 'grid_on': False, 'grid_linestyle': '--',
            'grid_linewidth': 0.4, 'grid_alpha': 0.3,
            'minor_grid_color': '#eeeeee', 'minor_grid_on': False,
            'title_color': '#000000', 'xlabel_color': '#000000', 'ylabel_color': '#000000',
            'border_top': False, 'border_right': False,
            'color_palette': 'Matplotlib',
        },
        'Midnight blue': {
            'chart_bg_color': '#0d1b2a', 'chart_fg_color': '#e0e0e0', 'plot_bg_color': '#0d1b2a',
            'grid_color': '#1b3a5c', 'grid_on': True, 'grid_linestyle': '-',
            'grid_linewidth': 0.4, 'grid_alpha': 0.4,
            'minor_grid_color': '#112233', 'minor_grid_on': False,
            'title_color': '#ffffff', 'xlabel_color': '#aac8e4', 'ylabel_color': '#aac8e4',
            'border_top': False, 'border_right': False,
            'color_palette': 'Bold',
        },
        'Warm parchment': {
            'chart_bg_color': '#f5f0e8', 'chart_fg_color': '#3d2b1f', 'plot_bg_color': '#faf7f0',
            'grid_color': '#c8b89a', 'grid_on': True, 'grid_linestyle': '--',
            'grid_linewidth': 0.5, 'grid_alpha': 0.4,
            'minor_grid_color': '#e0d5c2', 'minor_grid_on': False,
            'title_color': '#3d2b1f', 'xlabel_color': '#5c4033', 'ylabel_color': '#5c4033',
            'color_palette': 'Pastel',
        },
        'High contrast': {
            'chart_bg_color': '#000000', 'chart_fg_color': '#ffffff', 'plot_bg_color': '#000000',
            'grid_color': '#444444', 'grid_on': True, 'grid_linestyle': ':',
            'grid_linewidth': 0.5, 'grid_alpha': 0.6,
            'minor_grid_color': '#222222', 'minor_grid_on': False,
            'title_color': '#ffffff', 'xlabel_color': '#cccccc', 'ylabel_color': '#cccccc',
            'border_top': True, 'border_right': True,
            'color_palette': 'Bold',
        },
        'Pastel soft': {
            'chart_bg_color': '#fdfbf7', 'chart_fg_color': '#444444', 'plot_bg_color': '#fdfbf7',
            'grid_color': '#ddd5e8', 'grid_on': True, 'grid_linestyle': '--',
            'grid_linewidth': 0.5, 'grid_alpha': 0.5,
            'minor_grid_color': '#f0ecf5', 'minor_grid_on': False,
            'title_color': '#444444', 'xlabel_color': '#666666', 'ylabel_color': '#666666',
            'color_palette': 'Pastel',
        },
    }

    # Registry of all schemes (built-in + user-loaded); populated by _init_color_schemes
    _COLOR_SCHEME_REGISTRY: dict = {}

    def _init_color_schemes(self):
        """Populate the color scheme combo with built-ins and refresh the swatch."""
        self._COLOR_SCHEME_REGISTRY = dict(self._BUILTIN_COLOR_SCHEMES)
        self._cs_combo.blockSignals(True)
        self._cs_combo.clear()
        self._cs_combo.addItems(list(self._COLOR_SCHEME_REGISTRY.keys()))
        self._cs_combo.blockSignals(False)
        self._cs_combo.currentIndexChanged.connect(self._refresh_cs_swatches)
        self._refresh_cs_swatches()

    def _refresh_cs_swatches(self):
        """Update the 5 preview swatches for the currently selected scheme."""
        name = self._cs_combo.currentText()
        scheme = self._COLOR_SCHEME_REGISTRY.get(name, {})
        colors = [
            scheme.get('chart_bg_color', '#ffffff'),
            scheme.get('plot_bg_color',  '#ffffff'),
            scheme.get('chart_fg_color', '#000000'),
            scheme.get('grid_color',     '#cccccc'),
            scheme.get('title_color',    '#000000'),
        ]
        for sw, color in zip(self._cs_swatches, colors):
            sw.setStyleSheet(
                f'background:{color}; border:1px solid #888; border-radius:2px;')

    def _scheme_from_current_settings(self) -> dict:
        """Extract only the color-scheme keys from the current UI state."""
        full = self._collect_settings()
        return {k: full[k] for k in self._COLOR_SCHEME_KEYS if k in full}

    def _apply_color_scheme_dict(self, scheme: dict):
        """Apply a partial settings dict containing only color-scheme keys."""
        # Build a full settings dict from current state, overwrite scheme keys only
        full = self._collect_settings()
        full.update(scheme)
        self._applying_settings = True
        try:
            self._apply_settings(full)
        finally:
            self._applying_settings = False
        self.update_preview()

    def _apply_color_scheme_selected(self):
        """Apply the scheme currently selected in the combo."""
        name = self._cs_combo.currentText()
        scheme = self._COLOR_SCHEME_REGISTRY.get(name)
        if scheme:
            self._apply_color_scheme_dict(scheme)

    def _save_color_scheme(self):
        """Save the current chart colors as a .pvizc color-scheme file."""
        import zipfile as _zf, json as _json
        from PyQt6.QtWidgets import QInputDialog
        from ui.helpers import _get_dir, _remember_dir

        name, ok = QInputDialog.getText(
            self, 'Save Color Scheme', 'Scheme name:', text='My Scheme')
        if not ok or not name.strip():
            return
        name = name.strip()

        _stem = (os.path.splitext(os.path.basename(self._current_filepath))[0]
                 if getattr(self, '_current_filepath', None) else 'untitled')
        fp, _ = QFileDialog.getSaveFileName(
            self, 'Save Color Scheme', os.path.join(_get_dir(), _stem + '.pvizc'),
            'plotviz Color Scheme (*.pvizc);;All Files (*)')
        if not fp:
            return
        _remember_dir(fp)
        if not fp.endswith('.pvizc'):
            fp += '.pvizc'

        try:
            scheme = self._scheme_from_current_settings()
            payload = {
                '_app': 'plotviz',
                '_file_type': 'color_scheme',
                '_scheme_name': name,
            }
            payload.update(scheme)
            with _zf.ZipFile(fp, 'w', _zf.ZIP_DEFLATED) as zf:
                zf.writestr('settings.json', _json.dumps(payload, indent=2))

            # Register in the combo so it can be re-applied this session
            self._COLOR_SCHEME_REGISTRY[name] = scheme
            if self._cs_combo.findText(name) < 0:
                self._cs_combo.addItem(name)
            self._cs_combo.setCurrentText(name)
            QMessageBox.information(self, 'Saved', f'Color scheme saved:\n{fp}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _load_color_scheme(self):
        """Load a .pvizc color-scheme file and register it in the combo."""
        import zipfile as _zf, json as _json
        from ui.helpers import _get_dir, _remember_dir

        fp, _ = QFileDialog.getOpenFileName(
            self, 'Load Color Scheme', _get_dir(),
            'plotviz Color Scheme (*.pvizc);;All Files (*)')
        if not fp:
            return
        _remember_dir(fp)

        try:
            with _zf.ZipFile(fp, 'r') as zf:
                payload = _json.loads(zf.read('settings.json'))

            # Accept both color_scheme and full template files
            name = payload.get('_scheme_name') or os.path.splitext(
                os.path.basename(fp))[0]

            # Extract only the color-scheme keys (ignore layout, data, etc.)
            scheme = {k: payload[k] for k in self._COLOR_SCHEME_KEYS if k in payload}
            if not scheme:
                QMessageBox.warning(self, 'Invalid',
                    'No color settings found in this file.')
                return

            self._COLOR_SCHEME_REGISTRY[name] = scheme
            if self._cs_combo.findText(name) < 0:
                self._cs_combo.addItem(name)
            self._cs_combo.setCurrentText(name)
            self._refresh_cs_swatches()

            reply = QMessageBox.question(
                self, 'Apply?',
                f'Scheme "{name}" loaded.\nApply it now?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._apply_color_scheme_dict(scheme)
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _load_color_scheme_from_path(self, fp: str):
        """Load a .pvizc directly from *fp* (no dialog — Finder/cold-launch)."""
        import zipfile as _zf, json as _json
        try:
            with _zf.ZipFile(fp, 'r') as zf:
                payload = _json.loads(zf.read('settings.json'))
            name = payload.get('_scheme_name') or os.path.splitext(
                os.path.basename(fp))[0]
            scheme = {k: payload[k] for k in self._COLOR_SCHEME_KEYS if k in payload}
            if not scheme:
                return
            self._COLOR_SCHEME_REGISTRY[name] = scheme
            if self._cs_combo.findText(name) < 0:
                self._cs_combo.addItem(name)
            self._cs_combo.setCurrentText(name)
            self._refresh_cs_swatches()
            self._apply_color_scheme_dict(scheme)
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA
    # ═══════════════════════════════════════════════════════════════════════════
    def _open_app_settings_dialog(self):
        """App-level settings dialog: paths, defaults, UI options."""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        import config.settings as _cfg
        from config._version import __version__

        dlg = QDialog(self)
        dlg.setWindowTitle('Preferences' if sys.platform == 'darwin' else 'Settings')
        dlg.setMinimumWidth(520)
        lay = QVBoxLayout(dlg); lay.setSpacing(12)

        # ── Config paths ─────────────────────────────────────────────────────
        grp_paths = QGroupBox('Configuration files')
        paths_form = QFormLayout(grp_paths); paths_form.setSpacing(6)

        def _path_row(label, path_str):
            row = QHBoxLayout(); row.setSpacing(4)
            le = QLineEdit(path_str); le.setReadOnly(True)
            le.setToolTip(path_str)
            btn = QPushButton('📂'); btn.setFixedWidth(32)
            btn.setToolTip('Open containing folder')
            import os as _os
            folder = _os.path.dirname(path_str)
            btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(folder)))
            row.addWidget(le, 1); row.addWidget(btn)
            paths_form.addRow(label, row)

        _path_row('Settings file:', str(_cfg.CFG_FILE))
        _path_row('Config folder:', str(_cfg.CFG_FILE.parent))

        lay.addWidget(grp_paths)

        # ── Appearance ───────────────────────────────────────────────────────
        grp_appearance = QGroupBox('Appearance')
        appearance_form = QFormLayout(grp_appearance); appearance_form.setSpacing(6)

        from PyQt6.QtWidgets import QComboBox as _QComboBox
        appearance_combo = _QComboBox()
        appearance_combo.addItems(['System', 'Light', 'Dark'])
        current_theme = _cfg.get('theme') or 'System'
        idx = appearance_combo.findText(current_theme)
        if idx >= 0:
            appearance_combo.setCurrentIndex(idx)
        appearance_combo.setToolTip('Application colour scheme (takes effect immediately)')
        appearance_combo.currentTextChanged.connect(self._apply_colour_scheme)
        appearance_form.addRow('Colour scheme:', appearance_combo)

        lay.addWidget(grp_appearance)

        # ── UI defaults ──────────────────────────────────────────────────────
        grp_ui = QGroupBox('Defaults')
        ui_form = QFormLayout(grp_ui); ui_form.setSpacing(6)

        chk_toolbar = QCheckBox()
        chk_toolbar.setChecked(_cfg.get('show_toolbar', True))
        chk_toolbar.setToolTip('Show the navigation toolbar below the chart canvas')
        ui_form.addRow('Show navigation toolbar:', chk_toolbar)

        max_recent_spin = QSpinBox(); max_recent_spin.setRange(1, 30)
        max_recent_spin.setValue(_cfg.MAX_RECENT)
        max_recent_spin.setFixedWidth(60)
        ui_form.addRow('Max recent files:', max_recent_spin)

        lay.addWidget(grp_ui)

        # ── Maintenance ──────────────────────────────────────────────────────
        grp_maint = QGroupBox('Maintenance')
        maint_lay = QVBoxLayout(grp_maint); maint_lay.setSpacing(6)

        recent_row = QHBoxLayout()
        lbl_recent = QLabel(f'{len(_cfg.get_recent_files())} recent file(s) stored')
        btn_clear_recent = QPushButton('Clear recent files')
        def _clear_recent():
            _cfg.set('recent_files', [])
            lbl_recent.setText('0 recent file(s) stored')
            if hasattr(self, '_rebuild_recent_files_ui'):
                self._rebuild_recent_files_ui()
        btn_clear_recent.clicked.connect(_clear_recent)
        recent_row.addWidget(lbl_recent); recent_row.addStretch(); recent_row.addWidget(btn_clear_recent)
        maint_lay.addLayout(recent_row)

        btn_reset_settings = QPushButton('Reset all settings to defaults…')
        btn_reset_settings.setToolTip('Resets settings.json to factory defaults (does not affect chart data)')
        def _reset_settings():
            from PyQt6.QtWidgets import QMessageBox
            if QMessageBox.question(dlg, 'Reset settings',
                'Reset all app settings to defaults?\nThis cannot be undone.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                _cfg.save(_cfg.DEFAULTS.copy())
                _cfg.settings.update(_cfg.DEFAULTS.copy())
                QMessageBox.information(dlg, 'Done', 'Settings reset. Some changes take effect on next launch.')
        btn_reset_settings.clicked.connect(_reset_settings)
        maint_lay.addWidget(btn_reset_settings)

        lay.addWidget(grp_maint)

        # ── Buttons ──────────────────────────────────────────────────────────
        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(dlg.accept)
        bbox.rejected.connect(dlg.reject)
        lay.addWidget(bbox)

        _original_theme = current_theme  # snapshot before dialog opens

        if dlg.exec() != QDialog.DialogCode.Accepted:
            # Revert any live appearance change the user previewed then cancelled
            if appearance_combo.currentText() != _original_theme:
                self._apply_colour_scheme(_original_theme)
            return

        # Apply changes
        chosen_theme = appearance_combo.currentText()
        if hasattr(self, 'colour_scheme_combo'):
            idx2 = self.colour_scheme_combo.findText(chosen_theme)
            if idx2 >= 0:
                self.colour_scheme_combo.blockSignals(True)
                self.colour_scheme_combo.setCurrentIndex(idx2)
                self.colour_scheme_combo.blockSignals(False)
        self._apply_colour_scheme(chosen_theme)

        _cfg.set('show_toolbar', chk_toolbar.isChecked())
        if hasattr(self, 'canvas') and hasattr(self.canvas, 'toolbar'):
            tb = self.canvas.toolbar
            if tb:
                tb.setVisible(chk_toolbar.isChecked())
        _cfg.MAX_RECENT = max_recent_spin.value()

    def _show_about(self):
        """Display the About dialog."""
        from config._version import __version__
        dlg = QMessageBox(self)
        dlg.setWindowTitle('About plotviz')
        dlg.setText(
            f'<h2>plotviz&nbsp;{__version__}</h2>'
            '<p>Publication-quality chart generator.</p>'
            '<p>Copyright &copy; 2026 Paulo Cachim<br>'
            'Licensed under the <a href="https://opensource.org/licenses/MIT">MIT License</a>.</p>'
        )
        dlg.setIconPixmap(QApplication.windowIcon().pixmap(64, 64))
        dlg.exec()

    # ── Undo / Redo ─────────────────────────────────────────────────────────────
    def _snapshot(self):
        """Capture current full state for undo.  Called by update_preview."""
        if not hasattr(self, '_undo_suspended') or self._undo_suspended:
            return
        if not hasattr(self, '_collect_settings') or not hasattr(self, 'datasets'):
            return
        if not hasattr(self, '_undo_stack'):
            return
        import copy
        snap = (
            self._collect_settings(),
            self._collect_series_meta(),
            copy.deepcopy(self.datasets),
        )
        # Avoid duplicate consecutive snapshots
        if self._undo_stack and self._undo_stack[-1][0] == snap[0]                 and self._undo_stack[-1][1] == snap[1]:
            return
        self._undo_stack.append(snap)
        if len(self._undo_stack) > self._MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._update_undo_buttons()

    def _restore_snapshot(self, snap):
        """Apply a (settings, series_meta, datasets) snapshot without pushing to undo."""
        import copy
        self._undo_suspended = True
        self._applying_settings = True
        try:
            settings_d, series_d, datasets_d = snap
            self.datasets = copy.deepcopy(datasets_d)
            self.update_lists(keep_selections=False)
            self._apply_settings(settings_d)
            self._apply_series_meta(series_d)
        finally:
            self._applying_settings = False
            self._undo_suspended = False
        self.update_preview()
        self._update_undo_buttons()

    def _undo(self):
        if len(self._undo_stack) < 2:
            return
        # Current state is at top; pop it to redo, restore the one before it
        current = self._undo_stack.pop()
        self._redo_stack.append(current)
        self._restore_snapshot(self._undo_stack[-1])

    def _redo(self):
        if not self._redo_stack:
            return
        snap = self._redo_stack.pop()
        self._undo_stack.append(snap)
        self._restore_snapshot(snap)

    def _update_undo_buttons(self):
        if hasattr(self, '_btn_undo'):
            self._btn_undo.setEnabled(len(self._undo_stack) >= 2)
        if hasattr(self, '_btn_redo'):
            self._btn_redo.setEnabled(bool(self._redo_stack))

    def _default_settings(self) -> dict:
        """Return a settings dict matching widget construction defaults — used by New Plot."""
        def _ser(d): return {str(k): v for k, v in d.items()}
        s = {
            '_app': 'plotviz', '_version': '1.3',
            'chart_type':       'Line',
            'title_show':       True,  'title_text':  '',
            'title_font':       'sans-serif', 'title_size': 14, 'title_color': '#000000',
            'title_x':          0.5,   'title_y':     0.97,
            'sp_hspace':        0.35,  'sp_wspace':   0.35,
            'sp_titles':             _ser({0: ''}),
            'subplot_title_show':    _ser({0: True}),
            'subplot_title_font':    _ser({0: 'sans-serif'}),
            'subplot_title_size':    _ser({0: 11}),
            'subplot_title_color':   _ser({0: '#000000'}),
            'subplot_xlabels':       _ser({0: ''}),
            'subplot_xlabel_show':   _ser({0: True}),
            'subplot_ylabels':       _ser({0: ''}),
            'subplot_ylabel_show':   _ser({0: True}),
            'subplot_y2labels':      _ser({0: ''}),
            'subplot_y2label_show':  _ser({0: True}),
            'subplot_legends':       _ser({0: True}),
            'subplot_legend_locs':   _ser({0: 'best'}),
            'subplot_legend_x':      _ser({0: 0.01}),
            'subplot_legend_y':      _ser({0: 0.99}),
            'subplot_legend_fontsize': _ser({0: 9}),
            'subplot_legend_ncols':  _ser({0: 1}),
            'subplot_legend_frameon': _ser({0: True}),
            'subplot_legend_color':  _ser({0: '#000000'}),
            'subplot_legend_facecolor': _ser({0: '#ffffff'}),
            'subplot_legend_alpha':  _ser({0: 0.8}),
            'subplot_legend_edgecolor': _ser({0: '#cccccc'}),
            'subplot_xlims':         _ser({0: None}),
            'subplot_ylims':         _ser({0: None}),
            'subplot_y2lims':        _ser({0: None}),
            'subplot_xscales':       _ser({0: 'linear'}),
            'subplot_yscales':       _ser({0: 'linear'}),
            'subplot_xtick_sizes':   _ser({0: 9}),
            'subplot_ytick_sizes':   _ser({0: 9}),
            'subplot_xtick_dir':     _ser({0: 'out'}),
            'subplot_ytick_dir':     _ser({0: 'out'}),
            'subplot_xtick_minor':   _ser({0: False}),
            'subplot_ytick_minor':   _ser({0: False}),
            'subplot_xtick_rotation':_ser({0: 0}),
            'subplot_ytick_rotation':_ser({0: 0}),
            'subplot_xtick_step':    _ser({0: 0.0}),
            'subplot_ytick_step':    _ser({0: 0.0}),
            'subplot_x_formatter':   _ser({0: 'auto'}),
            'subplot_y_formatter':   _ser({0: 'auto'}),
            'subplot_xticks_show':   _ser({0: True}),
            'subplot_yticks_show':   _ser({0: True}),
            'subplot_ann_visible':   _ser({0: True}),
            'xlabel_font': 'sans-serif', 'xlabel_size': 11, 'xlabel_color': '#000000',
            'ylabel_font': 'sans-serif', 'ylabel_size': 11, 'ylabel_color': '#000000',
            'y2label_font':'sans-serif', 'y2label_size':11, 'y2label_color':'#000000',
            'color_palette':    'Matplotlib',
            'preset':           'Default',
            'chart_bg_color':   '#ffffff',
            'chart_fg_color':   '#000000',
            'plot_bg_color':    '#ffffff',
            'border_top':    True, 'border_bottom': True,
            'border_left':   True, 'border_right':  True,
            'curve_styles':     {},
            'fig_preset':    '20 × 15 cm',
            'fig_unit':      'cm',
            'fig_width':     20.0, 'fig_height': 15.0,
            'fig_left':      0.10, 'fig_right':  0.95,
            'fig_bottom':    0.10, 'fig_top':    0.95,
            'grid_on':        True,  'grid_color': '#cccccc',
            'grid_linestyle': '--',  'grid_linewidth': 0.5, 'grid_alpha': 0.4,
            'minor_grid_on':  False, 'minor_grid_color': '#e8e8e8',
            'minor_grid_linestyle': ':', 'minor_grid_linewidth': 0.3, 'minor_grid_alpha': 0.2,
            'dpi':           300,
            'fit_ci_index': 0, 'fit_pi_index': 0, 'fit_ci_alpha': 0.25,
            'fit_result':    None,
            'subplot_rows':  1,    'subplot_cols': 1,
            'subplot_mosaic':None, 'sp_sharex':    False, 'sp_sharey': False,
            'hist_bins':     20,   'hist_density':  False,
            'bar_width':     0.8,  'bar_stacked':   False, 'bar_horizontal': False,
            'scatter_size':  20,   'scatter_alpha': 0.8,
            'err_capsize':   4,    'cmap':          'viridis',
            'contour_levels':10,   'heat_colorbar': True,
            'pie_autopct':   True, 'pie_shadow':    False,
            'area_alpha':    0.4,  'area_stacked':  False,
            'violin_show_means':   True, 'violin_show_medians': True,
            'ann_fontcolor': '#000000', 'ann_fontsize': 10,
            'ann_font':      'sans-serif', 'ann_bgcolor': '#ffffcc',
            'ann_bg_alpha':  0.9,  'ann_edgecolor': '#aaaaaa',
            'line_default_style':  '-',    'line_default_marker': 'None',
            'line_default_lw':     1.5,    'line_default_markersize': 6,
        }
        return s

    def _reset_app(self):
        """Clear all data and start a new plot."""
        if getattr(self, '_is_dirty', False):
            mb = QMessageBox(self)
            mb.setWindowTitle('New Plot')
            mb.setText('You have unsaved changes.')
            mb.setInformativeText('Do you want to save before starting a new plot?')
            btn_save   = mb.addButton('Save',    QMessageBox.ButtonRole.AcceptRole)
            btn_discard = mb.addButton('Discard', QMessageBox.ButtonRole.DestructiveRole)
            mb.addButton('Cancel', QMessageBox.ButtonRole.RejectRole)
            mb.exec()
            clicked = mb.clickedButton()
            if clicked is btn_save:
                self._save_project()
            elif clicked is not btn_discard:
                return  # Cancel
        else:
            if QMessageBox.question(self, 'New Plot', 'Start a new plot?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                    ) != QMessageBox.StandardButton.Yes:
                return
        self._current_filepath = None
        self._update_window_title()
        self._is_dirty = False
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._update_undo_buttons()
        self.datasets.clear()
        self.curve_styles.clear()
        self.canvas.annotations.clear()
        self._last_fit = None
        self._subplot_mosaic = None
        # Clear series table BEFORE _apply_settings triggers any redraws,
        # otherwise stale rows referencing cleared datasets cause a crash.
        self.series_table.setRowCount(0)
        self._refresh_curve_select()
        # Clear chart-type tracking so _apply_settings always initialises a
        # fresh Cartesian/Line state, regardless of what was loaded before.
        self.subplot_chart_types.clear()
        if hasattr(self, 'subplot_plot_modes'):
            self.subplot_plot_modes.clear()
        if hasattr(self, 'subplot_chart_opts'):
            self.subplot_chart_opts.clear()
        # Reset all UI widgets to fresh defaults via _apply_settings
        self._undo_suspended = True
        self._applying_settings = True
        try:
            self._apply_settings(self._default_settings())
        finally:
            self._applying_settings = False
            self._undo_suspended = False
        self.update_lists()
        self.on_subplot_layout_changed()
        self.update_preview()
        self.refresh_annotation_list()
        self._notify_sns_explorer()

    def load_data(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 'Load Files', _get_dir(), 'Data Files (*.csv *.xlsx *.xls *.json *.txt);;All (*)')
        if not files:
            return
        _remember_dir(files[0])
        for fp in files:
            try:
                dlg = DataImportDialog(fp, self)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    continue
                for name, arr in dlg.get_selected_data().items():
                    base, cnt = name, 1
                    while name in self.datasets:
                        name = f'{base}_{cnt}'; cnt += 1
                    self.datasets[name] = arr
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed: {fp}\n{e}')
        self.update_lists()
        if self.series_table.rowCount() == 0:
            self._add_series_row()
        self._notify_sns_explorer()


    def _remove_selected_datasets(self):
        """Remove datasets selected in the dataset list, then refresh."""
        selected = [item.text() for item in self.dataset_list.selectedItems()]
        if not selected:
            return
        for name in selected:
            self.datasets.pop(name, None)
        self.update_lists()
        self.update_preview()
        self._notify_sns_explorer()

    def update_lists(self, keep_selections=False):
        """Refresh dataset list, combo_z, combo_err, and series table combos."""
        cols = sorted(self.datasets)
        zp  = self.combo_z.currentText(); ep = self.combo_err.currentText()
        fy2p = getattr(self, 'combo_fill_y2', None)
        fy2p = fy2p.currentText() if fy2p else '(none)'
        qup = getattr(self.quiver_u_combo,  'currentText', lambda: '(none)')()
        qvp = getattr(self.quiver_v_combo,  'currentText', lambda: '(none)')()
        bup = getattr(self.barbs_u_combo,   'currentText', lambda: '(none)')()
        bvp = getattr(self.barbs_v_combo,   'currentText', lambda: '(none)')()
        sup = getattr(self.stream_u_combo,  'currentText', lambda: '(none)')()
        svp = getattr(self.stream_v_combo,  'currentText', lambda: '(none)')()
        bsp = getattr(self.bubble_size_combo, 'currentText', lambda: '(uniform)')()

        self.dataset_list.clear(); self.combo_x.clear()
        self.y_list.clear()
        self.combo_z.clear(); self.combo_z.addItem('(none)')
        self.combo_err.clear(); self.combo_err.addItem('(none)')
        if hasattr(self, 'combo_fill_y2'):
            self.combo_fill_y2.blockSignals(True)
            self.combo_fill_y2.clear(); self.combo_fill_y2.addItem('(none)')

        for col in cols:
            self.dataset_list.addItem(col)
            self.combo_x.addItem(col); self.y_list.addItem(col)
            self.combo_z.addItem(col); self.combo_err.addItem(col)
            if hasattr(self, 'combo_fill_y2'):
                self.combo_fill_y2.addItem(col)

        if hasattr(self, 'combo_fill_y2'):
            i = self.combo_fill_y2.findText(fy2p)
            self.combo_fill_y2.setCurrentIndex(i if i >= 0 else 0)
            self.combo_fill_y2.blockSignals(False)

        for combo, prev in [(self.combo_z, zp), (self.combo_err, ep)]:
            i = combo.findText(prev)
            if i >= 0: combo.setCurrentIndex(i)

        # Refresh quiver/barbs/streamplot U/V and bubble size combos
        for combo, sentinel, prev in [
            (self.quiver_u_combo,    '(none)',    qup),
            (self.quiver_v_combo,    '(none)',    qvp),
            (self.barbs_u_combo,     '(none)',    bup),
            (self.barbs_v_combo,     '(none)',    bvp),
            (self.stream_u_combo,    '(none)',    sup),
            (self.stream_v_combo,    '(none)',    svp),
            (self.bubble_size_combo, '(uniform)', bsp),
            (self.err_xerr_combo, '(none)', getattr(self.err_xerr_combo, '_prev', '(none)')),
        ]:
            combo.blockSignals(True); combo.clear()
            combo.addItem(sentinel)
            combo.addItems(cols)
            i = combo.findText(prev); combo.setCurrentIndex(i if i >= 0 else 0)
            combo.blockSignals(False)

        # Refresh series table combos
        self._refresh_series_combos()
        self._refresh_curve_select()

        # Keep fn_source_combo in sync (Advanced tab)
        prev_fn = self.fn_source_combo.currentText()
        self.fn_source_combo.blockSignals(True)
        self.fn_source_combo.clear()
        self.fn_source_combo.addItems(cols)
        i_fn = self.fn_source_combo.findText(prev_fn)
        self.fn_source_combo.setCurrentIndex(i_fn if i_fn >= 0 else 0)
        self.fn_source_combo.blockSignals(False)

        # Notify Seaborn Explorer if it is open
        self._notify_sns_explorer()

    def _refresh_series_combos(self):
        """Re-populate the X/Y QComboBox widgets in every series row and sync Plot spin ranges."""
        cols = sorted(self.datasets)
        n = max(1, self.subplot_rows * self.subplot_cols)
        self.series_table.blockSignals(True)
        for row in range(self.series_table.rowCount()):
            for col_idx in (0, 1):
                cb = self.series_table.cellWidget(row, col_idx)
                if cb is None:
                    cb = QComboBox()
                    handler = self._on_x_col_changed if col_idx == 0 else self.update_preview
                    cb.currentIndexChanged.connect(handler)
                    self.series_table.setCellWidget(row, col_idx, cb)
                prev = cb.currentText()
                cb.blockSignals(True)
                cb.clear(); cb.addItems(cols)
                i = cb.findText(prev)
                cb.setCurrentIndex(i if i >= 0 else 0)
                cb.blockSignals(False)
            # Keep Plot spinbox range in sync
            spin = self.series_table.cellWidget(row, 4)
            if spin:
                spin.blockSignals(True); spin.setRange(1, n); spin.blockSignals(False)
        self.series_table.blockSignals(False)

    def _on_series_item_changed(self, item):
        """Handles itemChanged on the series table. Only acts when the row is
        fully constructed (all 6 cell widgets/items present) to avoid firing
        update_preview mid-insertion."""
        if item is None:
            return
        row = item.row()
        # A complete row has: cellWidget(0), cellWidget(1), item(2),
        # cellWidget(3), cellWidget(4), item(5)
        if (self.series_table.cellWidget(row, 0) is None or
                self.series_table.cellWidget(row, 1) is None or
                self.series_table.cellWidget(row, 3) is None or
                self.series_table.cellWidget(row, 4) is None or
                self.series_table.item(row, 5) is None):
            return
        # Only respond to label (col 2) and Y2 checkbox (col 5)
        if item.column() in (2, 5):
            # When label (col 2) is edited, rename the curve_styles key so
            # per-series style, color, opts etc. follow the new label.
            if item.column() == 2:
                new_label = item.text()
                # Find what the old label was — any curve_styles key that
                # isn't the new name and whose row still maps to this row.
                # Heuristic: scan curve_styles for a key that no other row
                # currently uses and rename it to new_label.
                current_labels = set()
                for r in range(self.series_table.rowCount()):
                    if r == row:
                        continue
                    it = self.series_table.item(r, 2)
                    current_labels.add(it.text() if it else f'Series {r+1}')
                # The old key is the one in curve_styles that is neither the
                # new label nor any other current row label.  Fallback: look
                # for the previous text stored by Qt before the edit — we do
                # this by finding any key that would be orphaned after rename.
                orphaned = [k for k in list(self.curve_styles)
                            if k not in current_labels and k != new_label]
                if len(orphaned) == 1:
                    old_label = orphaned[0]
                    self.curve_styles[new_label] = self.curve_styles.pop(old_label)
                elif new_label not in self.curve_styles:
                    # Try to inherit from a key with "Series N" pattern for this row
                    fallback_key = f'Series {row + 1}'
                    if fallback_key in self.curve_styles:
                        self.curve_styles[new_label] = self.curve_styles.pop(fallback_key)
            # When Y2 is checked for the first time, preserve the series color
            if item.column() == 5 and item.checkState() == Qt.CheckState.Checked:
                lbl_item = self.series_table.item(row, 2)
                label = lbl_item.text() if lbl_item else f'Series {row+1}'
                if label not in self.curve_styles:
                    # Copy current default color so it's preserved on y2 axis
                    self.curve_styles[label] = {
                        'color': getattr(self, 'curve_color', '#1f77b4'),
                        'linestyle': '-', 'marker': 'None',
                        'linewidth': 1.5, 'markersize': 6,
                        'marker_color': getattr(self, 'curve_color', '#1f77b4'),
                    }
            self._refresh_curve_select()
            self.update_preview()

    def _refresh_curve_select(self):
        """Sync the per-curve style combo with series labels on the active subplot.
        When multiple subplots exist, only series whose Plot spinbox matches the
        currently selected subplot in the Series tab are shown.
        """
        n = self.subplot_rows * self.subplot_cols
        active_sp = None
        if n > 1 and hasattr(self, 'series_curve_sp_active'):
            active_sp = self.series_curve_sp_active.currentIndex() + 1  # 1-based

        labels = []
        for row in range(self.series_table.rowCount()):
            if active_sp is not None:
                spin = self.series_table.cellWidget(row, 4)
                row_sp = spin.value() if spin else 1
                if row_sp != active_sp:
                    continue
            item = self.series_table.item(row, 2)
            labels.append(item.text() if item else f'Series {row+1}')

        self.curve_select.blockSignals(True)
        prev = self.curve_select.currentText()
        self.curve_select.clear()
        self.curve_select.addItems(labels)
        idx = self.curve_select.findText(prev)
        self.curve_select.setCurrentIndex(idx if idx >= 0 else 0)
        self.curve_select.blockSignals(False)
        self.load_curve_style()

    def _add_series_row(self):
        cols = sorted(self.datasets)
        row = self.series_table.rowCount()
        self.series_table.blockSignals(True)
        self.series_table.insertRow(row)

        # ── Determine sensible defaults (avoid duplicating row 0) ──────────────
        row0_x = ''
        row0_y = ''
        if row > 0:
            xcb0 = self.series_table.cellWidget(0, 0)
            ycb0 = self.series_table.cellWidget(0, 1)
            if xcb0: row0_x = xcb0.currentText()
            if ycb0: row0_y = ycb0.currentText()

        default_x_col = row0_x if (row0_x and row0_x in self.datasets) else (cols[0] if cols else '')

        row0_y_is_cat = self._is_categorical(self.datasets[row0_y]) if (row0_y and row0_y in self.datasets) else None
        default_y_col = ''
        # Pass 1: same type as row0-Y but different column
        for c in cols:
            if c == row0_y: continue
            if row0_y_is_cat is not None and self._is_categorical(self.datasets[c]) == row0_y_is_cat:
                default_y_col = c; break
        # Pass 2: any column different from row0-Y
        if not default_y_col:
            for c in cols:
                if c != row0_y:
                    default_y_col = c; break
        if not default_y_col:
            default_y_col = row0_y or (cols[0] if cols else '')

        # ── Build all widgets with their signals BLOCKED, then setCellWidget ───
        # X combo
        cb_x = QComboBox(); cb_x.blockSignals(True)
        cb_x.addItems(cols)
        idx_x = cb_x.findText(default_x_col)
        if idx_x >= 0: cb_x.setCurrentIndex(idx_x)
        cb_x.blockSignals(False)
        # Connect AFTER index is set so no spurious signal fires during construction
        cb_x.currentIndexChanged.connect(self._on_x_col_changed)
        self.series_table.setCellWidget(row, 0, cb_x)

        # Y combo
        cb_y = QComboBox(); cb_y.blockSignals(True)
        cb_y.addItems(cols)
        idx_y = cb_y.findText(default_y_col)
        if idx_y >= 0: cb_y.setCurrentIndex(idx_y)
        cb_y.blockSignals(False)
        cb_y.currentIndexChanged.connect(self.update_preview)
        cb_y.currentIndexChanged.connect(lambda _: self._update_label_placeholders())
        self.series_table.setCellWidget(row, 1, cb_y)

        # Label — explicitly set editable flag so double-click editing works reliably
        _lbl_item = QTableWidgetItem(f'Series {row+1}')
        _lbl_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
        self.series_table.setItem(row, 2, _lbl_item)

        # Type combo — constrained to the current plot mode's allowed types
        allowed_types = list(PLOT_MODE_GROUPS.get(
            self.plot_mode_combo.currentText() if hasattr(self, 'plot_mode_combo') else 'Standard',
            PER_SERIES_TYPES
        ))
        type_cb = QComboBox(); type_cb.addItems(allowed_types)
        if hasattr(self, 'chart_type_combo'):
            current_type = self.chart_type_combo.currentText()
            i = type_cb.findText(current_type)
            if i >= 0: type_cb.setCurrentIndex(i)
        type_cb.currentTextChanged.connect(self._on_series_row_type_changed)
        self.series_table.setCellWidget(row, 3, type_cb)

        # Plot spinbox — default to whichever subplot is active in the Subplots tab
        active_subplot = self.sp_active.currentIndex() + 1  # sp_active is 0-based, spinbox is 1-based
        plot_spin = QSpinBox()
        plot_spin.setRange(1, max(1, self.subplot_rows * self.subplot_cols))
        plot_spin.setValue(max(1, active_subplot))
        plot_spin.setMinimumWidth(36)
        plot_spin.valueChanged.connect(self.update_preview)
        plot_spin.valueChanged.connect(lambda _: self._filter_series_table_by_subplot())
        self.series_table.setCellWidget(row, 4, plot_spin)

        # Y2 checkbox item
        y2_item = QTableWidgetItem()
        y2_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        y2_item.setCheckState(Qt.CheckState.Unchecked)
        self.series_table.setItem(row, 5, y2_item)

        # Auto-assign a palette color to this series (stored in curve_styles)
        lbl = f'Series {row+1}'
        auto_color = self._palette_color(self._local_palette_index(row))
        existing = self.curve_styles.get(lbl, {})
        if not existing.get('color_locked', False):
            existing.setdefault('color', auto_color)
            existing.setdefault('marker_color', auto_color)
            self.curve_styles[lbl] = existing

        self.series_table.blockSignals(False)
        self._refresh_curve_select()
        self._filter_series_table_by_subplot()
        self.update_preview()

    def _on_x_col_changed(self):
        """Called when any X column combo changes. Captures sender immediately
        (self.sender() is only valid synchronously), then defers all logic via
        QTimer so the combo is off the call stack before any row manipulation."""
        from PyQt6.QtCore import QTimer
        sender = self.sender()
        # Guard: if a deferred call is already queued, don't queue another
        if getattr(self, '_x_col_change_pending', False):
            return
        self._x_col_change_pending = True
        QTimer.singleShot(0, lambda: self._on_x_col_changed_deferred(sender))

    def _on_x_col_changed_deferred(self, sender):
        """Actual type-mismatch logic, runs after signal call stack is clear."""
        self._x_col_change_pending = False
        n_subplots = self.subplot_rows * self.subplot_cols

        # Find which row the changed combo belongs to
        changed_row = -1
        if sender is not None:
            for r in range(self.series_table.rowCount()):
                if self.series_table.cellWidget(r, 0) is sender:
                    changed_row = r
                    break

        if changed_row < 0:
            self.update_preview(); return

        changed_spin = self.series_table.cellWidget(changed_row, 4)
        changed_subplot = (changed_spin.value() - 1) if (changed_spin and n_subplots > 1) else 0

        # Collect (row_index, is_categorical) for every row on the same subplot
        row_types = []
        for row in range(self.series_table.rowCount()):
            xcb = self.series_table.cellWidget(row, 0)
            if xcb is None: continue
            spin = self.series_table.cellWidget(row, 4)
            row_subplot = (spin.value() - 1) if (spin and n_subplots > 1) else 0
            if row_subplot != changed_subplot: continue
            col = xcb.currentText()
            if col not in self.datasets: continue
            row_types.append((row, self._is_categorical(self.datasets[col])))

        if len(row_types) < 2:
            self.update_preview(); return

        has_cat = any(t for _, t in row_types)
        has_num = any(not t for _, t in row_types)
        if not (has_cat and has_num):
            self.update_preview(); return

        # changed_type = the NEW type of the row that just changed
        changed_type = next((t for r, t in row_types if r == changed_row), row_types[-1][1])
        keep_name = 'categorical' if changed_type else 'numerical'
        drop_name = 'numerical' if changed_type else 'categorical'
        subplot_label = f'Subplot {changed_subplot + 1}' if n_subplots > 1 else 'this chart'

        ans = QMessageBox.question(
            self, 'Incompatible X types',
            f'In {subplot_label}, the selected X column is {keep_name}, '
            f'but other series use {drop_name} X data.\n\n'
            f'Remove the {drop_name} series and keep only {keep_name}?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if ans == QMessageBox.StandardButton.Yes:
            rows_to_remove = sorted(
                [r for r, t in row_types if t != changed_type],
                reverse=True
            )
            # Disconnect signals from widgets about to be destroyed
            for r in rows_to_remove:
                xcb = self.series_table.cellWidget(r, 0)
                ycb = self.series_table.cellWidget(r, 1)
                for w in (xcb, ycb):
                    if w is not None:
                        try: w.currentIndexChanged.disconnect()
                        except Exception: pass
            self.series_table.blockSignals(True)
            for r in rows_to_remove:
                self.series_table.removeRow(r)
            self.series_table.blockSignals(False)
            self._refresh_curve_select()
        else:
            # Revert the changed combo back to a column matching the OLD type
            old_type = not changed_type
            if sender is not None:
                sender.blockSignals(True)
                reverted = False
                for col in sorted(self.datasets):
                    if self._is_categorical(self.datasets[col]) == old_type:
                        idx = sender.findText(col)
                        if idx >= 0:
                            sender.setCurrentIndex(idx)
                            reverted = True
                            break
                if not reverted:
                    sender.setCurrentIndex(0)
                sender.blockSignals(False)

        self.update_preview()

    def _del_series_row(self):
        rows = sorted({idx.row() for idx in self.series_table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.series_table.removeRow(r)
        self._refresh_curve_select()
        self.update_preview()

    def _get_y2_cols_from_table(self):
        """Return list of Y column names whose Y2 checkbox is checked."""
        result = []
        for row in range(self.series_table.rowCount()):
            y2_item = self.series_table.item(row, 5)
            if y2_item and y2_item.checkState() == Qt.CheckState.Checked:
                ycb = self.series_table.cellWidget(row, 1)
                if ycb:
                    result.append(ycb.currentText())
        return result

    def _get_series_type(self, row):
        """Return the per-series chart type for a row (col 3 QComboBox)."""
        type_cb = self.series_table.cellWidget(row, 3)
        return type_cb.currentText() if type_cb else 'Line'

    def _get_series(self, primary_only=False):
        """Return list of (xdata, ydata, label, series_ct) for every valid series row.
        If primary_only=True, skip rows where Y2 checkbox is checked."""
        result = []
        for row in range(self.series_table.rowCount()):
            xcb = self.series_table.cellWidget(row, 0)
            ycb = self.series_table.cellWidget(row, 1)
            lbl_item = self.series_table.item(row, 2)
            if xcb is None or ycb is None: continue
            if primary_only:
                y2_item = self.series_table.item(row, 5)
                if y2_item and y2_item.checkState() == Qt.CheckState.Checked:
                    continue
            xc = xcb.currentText(); yc = ycb.currentText()
            if xc not in self.datasets or yc not in self.datasets: continue
            label = lbl_item.text() if lbl_item and lbl_item.text() else yc
            result.append((self.datasets[xc], self.datasets[yc], label, self._get_series_type(row)))
        return result

    def _get_series_full(self):
        """Return list of (xdata, ydata, label, xc, yc) — includes column names."""
        result = []
        for row in range(self.series_table.rowCount()):
            xcb = self.series_table.cellWidget(row, 0)
            ycb = self.series_table.cellWidget(row, 1)
            lbl_item = self.series_table.item(row, 2)
            if xcb is None or ycb is None: continue
            xc = xcb.currentText(); yc = ycb.currentText()
            if xc not in self.datasets or yc not in self.datasets: continue
            label = lbl_item.text() if lbl_item and lbl_item.text() else yc
            result.append((self.datasets[xc], self.datasets[yc], label, xc, yc))
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # CURVE STYLES
    # ═══════════════════════════════════════════════════════════════════════════
    def on_y_selection_changed(self):
        self.update_preview()

    def select_series_by_label(self, label):
        """Called when user clicks a plotted series on the canvas.

        Switches to the Series tab, highlights the matching curve, and also
        selects the matching row in the Data tab so option groups update.
        """
        # ── Series tab: select the curve for style editing ───────────────────
        idx = self.curve_select.findText(label)
        if idx >= 0:
            # Series tab is index 3 (Chart/Axes/Style/Series/Data/Annotations/Advanced)
            self.tabs.setCurrentIndex(3)
            if self.curve_select.currentIndex() == idx:
                self.load_curve_style()
            else:
                self.curve_select.setCurrentIndex(idx)

        # ── Data tab: also select the matching series table row ───────────────
        # This loads the per-series option groups (bar width, scatter size, etc.)
        for row in range(self.series_table.rowCount()):
            lbl_item = self.series_table.item(row, 2)
            if lbl_item and lbl_item.text() == label:
                # Make that subplot visible first
                spin = self.series_table.cellWidget(row, 4)
                if spin and self.subplot_rows * self.subplot_cols > 1:
                    subplot_idx = spin.value() - 1
                    self.series_sp_active.blockSignals(True)
                    self.series_sp_active.setCurrentIndex(subplot_idx)
                    self.series_sp_active.blockSignals(False)
                    self.series_curve_sp_active.blockSignals(True)
                    self.series_curve_sp_active.setCurrentIndex(subplot_idx)
                    self.series_curve_sp_active.blockSignals(False)
                    self._filter_series_table_by_subplot(subplot_idx)
                self.series_table.selectRow(row)
                self._refresh_curve_select()
                break

        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(f'Selected: {label}', 3000)

    def load_curve_style(self):
        curve = self.curve_select.currentText()
        s = self.curve_styles.get(curve, {})
        self.curve_color = s.get('color', '#1f77b4')
        self.curve_linestyle.blockSignals(True)
        self.curve_linestyle.setCurrentText(s.get('linestyle', '-'))
        self.curve_linestyle.blockSignals(False)
        self.curve_marker.blockSignals(True)
        self.curve_marker.setCurrentText(s.get('marker', 'None'))
        self.curve_marker.blockSignals(False)
        self.curve_linewidth.blockSignals(True)
        self.curve_linewidth.setValue(s.get('linewidth', 1.5))
        self.curve_linewidth.blockSignals(False)
        self.curve_markersize.blockSignals(True)
        self.curve_markersize.setValue(s.get('markersize', 6))
        self.curve_markersize.blockSignals(False)
        self.curve_marker_color = s.get('marker_color', self.curve_color)
        self.curve_color_label.setText('■')
        self.curve_color_label.setStyleSheet(f'color:{self.curve_color};font-size:16px;')
        self.curve_marker_color_label.setText('■')
        self.curve_marker_color_label.setStyleSheet(f'color:{self.curve_marker_color};font-size:16px;')
        self._refresh_lock_indicator()
        # Load per-series type options (fill, alpha, linewidth, etc.) for this series
        # and update which type-option group is visible.  Entirely driven by curve_select.
        if curve:
            self._load_series_options_by_label(curve)
            for row in range(self.series_table.rowCount()):
                item = self.series_table.item(row, 2)
                lbl = item.text() if item else f'Series {row+1}'
                if lbl == curve:
                    type_cb = self.series_table.cellWidget(row, 3)
                    if type_cb:
                        self._update_option_group_visibility(type_cb.currentText())
                    break

    def save_curve_style(self, lock_color=False):
        curve = self.curve_select.currentText()
        if curve:
            existing = self.curve_styles.get(curve, {})
            self.curve_styles[curve] = {
                'color': self.curve_color,
                'linestyle': self.curve_linestyle.currentText(),
                'marker': self.curve_marker.currentText(),
                'linewidth': self.curve_linewidth.value(),
                'markersize': self.curve_markersize.value(),
                'marker_color': self.curve_marker_color,
                'color_locked': existing.get('color_locked', False) or lock_color,
                # Preserve per-series type options so changing color/marker doesn't wipe them
                'opts': existing.get('opts', {}),
            }
            self._refresh_lock_indicator()
            self.update_preview()

    # ═══════════════════════════════════════════════════════════════════════════
    # SUBPLOTS
    # ═══════════════════════════════════════════════════════════════════════════
    def _get_series_for_subplot(self, subplot_idx):
        """Return (primary_series, y2_series) 4-tuples for the given subplot (0-based).
        Series rows are filtered by their Plot spinbox value (1-based == subplot_idx+1).
        When n==1 all rows belong to subplot 0 regardless of their Plot value."""
        from ui.tab_builders import WHOLE_CHART_TYPES
        n = self.subplot_rows * self.subplot_cols
        primary, secondary = [], []
        for row in range(self.series_table.rowCount()):
            xcb  = self.series_table.cellWidget(row, 0)
            ycb  = self.series_table.cellWidget(row, 1)
            lbl_item = self.series_table.item(row, 2)
            type_cb  = self.series_table.cellWidget(row, 3)
            plot_spin = self.series_table.cellWidget(row, 4)
            y2_item  = self.series_table.item(row, 5)
            if xcb is None or ycb is None: continue
            # Plot assignment filter (1-based; all go to 0 when n==1)
            row_plot = (plot_spin.value() - 1) if (plot_spin and n > 1) else 0
            if row_plot != subplot_idx: continue
            xc = xcb.currentText(); yc = ycb.currentText()
            if xc not in self.datasets or yc not in self.datasets: continue
            label = lbl_item.text() if lbl_item and lbl_item.text() else yc
            # Per-series chart type — use subplot's chart type if it's a whole-chart type
            sp_ct = self.subplot_chart_types.get(subplot_idx, 'Line')
            if sp_ct in WHOLE_CHART_TYPES:
                sct = sp_ct
            else:
                sct = type_cb.currentText() if type_cb else 'Line'
            tup = (self.datasets[xc], self.datasets[yc], label, sct)
            is_y2 = bool(y2_item and y2_item.checkState() == Qt.CheckState.Checked)
            if is_y2:
                secondary.append(tup)
            else:
                primary.append(tup)
        return primary, secondary

    def _get_series_row_offset(self, subplot_idx):
        """Return the global series-table row index of the first series assigned
        to `subplot_idx`. Used to index palette colours correctly across subplots."""
        n = self.subplot_rows * self.subplot_cols
        for row in range(self.series_table.rowCount()):
            xcb  = self.series_table.cellWidget(row, 0)
            ycb  = self.series_table.cellWidget(row, 1)
            plot_spin = self.series_table.cellWidget(row, 4)
            if xcb is None or ycb is None:
                continue
            row_plot = (plot_spin.value() - 1) if (plot_spin and n > 1) else 0
            if row_plot == subplot_idx:
                xc = xcb.currentText(); yc = ycb.currentText()
                if xc in self.datasets and yc in self.datasets:
                    return row
        return 0

    def _get_col_names_for_subplot(self, subplot_idx):
        """Return (x_cols, y_cols, y2_cols) — lists of column name strings for
        the given subplot. Used to build default axis labels when none are set."""
        n = self.subplot_rows * self.subplot_cols
        x_cols, y_cols, y2_cols = [], [], []
        for row in range(self.series_table.rowCount()):
            xcb  = self.series_table.cellWidget(row, 0)
            ycb  = self.series_table.cellWidget(row, 1)
            plot_spin = self.series_table.cellWidget(row, 4)
            y2_item  = self.series_table.item(row, 5)
            if xcb is None or ycb is None: continue
            row_plot = (plot_spin.value() - 1) if (plot_spin and n > 1) else 0
            if row_plot != subplot_idx: continue
            xc = xcb.currentText(); yc = ycb.currentText()
            if xc not in self.datasets or yc not in self.datasets: continue
            is_y2 = bool(y2_item and y2_item.checkState() == Qt.CheckState.Checked)
            if xc not in x_cols: x_cols.append(xc)
            if is_y2:
                if yc not in y2_cols: y2_cols.append(yc)
            else:
                if yc not in y_cols: y_cols.append(yc)
        return x_cols, y_cols, y2_cols

    def _update_label_placeholders(self):
        """Update placeholder text on Axes tab inputs to reflect auto-derived defaults.
        Never writes into stored dicts — user values are empty string = auto."""
        if not hasattr(self, 'sp_title_input') or not hasattr(self, 'sp_active'):
            return
        idx = self.sp_active.currentIndex()
        if idx < 0: idx = 0
        x_cols, y_cols, y2_cols = self._get_col_names_for_subplot(idx)

        # Subplot title placeholder: "Subplot N"
        self.sp_title_input.setPlaceholderText(f'Subplot {idx+1}')

        # X/Y label placeholders: derived from column names
        self.xlabel_input.setPlaceholderText(x_cols[0] if x_cols else 'X label')
        self.ylabel_input.setPlaceholderText(', '.join(y_cols) if y_cols else 'Y label')
        self.y2label_input.setPlaceholderText(', '.join(y2_cols) if y2_cols else 'Y2 label')

    def on_subplot_layout_changed(self, n_override=None):
        r, c = self.sp_rows.value(), self.sp_cols.value()
        self.subplot_rows, self.subplot_cols = r, c
        # When spinboxes are changed manually (not from mosaic dialog), clear mosaic
        if n_override is None:
            self._subplot_mosaic = None
        n = n_override if n_override is not None else r * c
        # Ensure all dicts have entries for every subplot slot
        for i in range(n):
            self.subplot_chart_opts.setdefault(i, self._default_chart_opts())
            self.subplot_chart_types.setdefault(i, 'Line')
            self.subplot_plot_modes.setdefault(i, 'Standard')
            self.sp_titles.setdefault(i, '')
            self.subplot_title_show.setdefault(i, True)
            self.subplot_title_font.setdefault(i, 'sans-serif')
            self.subplot_title_size.setdefault(i, 11)
            self.subplot_title_color.setdefault(i, '#000000')
            self.subplot_xlabels.setdefault(i, '')
            self.subplot_xlabel_show.setdefault(i, True)
            self.subplot_ylabels.setdefault(i, '')
            self.subplot_ylabel_show.setdefault(i, True)
            self.subplot_y2labels.setdefault(i, '')
            self.subplot_y2label_show.setdefault(i, True)
            self.subplot_legends.setdefault(i, True)
            self.subplot_legend_locs.setdefault(i, 'best')
            self.subplot_legend_x.setdefault(i, 0.01)
            self.subplot_legend_y.setdefault(i, 0.99)
            self.subplot_legend_fontsize.setdefault(i, 9)
            self.subplot_legend_ncols.setdefault(i, 1)
            self.subplot_legend_frameon.setdefault(i, True)
            self.subplot_legend_color.setdefault(i, '#000000')
            self.subplot_legend_facecolor.setdefault(i, '#ffffff')
            self.subplot_legend_alpha.setdefault(i, 0.8)
            self.subplot_legend_edgecolor.setdefault(i, '#cccccc')
            self.subplot_xlims.setdefault(i, None)
            self.subplot_ylims.setdefault(i, None)
            self.subplot_y2lims.setdefault(i, None)
            self.subplot_xscales.setdefault(i, 'linear')
            self.subplot_yscales.setdefault(i, 'linear')
            self.subplot_xtick_sizes.setdefault(i, 9)
            self.subplot_ytick_sizes.setdefault(i, 9)
            self.subplot_xtick_dir.setdefault(i, 'out')
            self.subplot_ytick_dir.setdefault(i, 'out')
            self.subplot_xtick_minor.setdefault(i, False)
            self.subplot_ytick_minor.setdefault(i, False)
            self.subplot_xtick_rotation.setdefault(i, 0)
            self.subplot_ytick_rotation.setdefault(i, 0)
            self.subplot_xtick_step.setdefault(i, 0.0)
            self.subplot_ytick_step.setdefault(i, 0.0)
            self.subplot_x_formatter.setdefault(i, 'auto')
            self.subplot_y_formatter.setdefault(i, 'auto')
            self.subplot_xticks_show.setdefault(i, True)
            self.subplot_yticks_show.setdefault(i, True)
            self.subplot_ann_visible.setdefault(i, True)
        # Prune entries beyond current grid
        all_dicts = (self.subplot_chart_types, self.subplot_plot_modes, self.subplot_chart_opts,
                     self.sp_titles, self.subplot_title_show,
                     self.subplot_title_font, self.subplot_title_size, self.subplot_title_color,
                     self.subplot_xlabels, self.subplot_xlabel_show,
                     self.subplot_ylabels, self.subplot_ylabel_show,
                     self.subplot_y2labels, self.subplot_y2label_show,
                     self.subplot_legends, self.subplot_legend_locs,
                     self.subplot_legend_x, self.subplot_legend_y,
                     self.subplot_legend_fontsize, self.subplot_legend_ncols,
                     self.subplot_legend_frameon, self.subplot_legend_color,
                     self.subplot_legend_facecolor, self.subplot_legend_alpha,
                     self.subplot_legend_edgecolor,
                     self.subplot_xlims, self.subplot_ylims, self.subplot_y2lims,
                     self.subplot_xscales, self.subplot_yscales,
                     self.subplot_xtick_sizes, self.subplot_ytick_sizes,
                     self.subplot_xtick_dir, self.subplot_ytick_dir,
                     self.subplot_xtick_minor, self.subplot_ytick_minor,
                     self.subplot_xtick_rotation, self.subplot_ytick_rotation,
                     self.subplot_xtick_step, self.subplot_ytick_step,
                     self.subplot_x_formatter, self.subplot_y_formatter,
                     self.subplot_xticks_show, self.subplot_yticks_show,
                     self.subplot_ann_visible)
        for i in list(self.subplot_chart_types):
            if i >= n:
                for d in all_dicts:
                    d.pop(i, None)
        # Update Plot spinbox range on every series row
        self._update_plot_spin_ranges(n)
        # Rebuild all subplot selectors — per-tab rows stay hidden (global combo handles it)
        for combo, vis_attr in [
            (self.sp_active,              '_axes_sp_row_widget'),
            (self.series_sp_active,       '_series_sp_row_widget'),
            (self.ann_sp_active,          '_ann_sp_row_widget'),
            (self.series_curve_sp_active, '_series_curve_sp_row_widget'),
        ]:
            combo.blockSignals(True); combo.clear()
            for i in range(n): combo.addItem(f'Subplot {i+1}')
            combo.setCurrentIndex(0)          # set index while signals still blocked
            combo.blockSignals(False)
            widget = getattr(self, vis_attr, None)
            if widget: widget.setVisible(False)   # always hidden; global_sp_active used instead
        # Rebuild and show/hide the global subplot selector above the tabs
        if hasattr(self, 'global_sp_active'):
            self.global_sp_active.blockSignals(True)
            self.global_sp_active.clear()
            for i in range(n): self.global_sp_active.addItem(f'Subplot {i+1}')
            self.global_sp_active.setCurrentIndex(0)  # set index while signals still blocked
            self.global_sp_active.blockSignals(False)
        if hasattr(self, '_global_sp_container'):
            self._global_sp_container.setVisible(n > 1)
        if hasattr(self, '_axes_title_section'):
            _was_single = not self._axes_title_section.isVisible()
            self._axes_title_section.setVisible(n > 1)
            # Switching 1 → many: promote the single-subplot title to the main chart title
            if _was_single and n > 1 and hasattr(self, 'title_input'):
                existing = self.title_input.text().strip()
                if not existing:
                    # Use whatever the user had typed as the subplot title (subplot 0)
                    single_title = self.sp_titles.get(0, '').strip()
                    if not single_title:
                        single_title = self.title_input.placeholderText() or 'Main title'
                    self.title_input.setText(single_title)
                    if hasattr(self, 'title_check'):
                        self.title_check.setChecked(True)
        self.on_active_subplot_changed()
        self._filter_series_table_by_subplot(0)
        # Sync ann visibility checkbox for subplot 0
        if hasattr(self, 'ann_subplot_visible'):
            self.ann_subplot_visible.blockSignals(True)
            self.ann_subplot_visible.setChecked(self.subplot_ann_visible.get(0, True))
            self.ann_subplot_visible.blockSignals(False)
        self.update_preview()


    def _update_plot_spin_ranges(self, n=None):
        """Update the max of every Plot spinbox to match the current subplot count."""
        if n is None: n = self.subplot_rows * self.subplot_cols
        n = max(1, n)
        for row in range(self.series_table.rowCount()):
            spin = self.series_table.cellWidget(row, 4)
            if spin:
                spin.blockSignals(True)
                spin.setRange(1, n)
                spin.blockSignals(False)

    def _filter_series_table_by_subplot(self, subplot_idx=None):
        """Show only series rows that belong to the active subplot.
        When there is only 1 subplot, all rows are shown.
        Clears the Qt selection after hiding/showing so that stale selections
        from the previous subplot never bleed into _on_series_selection_changed.
        """
        if not hasattr(self, 'series_table'):
            return
        n = self.subplot_rows * self.subplot_cols
        if n <= 1:
            # Single subplot — show everything and auto-select the first row
            for row in range(self.series_table.rowCount()):
                self.series_table.setRowHidden(row, False)
            self.series_table.blockSignals(True)
            self.series_table.clearSelection()
            for row in range(self.series_table.rowCount()):
                self.series_table.selectRow(row)
                break
            self.series_table.blockSignals(False)
            self._on_series_selection_changed()
            return
        if subplot_idx is None:
            subplot_idx = self.series_sp_active.currentIndex()
        target = subplot_idx + 1   # spinbox is 1-based
        # Block signals while adjusting visibility so itemSelectionChanged
        # does not fire with a partially-updated hidden set.
        self.series_table.blockSignals(True)
        for row in range(self.series_table.rowCount()):
            spin = self.series_table.cellWidget(row, 4)
            row_subplot = spin.value() if spin else 1
            self.series_table.setRowHidden(row, row_subplot != target)
        self.series_table.clearSelection()
        # Auto-select the first visible row so option groups always reflect a
        # real series when the user switches subplots.
        for row in range(self.series_table.rowCount()):
            if not self.series_table.isRowHidden(row):
                self.series_table.selectRow(row)
                break
        self.series_table.blockSignals(False)
        # Manually trigger option load for the now-selected row (signals were blocked)
        self._on_series_selection_changed()

    def on_active_subplot_changed(self):
        """Load per-subplot state into the Axes and Annotations tab widgets.
        Also keeps ann_sp_active and series_sp_active in sync with sp_active."""
        idx = self.sp_active.currentIndex()
        if idx < 0: idx = 0

        # ── Sync all subplot selectors silently (including global top-bar combo) ─
        for combo in (self.ann_sp_active, self.series_sp_active, self.series_curve_sp_active):
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        if hasattr(self, 'global_sp_active'):
            self.global_sp_active.blockSignals(True)
            self.global_sp_active.setCurrentIndex(idx)
            self.global_sp_active.blockSignals(False)

        def _load(widget, value):
            widget.blockSignals(True)
            if hasattr(widget, 'setChecked'):   widget.setChecked(value)
            elif hasattr(widget, 'setText'):    widget.setText(value)
            elif hasattr(widget, 'setValue'):   widget.setValue(value)
            elif hasattr(widget, 'setCurrentText'): widget.setCurrentText(value)
            widget.blockSignals(False)

        # Title
        _load(self.title_show_check, self.subplot_title_show.get(idx, True))
        _load(self.sp_title_input, self.sp_titles.get(idx, ''))
        _load(self.sp_title_font, self.subplot_title_font.get(idx, 'sans-serif'))
        _load(self.sp_title_size, self.subplot_title_size.get(idx, 11))
        sp_tc = self.subplot_title_color.get(idx, '#000000')
        self.sp_title_color = sp_tc
        if hasattr(self, 'sp_title_color_label'):
            self.sp_title_color_label.setStyleSheet(f'color:{sp_tc};font-size:16px;')
        # X axis
        _load(self.xlabel_show_check, self.subplot_xlabel_show.get(idx, True))
        _load(self.xlabel_input,      self.subplot_xlabels.get(idx, ''))
        xlim = self.subplot_xlims.get(idx)
        _load(self.x_auto,  xlim is None)
        _load(self.x_min,   xlim[0] if xlim else 0.0)
        _load(self.x_max,   xlim[1] if xlim else 1.0)
        self._set_scale_rb(self.xscale_group, self.subplot_xscales.get(idx, 'linear'))
        _load(self.xtick_size, self.subplot_xtick_sizes.get(idx, 9))
        _load(self.xtick_dir,      self.subplot_xtick_dir.get(idx, 'out'))
        _load(self.xtick_minor,    self.subplot_xtick_minor.get(idx, False))
        _load(self.xtick_rotation, self.subplot_xtick_rotation.get(idx, 0))
        _load(self.xtick_step,     self.subplot_xtick_step.get(idx, 0.0))
        _load(self.x_formatter,    self.subplot_x_formatter.get(idx, 'auto'))
        _load(self.xticks_show,    self.subplot_xticks_show.get(idx, True))
        # Y axis
        _load(self.ylabel_show_check, self.subplot_ylabel_show.get(idx, True))
        _load(self.ylabel_input,      self.subplot_ylabels.get(idx, ''))
        ylim = self.subplot_ylims.get(idx)
        _load(self.y_auto,  ylim is None)
        _load(self.y_min,   ylim[0] if ylim else 0.0)
        _load(self.y_max,   ylim[1] if ylim else 1.0)
        self._set_scale_rb(self.yscale_group, self.subplot_yscales.get(idx, 'linear'))
        _load(self.ytick_size, self.subplot_ytick_sizes.get(idx, 9))
        _load(self.ytick_dir,      self.subplot_ytick_dir.get(idx, 'out'))
        _load(self.ytick_minor,    self.subplot_ytick_minor.get(idx, False))
        _load(self.ytick_rotation, self.subplot_ytick_rotation.get(idx, 0))
        _load(self.ytick_step,     self.subplot_ytick_step.get(idx, 0.0))
        _load(self.y_formatter,    self.subplot_y_formatter.get(idx, 'auto'))
        _load(self.yticks_show,    self.subplot_yticks_show.get(idx, True))
        _load(self.equal_scale_check, self.subplot_equal_aspect.get(idx, False))
        # Y2 axis
        _load(self.y2label_show_check, self.subplot_y2label_show.get(idx, True))
        _load(self.y2label_input,      self.subplot_y2labels.get(idx, ''))
        y2lim = self.subplot_y2lims.get(idx)
        _load(self.y2_auto, y2lim is None)
        _load(self.y2_min,  y2lim[0] if y2lim else 0.0)
        _load(self.y2_max,  y2lim[1] if y2lim else 1.0)
        # Legend
        _load(self.legend_show_check, self.subplot_legends.get(idx, True))
        loc = self.subplot_legend_locs.get(idx, 'best')
        i_loc = self.legend_pos.findText(loc)
        self.legend_pos.blockSignals(True)
        self.legend_pos.setCurrentIndex(i_loc if i_loc >= 0 else 0)
        self.legend_pos.blockSignals(False)
        _load(self.legend_x, self.subplot_legend_x.get(idx, 0.01))
        _load(self.legend_y, self.subplot_legend_y.get(idx, 0.99))
        _load(self.legend_fontsize, self.subplot_legend_fontsize.get(idx, 9))
        _load(self.legend_ncols, self.subplot_legend_ncols.get(idx, 1))
        _load(self.legend_frameon, self.subplot_legend_frameon.get(idx, True))
        # Legend colors
        for attr, sw_attr, default in [
            ('legend_color',     'legend_color_sw',     '#000000'),
            ('legend_facecolor', 'legend_facecolor_sw', '#ffffff'),
            ('legend_edgecolor', 'legend_edgecolor_sw', '#cccccc'),
        ]:
            val = getattr(self, attr.replace('legend_', 'subplot_legend_'), {}).get(idx, default)
            # use the per-subplot dicts
            val = {
                'legend_color':     self.subplot_legend_color,
                'legend_facecolor': self.subplot_legend_facecolor,
                'legend_edgecolor': self.subplot_legend_edgecolor,
            }[attr].get(idx, default)
            setattr(self, attr, val)
            sw = getattr(self, sw_attr, None)
            if sw: sw.setStyleSheet(f'color:{val};font-size:15px;')
        _load(self.legend_alpha, self.subplot_legend_alpha.get(idx, 0.8))

        self._update_label_placeholders()
        # Refresh annotation-tab visibility and list to match
        visible = self.subplot_ann_visible.get(idx, True)
        self.ann_subplot_visible.blockSignals(True)
        self.ann_subplot_visible.setChecked(visible)
        self.ann_subplot_visible.blockSignals(False)
        self.refresh_annotation_list()
        # Filter series table to only show rows for this subplot
        self._filter_series_table_by_subplot(idx)
        # Load per-subplot chart option group values into their widgets
        self._load_chart_opts(idx)

        # ── Sync chart_type_combo / plot_mode_combo to this subplot's state ─────
        # For whole-chart types (Polar, Heatmap, Pie, etc.) the type lives in
        # subplot_chart_types, not in the series-table rows, so we must push it
        # into chart_type_combo explicitly whenever the active subplot changes.
        from ui.tab_builders import WHOLE_CHART_TYPES
        # Sync plot_mode_combo to the stored mode for this subplot
        if hasattr(self, 'plot_mode_combo'):
            stored_mode = self.subplot_plot_modes.get(idx, 'Standard')
            self.plot_mode_combo.blockSignals(True)
            mi = self.plot_mode_combo.findText(stored_mode)
            if mi >= 0:
                self.plot_mode_combo.setCurrentIndex(mi)
            self.plot_mode_combo.blockSignals(False)
            # Do NOT call _on_plot_mode_changed here: it resets type combos to
            # allowed[0] (Line) and overwrites option-group visibility, undoing
            # what _filter_series_table_by_subplot/_on_series_selection_changed
            # already set correctly for the selected row.
        sp_ct = self.subplot_chart_types.get(idx, None)
        if sp_ct in WHOLE_CHART_TYPES and hasattr(self, 'chart_type_combo'):
            self.chart_type_combo.blockSignals(True)
            i = self.chart_type_combo.findText(sp_ct)
            if i >= 0:
                self.chart_type_combo.setCurrentIndex(i)
            self.chart_type_combo.blockSignals(False)
            self._update_option_group_visibility(sp_ct)
        # Keep curve_select in the Series tab filtered to this subplot
        self._refresh_curve_select()

    # ── Axes tab save-back handlers ──────────────────────────────────────────
    def _save_axes_state(self):
        """Read all Axes tab widgets and persist to the current subplot's dicts.
        Legend and subplot-title widgets now live in the Annotations tab and
        use ann_sp_active; all other axes widgets still use sp_active."""
        idx = self.sp_active.currentIndex()
        if idx < 0: idx = 0
        # Legend and subplot title are in the Annotations tab — use that selector
        ann_idx = self.ann_sp_active.currentIndex()
        if ann_idx < 0: ann_idx = 0
        self.sp_titles[ann_idx]            = self.sp_title_input.text().strip()
        self.subplot_title_show[ann_idx]   = self.title_show_check.isChecked()
        self.subplot_title_font[ann_idx]   = self.sp_title_font.currentText()
        self.subplot_title_size[ann_idx]   = self.sp_title_size.value()
        self.subplot_title_color[ann_idx]  = self.sp_title_color
        self.subplot_legends[ann_idx]      = self.legend_show_check.isChecked()
        self.subplot_legend_locs[ann_idx]  = self.legend_pos.currentText()
        self.subplot_legend_x[ann_idx]     = self.legend_x.value()
        self.subplot_legend_y[ann_idx]     = self.legend_y.value()
        self.subplot_legend_fontsize[ann_idx] = self.legend_fontsize.value()
        self.subplot_legend_ncols[ann_idx] = self.legend_ncols.value()
        self.subplot_legend_frameon[ann_idx] = self.legend_frameon.isChecked()
        self.subplot_legend_color[ann_idx]   = getattr(self, 'legend_color', '#000000')
        self.subplot_legend_facecolor[ann_idx] = getattr(self, 'legend_facecolor', '#ffffff')
        self.subplot_legend_alpha[ann_idx]   = self.legend_alpha.value()
        self.subplot_legend_edgecolor[ann_idx] = getattr(self, 'legend_edgecolor', '#cccccc')
        # Axes-tab fields use sp_active
        self.subplot_xlabels[idx]      = self.xlabel_input.text().strip()
        self.subplot_xlabel_show[idx]  = self.xlabel_show_check.isChecked()
        self.subplot_ylabels[idx]      = self.ylabel_input.text().strip()
        self.subplot_ylabel_show[idx]  = self.ylabel_show_check.isChecked()
        self.subplot_y2labels[idx]     = self.y2label_input.text().strip()
        self.subplot_y2label_show[idx] = self.y2label_show_check.isChecked()
        self.subplot_xlims[idx]  = None if self.x_auto.isChecked() else (self.x_min.value(), self.x_max.value())
        self.subplot_ylims[idx]  = None if self.y_auto.isChecked() else (self.y_min.value(), self.y_max.value())
        self.subplot_y2lims[idx] = None if self.y2_auto.isChecked() else (self.y2_min.value(), self.y2_max.value())
        self.subplot_xscales[idx]       = self._get_xscale()
        self.subplot_yscales[idx]       = self._get_yscale()
        self.subplot_xtick_sizes[idx]   = self.xtick_size.value()
        self.subplot_ytick_sizes[idx]   = self.ytick_size.value()
        self.subplot_xtick_dir[idx]     = self.xtick_dir.currentText()
        self.subplot_ytick_dir[idx]     = self.ytick_dir.currentText()
        self.subplot_xtick_minor[idx]   = self.xtick_minor.isChecked()
        self.subplot_ytick_minor[idx]   = self.ytick_minor.isChecked()
        self.subplot_xtick_rotation[idx]= self.xtick_rotation.value()
        self.subplot_ytick_rotation[idx]= self.ytick_rotation.value()
        self.subplot_xtick_step[idx]    = self.xtick_step.value()
        self.subplot_ytick_step[idx]    = self.ytick_step.value()
        self.subplot_x_formatter[idx]   = self.x_formatter.currentText()
        self.subplot_y_formatter[idx]   = self.y_formatter.currentText()
        self.subplot_xticks_show[idx]   = self.xticks_show.isChecked()
        self.subplot_yticks_show[idx]   = self.yticks_show.isChecked()
        self.subplot_equal_aspect[idx]  = self.equal_scale_check.isChecked()
        self.update_preview()

    # Legacy aliases kept so existing signal connections don't need changes
    def _on_sp_chart_type_changed(self, ct):
        idx = self.sp_active.currentIndex()
        if idx < 0: idx = 0
        self.subplot_chart_types[idx] = ct
        self.update_preview()

    def _pick_sp_title_color(self):
        cur = getattr(self, 'sp_title_color', '#000000')
        col = _show_color_dialog(QColor(cur), self, palette_colors=self._active_palette_colors())
        if col.isValid():
            self.sp_title_color = col.name()
            self.sp_title_color_label.setStyleSheet(f'color:{col.name()};font-size:16px;')
            self._save_axes_state()
            self.update_preview()

    def _pick_legend_color(self, target):
        """Pick color for legend text / background / edge."""
        mapping = {
            'text': ('legend_color',     'legend_color_sw'),
            'bg':   ('legend_facecolor', 'legend_facecolor_sw'),
            'edge': ('legend_edgecolor', 'legend_edgecolor_sw'),
        }
        attr, sw_attr = mapping[target]
        cur = getattr(self, attr, '#000000')
        col = _show_color_dialog(QColor(cur), self, palette_colors=self._active_palette_colors())
        if col.isValid():
            setattr(self, attr, col.name())
            sw = getattr(self, sw_attr, None)
            if sw:
                sw.setStyleSheet(f'color:{col.name()};font-size:15px;')
            self._on_sp_legend_changed()

    def _on_sp_title_changed(self):       self._save_axes_state(); self.update_preview()
    def _on_sp_title_show_changed(self):  self._save_axes_state()
    def _on_sp_xlabel_changed(self):      self._save_axes_state()
    def _on_sp_xlabel_show_changed(self): self._save_axes_state()
    def _on_sp_ylabel_changed(self):      self._save_axes_state()
    def _on_sp_ylabel_show_changed(self): self._save_axes_state()
    def _on_sp_y2label_changed(self):     self._save_axes_state()
    def _on_sp_y2label_show_changed(self):self._save_axes_state()
    def _on_sp_legend_changed(self):      self._save_axes_state()
    def _on_sp_lim_changed(self):         self._save_axes_state()

    # ── Global subplot selector (above the tabs) ────────────────────────────
    def _on_global_sp_changed(self, idx):
        """Global subplot selector in the top bar changed — sync all tab selectors."""
        if idx < 0:
            return
        for combo in (self.sp_active, self.series_sp_active, self.ann_sp_active, self.series_curve_sp_active):
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        self.on_active_subplot_changed()

    # ── Series-tab subplot selector ──────────────────────────────────────────
    def _on_series_subplot_changed(self, idx):
        """Data-tab subplot selector changed.

        1. Silently sync the other selectors so they stay consistent.
        2. Save chart opts for the OLD subplot, load chart opts for the NEW one.
        3. Update plot_mode_combo to this subplot's stored mode (silently).
        4. Filter the series table to show only this subplot's rows.
        """
        if idx < 0:
            return
        # Save current widget values into the OLD subplot before switching
        old_idx = self.sp_active.currentIndex()
        if old_idx >= 0:
            self._save_chart_opts(old_idx)
        # Keep all selectors in sync silently
        for combo in (self.sp_active, self.ann_sp_active, self.series_curve_sp_active):
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        if hasattr(self, 'global_sp_active'):
            self.global_sp_active.blockSignals(True)
            self.global_sp_active.setCurrentIndex(idx)
            self.global_sp_active.blockSignals(False)
        # Load chart opts for the new subplot into the widgets
        self._load_chart_opts(idx)
        # Restore the plot mode for this subplot
        if hasattr(self, 'plot_mode_combo'):
            stored_mode = self.subplot_plot_modes.get(idx, 'Standard')
            self.plot_mode_combo.blockSignals(True)
            mi = self.plot_mode_combo.findText(stored_mode)
            if mi >= 0:
                self.plot_mode_combo.setCurrentIndex(mi)
            self.plot_mode_combo.blockSignals(False)
            # Do NOT call _on_plot_mode_changed here — same reason as
            # on_active_subplot_changed: it resets series types to Line.
        # Filter table and auto-select first row
        self._filter_series_table_by_subplot(idx)
        # Keep curve_select in the Series tab filtered to this subplot
        self._refresh_curve_select()

    # ── Series-tab (Per-Curve) subplot selector ───────────────────────────────
    def _on_series_curve_sp_changed(self, idx):
        """Series tab subplot selector changed.

        Only purpose: keep the other selectors in sync and refresh curve_select
        so it shows only the series belonging to this subplot.
        Must NOT call _on_plot_mode_changed — that rewrites type combos and
        can inadvertently reset series types (e.g. Bar -> Line).
        """
        if idx < 0:
            return
        for combo in (self.sp_active, self.series_sp_active, self.ann_sp_active):
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        if hasattr(self, 'global_sp_active'):
            self.global_sp_active.blockSignals(True)
            self.global_sp_active.setCurrentIndex(idx)
            self.global_sp_active.blockSignals(False)
        # Keep the Data-tab series table filtered to the same subplot
        self._filter_series_table_by_subplot(idx)
        # Refresh curve_select to show only series on this subplot
        self._refresh_curve_select()

    # ── Annotations-tab subplot selector ─────────────────────────────────────
    def _on_ann_subplot_changed(self, idx):
        """Annotations-tab subplot selector changed — sync all selectors and reload widgets."""
        if idx < 0: return
        self.sp_active.blockSignals(True)
        self.sp_active.setCurrentIndex(idx)
        self.sp_active.blockSignals(False)
        self.series_sp_active.blockSignals(True)
        self.series_sp_active.setCurrentIndex(idx)
        self.series_sp_active.blockSignals(False)
        self.series_curve_sp_active.blockSignals(True)
        self.series_curve_sp_active.setCurrentIndex(idx)
        self.series_curve_sp_active.blockSignals(False)
        self.on_active_subplot_changed()

    def _on_ann_subplot_visibility_changed(self, state):
        """Toggle visibility of all annotations on the current subplot."""
        idx = self.ann_sp_active.currentIndex()
        if idx < 0: idx = 0
        self.subplot_ann_visible[idx] = bool(state)
        self.update_preview()

    def _open_subplot_config_dialog(self):
        """Open a visual subplot layout picker with a custom mosaic editor."""
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                                     QLabel, QDialogButtonBox, QPushButton, QWidget,
                                     QCheckBox, QTabWidget, QSpinBox, QSizePolicy,
                                     QScrollArea, QFrame)

        # (label, rows, cols, mosaic_or_None)
        LAYOUTS = [
            ('Single',       1, 1, None),
            ('1 × 2',        1, 2, None),
            ('1 × 3',        1, 3, None),
            ('2 × 1',        2, 1, None),
            ('2 × 2',        2, 2, None),
            ('2 × 3',        2, 3, None),
            ('3 × 1',        3, 1, None),
            ('3 × 2',        3, 2, None),
            ('3 × 3',        3, 3, None),
            ('1 top\n2 down',   2, 2, [['A','A'],['B','C']]),
            ('2 top\n1 down',   2, 2, [['A','B'],['C','C']]),
            ('1 left\n2 right', 2, 2, [['A','B'],['A','C']]),
            ('2 left\n1 right', 2, 2, [['A','C'],['B','C']]),
            ('1 top\n3 down',   2, 3, [['A','A','A'],['B','C','D']]),
            ('3 top\n1 down',   2, 3, [['A','B','C'],['D','D','D']]),
            ('2×2 mosaic\n1+1+2', 2, 2, [['A','B'],['C','C']]),
            ('3 rows\n1 wide top', 3, 2, [['A','A'],['B','C'],['D','E']]),
            ('3 rows\n1 wide bot', 3, 2, [['A','B'],['C','D'],['E','E']]),
        ]

        # ── Colour palette for custom editor cells ────────────────────────────
        CELL_COLOURS = ['#c8d8f0','#f0c8d8','#d8f0c8','#f0eac8',
                        '#e8c8f0','#c8f0ee','#f5d7b5','#d8d8d8']

        dlg = QDialog(self)
        dlg.setWindowTitle('Subplot Layout')
        dlg.setMinimumWidth(620); dlg.setMinimumHeight(520)
        dlg_lay = QVBoxLayout(dlg)

        inner_tabs = QTabWidget()
        dlg_lay.addWidget(inner_tabs)

        # ══════════════════════════════════════════════════════════════════════
        # TAB 1 — Presets gallery
        # ══════════════════════════════════════════════════════════════════════
        presets_w = QWidget(); presets_lay = QVBoxLayout(presets_w)

        def _make_preview(rows, cols, mosaic, size=(88,60)):
            w = QWidget(); w.setFixedSize(*size)
            g = QGridLayout(w); g.setSpacing(2); g.setContentsMargins(3,3,3,3)
            style = 'background:#cce;border:1px solid #77a;font-size:8px;border-radius:2px;'
            if mosaic is None:
                for r in range(rows):
                    for c in range(cols):
                        lbl = QLabel(str(r*cols+c+1))
                        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        lbl.setStyleSheet(style); g.addWidget(lbl, r, c)
            else:
                seen = {}
                for ri, row in enumerate(mosaic):
                    for ci, cell in enumerate(row):
                        if cell not in seen: seen[cell] = [ri, ci, ri, ci]
                        else:
                            seen[cell][2] = max(seen[cell][2], ri)
                            seen[cell][3] = max(seen[cell][3], ci)
                for idx_c, (cell, (r0,c0,r1,c1)) in enumerate(seen.items()):
                    lbl = QLabel(str(idx_c+1))
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl.setStyleSheet(style)
                    g.addWidget(lbl, r0, c0, r1-r0+1, c1-c0+1)
            return w

        selected_preset = [0]
        card_group = []   # list of (preview_btn, label_btn) pairs

        per_row = 5
        grid_w = QWidget(); grid = QGridLayout(grid_w); grid.setSpacing(10)

        SELECTED_BORDER = '2px solid #3378ff'
        NORMAL_BORDER   = '1px solid #aaa'
        SELECTED_BG     = '#e8f0ff'
        NORMAL_BG       = 'transparent'

        def _select_preset(i):
            selected_preset[0] = i
            for j, (pb, lb) in enumerate(card_group):
                sel = (j == i)
                border = SELECTED_BORDER if sel else NORMAL_BORDER
                bg     = SELECTED_BG     if sel else NORMAL_BG
                pb.setStyleSheet(
                    f'QPushButton{{background:{bg};border:{border};border-radius:4px;padding:2px;}}'
                    f'QPushButton:hover{{background:#ddeeff;}}')
                lb.setStyleSheet(
                    f'QPushButton{{background:{bg};border:{border};border-radius:4px;'
                    f'font-size:10px;padding:2px;}}'
                    f'QPushButton:hover{{background:#ddeeff;}}')

        for i, (name, rows, cols, mosaic) in enumerate(LAYOUTS):
            cell = QWidget()
            cly = QVBoxLayout(cell); cly.setSpacing(2); cly.setContentsMargins(0,0,0,0)
            cly.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            # Clickable preview container
            prev_widget = _make_preview(rows, cols, mosaic)
            prev_btn = QPushButton()
            prev_btn.setFixedSize(96, 68)
            prev_btn.setFlat(True)
            inner = QVBoxLayout(prev_btn); inner.setContentsMargins(4,4,4,4)
            inner.addWidget(prev_widget)
            prev_btn.clicked.connect(lambda _, idx=i: _select_preset(idx))

            # Label button below
            lbl_btn = QPushButton(name)
            lbl_btn.setFixedHeight(36)
            lbl_btn.clicked.connect(lambda _, idx=i: _select_preset(idx))

            card_group.append((prev_btn, lbl_btn))
            cly.addWidget(prev_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            cly.addWidget(lbl_btn)
            grid.addWidget(cell, i // per_row, i % per_row)

        _select_preset(0)
        scroll_presets = QScrollArea(); scroll_presets.setWidgetResizable(True)
        scroll_presets.setWidget(grid_w)
        presets_lay.addWidget(scroll_presets)
        inner_tabs.addTab(presets_w, '🗂 Presets')

        # ══════════════════════════════════════════════════════════════════════
        # TAB 2 — Custom mosaic editor
        # ══════════════════════════════════════════════════════════════════════
        custom_w = QWidget(); custom_lay = QVBoxLayout(custom_w)

        # Grid size controls
        size_row = QHBoxLayout(); size_row.setSpacing(8)
        size_row.addWidget(QLabel('Rows:'))
        custom_rows = QSpinBox(); custom_rows.setRange(1, 8); custom_rows.setValue(2); custom_rows.setFixedWidth(52)
        size_row.addWidget(custom_rows)
        size_row.addWidget(QLabel('Cols:'))
        custom_cols = QSpinBox(); custom_cols.setRange(1, 8); custom_cols.setValue(2); custom_cols.setFixedWidth(52)
        size_row.addWidget(custom_cols)
        btn_rebuild = QPushButton('↺ Rebuild grid'); btn_rebuild.setFixedWidth(110)
        size_row.addWidget(btn_rebuild)
        size_row.addStretch(); custom_lay.addLayout(size_row)

        custom_lay.addWidget(QLabel(
            'Click cells to assign them to a subplot panel (drag to paint). '
            'Cells with the same colour/letter form one panel.'))

        # State for the custom editor
        custom_state = {
            'rows': 2, 'cols': 2,
            'grid': [['A','B'],['C','D']],   # current letter assignments
            'painting': False,
            'paint_letter': 'A',
        }

        # All available letters (panels)
        ALL_LETTERS = [chr(ord('A')+i) for i in range(26)]

        # Panel palette selector
        palette_row = QHBoxLayout(); palette_row.setSpacing(4)
        palette_row.addWidget(QLabel('Active panel:'))
        palette_btns = {}

        def _letter_colour(letter):
            idx = ord(letter) - ord('A')
            return CELL_COLOURS[idx % len(CELL_COLOURS)]

        for letter in ALL_LETTERS[:8]:
            pb = QPushButton(letter); pb.setFixedSize(30, 28); pb.setCheckable(True)
            pb.setStyleSheet(f'background:{_letter_colour(letter)};border-radius:4px;font-weight:bold;')
            palette_btns[letter] = pb
            def _sel_letter(checked, l=letter):
                custom_state['paint_letter'] = l
                for ll, bb in palette_btns.items():
                    bb.setChecked(ll == l)
            pb.clicked.connect(_sel_letter)
            palette_row.addWidget(pb)
        palette_btns['A'].setChecked(True)
        palette_row.addStretch(); custom_lay.addLayout(palette_row)

        # The cell grid container
        grid_frame = QFrame()
        grid_frame.setFrameShape(QFrame.Shape.StyledPanel)
        grid_frame_lay = QGridLayout(grid_frame)
        grid_frame_lay.setSpacing(3); grid_frame_lay.setContentsMargins(6,6,6,6)
        custom_lay.addWidget(grid_frame)

        cell_btns = {}   # (r,c) → QPushButton

        # Live preview container — a QWidget with a QGridLayout that mirrors the mosaic
        preview_container = QWidget()
        preview_container.setFixedSize(180, 120)
        preview_grid_lay = QGridLayout(preview_container)
        preview_grid_lay.setSpacing(3); preview_grid_lay.setContentsMargins(4,4,4,4)
        preview_cells = {}  # (r,c) → QLabel

        def _update_preview_widget():
            """Rebuild the small preview to mirror current grid state."""
            for lbl in preview_cells.values():
                preview_grid_lay.removeWidget(lbl); lbl.deleteLater()
            preview_cells.clear()
            rows = custom_state['rows']; cols = custom_state['cols']
            grid = custom_state['grid']
            # Compute spans by finding each letter's bounding box
            spans = {}
            for ri, row in enumerate(grid):
                for ci, letter in enumerate(row):
                    if letter not in spans:
                        spans[letter] = [ri, ci, ri, ci]
                    else:
                        spans[letter][2] = max(spans[letter][2], ri)
                        spans[letter][3] = max(spans[letter][3], ci)
            # Number panels in order of first appearance
            order = list(dict.fromkeys(letter for row in grid for letter in row))
            for num, letter in enumerate(order, 1):
                r0, c0, r1, c1 = spans[letter]
                lbl = QLabel(str(num))
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet(
                    f'background:{_letter_colour(letter)};border:1px solid #777;'
                    f'border-radius:3px;font-size:11px;font-weight:bold;')
                preview_grid_lay.addWidget(lbl, r0, c0, r1-r0+1, c1-c0+1)
                preview_cells[letter] = lbl

        def _refresh_grid_ui():
            # Clear existing paint buttons
            for btn in cell_btns.values():
                grid_frame_lay.removeWidget(btn); btn.deleteLater()
            cell_btns.clear()
            rows = custom_state['rows']; cols = custom_state['cols']
            grid = custom_state['grid']
            for r in range(rows):
                for c in range(cols):
                    letter = grid[r][c]
                    btn = QPushButton(letter)
                    btn.setFixedSize(60, 44)
                    btn.setStyleSheet(
                        f'background:{_letter_colour(letter)};border-radius:4px;'
                        f'font-size:14px;font-weight:bold;border:1px solid #888;')
                    def _paint(checked=False, rr=r, cc=c):
                        custom_state['grid'][rr][cc] = custom_state['paint_letter']
                        _refresh_grid_ui()
                    btn.clicked.connect(_paint)
                    grid_frame_lay.addWidget(btn, r, c)
                    cell_btns[(r,c)] = btn
            _update_preview_widget()

        def _rebuild_grid():
            rows = custom_rows.value(); cols = custom_cols.value()
            old = custom_state['grid']
            new_grid = []
            for r in range(rows):
                row_data = []
                for c in range(cols):
                    if r < len(old) and c < len(old[r]):
                        row_data.append(old[r][c])
                    else:
                        used = {cell for row in new_grid for cell in row}
                        for l in ALL_LETTERS:
                            if l not in used:
                                row_data.append(l); break
                        else:
                            row_data.append('A')
                new_grid.append(row_data)
            custom_state['rows'] = rows; custom_state['cols'] = cols
            custom_state['grid'] = new_grid
            _refresh_grid_ui()

        btn_rebuild.clicked.connect(_rebuild_grid)
        _refresh_grid_ui()   # initial render

        # Live preview
        prev_row = QHBoxLayout()
        prev_row.addWidget(QLabel('Preview:'))
        prev_row.addWidget(preview_container)
        prev_row.addStretch()
        custom_lay.addLayout(prev_row)
        custom_lay.addStretch()

        inner_tabs.addTab(custom_w, '✏️ Custom mosaic')

        # ── Shared options ────────────────────────────────────────────────────
        share_row = QHBoxLayout()
        share_x = QCheckBox('Share X axis'); share_x.setChecked(self.sp_sharex.isChecked())
        share_y = QCheckBox('Share Y axis'); share_y.setChecked(self.sp_sharey.isChecked())
        share_row.addWidget(share_x); share_row.addWidget(share_y); share_row.addStretch()
        dlg_lay.addLayout(share_row)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        dlg_lay.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        self.sp_sharex.setChecked(share_x.isChecked())
        self.sp_sharey.setChecked(share_y.isChecked())

        # Determine which tab was active → presets or custom
        if inner_tabs.currentIndex() == 0:
            # Preset selected
            _, rows, cols, mosaic = LAYOUTS[selected_preset[0]]
        else:
            # Custom mosaic
            rows = custom_state['rows']; cols = custom_state['cols']
            raw_grid = custom_state['grid']
            # Validate: every cell must have same letter = forms a contiguous block
            # (matplotlib mosaic just needs the list-of-lists, contiguity checked at render)
            mosaic = raw_grid

        self._subplot_mosaic = mosaic

        # Block signals on both spinboxes so we control exactly when
        # on_subplot_layout_changed fires (once, with both values correct).
        self.sp_rows.blockSignals(True); self.sp_cols.blockSignals(True)
        self.sp_rows.setValue(rows); self.sp_cols.setValue(cols)
        self.sp_rows.blockSignals(False); self.sp_cols.blockSignals(False)
        self.subplot_rows = rows; self.subplot_cols = cols

        if mosaic is None:
            self.on_subplot_layout_changed()
        else:
            cells = list(dict.fromkeys(c for row in mosaic for c in row))
            n = len(cells)
            self.on_subplot_layout_changed(n_override=n)
        self.update_preview()

    def _adv_generate_or_apply(self):
        """Dispatch to x-range generator or column-function applier based on mode radio."""
        if self._adv_mode_range.isChecked():
            self._generate_fx()
        else:
            self._apply_col_function()

    # ═══════════════════════════════════════════════════════════════════════════
    # PRESET / FIT
    # ═══════════════════════════════════════════════════════════════════════════
    def apply_preset(self, name):
        ChartPresets.apply(name); self.update_preview()

    def _rename_table_col(self, col_idx):
        from PyQt6.QtWidgets import QInputDialog
        old = self.data_table.horizontalHeaderItem(col_idx)
        old_name = old.text() if old else f'col_{col_idx+1}'
        name, ok = QInputDialog.getText(self, 'Rename column', 'Column name:', text=old_name)
        if ok and name.strip():
            self.data_table.setHorizontalHeaderItem(col_idx, QTableWidgetItem(name.strip()))

    def _generate_fx(self):
        try:
            x_min = self.gen_x_min.value()
            x_max = self.gen_x_max.value()
            n     = self.gen_x_n.value()
            expr  = self.gen_expr.text().strip()
            xname = self.gen_x_name.text().strip() or 'x'
            yname = self.gen_y_name.text().strip() or 'y'
            if x_min >= x_max:
                self.gen_status.setText('❌  x_min must be less than x_max'); return

            xarr = np.linspace(x_min, x_max, n)
            ns = {k: getattr(np, k) for k in dir(np) if not k.startswith('_')}
            ns.update({'x': xarr, 'pi': np.pi, 'e': np.e,
                       'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
                       'exp': np.exp, 'log': np.log, 'log10': np.log10,
                       'sqrt': np.sqrt, 'abs': np.abs})
            yarr = eval(expr, {'__builtins__': {}}, ns)
            yarr = np.asarray(yarr, dtype=float)
            if yarr.shape == (): yarr = np.full(n, float(yarr))

            stored_x, stored_y = xname, yname
            for attr, nm, arr in (('stored_x', xname, xarr), ('stored_y', yname, yarr)):
                base, cnt = nm, 1
                while base in self.datasets: base = f'{nm}_{cnt}'; cnt += 1
                self.datasets[base] = arr
                if attr == 'stored_x': stored_x = base
                else: stored_y = base
            self.update_lists()

            # Show editable popup before inserting series
            popup = self._show_new_series_info(stored_y, n, source='f(x)', x_col=stored_x, y_col=stored_y)
            if popup is None:
                self.gen_status.setText(f'✓  Datasets created — series not added'); return
            series_label, subplot_num, chart_type = popup

            self.series_table.blockSignals(True)
            row = self.series_table.rowCount()
            self.series_table.insertRow(row)
            cols_sorted = sorted(self.datasets)
            for col_idx, col_name in ((0, stored_x), (1, stored_y)):
                cb = QComboBox(); cb.addItems(cols_sorted)
                idx2 = cb.findText(col_name)
                if idx2 >= 0: cb.setCurrentIndex(idx2)
                handler = self._on_x_col_changed if col_idx == 0 else self.update_preview
                cb.currentIndexChanged.connect(handler)
                self.series_table.setCellWidget(row, col_idx, cb)
            self.series_table.setItem(row, 2, QTableWidgetItem(series_label))
            _mode = self.plot_mode_combo.currentText() if hasattr(self, 'plot_mode_combo') else 'Standard'
            _allowed = list(PLOT_MODE_GROUPS.get(_mode, PER_SERIES_TYPES))
            type_cb = QComboBox(); type_cb.addItems(_allowed)
            i_type = type_cb.findText(chart_type) if chart_type in _allowed else 0
            type_cb.setCurrentIndex(max(i_type, 0))
            type_cb.currentTextChanged.connect(self._on_series_row_type_changed)
            self.series_table.setCellWidget(row, 3, type_cb)
            plot_spin = QSpinBox(); plot_spin.setRange(1, max(1, self.subplot_rows * self.subplot_cols))
            plot_spin.setValue(subplot_num); plot_spin.valueChanged.connect(self.update_preview)
            self.series_table.setCellWidget(row, 4, plot_spin)
            y2_item = QTableWidgetItem()
            y2_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            y2_item.setCheckState(Qt.CheckState.Unchecked)
            self.series_table.setItem(row, 5, y2_item)
            self.series_table.blockSignals(False)
            self._refresh_curve_select()
            self.update_preview()
            self.gen_status.setText(f'✓  Created "{stored_x}" and "{stored_y}"  ({n} points)')
        except Exception as e:
            self.gen_status.setText(f'❌  {e}')

    # ── Apply function to column ───────────────────────────────────────────────
    def _apply_col_function(self):
        try:
            src_col = self.fn_source_combo.currentText()
            var     = self.fn_var_name.text().strip() or 'x'
            expr    = self.fn_expr.text().strip()
            out_nm  = self.fn_out_name.text().strip() or 'result'
            if src_col not in self.datasets:
                self.fn_status.setText('❌  No source column selected'); return
            src_arr = self.datasets[src_col]
            ns = {k: getattr(np, k) for k in dir(np) if not k.startswith('_')}
            ns.update({var: src_arr, 'pi': np.pi, 'e': np.e,
                       'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
                       'exp': np.exp, 'log': np.log, 'log10': np.log10,
                       'sqrt': np.sqrt, 'abs': np.abs})
            result = eval(expr, {'__builtins__': {}}, ns)
            result = np.asarray(result)
            if result.shape == (): result = np.full(len(src_arr), float(result))
            base, cnt = out_nm, 1
            stored_nm = base
            while stored_nm in self.datasets: stored_nm = f'{base}_{cnt}'; cnt += 1
            self.datasets[stored_nm] = result
            self.update_lists()

            # Show editable popup before inserting series
            n2 = len(result)
            popup = self._show_new_series_info(stored_nm, n2, source='f(col)', x_col=src_col, y_col=stored_nm)
            if popup is None:
                self.fn_status.setText(f'✓  Column "{stored_nm}" created — series not added'); return
            series_label, subplot_num, chart_type = popup

            self._add_series_row()
            last = self.series_table.rowCount() - 1
            lbl_item = self.series_table.item(last, 2)
            if lbl_item: lbl_item.setText(series_label)
            sp_spin = self.series_table.cellWidget(last, 4)
            if sp_spin: sp_spin.setValue(subplot_num)
            type_cb2 = self.series_table.cellWidget(last, 3)
            if type_cb2:
                i = type_cb2.findText(chart_type)
                if i >= 0: type_cb2.setCurrentIndex(i)
            xcb = self.series_table.cellWidget(last, 0)
            ycb = self.series_table.cellWidget(last, 1)
            if xcb:
                xcb.blockSignals(True)
                i = xcb.findText(src_col)
                if i >= 0: xcb.setCurrentIndex(i)
                xcb.blockSignals(False)
            if ycb:
                ycb.blockSignals(True)
                i = ycb.findText(stored_nm)
                if i >= 0: ycb.setCurrentIndex(i)
                ycb.blockSignals(False)
            self.update_preview()
            self.fn_status.setText(f'✓  Created "{stored_nm}"  ({n2} points)')
        except Exception as e:
            self.fn_status.setText(f'❌  {e}')

    # ── Inspect loaded series values ───────────────────────────────────────────
    def _show_new_series_info(self, series_name, n_points, source='', x_col='', y_col=''):
        """Show an editable info popup after a new series is created from the Advanced tab.
        Returns (label, subplot, chart_type) on OK, or None on Cancel.
        Caller must use the returned values to set series properties after insertion."""
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout,
                                     QDialogButtonBox, QLabel, QLineEdit,
                                     QSpinBox, QComboBox)
        dlg = QDialog(self)
        dlg.setWindowTitle('New Series Created')
        dlg.setFixedWidth(370)
        vlay = QVBoxLayout(dlg)

        info = QLabel(f'<b>{n_points}</b> points   ·   source: <i>{source}</i>')
        info.setStyleSheet('font-size:12px; padding:3px 0;')
        vlay.addWidget(info)

        form = QFormLayout(); form.setSpacing(7)
        form.addRow('X column:', QLabel(f'<tt>{x_col}</tt>'))
        form.addRow('Y column:', QLabel(f'<tt>{y_col}</tt>'))

        le_label = QLineEdit(series_name)
        form.addRow('Series label:', le_label)

        sp_subplot = QSpinBox()
        sp_subplot.setRange(1, max(1, self.subplot_rows * self.subplot_cols))
        sp_subplot.setValue(1)
        form.addRow('Subplot:', sp_subplot)

        cb_type = QComboBox()
        from ui.tab_builders import PLOT_MODE_GROUPS
        _mode = self.plot_mode_combo.currentText() if hasattr(self, 'plot_mode_combo') else 'Standard'
        cb_type.addItems(PLOT_MODE_GROUPS.get(_mode, list(PLOT_MODE_GROUPS['Standard'])))
        form.addRow('Series type:', cb_type)
        vlay.addLayout(form)

        note = QLabel('Customise the series before it is added to the chart.')
        note.setStyleSheet('color:#666; font-size:11px;')
        note.setWordWrap(True)
        vlay.addWidget(note)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        vlay.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        return le_label.text().strip() or series_name, sp_subplot.value(), cb_type.currentText()

    def _inspect_series(self):
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                     QTableWidget, QTableWidgetItem,
                                     QPushButton, QLabel, QSizePolicy,
                                     QDialogButtonBox)
        if not self.datasets:
            return

        selected_items = [item.text() for item in self.dataset_list.selectedItems()]
        cols = selected_items if selected_items else sorted(self.datasets)
        cols = [c for c in cols if c in self.datasets]
        if not cols:
            return

        n_rows = max(len(self.datasets[c]) for c in cols)

        dlg = QDialog(self)
        dlg.setWindowTitle('Inspect / Edit Series Values')
        dlg.resize(min(140 + 110 * len(cols), 1100), 560)
        vlay = QVBoxLayout(dlg)

        info = QLabel(
            f'{len(cols)} column(s)   ·   up to {n_rows} row(s)   —   '
            '<b>double-click a cell to edit</b>')
        info.setStyleSheet('color:#555; font-size:11px;')
        vlay.addWidget(info)

        tbl = QTableWidget(n_rows, len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.horizontalHeader().setStretchLastSection(False)
        tbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        for ci, col in enumerate(cols):
            arr = self.datasets[col]
            is_cat = self._is_categorical(arr)
            for ri in range(len(arr)):
                v = arr[ri]
                text = str(v) if is_cat else f'{v:.6g}'
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                tbl.setItem(ri, ci, item)
            tbl.resizeColumnToContents(ci)

        vlay.addWidget(tbl)

        note2 = QLabel('Changes are written back when you click Apply or OK.')
        note2.setStyleSheet('color:#888; font-size:10px;')
        vlay.addWidget(note2)

        def _apply_edits():
            for ci, col in enumerate(cols):
                arr = self.datasets[col]
                is_cat = self._is_categorical(arr)
                new_vals = []
                for ri in range(n_rows):
                    item = tbl.item(ri, ci)
                    if item is None or item.text().strip() == '':
                        new_vals.append('' if is_cat else np.nan)
                        continue
                    txt = item.text().strip()
                    if is_cat:
                        new_vals.append(txt)
                    else:
                        try:
                            new_vals.append(float(txt))
                        except ValueError:
                            new_vals.append(np.nan)
                if is_cat:
                    self.datasets[col] = np.array(new_vals, dtype=object)
                else:
                    self.datasets[col] = np.array(new_vals, dtype=float)
            self.update_preview()
            info.setText(f'✓  Applied edits to: {", ".join(cols)}')

        btn_row = QHBoxLayout()
        btn_apply = QPushButton('✔ Apply')
        btn_apply.clicked.connect(_apply_edits)
        btn_ok    = QPushButton('OK')
        btn_ok.clicked.connect(lambda: (_apply_edits(), dlg.accept()))
        btn_cancel = QPushButton('Cancel')
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_apply)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        vlay.addLayout(btn_row)

        dlg.exec()
    def _new_data_table(self):
        rows = self.table_rows_spin.value()
        cols = self.table_cols_spin.value()
        self.data_table.blockSignals(True)
        self.data_table.setRowCount(rows)
        self.data_table.setColumnCount(cols)
        self.data_table.setHorizontalHeaderLabels([f'col_{i+1}' for i in range(cols)])
        self.data_table.clearContents()
        self.data_table.blockSignals(False)
        self.table_status.setText('')

    def _table_add_row(self):
        self.data_table.insertRow(self.data_table.rowCount())

    def _table_del_row(self):
        rows = sorted({idx.row() for idx in self.data_table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.data_table.removeRow(r)
        if not rows:
            r = self.data_table.rowCount() - 1
            if r >= 0: self.data_table.removeRow(r)

    def _table_add_col(self):
        c = self.data_table.columnCount()
        self.data_table.insertColumn(c)
        self.data_table.setHorizontalHeaderItem(c, QTableWidgetItem(f'col_{c+1}'))

    def _table_del_col(self):
        cols = sorted({idx.column() for idx in self.data_table.selectedIndexes()}, reverse=True)
        for c in cols:
            self.data_table.removeColumn(c)
        if not cols:
            c = self.data_table.columnCount() - 1
            if c >= 0: self.data_table.removeColumn(c)

    def _table_clear(self):
        for r in range(self.data_table.rowCount()):
            for c in range(self.data_table.columnCount()):
                self.data_table.setItem(r, c, QTableWidgetItem(''))

    def _table_paste_csv(self):
        """Paste clipboard CSV/TSV text into the table, expanding it as needed."""
        text = QApplication.clipboard().text().strip()
        if not text:
            self.table_status.setText('❌  Clipboard is empty'); return
        # Detect delimiter
        delim = '\t' if '\t' in text.split('\n')[0] else ','
        reader = list(csv.reader(io.StringIO(text), delimiter=delim))
        if not reader:
            self.table_status.setText('❌  No data found'); return
        # Check if first row looks like a header
        first = reader[0]
        def _is_num(v):
            try: float(v); return True
            except ValueError: return False
        has_header = any(v.strip() and not _is_num(v) for v in first)
        data_rows = reader[1:] if has_header else reader
        headers   = [v.strip() for v in first] if has_header else [f'col_{i+1}' for i in range(len(first))]
        n_cols = max(len(headers), max((len(r) for r in data_rows), default=0))
        n_rows = len(data_rows)
        # Resize table
        self.data_table.setRowCount(n_rows)
        self.data_table.setColumnCount(n_cols)
        while len(headers) < n_cols: headers.append(f'col_{len(headers)+1}')
        self.data_table.setHorizontalHeaderLabels(headers)
        for r, row in enumerate(data_rows):
            for c, val in enumerate(row):
                self.data_table.setItem(r, c, QTableWidgetItem(val.strip()))
        self.table_status.setText(f'✓  Pasted {n_rows} rows × {n_cols} cols')

    def _table_copy_csv(self):
        """Copy table contents to clipboard as CSV."""
        out = io.StringIO()
        w = csv.writer(out)
        headers = [self.data_table.horizontalHeaderItem(c).text()
                   if self.data_table.horizontalHeaderItem(c) else f'col_{c+1}'
                   for c in range(self.data_table.columnCount())]
        w.writerow(headers)
        for r in range(self.data_table.rowCount()):
            row = []
            for c in range(self.data_table.columnCount()):
                item = self.data_table.item(r, c)
                row.append(item.text() if item else '')
            w.writerow(row)
        QApplication.clipboard().setText(out.getvalue())
        self.table_status.setText(f'✓  Copied {self.data_table.rowCount()} rows to clipboard')

    def _load_table_data(self):
        """Parse the manual table and add each column as a dataset."""
        try:
            n_rows = self.data_table.rowCount()
            n_cols = self.data_table.columnCount()
            loaded = []
            for c in range(n_cols):
                header = self.data_table.horizontalHeaderItem(c)
                col_name = header.text() if header else f'col_{c+1}'
                raw = []
                for r in range(n_rows):
                    item = self.data_table.item(r, c)
                    raw.append(item.text().strip() if item else '')
                # Try all-numeric
                try:
                    arr = np.array([float(v) if v != '' else np.nan for v in raw], dtype=float)
                except ValueError:
                    arr = np.array(raw, dtype=object)
                base, cnt = col_name, 1
                while base in self.datasets: base = f'{col_name}_{cnt}'; cnt += 1
                self.datasets[base] = arr
                loaded.append(base)
            self.update_lists()
            if self.series_table.rowCount() == 0:
                self._add_series_row()
            else:
                self.update_preview()
            self.table_status.setText(f'✓  Loaded: {", ".join(loaded)}')
        except Exception as e:
            self.table_status.setText(f'❌  {e}')

    def _on_ci_changed(self):
        self._update_confidence_band()
        self.update_preview()

    def apply_fit(self):
        try:
            model = self.fit_combo.currentText()
            if model == 'None': return
            series = self._get_series_full()
            if not series:
                QMessageBox.warning(self, 'Warning', 'Add at least one series in the Data tab first.'); return

            # Find the series the user selected in the per-curve selector
            target_label = self.curve_select.currentText() if hasattr(self, 'curve_select') else ''
            matched = next((s for s in series if s[2] == target_label), None)
            if matched is None:
                matched = series[0]
            xd, yd, lbl, xc, yc = matched

            # Find the subplot (Plot spin value) of the source series row
            source_plot_num = 1
            for row in range(self.series_table.rowCount()):
                item = self.series_table.item(row, 2)
                if item and item.text() == lbl:
                    spin = self.series_table.cellWidget(row, 4)
                    if spin:
                        source_plot_num = spin.value()
                    break
            popt, pcov, func, eq_str, r2 = CurveFitter.fit(xd, yd, model)
            if popt is None:
                QMessageBox.warning(self, 'Fit Failed', f'Could not fit {model} to the data.'); return

            # Full statistics
            stats = CurveFitter.full_stats(xd, yd, popt, pcov, func, model)

            # Store everything for CI/PI plotting and serialization
            self._last_fit = dict(xd=xd, yd=yd, popt=popt, pcov=pcov, func=func,
                                  model=model, xc=xc, yc=yc, lbl=lbl,
                                  eq_str=eq_str, r2=r2, stats=stats)

            # Add fit curve as a new dataset
            nm = f'{lbl} ({model} fit)'
            self.datasets[nm] = func(xd, *popt)

            # Seed a default style for the fit curve if it has none yet.
            # This makes it immediately editable via the Per-Curve section
            # without any ambiguity. Use dashed orange to visually distinguish
            # fit curves from raw data series.
            if nm not in self.curve_styles:
                src_color = self.curve_styles.get(lbl, {}).get('color', '#ff7f0e')
                self.curve_styles[nm] = {
                    'color':        src_color,
                    'linestyle':    '--',
                    'marker':       'None',
                    'linewidth':    1.8,
                    'markersize':   6,
                    'marker_color': src_color,
                    'color_locked': False,
                }

            self.update_lists()

            # Add fit curve as a new series row if not already present
            labels_in_table = []
            for row in range(self.series_table.rowCount()):
                item = self.series_table.item(row, 2)
                if item: labels_in_table.append(item.text())
            if nm not in labels_in_table:
                row = self.series_table.rowCount()
                self.series_table.insertRow(row)
                for col_idx, col_name in ((0, xc), (1, nm)):
                    cb = QComboBox(); cb.addItems(sorted(self.datasets))
                    idx = cb.findText(col_name)
                    if idx >= 0: cb.setCurrentIndex(idx)
                    handler = self._on_x_col_changed if col_idx == 0 else self.update_preview
                    cb.currentIndexChanged.connect(handler)
                    self.series_table.setCellWidget(row, col_idx, cb)
                self.series_table.setItem(row, 2, QTableWidgetItem(nm))
                _mode = self.plot_mode_combo.currentText() if hasattr(self, 'plot_mode_combo') else 'Standard'
                _allowed = list(PLOT_MODE_GROUPS.get(_mode, PER_SERIES_TYPES))
                type_cb = QComboBox(); type_cb.addItems(_allowed)
                type_cb.currentTextChanged.connect(self._on_series_row_type_changed)
                self.series_table.setCellWidget(row, 3, type_cb)
                plot_spin = QSpinBox(); plot_spin.setRange(1, max(1, self.subplot_rows * self.subplot_cols))
                plot_spin.setValue(source_plot_num); plot_spin.valueChanged.connect(self.update_preview)
                self.series_table.setCellWidget(row, 4, plot_spin)
                y2_item = QTableWidgetItem()
                y2_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                y2_item.setCheckState(Qt.CheckState.Unchecked)
                self.series_table.setItem(row, 5, y2_item)
            else:
                # Row already exists — keep its subplot in sync with the source
                for row in range(self.series_table.rowCount()):
                    item = self.series_table.item(row, 2)
                    if item and item.text() == nm:
                        spin = self.series_table.cellWidget(row, 4)
                        if spin:
                            spin.blockSignals(True)
                            spin.setValue(source_plot_num)
                            spin.blockSignals(False)
                        break

            self._update_confidence_band()
            self._refresh_fit_results_panel()
            # Switch the Per-Curve selector to the fit curve so the user can
            # immediately style it — no ambiguity about which curve is active.
            if hasattr(self, 'curve_select'):
                idx = self.curve_select.findText(nm)
                if idx >= 0:
                    self.curve_select.setCurrentIndex(idx)
            self.update_preview()
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _refresh_fit_results_panel(self):
        """Populate the fit results QTextEdit with full regression output."""
        if not hasattr(self, '_last_fit') or self._last_fit is None:
            return
        fit  = self._last_fit
        st   = fit.get('stats', {})
        if not st:
            self.fit_results_text.setPlainText('No results.')
            return

        ci_pct = int((1 - st.get('alpha', 0.05)) * 100)
        lines = []
        lines.append(f'Model:  {fit["model"]}')
        lines.append(f'Equation:  {fit.get("eq_str", "")}')
        lines.append('')
        lines.append('── Goodness of Fit ──────────────────')
        lines.append(f'  n            = {st["n"]}')
        lines.append(f'  Parameters   = {st["p"]}')
        lines.append(f'  DoF          = {st["dof"]}')
        lines.append(f'  R²           = {st["r2"]:.6f}')
        lines.append(f'  Adj. R²      = {st["r2_adj"]:.6f}')
        lines.append(f'  RMSE         = {st["rmse"]:.6g}')
        lines.append(f'  MSE          = {st["mse"]:.6g}')
        lines.append(f'  SSE          = {st["sse"]:.6g}')
        lines.append(f'  SST          = {st["sst"]:.6g}')
        fv = st.get('f_stat', float('nan'))
        fp = st.get('f_pvalue', float('nan'))
        import math
        lines.append(f'  F-statistic  = {fv:.4g}' if not math.isnan(fv) else '  F-statistic  = —')
        lines.append(f'  F p-value    = {fp:.4g}' if not math.isnan(fp) else '  F p-value    = —')
        lines.append(f'  AIC          = {st["aic"]:.4g}')
        lines.append(f'  BIC          = {st["bic"]:.4g}')
        lines.append('')
        lines.append(f'── Parameters  ({ci_pct}% CI) ──────────────')
        names  = st['param_names']
        vals   = st['param_values']
        ses    = st['param_se']
        tstats = st['param_tstat']
        pvals  = st['param_pvalue']
        cilo   = st['param_ci_lo']
        cihi   = st['param_ci_hi']
        for i in range(st['p']):
            pv = pvals[i]; tv = tstats[i]
            pv_str = f'{pv:.4g}' if not math.isnan(pv) else '—'
            tv_str = f'{tv:.4g}' if not math.isnan(tv) else '—'
            lo_str = f'{cilo[i]:.4g}' if not math.isnan(cilo[i]) else '—'
            hi_str = f'{cihi[i]:.4g}' if not math.isnan(cihi[i]) else '—'
            lines.append(f'  {names[i]}')
            lines.append(f'    value  = {vals[i]:.6g}  ±{ses[i]:.4g}')
            lines.append(f'    t      = {tv_str}    p = {pv_str}')
            lines.append(f'    CI     = [{lo_str}, {hi_str}]')
        self.fit_results_text.setPlainText('\n'.join(lines))

    def _update_confidence_band(self):
        """Add/refresh confidence band and prediction band datasets based on _last_fit."""
        if not hasattr(self, '_last_fit') or self._last_fit is None: return
        ci_idx = self.fit_ci_combo.currentIndex()   # 0=off, 1/2/3 = n_sigma
        pi_idx = self.fit_pi_combo.currentIndex()
        fit = self._last_fit
        base = fit['lbl'] + f" ({fit['model']} fit)"

        # Remove all existing band datasets
        for suffix in (' CI upper', ' CI lower', ' PI upper', ' PI lower'):
            self.datasets.pop(base + suffix, None)

        if ci_idx > 0:
            y_ci_hi, y_ci_lo = CurveFitter.confidence_band(
                fit['xd'], fit['popt'], fit['pcov'], fit['func'], ci_idx)
            self.datasets[base + ' CI upper'] = y_ci_hi
            self.datasets[base + ' CI lower'] = y_ci_lo

        if pi_idx > 0 and 'yd' in fit:
            y_pi_hi, y_pi_lo = CurveFitter.prediction_band(
                fit['xd'], fit['yd'], fit['popt'], fit['pcov'], fit['func'], pi_idx)
            self.datasets[base + ' PI upper'] = y_pi_hi
            self.datasets[base + ' PI lower'] = y_pi_lo

        self.update_lists()

    # ═══════════════════════════════════════════════════════════════════════════
    # PLOTTING
    # ═══════════════════════════════════════════════════════════════════════════
    @staticmethod
    def _is_categorical(arr):
        """Return True if arr is a string/object array (categorical)."""
        try:
            return arr is not None and hasattr(arr, 'dtype') and arr.dtype.kind in ('U', 'S', 'O')
        except Exception:
            return False

