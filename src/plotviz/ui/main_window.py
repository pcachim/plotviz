"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/main_window.py  –  plotviz
Core application class. Tab UI, helpers, and event handlers.
Tab building, plot engine and serialization live in their own mixin modules.
"""

import os
import zipfile
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


from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QPushButton, QMessageBox, QSplitter, QFrame, QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from ui.nav_toolbar import NavigationToolbar2QT, SafeNavigationToolbar


class _NavToolbar(SafeNavigationToolbar):
    """Standard matplotlib toolbar with the Save button removed.
    The app has its own export workflow that controls DPI and format."""
    toolitems = [t for t in NavigationToolbar2QT.toolitems
                 if t[0] != 'Save']

from ui.canvas import CanvasPlotter
from ui.tab_builders import (
    TabBuildersMixin, COLOR_PALETTES, get_all_palettes,
)
from ui.plot_engine import PlotEngineMixin
from ui.serialization import SerializationMixin
from ui.python_export import PythonExportMixin
from ui.color_schemes import ColorSchemeMixin
from ui.curve_styles import CurveStyleMixin
from ui.subplots import SubplotMixin
from ui.data_io import DataMixin
from ui.fitting import FitPresetMixin
from ui.chart_options import ChartOptionsMixin
from ui.palettes import PaletteColorMixin
from ui.annotations import AnnotationUIMixin
from ui.seaborn_explorer import SeabornExplorer
from ui.code_runner import CodeRunnerDialog


import config.settings as settings



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


class PlotVizApp(TabBuildersMixin, PlotEngineMixin, SerializationMixin, PythonExportMixin, ColorSchemeMixin, CurveStyleMixin, SubplotMixin, DataMixin, FitPresetMixin, ChartOptionsMixin, PaletteColorMixin, AnnotationUIMixin, QMainWindow):
    @property
    def _is_dirty(self):
        """True while the chart has changes that are not saved to its file."""
        return self.__dict__.get('_dirty_flag', False)

    @_is_dirty.setter
    def _is_dirty(self, value):
        self.__dict__['_dirty_flag'] = bool(value)
        self._update_save_button()

    def _update_save_button(self):
        """The top-bar Save button is live only when there is something to save.

        That is: unsaved changes, or a chart that has no file yet (Save then asks where).
        """
        btn = getattr(self, '_btn_save', None)
        if btn is not None:
            btn.setEnabled(self._is_dirty or not getattr(self, '_current_filepath', None))

    def __init__(self):
        super().__init__()
        from config._version import __version__
        self.setWindowTitle(f'plotviz {__version__} - new chart')

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
        self._fits         = {}    # per-series: label -> fit dict
        self.subplot_rows  = 1
        self.subplot_cols  = 1
        self.subplot_chart_types  = {0: 'Line'}
        self.subplot_plot_modes   = {0: 'Standard'}
        self.subplot_chart_opts   = {}      # {subplot_idx: {opt_key: value}}
        self.subplot_canvas_opts  = {}      # {subplot_idx: canvas/border opts}
        self.subplot_grid_opts    = {}      # {subplot_idx: grid opts}
        self.sp_titles            = {0: ''}
        self.subplot_title_show   = {0: True}
        self.subplot_title_font     = {0: 'sans-serif'}
        self.subplot_title_size     = {0: 11}
        self.subplot_title_color    = {0: '#000000'}
        self.subplot_title_pad      = {0: 6}
        self.subplot_title_rotation = {0: 0}
        self.subplot_title_ha       = {0: 'center'}
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
        self._color_palette = 'Matplotlib'   # a new session starts from the first scheme's palette
        self.subplot_ann_visible  = {0: True}   # per-subplot annotation visibility
        self.subplot_equal_aspect = {0: False}  # per-subplot equal-scale (set_aspect('equal'))
        self.subplot_xaxis_pos    = {0: 'bottom'}  # x-axis position: bottom / top / zero
        self.subplot_yaxis_pos    = {0: 'left'}    # y-axis position: left / right / zero
        self.subplot_xlabel_rotation = {0: 0}
        self.subplot_xlabel_labelpad = {0: 4}
        self.subplot_xlabel_loc      = {0: 'center'}
        self.subplot_xlabel_ha       = {0: 'center'}
        self.subplot_ylabel_rotation = {0: 90}
        self.subplot_ylabel_labelpad = {0: 4}
        self.subplot_ylabel_loc      = {0: 'center'}
        self.subplot_ylabel_ha       = {0: 'center'}
        self.subplot_zlabels         = {0: ''}
        self.subplot_zlabel_show     = {0: True}
        self.subplot_zlabel_rotation = {0: 90}
        self.subplot_zlabel_labelpad = {0: 4}
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
        # Undo / redo live in the Edit menu (built below), which owns their shortcuts.

        # Undo/redo buttons start disabled
        self._update_undo_buttons()

        # ── Apply saved preferences to freshly-built widgets ──────────────────
        self._restore_prefs_from_settings()

        # LaTeX typesetting (text.usetex) is deliberately NOT enabled, whether or not
        # a LaTeX installation exists: the preview and the exported script never use
        # it, so the app must behave the same from source, from the .app and on any
        # machine. Maths such as $x^2$ still renders through matplotlib's mathtext.

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
        """Set the title bar to 'plotviz <version> - <stem>' or 'plotviz <version> - new chart'."""
        from config._version import __version__
        fp = getattr(self, '_current_filepath', None)
        if fp:
            import os as _os
            stem = _os.path.splitext(_os.path.basename(fp))[0]
        else:
            stem = 'new chart'
        self.setWindowTitle(f'plotviz {__version__} - {stem}')
        self._update_save_button()      # no file yet <-> Save must stay available

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
            except (OSError, ValueError, KeyError, zipfile.BadZipFile):
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
        """Debounced handler for window resize / splitter moves: redraw the preview.

        The figure's own size (width, height, margins, title position) belongs to
        the chart and is never changed by the window size; only the preview is
        re-laid out so the page stays centred in the new canvas.
        """
        if not hasattr(self, '_resize_timer'):
            from PyQt6.QtCore import QTimer
            self._resize_timer = QTimer(self)
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self._redraw_after_resize)
        self._resize_timer.start(80)   # 80 ms debounce

    def _redraw_after_resize(self):
        """Redraw the preview for the new canvas size, without touching the chart."""
        if not hasattr(self, 'canvas'):
            return
        if self.canvas.width() <= 0 or self.canvas.height() <= 0:
            return   # early startup layout passes
        # Resizing the window is not an edit: keep the "unsaved changes" flag as it was.
        had_flag = hasattr(self, '_is_dirty')
        dirty = getattr(self, '_is_dirty', False)
        self.update_preview()
        if had_flag:
            self._is_dirty = dirty

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

    def _open_documentation(self):
        """Open the plotviz online documentation in the default browser."""
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl('https://pcachim.github.io/plotviz/'))

    def _open_sample_chart(self):
        """Pick a sample chart in an Open dialog that starts in the samples folder."""
        from config.settings import plots_dir
        fp, _ = QFileDialog.getOpenFileName(
            self, 'Open Sample Chart', str(plots_dir()),
            'plotviz File (*.pviz);;zip File (*.zip);;All Files (*)')
        if fp:
            self._load_project_from_path(fp)

    def _open_sample_dataset(self):
        """Pick sample dataset files in an Open dialog that starts in the samples folder."""
        from config.settings import datasets_dir
        self._load_data_files('Open Sample Dataset', str(datasets_dir()), remember_dir=False)

    def closeEvent(self, event):
        """Persist window state and prefs before closing."""
        geo = self.geometry()
        settings.set('window_geometry', [geo.x(), geo.y(), geo.width(), geo.height()])
        settings.set('window_maximised', self.isMaximized())
        settings.set('theme', getattr(self, '_colour_mode', 'system').capitalize()
                     if not hasattr(self, 'colour_scheme_combo')
                     else self.colour_scheme_combo.currentText())
        if hasattr(self, '_export_fmt_combo'):
            settings.set('export_format', self._export_fmt_combo.currentText())
        if hasattr(self, 'dpi_spin'):
            settings.set('export_dpi', self.dpi_spin.value())
        if hasattr(self, 'fig_preset_combo'):
            settings.set('fig_preset', self.fig_preset_combo.currentText())
        event.accept()

    def _restore_prefs_from_settings(self):
        """Apply persisted preferences to UI widgets after init_ui() has run."""
        # Theme
        theme = settings.get('theme') or 'System'
        if hasattr(self, 'colour_scheme_combo'):
            idx = self.colour_scheme_combo.findText(theme)
            if idx >= 0:
                self.colour_scheme_combo.blockSignals(True)
                self.colour_scheme_combo.setCurrentIndex(idx)
                self.colour_scheme_combo.blockSignals(False)
        self._apply_colour_scheme(theme)

        # Colour palette
        pal = 'Matplotlib'
        # Your palettes and colour schemes are the files in their folders (palettes first:
        # a scheme file can refer to one of them)
        self._load_palette_library()
        self._load_library_schemes()
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
        # Instantiate the status bar up front so it reserves its bottom space
        # from the start. Otherwise the first _show_status() call (on the first
        # canvas click) creates it lazily, shrinking the content and producing a
        # one-off downward "jump" of the canvas and tabs.
        self.statusBar()
        main_layout = QHBoxLayout(central)

        self.tabs = QTabWidget()
        self.create_advanced_tab()   # built first: the Data tab shows it as its Generate page
        self.create_data_tab()       # Data tab: datasets + generators
        self.create_style_tab()      # Layout & Style tab: size, margins, colours, scheme, palette
        self.create_plots_tab()      # subplot selector + Plot, Curves, Axes, Canvas & Grid, Annotations

        # ── Menu bar — File ───────────────────────────────────────────────────
        from PyQt6.QtGui import QAction
        menubar = self.menuBar()

        file_menu = menubar.addMenu('File')

        def _go_data_tab():
            self.tabs.setCurrentIndex(0)   # Data tab, Datasets page
            if hasattr(self, 'data_inner_tabs'):
                self.data_inner_tabs.setCurrentIndex(0)

        def _go_figure_tab():
            self.tabs.setCurrentIndex(1)   # Layout & Style tab (palette and colour scheme)

        # ── New ───────────────────────────────────────────────────────────────
        act_new = QAction('New Chart', self)
        act_new.setStatusTip('Start a new, empty chart')
        act_new.setShortcut('Ctrl+N')
        act_new.triggered.connect(self._reset_app)
        file_menu.addAction(act_new)

        # ── Open / Load ───────────────────────────────────────────────────────
        file_menu.addSeparator()

        act_open = QAction('Open Chart…', self)
        act_open.setStatusTip('Open a chart (.pviz file)')
        act_open.setToolTip('Open a chart (.pviz file)')
        act_open.setShortcut('Ctrl+O')
        act_open.triggered.connect(self._load_project)
        file_menu.addAction(act_open)

        self._recent_menu = file_menu.addMenu('Open Recent')
        self._rebuild_recent_files_ui()

        act_open_tpl = QAction('Load Template…', self)
        act_open_tpl.setStatusTip('Apply a template (.pvizt file): settings only, no data')
        act_open_tpl.setToolTip('Apply a template (.pvizt file): settings only, no data')
        act_open_tpl.triggered.connect(self._load_template)
        file_menu.addAction(act_open_tpl)

        act_load_pal = QAction('Load Palette…', self)
        act_load_pal.setStatusTip('Load colour palettes from a .pvizp file')
        act_load_pal.setToolTip('Load colour palettes from a .pvizp file')
        act_load_pal.triggered.connect(
            lambda: (_go_figure_tab(), self._import_palette_bundle()))
        file_menu.addAction(act_load_pal)

        act_load_scheme = QAction('Load Scheme…', self)
        act_load_scheme.setStatusTip('Load a colour scheme from a .pvizc file')
        act_load_scheme.setToolTip('Load a colour scheme from a .pvizc file')
        act_load_scheme.triggered.connect(
            lambda: (_go_figure_tab(), self._load_color_scheme()))
        file_menu.addAction(act_load_scheme)

        # ── Load Data ─────────────────────────────────────────────────────────
        file_menu.addSeparator()

        act_load_data = QAction('Load Data…', self)
        act_load_data.setStatusTip('Load a CSV, Excel, JSON or text data file')
        act_load_data.setShortcut('Ctrl+L')
        act_load_data.triggered.connect(lambda: (_go_data_tab(), self.load_data()))
        file_menu.addAction(act_load_data)

        # ── Save ──────────────────────────────────────────────────────────────
        file_menu.addSeparator()

        act_save = QAction('Save Chart', self)
        act_save.setStatusTip('Save the chart to its .pviz file')
        act_save.setToolTip('Save the chart to its .pviz file')
        act_save.setShortcut('Ctrl+S')
        act_save.triggered.connect(self._save_project)
        file_menu.addAction(act_save)

        act_save_as = QAction('Save Chart As…', self)
        act_save_as.setStatusTip('Save the chart as a new .pviz file')
        act_save_as.setToolTip('Save the chart as a new .pviz file')
        act_save_as.setShortcut('Ctrl+Shift+S')
        act_save_as.triggered.connect(self._save_project_as)
        file_menu.addAction(act_save_as)

        act_save_tpl = QAction('Save Template…', self)
        act_save_tpl.setStatusTip('Save the settings, without data, as a .pvizt template')
        act_save_tpl.setToolTip('Save the settings, without data, as a .pvizt template')
        act_save_tpl.triggered.connect(self._save_template)
        file_menu.addAction(act_save_tpl)

        act_save_pal = QAction('Save Palette…', self)
        act_save_pal.setStatusTip('Save the custom palettes as a .pvizp file')
        act_save_pal.setToolTip('Save the custom palettes as a .pvizp file')
        act_save_pal.triggered.connect(
            lambda: (_go_figure_tab(), self._export_palette_bundle()))
        file_menu.addAction(act_save_pal)

        act_save_scheme = QAction('Save Scheme…', self)
        act_save_scheme.setStatusTip('Save the current colours as a .pvizc colour scheme')
        act_save_scheme.setToolTip('Save the current colours as a .pvizc colour scheme')
        act_save_scheme.triggered.connect(
            lambda: (_go_figure_tab(), self._save_color_scheme()))
        file_menu.addAction(act_save_scheme)

        # ── Export ────────────────────────────────────────────────────────────
        file_menu.addSeparator()

        act_export_img = QAction('Export Image…', self)
        act_export_img.setStatusTip('Export the chart as PNG, SVG, PDF, JPEG, TIFF or EPS')
        act_export_img.setShortcut('Ctrl+E')
        act_export_img.triggered.connect(
            lambda: self.export_chart())
        file_menu.addAction(act_export_img)

        act_export_py = QAction('Export Python Bundle…', self)
        act_export_py.setStatusTip('Export the chart as a standalone Python script bundle (.pvizx)')
        act_export_py.setToolTip('Export the chart as a standalone Python script bundle (.pvizx)')
        act_export_py.setShortcut('Ctrl+Shift+E')
        act_export_py.triggered.connect(
            self._export_python_bundle)
        file_menu.addAction(act_export_py)

        self._file_menu = file_menu

        # ── Menu bar — Edit ───────────────────────────────────────────────────
        edit_menu = menubar.addMenu('Edit')

        self._act_undo = QAction('Undo', self)
        self._act_undo.setShortcut('Ctrl+Z')
        self._act_undo.setStatusTip('Undo the last change')
        self._act_undo.triggered.connect(self._undo)
        edit_menu.addAction(self._act_undo)

        self._act_redo = QAction('Redo', self)
        self._act_redo.setShortcuts(['Ctrl+Y', 'Ctrl+Shift+Z'])
        self._act_redo.setStatusTip('Redo the change that was undone')
        self._act_redo.triggered.connect(self._redo)
        edit_menu.addAction(self._act_redo)
        self._act_undo.setEnabled(False)   # nothing to undo yet
        self._act_redo.setEnabled(False)

        edit_menu.addSeparator()

        # Not Ctrl+C: that would steal "copy" from text fields and tables.
        act_copy_img = QAction('Copy Image to Clipboard', self)
        act_copy_img.setShortcut('Ctrl+Shift+C')
        act_copy_img.setStatusTip('Copy the current chart as an image to the clipboard')
        act_copy_img.triggered.connect(self._copy_image_to_clipboard)
        edit_menu.addAction(act_copy_img)

        self._edit_menu = edit_menu

        # ── Menu bar — View ───────────────────────────────────────────────────
        view_menu = menubar.addMenu('View')
        for i in range(self.tabs.count()):
            name = self.tabs.tabText(i)
            action = QAction(name, self)
            action.setCheckable(True)
            action.setStatusTip(f"Show the {name.replace('&&', '&')} tab")
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
        sns_action.setShortcut('Ctrl+Shift+B')    # Ctrl+Shift+S is Save Chart As
        sns_action.setStatusTip('Open the Seaborn statistical chart explorer')
        sns_action.triggered.connect(self._open_seaborn_explorer)
        tools_menu.addAction(sns_action)

        code_action = QAction('Python Code Runner…', self)
        code_action.setShortcut('Ctrl+Shift+P')
        code_action.setStatusTip('Write or load Python code to draw a matplotlib/seaborn chart')
        code_action.triggered.connect(self._open_code_runner)
        tools_menu.addAction(code_action)

        cr_from_chart_action = QAction('Code Runner from chart', self)
        cr_from_chart_action.setShortcut('Ctrl+Shift+R')
        cr_from_chart_action.setStatusTip(
            'Export the current chart as a .pvizx bundle and open it in the Code Runner')
        cr_from_chart_action.triggered.connect(
            self._export_to_code_runner)
        tools_menu.addAction(cr_from_chart_action)

        self._tools_menu = tools_menu
        self._sns_explorer  = None   # lazily created
        self._code_runner   = None   # lazily created

        # ── Help menu ─────────────────────────────────────────────────────────
        help_menu = menubar.addMenu('Help')

        docs_action = QAction('Documentation', self)
        docs_action.setStatusTip('Open the plotviz online documentation')
        docs_action.triggered.connect(self._open_documentation)
        help_menu.addAction(docs_action)

        help_menu.addSeparator()

        sample_charts_action = QAction('Sample Charts…', self)
        sample_charts_action.setStatusTip('Choose one of the sample charts to open')
        sample_charts_action.triggered.connect(self._open_sample_chart)
        help_menu.addAction(sample_charts_action)

        sample_datasets_action = QAction('Sample Datasets…', self)
        sample_datasets_action.setStatusTip('Choose one or more sample datasets to load')
        sample_datasets_action.triggered.connect(self._open_sample_dataset)
        help_menu.addAction(sample_datasets_action)

        self._help_menu = help_menu

        # ── Settings and About placement ──────────────────────────────────────
        if sys.platform == 'darwin':
            # macOS: Qt maps a menu named after the app to the native application
            # menu (left of "File"). Preferences and About go there.
            app_menu = menubar.addMenu('plotviz')

            act_about_app = QAction('About plotviz', self)
            act_about_app.triggered.connect(self._show_about)
            app_menu.addAction(act_about_app)

            app_menu.addSeparator()

            act_prefs_app = QAction('Preferences…', self)
            act_prefs_app.setShortcut('Ctrl+,')
            act_prefs_app.triggered.connect(self._open_app_settings_dialog)
            app_menu.addAction(act_prefs_app)
        else:
            # Windows / Linux: Settings at the end of Edit, About at the end of Help.
            edit_menu.addSeparator()
            act_prefs = QAction('Settings…', self)
            act_prefs.setShortcut('Ctrl+Alt+S')
            act_prefs.setStatusTip('Open application settings / preferences')
            act_prefs.triggered.connect(self._open_app_settings_dialog)
            edit_menu.addAction(act_prefs)

            help_menu.addSeparator()
            act_about = QAction('About plotviz…', self)
            act_about.setStatusTip('About this application')
            act_about.triggered.connect(self._show_about)
            help_menu.addAction(act_about)

        # Tooltips
        for i, tip in enumerate([
            'Chart — open/save/export, subplot layout, colour palette',
            'Style — figure size, margins, colours, grid',
            'Plots — subplot selector, data series, axes and annotations',
            'Advanced — function generator and manual data table',
        ]):
            self.tabs.setTabToolTip(i, tip)

        self.canvas = CanvasPlotter()
        self.canvas.main_window = self
        self.toolbar = _NavToolbar(self.canvas, self)

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

        # Top action bar (above tabs): New | Open | Save | Export ... Undo | Redo
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(6, 4, 6, 4)
        top_bar_layout.setSpacing(4)

        btn_new = QPushButton('＋ New')
        btn_new.setToolTip('Start a new, blank chart (Ctrl+N)')
        btn_new.clicked.connect(self._reset_app)
        top_bar_layout.addWidget(btn_new)

        btn_open = QPushButton('📂')
        btn_open.setToolTip('Open a chart… (Ctrl+O)')
        btn_open.setFixedWidth(36)
        btn_open.clicked.connect(lambda: self._load_project())
        top_bar_layout.addWidget(btn_open)
        self._btn_open = btn_open

        btn_save = QPushButton('💾')
        btn_save.setToolTip('Save the chart (Ctrl+S); Save As… is in the File menu')
        btn_save.setFixedWidth(36)
        btn_save.clicked.connect(lambda: self._save_project())
        top_bar_layout.addWidget(btn_save)
        self._btn_save = btn_save
        self._update_save_button()

        # Exporting the picture is what the app is for: give it a labelled button
        btn_export = QPushButton('⬆ Export')
        btn_export.setToolTip('Export the chart as an image… (Ctrl+E)')
        btn_export.clicked.connect(lambda: self.export_chart())
        top_bar_layout.addWidget(btn_export)
        self._btn_export = btn_export

        top_bar_layout.addStretch()

        btn_undo = QPushButton('↩')
        btn_undo.setToolTip('Undo last change (Ctrl+Z)')
        btn_undo.clicked.connect(self._undo)
        btn_undo.setFixedWidth(36)
        top_bar_layout.addWidget(btn_undo)
        self._btn_undo = btn_undo

        btn_redo = QPushButton('↪')
        btn_redo.setToolTip('Redo (Ctrl+Y)')
        btn_redo.clicked.connect(self._redo)
        btn_redo.setFixedWidth(36)
        top_bar_layout.addWidget(btn_redo)
        self._btn_redo = btn_redo

        # Separator line below top bar
        top_sep = QFrame()
        top_sep.setFrameShape(QFrame.Shape.HLine)
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
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    def _hline(self):
        ln = QFrame()
        ln.setFrameShape(QFrame.Shape.HLine)
        ln.setFrameShadow(QFrame.Shadow.Sunken)
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
        """Update the 16 swatch squares in the Layout & Style tab to show the active palette."""
        self._refresh_combo_icons()
        all_pals = get_all_palettes()
        pal_name = getattr(self, '_color_palette', 'Matplotlib')
        colors = all_pals.get(pal_name, COLOR_PALETTES['Matplotlib'])
        for i, sw in enumerate(getattr(self, '_palette_swatches', [])):
            c = colors[i % len(colors)]
            sw.setStyleSheet(f'background:{c}; border:1px solid #888;')

    def _on_palette_changed(self, name):
        """Called when the palette combo changes. Updates state and re-colors unlocked series."""
        self._color_palette = name
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
        released = 0
        for row in range(self.series_table.rowCount()):
            lbl = self._resolve_series_label(row)
            s = self.curve_styles.get(lbl, {})
            released += bool(s.pop('color_locked', None))
            new_color = self._palette_color(self._local_palette_index(row))
            s['color'] = new_color
            s['marker_color'] = new_color
            self.curve_styles[lbl] = s
            # For Pie subplots, also update per-wedge entries keyed by x-value
            self._recolor_pie_wedges(row, self._local_palette_index(row))
        self._refresh_lock_indicator()
        self.load_curve_style()          # refresh the colour swatches of the Curves tab
        self.update_preview()
        self.statusBar().showMessage(
            f'Palette re-applied: {released} manually coloured series released.'
            if released else 'Palette re-applied: no series had a manual colour.', 5000)

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
        """Refresh File > Open Recent from the saved list of recent charts."""
        menu = getattr(self, '_recent_menu', None)
        if menu is None:
            return
        menu.clear()
        files = settings.get_recent_files()
        names = [os.path.basename(fp) for fp in files]
        for fp in files:
            name = os.path.basename(fp)
            if names.count(name) > 1:       # same name in two folders: say which
                name = f'{name}  —  {os.path.basename(os.path.dirname(fp))}'
            act = menu.addAction(name)
            act.setToolTip(fp)
            act.setStatusTip(fp)
            act.triggered.connect(lambda _=False, p=fp: self._open_recent_file(p))
        if not files:
            empty = menu.addAction('No recent charts')
            empty.setEnabled(False)

    def _open_recent_file(self, fp):
        """Open a recently used chart file chosen from File > Open Recent."""
        if not fp or not os.path.isfile(fp):
            QMessageBox.warning(self, 'Not found', f'File no longer exists:\n{fp}')
            settings.prune_recent_files()
            self._rebuild_recent_files_ui()
            return
        self._load_project_from_path(fp)
