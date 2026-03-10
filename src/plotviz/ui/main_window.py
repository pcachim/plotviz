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
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

from ui.canvas import CanvasPlotter
from ui.tab_builders import TabBuildersMixin, COLOR_PALETTES, get_all_palettes, PER_SERIES_TYPES
from ui.plot_engine import PlotEngineMixin
from ui.serialization import SerializationMixin


import config.settings as settings
from ui.helpers import _get_dir, _remember_dir, _show_color_dialog


# Backward-compat alias — all existing call sites work unchanged
class PaletteColorDialog:
    @staticmethod
    def getColor(initial=None, parent=None, palette_colors=None):
        return _show_color_dialog(initial, parent, palette_colors)

from data.scientific import CurveFitter
from styling.presets import ChartPresets


class AnnotationEditDialog(QDialog):
    """Edit a single annotation's position, label, style, and image zoom."""

    def __init__(self, ann, parent=None):
        super().__init__(parent)
        self.ann = ann
        self.setWindowTitle('Edit Annotation')
        layout = QVBoxLayout(self)
        form   = QFormLayout()

        atype = ann['type']
        self.fields = {}

        if atype == 'text':
            self.fields['label'] = QLineEdit(ann.get('label',''))
            form.addRow('Label:', self.fields['label'])
            self.fields['x'] = QDoubleSpinBox()
            self.fields['x'].setRange(-1e9, 1e9); self.fields['x'].setDecimals(6)
            self.fields['x'].setValue(ann['x'])
            form.addRow('X:', self.fields['x'])
            self.fields['y'] = QDoubleSpinBox()
            self.fields['y'].setRange(-1e9, 1e9); self.fields['y'].setDecimals(6)
            self.fields['y'].setValue(ann['y'])
            form.addRow('Y:', self.fields['y'])

            s = ann.get('style', {})
            self.fields['fontsize'] = QSpinBox()
            self.fields['fontsize'].setRange(6,72)
            self.fields['fontsize'].setValue(s.get('fontsize',10))
            form.addRow('Font size:', self.fields['fontsize'])

            self.fields['fontcolor'] = QLineEdit(s.get('fontcolor','#000000'))
            btn_fc = QPushButton('…')
            btn_fc.setFixedWidth(28)
            btn_fc.clicked.connect(lambda: self._pick_color('fontcolor'))
            row = QHBoxLayout(); row.addWidget(self.fields['fontcolor']); row.addWidget(btn_fc)
            w = QWidget(); w.setLayout(row)
            form.addRow('Font color:', w)

            self.fields['bg_alpha'] = QDoubleSpinBox()
            self.fields['bg_alpha'].setRange(0,1); self.fields['bg_alpha'].setSingleStep(0.05)
            self.fields['bg_alpha'].setValue(s.get('bg_alpha',0.9))
            form.addRow('BG opacity:', self.fields['bg_alpha'])

            self.fields['bg_color'] = QLineEdit(s.get('bg_color','#ffffcc'))
            btn_bg = QPushButton('…')
            btn_bg.setFixedWidth(28)
            btn_bg.clicked.connect(lambda: self._pick_color('bg_color'))
            row2 = QHBoxLayout(); row2.addWidget(self.fields['bg_color']); row2.addWidget(btn_bg)
            w2 = QWidget(); w2.setLayout(row2)
            form.addRow('BG color:', w2)

        elif atype == 'arrow':
            for k, label in [('x0','Tail X'),('y0','Tail Y'),('x1','Tip X'),('y1','Tip Y')]:
                sb = QDoubleSpinBox()
                sb.setRange(-1e9,1e9); sb.setDecimals(6)
                sb.setValue(ann[k])
                self.fields[k] = sb
                form.addRow(label+':', sb)
            self.fields['label'] = QLineEdit(ann.get('label',''))
            form.addRow('Label:', self.fields['label'])
            s = ann.get('style', {})
            self.fields['fontcolor'] = QLineEdit(s.get('fontcolor','#000000'))
            btn_fc2 = QPushButton('…'); btn_fc2.setFixedWidth(28)
            btn_fc2.clicked.connect(lambda: self._pick_color('fontcolor'))
            row3 = QHBoxLayout(); row3.addWidget(self.fields['fontcolor']); row3.addWidget(btn_fc2)
            w3 = QWidget(); w3.setLayout(row3)
            form.addRow('Arrow color:', w3)

        elif atype == 'image':
            self.fields['x'] = QDoubleSpinBox()
            self.fields['x'].setRange(-1e9,1e9); self.fields['x'].setDecimals(6)
            self.fields['x'].setValue(ann['x'])
            form.addRow('X:', self.fields['x'])
            self.fields['y'] = QDoubleSpinBox()
            self.fields['y'].setRange(-1e9,1e9); self.fields['y'].setDecimals(6)
            self.fields['y'].setValue(ann['y'])
            form.addRow('Y:', self.fields['y'])
            self.fields['zoom'] = QDoubleSpinBox()
            self.fields['zoom'].setRange(0.01,5.0); self.fields['zoom'].setSingleStep(0.05)
            self.fields['zoom'].setValue(ann.get('zoom',0.15))
            form.addRow('Zoom:', self.fields['zoom'])

        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _pick_color(self, field_key):
        cur = self.fields[field_key].text() if field_key in self.fields else '#000000'
        # Pull active palette from main window if available
        mw = QApplication.activeWindow()
        pal_colors = (mw._active_palette_colors()
                      if mw and hasattr(mw, '_active_palette_colors') else None)
        color = PaletteColorDialog.getColor(QColor(cur), self, palette_colors=pal_colors)
        if color.isValid():
            self.fields[field_key].setText(color.name())

    def apply(self):
        """Write edited values back into self.ann."""
        ann   = self.ann
        atype = ann['type']
        if atype == 'text':
            ann['label'] = self.fields['label'].text()
            ann['x']     = self.fields['x'].value()
            ann['y']     = self.fields['y'].value()
            ann.setdefault('style', {})
            ann['style']['fontsize']  = self.fields['fontsize'].value()
            ann['style']['fontcolor'] = self.fields['fontcolor'].text()
            ann['style']['bg_alpha']  = self.fields['bg_alpha'].value()
            ann['style']['bg_color']  = self.fields['bg_color'].text()
            # Preserve edge_color if already set
            ann['style'].setdefault('edge_color', '#aaaaaa')
            ann['style'].setdefault('fontfamily', 'sans-serif')
        elif atype == 'arrow':
            for k in ('x0','y0','x1','y1'):
                ann[k] = self.fields[k].value()
            ann['label'] = self.fields['label'].text()
            ann.setdefault('style', {})
            ann['style']['fontcolor'] = self.fields['fontcolor'].text()
            ann['style'].setdefault('fontsize', 10)
            ann['style'].setdefault('fontfamily', 'sans-serif')
        elif atype == 'image':
            ann['x']    = self.fields['x'].value()
            ann['y']    = self.fields['y'].value()
            ann['zoom'] = self.fields['zoom'].value()


# ═══════════════════════════════════════════════════════════════════════════════
# DATA IMPORT DIALOG
# ═══════════════════════════════════════════════════════════════════════════════
class DataImportDialog(QDialog):
    """
    Per-file import wizard.  Lets the user:
      • choose sheet (Excel), separator (CSV/TXT), or JSON orientation
      • set header row & skip rows
      • preview the raw table
      • select / deselect / rename individual columns
    """

    # ── supported separators for CSV / TXT ───────────────────────────────────
    _SEP_LABELS = ['Auto-detect', 'Comma  (,)', 'Semicolon  (;)',
                   'Tab  (\\t)', 'Space / whitespace', 'Pipe  (|)', 'Custom…']
    _SEP_CHARS  = [None, ',', ';', '\t', r'\s+', '|', None]

    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self.filepath  = filepath
        self.ext       = os.path.splitext(filepath)[1].lower()
        self._raw_df   = None        # full DataFrame from last parse
        self._col_data = {}          # col_name → np.ndarray after dtype inference
        self._col_checks  = {}       # col_name → QCheckBox
        self._col_renames = {}       # col_name → QLineEdit
        self._building = False       # guard against recursive refresh

        self.setWindowTitle(f'Import — {os.path.basename(filepath)}')
        self.setMinimumSize(860, 620)
        self._build_ui()
        self._refresh()

    # ─── UI construction ─────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)

        # ── top bar: file path label ──────────────────────────────────────────
        path_lbl = QLabel(f'<b>File:</b> {self.filepath}')
        path_lbl.setWordWrap(True)
        root.addWidget(path_lbl)

        # ── format-specific options ───────────────────────────────────────────
        opt_box = QGroupBox('Parse options')
        opt_lay = QHBoxLayout(opt_box)
        opt_lay.setSpacing(12)

        # Sheet selector (Excel only)
        self._sheet_label = QLabel('Sheet:')
        self._sheet_combo = QComboBox(); self._sheet_combo.setMinimumWidth(120)
        self._sheet_combo.currentTextChanged.connect(self._refresh)
        opt_lay.addWidget(self._sheet_label)
        opt_lay.addWidget(self._sheet_combo)
        is_excel = self.ext in ('.xlsx', '.xls')
        self._sheet_label.setVisible(is_excel)
        self._sheet_combo.setVisible(is_excel)
        if is_excel:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(self.filepath, read_only=True, data_only=True)
                self._sheet_combo.blockSignals(True)
                self._sheet_combo.addItems(wb.sheetnames)
                self._sheet_combo.blockSignals(False)
                wb.close()
            except Exception:
                try:
                    xl = pd.ExcelFile(self.filepath)
                    self._sheet_combo.blockSignals(True)
                    self._sheet_combo.addItems(xl.sheet_names)
                    self._sheet_combo.blockSignals(False)
                except Exception:
                    pass

        # Separator (CSV / TXT only)
        self._sep_label = QLabel('Separator:')
        self._sep_combo = QComboBox()
        self._sep_combo.addItems(self._SEP_LABELS)
        self._sep_combo.currentIndexChanged.connect(self._on_sep_changed)
        self._sep_custom = QLineEdit(); self._sep_custom.setPlaceholderText('regex / char')
        self._sep_custom.setFixedWidth(80); self._sep_custom.setVisible(False)
        self._sep_custom.editingFinished.connect(self._refresh)
        opt_lay.addWidget(self._sep_label)
        opt_lay.addWidget(self._sep_combo)
        opt_lay.addWidget(self._sep_custom)
        is_text = self.ext in ('.csv', '.txt')
        self._sep_label.setVisible(is_text)
        self._sep_combo.setVisible(is_text)
        if is_text:
            # default: comma for csv, whitespace for txt
            self._sep_combo.blockSignals(True)
            self._sep_combo.setCurrentIndex(1 if self.ext == '.csv' else 4)
            self._sep_combo.blockSignals(False)

        # JSON orientation
        self._json_label = QLabel('Orientation:')
        self._json_combo = QComboBox()
        self._json_combo.addItems(['columns (default)', 'records', 'index', 'split', 'values'])
        self._json_combo.currentTextChanged.connect(self._refresh)
        opt_lay.addWidget(self._json_label)
        opt_lay.addWidget(self._json_combo)
        is_json = self.ext == '.json'
        self._json_label.setVisible(is_json)
        self._json_combo.setVisible(is_json)

        # Header row & skip rows (always visible)
        opt_lay.addWidget(QLabel('Header row:'))
        self._header_spin = QSpinBox(); self._header_spin.setRange(0, 100)
        self._header_spin.setValue(0); self._header_spin.setFixedWidth(55)
        self._header_spin.valueChanged.connect(self._refresh)
        opt_lay.addWidget(self._header_spin)

        opt_lay.addWidget(QLabel('Skip rows:'))
        self._skip_spin = QSpinBox(); self._skip_spin.setRange(0, 1000)
        self._skip_spin.setValue(0); self._skip_spin.setFixedWidth(55)
        self._skip_spin.valueChanged.connect(self._refresh)
        opt_lay.addWidget(self._skip_spin)

        opt_lay.addStretch()
        root.addWidget(opt_box)

        # ── splitter: preview (top) + column picker (bottom) ─────────────────
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Preview table
        preview_w = QWidget(); preview_lay = QVBoxLayout(preview_w); preview_lay.setContentsMargins(0,0,0,0)
        hdr_row = QHBoxLayout()
        hdr_row.addWidget(QLabel('<b>Data preview</b> (first 100 rows):'))
        self._shape_lbl = QLabel('')
        self._shape_lbl.setStyleSheet('color:#555;font-size:11px;')
        hdr_row.addWidget(self._shape_lbl); hdr_row.addStretch()
        preview_lay.addLayout(hdr_row)
        self._preview_table = QTableWidget()
        self._preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectColumns)
        self._preview_table.horizontalHeader().setStretchLastSection(False)
        self._preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._preview_table.setMinimumHeight(180)
        preview_lay.addWidget(self._preview_table)
        splitter.addWidget(preview_w)

        # Column picker
        picker_w = QWidget(); picker_lay = QVBoxLayout(picker_w); picker_lay.setContentsMargins(0,0,0,0)
        pick_hdr = QHBoxLayout()
        pick_hdr.addWidget(QLabel('<b>Columns to import</b> (✔ = include, edit name to rename):'))
        btn_all  = QPushButton('Select all');   btn_all.setFixedWidth(90)
        btn_none = QPushButton('Select none');  btn_none.setFixedWidth(90)
        btn_all.clicked.connect(lambda: self._set_all_checks(True))
        btn_none.clicked.connect(lambda: self._set_all_checks(False))
        pick_hdr.addStretch(); pick_hdr.addWidget(btn_all); pick_hdr.addWidget(btn_none)
        picker_lay.addLayout(pick_hdr)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self._col_picker_widget = QWidget()
        self._col_picker_lay = QVBoxLayout(self._col_picker_widget)
        self._col_picker_lay.setSpacing(3); self._col_picker_lay.setContentsMargins(4,4,4,4)
        scroll.setWidget(self._col_picker_widget)
        picker_lay.addWidget(scroll)
        splitter.addWidget(picker_w)

        splitter.setSizes([280, 200])
        root.addWidget(splitter, 1)

        # ── status / error label ──────────────────────────────────────────────
        self._status_lbl = QLabel('')
        self._status_lbl.setStyleSheet('color:#b00;font-size:11px;')
        self._status_lbl.setWordWrap(True)
        root.addWidget(self._status_lbl)

        # ── dialog buttons ────────────────────────────────────────────────────
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        self._ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setText('Import selected columns')
        root.addWidget(btns)

    # ─── separator combo ─────────────────────────────────────────────────────
    def _on_sep_changed(self, idx):
        is_custom = (idx == len(self._SEP_LABELS) - 1)
        self._sep_custom.setVisible(is_custom)
        if not is_custom:
            self._refresh()

    def _current_sep(self):
        idx = self._sep_combo.currentIndex()
        if idx == len(self._SEP_CHARS) - 1:          # Custom
            return self._sep_custom.text() or ','
        return self._SEP_CHARS[idx]                   # may be None (auto)

    # ─── core parse / refresh ────────────────────────────────────────────────
    def _refresh(self):
        if self._building:
            return
        self._building = True
        try:
            self._raw_df = self._parse()
            if self._raw_df is not None:
                self._status_lbl.setText('')
                self._populate_preview(self._raw_df)
                self._infer_col_data(self._raw_df)
                self._rebuild_col_picker(self._raw_df)
                self._shape_lbl.setText(
                    f'{len(self._raw_df):,} rows × {len(self._raw_df.columns):,} columns')
        except Exception as e:
            self._status_lbl.setText(f'Parse error: {e}')
            self._preview_table.setRowCount(0)
            self._preview_table.setColumnCount(0)
            self._shape_lbl.setText('')
        finally:
            self._building = False

    def _parse(self):
        import pandas as pd
        ext  = self.ext
        hdr  = self._header_spin.value()
        skip = self._skip_spin.value()

        if ext in ('.xlsx', '.xls'):
            sheet = self._sheet_combo.currentText() or 0
            return pd.read_excel(self.filepath, sheet_name=sheet,
                                 header=hdr, skiprows=skip or None)

        if ext == '.json':
            orient_map = {
                'columns (default)': None, 'records': 'records',
                'index': 'index', 'split': 'split', 'values': 'values',
            }
            orient = orient_map.get(self._json_combo.currentText())
            with open(self.filepath) as f:
                import json as _json
                raw = _json.load(f)
            if isinstance(raw, list):
                return pd.DataFrame(raw)
            kw = {'orient': orient} if orient else {}
            return pd.read_json(self.filepath, **kw)

        # CSV / TXT
        sep = self._current_sep()
        if sep is None:                       # auto-detect
            try:
                with open(self.filepath, newline='') as f:
                    dialect = csv.Sniffer().sniff(f.read(4096))
                sep = dialect.delimiter
            except Exception:
                sep = ','
        kw = dict(header=hdr, skiprows=skip or None)
        if sep == r'\s+':
            return pd.read_csv(self.filepath, sep=r'\s+', engine='python', **kw)
        return pd.read_csv(self.filepath, sep=sep, **kw)

    # ─── preview table ───────────────────────────────────────────────────────
    def _populate_preview(self, df):
        preview = df.head(100)
        self._preview_table.blockSignals(True)
        self._preview_table.setRowCount(len(preview))
        self._preview_table.setColumnCount(len(preview.columns))
        self._preview_table.setHorizontalHeaderLabels([str(c) for c in preview.columns])
        for ri, row in enumerate(preview.itertuples(index=False)):
            for ci, val in enumerate(row):
                self._preview_table.setItem(ri, ci, QTableWidgetItem(str(val)))
        self._preview_table.blockSignals(False)

    # ─── dtype inference ─────────────────────────────────────────────────────
    def _infer_col_data(self, df):
        import numpy as np, pandas as pd
        self._col_data = {}
        for col in df.columns:
            series = df[col]
            numeric = pd.to_numeric(series, errors='coerce')
            non_null = series.notna().sum()
            if non_null > 0 and numeric.notna().sum() == non_null:
                self._col_data[str(col)] = numeric.to_numpy(dtype=float, na_value=np.nan)
            else:
                self._col_data[str(col)] = series.fillna('').astype(str).to_numpy()

    # ─── column picker ───────────────────────────────────────────────────────
    def _rebuild_col_picker(self, df):
        # Save existing check states + rename text before wiping
        prev_checks  = {col: cb.isChecked()  for col, cb in self._col_checks.items()}
        prev_renames = {col: le.text()        for col, le in self._col_renames.items()}

        # Clear layout
        while self._col_picker_lay.count():
            item = self._col_picker_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._col_checks.clear()
        self._col_renames.clear()

        cols = [str(c) for c in df.columns]
        dtype_icons = {'float': '🔢', 'str': '🔤'}

        # Header row
        hdr_w = QWidget()
        hdr_l = QHBoxLayout(hdr_w); hdr_l.setContentsMargins(0,0,0,0); hdr_l.setSpacing(6)
        lbl_inc  = QLabel('Include'); lbl_inc.setFixedWidth(56); lbl_inc.setStyleSheet('font-weight:bold;')
        lbl_orig = QLabel('Original name'); lbl_orig.setFixedWidth(180); lbl_orig.setStyleSheet('font-weight:bold;')
        lbl_type = QLabel('Type'); lbl_type.setFixedWidth(42); lbl_type.setStyleSheet('font-weight:bold;')
        lbl_imp  = QLabel('Import as (rename)'); lbl_imp.setStyleSheet('font-weight:bold;')
        hdr_l.addWidget(lbl_inc); hdr_l.addWidget(lbl_orig)
        hdr_l.addWidget(lbl_type); hdr_l.addWidget(lbl_imp); hdr_l.addStretch()
        self._col_picker_lay.addWidget(hdr_w)

        # One row per column
        for col in cols:
            arr = self._col_data.get(col)
            dtype_icon = dtype_icons['float'] if (arr is not None and arr.dtype != object) else dtype_icons['str']

            row_w = QWidget()
            row_l = QHBoxLayout(row_w); row_l.setContentsMargins(0,0,0,0); row_l.setSpacing(6)

            chk = QCheckBox()
            chk.setChecked(prev_checks.get(col, True))
            chk.setFixedWidth(56)
            self._col_checks[col] = chk

            orig_lbl = QLabel(col); orig_lbl.setFixedWidth(180)
            orig_lbl.setToolTip(col)

            type_lbl = QLabel(dtype_icon); type_lbl.setFixedWidth(42)
            type_lbl.setToolTip('Numeric' if dtype_icon == dtype_icons['float'] else 'Text/categorical')

            rename_edit = QLineEdit(prev_renames.get(col, col))
            rename_edit.setMinimumWidth(160)
            rename_edit.setPlaceholderText(col)
            self._col_renames[col] = rename_edit

            # Grey out rename when unchecked
            def _on_check(state, le=rename_edit):
                le.setEnabled(bool(state))
            chk.stateChanged.connect(_on_check)
            rename_edit.setEnabled(chk.isChecked())

            row_l.addWidget(chk)
            row_l.addWidget(orig_lbl)
            row_l.addWidget(type_lbl)
            row_l.addWidget(rename_edit)
            row_l.addStretch()
            self._col_picker_lay.addWidget(row_w)

        self._col_picker_lay.addStretch()

    def _set_all_checks(self, state: bool):
        for chk in self._col_checks.values():
            chk.setChecked(state)

    # ─── accept / collect ─────────────────────────────────────────────────────
    def _on_accept(self):
        selected = {col for col, chk in self._col_checks.items() if chk.isChecked()}
        if not selected:
            QMessageBox.warning(self, 'No columns', 'Select at least one column to import.')
            return
        self.accept()

    def get_selected_data(self) -> dict:
        """Return {import_name: np.ndarray} for all checked columns."""
        result = {}
        for col, chk in self._col_checks.items():
            if not chk.isChecked():
                continue
            new_name = self._col_renames[col].text().strip() or col
            arr = self._col_data.get(col)
            if arr is not None:
                result[new_name] = arr
        return result


class ChartStudioApp(TabBuildersMixin, PlotEngineMixin, SerializationMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        from config._version import __version__
        self.setWindowTitle(f'plotviz {__version__} – Publication-Quality Chart Generator')

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
        self.sp_titles            = {0: ''}
        self.subplot_title_show   = {0: True}
        self.subplot_xlabels      = {0: ''}
        self.subplot_xlabel_show  = {0: True}
        self.subplot_ylabels      = {0: ''}
        self.subplot_ylabel_show  = {0: True}
        self.subplot_y2labels     = {0: ''}
        self.subplot_y2label_show = {0: True}
        self.subplot_legends      = {0: True}
        self.subplot_legend_locs  = {0: 'best'}
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
        self.fit_color     = '#ff7f0e'   # default fit curve style
        self.fit_linestyle = '--'
        self.fit_linewidth = 1.5

        self.init_ui()

        # ── Apply saved preferences to freshly-built widgets ──────────────────
        self._restore_prefs_from_settings()

        # Only enable LaTeX rendering if a LaTeX installation is present.
        # In a frozen .app bundle (or any machine without LaTeX) kpsewhich
        # does not exist, so usetex must stay False or every render call fails.
        import shutil
        if not getattr(__import__('sys'), 'frozen', False) and shutil.which('latex'):
            try:
                plt.rcParams['text.usetex'] = True
                plt.rcParams['text.latex.preamble'] = r'\usepackage{amsmath}\usepackage{amssymb}'
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════════════════════
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
        from ui.tab_builders import _CUSTOM_PALETTES
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
            from ui.tab_builders import add_custom_palette
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
        self.create_data_tab()       # subplot grid + series table + chart-type options
        self.create_style_tab()
        self.create_axes_tab()       # per-subplot selector + titles, labels, limits, legend
        self.create_annotations_tab()
        self.create_advanced_tab()

        # Tooltips shown when hovering over each tab
        for i, tip in enumerate([
            'Data — load files, open/save charts, export images',
            'Series — subplot grid, series table, chart type options',
            'Style — colours, figure size, margins, curves, grid',
            'Axes — per-subplot titles, labels, axis limits and legend',
            'Annotate — place text, arrows and images on the chart',
            'Advanced — curve fitting and function generator',
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

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tabs)
        splitter.addWidget(cv_widget)
        splitter.setSizes([550, 1450])
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
        """Show/hide chart-type option groups for the given chart type string."""
        if not hasattr(self, 'hist_group'):
            return
        vis = {
            self.line_group:      ct == 'Line',
            self.scatter_group:   ct == 'Scatter',
            self.bar_group:       ct == 'Bar',
            self.hist_group:      ct == 'Histogram',
            self.err_group:       ct == 'Errorbar',
            self.heat_group:      ct in ('Heatmap', 'Contour', '3D Surface'),
            self.pie_group:       ct == 'Pie',
            self.area_group:      ct == 'Area',
            self.violin_group:    ct == 'Violin',
            self.boxplot_group:   ct == 'Boxplot',
            self.step_group:      ct == 'Step',
            self.stem_group:      ct == 'Stem',
            self.bubble_group:    ct == 'Bubble',
            self.waterfall_group: ct == 'Waterfall',
            self.hist2d_group:    ct == 'Hist2D',
            self.hexbin_group:    ct == 'Hexbin',
            self.polar_group:     ct == 'Polar',
            self.radar_group:     ct == 'Radar',
            self.ecdf_group:      ct == 'ECDF',
            self.quiver_group:    ct == 'Quiver',
        }
        for grp, show in vis.items():
            grp.setVisible(show)

    def _on_chart_type_changed(self, ct):
        """Chart type selector changed — push to all selected series rows, update option groups."""
        # Push to every selected row's Type combo (col 3)
        if hasattr(self, 'series_table'):
            selected_rows = set(idx.row() for idx in self.series_table.selectedIndexes())
            if not selected_rows:
                selected_rows = set(range(self.series_table.rowCount()))
            for row in selected_rows:
                type_cb = self.series_table.cellWidget(row, 3)
                if type_cb:
                    type_cb.blockSignals(True)
                    i = type_cb.findText(ct)
                    if i >= 0: type_cb.setCurrentIndex(i)
                    type_cb.blockSignals(False)
        self._update_option_group_visibility(ct)
        if hasattr(self, 'datasets'):
            self.update_preview()

    def _on_series_selection_changed(self):
        """Series table selection changed — pull chart type from the first selected row."""
        if not hasattr(self, 'chart_type_combo'): return
        selected_rows = set(idx.row() for idx in self.series_table.selectedIndexes())
        if not selected_rows: return
        row = min(selected_rows)
        type_cb = self.series_table.cellWidget(row, 3)
        if type_cb:
            ct = type_cb.currentText()
            self.chart_type_combo.blockSignals(True)
            i = self.chart_type_combo.findText(ct)
            if i >= 0: self.chart_type_combo.setCurrentIndex(i)
            self.chart_type_combo.blockSignals(False)
            self._update_option_group_visibility(ct)

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    def _hline(self):
        ln = QFrame(); ln.setFrameShape(QFrame.Shape.HLine); ln.setFrameShadow(QFrame.Shadow.Sunken)
        return ln

    @staticmethod
    def _sec_label(txt):
        """Section header label styled like the DATASETS label."""
        from PyQt6.QtWidgets import QLabel
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
        self._refresh_lock_indicator()
        self.update_preview()

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
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                      QLineEdit, QPushButton, QListWidget,
                                      QDialogButtonBox, QMessageBox)
        from ui.tab_builders import get_all_palettes, add_custom_palette, _CUSTOM_PALETTES
        from ui.helpers import _show_color_dialog

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
        from ui.tab_builders import _CUSTOM_PALETTES
        return json.dumps(_CUSTOM_PALETTES, indent=2)

    def _load_custom_palettes_json(self, json_str):
        """Load custom palettes from a JSON string."""
        from ui.tab_builders import add_custom_palette
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
            'fit_color':    getattr(self, 'fit_color',         '#ff7700'),
            'title':        getattr(self, 'title_color',       '#000000'),
            'xlabel':       getattr(self, 'xlabel_color',      '#000000'),
            'ylabel':       getattr(self, 'ylabel_color',      '#000000'),
            'y2label':      getattr(self, 'y2label_color',     '#000000'),
            'curve':        getattr(self, 'curve_color',       '#1f77b4'),
            'curve_marker': getattr(self, 'curve_marker_color','#1f77b4'),
        }.get(target, '#000000')
        color = PaletteColorDialog.getColor(
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
        if target == 'fit_color':
            self.fit_color = hx
            self.fit_color_swatch.setStyleSheet(f'color:{hx};font-size:18px;')
            self.fit_color_hex_lbl.setText(hx)
            self.update_preview(); return
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
        color = PaletteColorDialog.getColor(
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
        color = PaletteColorDialog.getColor(
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
    # DATA
    # ═══════════════════════════════════════════════════════════════════════════
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

    def _reset_app(self):
        """Clear all data and reset UI to defaults."""
        if QMessageBox.question(self, 'Reset', 'Clear all data and reset to defaults?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                ) != QMessageBox.StandardButton.Yes:
            return
        self.datasets.clear()
        self.curve_styles.clear()
        self.canvas.annotations.clear()
        self.subplot_chart_types  = {0: 'Line'}
        self.sp_titles            = {0: ''}
        self.subplot_title_show   = {0: True}
        self.subplot_xlabels      = {0: ''}
        self.subplot_xlabel_show  = {0: True}
        self.subplot_ylabels      = {0: ''}
        self.subplot_ylabel_show  = {0: True}
        self.subplot_y2labels     = {0: ''}
        self.subplot_y2label_show = {0: True}
        self.subplot_legends      = {0: True}
        self.subplot_legend_locs  = {0: 'best'}
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
        self._subplot_mosaic = None
        self._color_palette = 'Matplotlib'
        self.subplot_ann_visible  = {0: True}
        # Reset subplot layout spinboxes — triggers on_subplot_layout_changed via signal
        self.sp_rows.blockSignals(True); self.sp_cols.blockSignals(True)
        self.sp_rows.setValue(1);        self.sp_cols.setValue(1)
        self.sp_rows.blockSignals(False); self.sp_cols.blockSignals(False)
        self.subplot_rows = 1;           self.subplot_cols = 1
        self.on_subplot_layout_changed()
        self.update_lists()
        self.series_table.setRowCount(0)
        self._refresh_curve_select()
        # Redraw canvas with current layout and styles (no data = blank styled axes)
        self.update_preview()
        self.refresh_annotation_list()

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


    def _remove_selected_datasets(self):
        """Remove datasets selected in the dataset list, then refresh."""
        selected = [item.text() for item in self.dataset_list.selectedItems()]
        if not selected:
            return
        for name in selected:
            self.datasets.pop(name, None)
        self.update_lists()
        self.update_preview()

    def update_lists(self, keep_selections=False):
        """Refresh dataset list, combo_z, combo_err, and series table combos."""
        cols = sorted(self.datasets)
        zp = self.combo_z.currentText(); ep = self.combo_err.currentText()
        qup = getattr(self.quiver_u_combo, 'currentText', lambda: '(none)')()
        qvp = getattr(self.quiver_v_combo, 'currentText', lambda: '(none)')()
        bsp = getattr(self.bubble_size_combo, 'currentText', lambda: '(uniform)')()

        self.dataset_list.clear(); self.combo_x.clear()
        self.y_list.clear()
        self.combo_z.clear(); self.combo_z.addItem('(none)')
        self.combo_err.clear(); self.combo_err.addItem('(none)')

        for col in cols:
            self.dataset_list.addItem(col)
            self.combo_x.addItem(col); self.y_list.addItem(col)
            self.combo_z.addItem(col); self.combo_err.addItem(col)

        for combo, prev in [(self.combo_z, zp), (self.combo_err, ep)]:
            i = combo.findText(prev)
            if i >= 0: combo.setCurrentIndex(i)

        # Refresh quiver U/V and bubble size combos
        for combo, sentinel, prev in [
            (self.quiver_u_combo, '(none)',    qup),
            (self.quiver_v_combo, '(none)',    qvp),
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
        """Sync the per-curve style combo with current series table labels."""
        labels = []
        for row in range(self.series_table.rowCount()):
            item = self.series_table.item(row, 2)
            labels.append(item.text() if item else f'Series {row+1}')
        self.curve_select.blockSignals(True)
        prev = self.curve_select.currentText()
        self.curve_select.clear()
        self.curve_select.addItems(labels)
        # Try to restore previous selection
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
        self.series_table.setCellWidget(row, 1, cb_y)

        # Label
        self.series_table.setItem(row, 2, QTableWidgetItem(f'Series {row+1}'))

        # Type combo
        type_cb = QComboBox(); type_cb.addItems(PER_SERIES_TYPES)
        type_cb.currentIndexChanged.connect(self.update_preview)
        type_cb.currentIndexChanged.connect(self._on_series_selection_changed)
        self.series_table.setCellWidget(row, 3, type_cb)

        # Plot spinbox — default to whichever subplot is active in the Subplots tab
        active_subplot = self.sp_active.currentIndex() + 1  # sp_active is 0-based, spinbox is 1-based
        plot_spin = QSpinBox()
        plot_spin.setRange(1, max(1, self.subplot_rows * self.subplot_cols))
        plot_spin.setValue(max(1, active_subplot))
        plot_spin.setMinimumWidth(36)
        plot_spin.valueChanged.connect(self.update_preview)
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

        Switches to the Style tab and sets the curve selector to the
        matching series so the user can immediately edit its style.
        """
        idx = self.curve_select.findText(label)
        if idx < 0:
            return
        # Switch to Style tab (index 2: File/Data/Style/Axes/Annotate/Advanced)
        self.tabs.setCurrentIndex(2)
        # Select the curve — triggers load_curve_style via currentIndexChanged signal
        if self.curve_select.currentIndex() == idx:
            # Already selected — force a reload so swatches reflect current state
            self.load_curve_style()
        else:
            self.curve_select.setCurrentIndex(idx)
        # Show feedback in the status bar
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
        # Render color swatches using stylesheet so color is always correct
        self.curve_color_label.setText('■')
        self.curve_color_label.setStyleSheet(f'color:{self.curve_color};font-size:16px;')
        self.curve_marker_color_label.setText('■')
        self.curve_marker_color_label.setStyleSheet(f'color:{self.curve_marker_color};font-size:16px;')
        self._refresh_lock_indicator()

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
                # Preserve existing lock; only set True when caller explicitly requests it
                'color_locked': existing.get('color_locked', False) or lock_color,
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
        """Set placeholder text on all empty title/label inputs to show
        the auto-derived defaults for the currently active subplot."""
        if not hasattr(self, 'sp_title_input') or not hasattr(self, 'sp_active'):
            return
        idx = self.sp_active.currentIndex()
        if idx < 0: idx = 0
        x_cols, y_cols, y2_cols = self._get_col_names_for_subplot(idx)

        # Subplot title: use joined Y column names, or 'Chart' as last resort
        default_title = ', '.join(y_cols) if y_cols else ('Chart' if not self.sp_titles.get(idx) else '')
        self.sp_title_input.setPlaceholderText(default_title or 'Title text (optional)')

        # X label: first X column name
        default_xl = x_cols[0] if x_cols else ''
        self.xlabel_input.setPlaceholderText(default_xl or 'X label (optional)')

        # Y label: joined primary Y column names
        default_yl = ', '.join(y_cols) if y_cols else ''
        self.ylabel_input.setPlaceholderText(default_yl or 'Y label (optional)')

        # Y2 label: joined Y2 column names
        default_y2l = ', '.join(y2_cols) if y2_cols else ''
        self.y2label_input.setPlaceholderText(default_y2l or 'Y2 label (optional)')

        # Global chart title (Style tab) — show first subplot's Y cols or 'Chart'
        if hasattr(self, 'title_input'):
            if not self.title_input.text():
                self.title_input.setPlaceholderText(
                    ', '.join(y_cols) if y_cols else 'Chart')

    def on_subplot_layout_changed(self, n_override=None):
        r, c = self.sp_rows.value(), self.sp_cols.value()
        self.subplot_rows, self.subplot_cols = r, c
        # When spinboxes are changed manually (not from mosaic dialog), clear mosaic
        if n_override is None:
            self._subplot_mosaic = None
        n = n_override if n_override is not None else r * c
        # Ensure all dicts have entries for every subplot slot
        for i in range(n):
            self.subplot_chart_types.setdefault(i, 'Line')
            self.sp_titles.setdefault(i, '')
            self.subplot_title_show.setdefault(i, True)
            self.subplot_xlabels.setdefault(i, '')
            self.subplot_xlabel_show.setdefault(i, True)
            self.subplot_ylabels.setdefault(i, '')
            self.subplot_ylabel_show.setdefault(i, True)
            self.subplot_y2labels.setdefault(i, '')
            self.subplot_y2label_show.setdefault(i, True)
            self.subplot_legends.setdefault(i, True)
            self.subplot_legend_locs.setdefault(i, 'best')
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
        all_dicts = (self.subplot_chart_types, self.sp_titles, self.subplot_title_show,
                     self.subplot_xlabels, self.subplot_xlabel_show,
                     self.subplot_ylabels, self.subplot_ylabel_show,
                     self.subplot_y2labels, self.subplot_y2label_show,
                     self.subplot_legends, self.subplot_legend_locs,
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
        # Rebuild all subplot selectors and show/hide them
        for combo, vis_attr in [
            (self.sp_active,         '_axes_sp_row_widget'),
            (self.series_sp_active,  '_series_sp_row_widget'),
            (self.ann_sp_active,     '_ann_sp_row_widget'),
        ]:
            combo.blockSignals(True); combo.clear()
            for i in range(n): combo.addItem(f'Subplot {i+1}')
            combo.blockSignals(False)
            combo.setCurrentIndex(0)
            widget = getattr(self, vis_attr, None)
            if widget: widget.setVisible(n > 1)
        self.on_active_subplot_changed()
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

    def on_active_subplot_changed(self):
        """Load per-subplot state into the Axes tab widgets (blocks signals to avoid feedback)."""
        idx = self.sp_active.currentIndex()
        if idx < 0: idx = 0

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

        self._update_label_placeholders()

    # ── Axes tab save-back handlers ──────────────────────────────────────────
    def _save_axes_state(self):
        """Read all Axes tab widgets and persist to the current subplot's dicts."""
        idx = self.sp_active.currentIndex()
        if idx < 0: idx = 0
        self.sp_titles[idx]            = self.sp_title_input.text().strip()
        self.subplot_title_show[idx]   = self.title_show_check.isChecked()
        self.subplot_xlabels[idx]      = self.xlabel_input.text().strip()
        self.subplot_xlabel_show[idx]  = self.xlabel_show_check.isChecked()
        self.subplot_ylabels[idx]      = self.ylabel_input.text().strip()
        self.subplot_ylabel_show[idx]  = self.ylabel_show_check.isChecked()
        self.subplot_y2labels[idx]     = self.y2label_input.text().strip()
        self.subplot_y2label_show[idx] = self.y2label_show_check.isChecked()
        self.subplot_legends[idx]      = self.legend_show_check.isChecked()
        self.subplot_legend_locs[idx]  = self.legend_pos.currentText()
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
        self.update_preview()

    # Legacy aliases kept so existing signal connections don't need changes
    def _on_sp_chart_type_changed(self, ct):
        idx = self.sp_active.currentIndex()
        if idx < 0: idx = 0
        self.subplot_chart_types[idx] = ct
        self.update_preview()

    def _on_sp_title_changed(self):       self._save_axes_state()
    def _on_sp_title_show_changed(self):  self._save_axes_state()
    def _on_sp_xlabel_changed(self):      self._save_axes_state()
    def _on_sp_xlabel_show_changed(self): self._save_axes_state()
    def _on_sp_ylabel_changed(self):      self._save_axes_state()
    def _on_sp_ylabel_show_changed(self): self._save_axes_state()
    def _on_sp_y2label_changed(self):     self._save_axes_state()
    def _on_sp_y2label_show_changed(self):self._save_axes_state()
    def _on_sp_legend_changed(self):      self._save_axes_state()
    def _on_sp_lim_changed(self):         self._save_axes_state()

    # ── Series-tab subplot selector ──────────────────────────────────────────
    def _on_series_subplot_changed(self, idx):
        """Keep the Axes-tab active subplot in sync when changed from Series tab."""
        if idx < 0: return
        self.sp_active.blockSignals(True)
        self.sp_active.setCurrentIndex(idx)
        self.sp_active.blockSignals(False)
        self.on_active_subplot_changed()

    # ── Annotations-tab subplot selector ─────────────────────────────────────
    def _on_ann_subplot_changed(self, idx):
        """Refresh the annotation list and show/hide toggle for the selected subplot."""
        if idx < 0: return
        visible = self.subplot_ann_visible.get(idx, True)
        self.ann_subplot_visible.blockSignals(True)
        self.ann_subplot_visible.setChecked(visible)
        self.ann_subplot_visible.blockSignals(False)
        self.refresh_annotation_list()

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
        btn_group = []

        per_row = 5
        grid_w = QWidget(); grid = QGridLayout(grid_w); grid.setSpacing(10)

        def _make_picker(i):
            def _pick(_=False):
                selected_preset[0] = i
                for j, ob in enumerate(btn_group):
                    ob.setChecked(j == i)
            return _pick

        for i, (name, rows, cols, mosaic) in enumerate(LAYOUTS):
            cell = QWidget()
            cly = QVBoxLayout(cell); cly.setSpacing(3); cly.setContentsMargins(0,0,0,0)
            cly.addWidget(_make_preview(rows, cols, mosaic))
            btn = QPushButton(name); btn.setCheckable(True); btn.setFixedHeight(36)
            btn.clicked.connect(_make_picker(i)); btn_group.append(btn); cly.addWidget(btn)
            grid.addWidget(cell, i // per_row, i % per_row)

        btn_group[0].setChecked(True)
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

        if mosaic is None:
            self.sp_rows.setValue(rows)
            self.sp_cols.setValue(cols)
        else:
            cells = list(dict.fromkeys(c for row in mosaic for c in row))
            n = len(cells)
            self.sp_rows.blockSignals(True); self.sp_cols.blockSignals(True)
            self.sp_rows.setValue(rows); self.sp_cols.setValue(cols)
            self.sp_rows.blockSignals(False); self.sp_cols.blockSignals(False)
            self.subplot_rows = rows; self.subplot_cols = cols
            self.on_subplot_layout_changed(n_override=n)
            self.update_preview()

    def _adv_generate_or_apply(self):
        """Dispatch to x-range generator or column-function applier based on mode radio."""
        if self._adv_mode_range.isChecked():
            self._generate_fx()
        else:
            self._apply_col_function()

    def _on_fit_style_changed(self):
        self.fit_linestyle = self.fit_ls_combo.currentText()
        self.fit_linewidth = self.fit_lw_spin.value()
        self.update_preview()

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
            type_cb = QComboBox(); type_cb.addItems(PER_SERIES_TYPES)
            i_type = type_cb.findText(chart_type)
            if i_type >= 0: type_cb.setCurrentIndex(i_type)
            type_cb.currentIndexChanged.connect(self.update_preview)
            type_cb.currentIndexChanged.connect(self._on_series_selection_changed)
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
        from ui.tab_builders import ALL_CHART_TYPES
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
        cb_type.addItems(ALL_CHART_TYPES)
        form.addRow('Chart type:', cb_type)
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
            xd, yd, lbl, xc, yc = series[0]
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
                type_cb = QComboBox(); type_cb.addItems(PER_SERIES_TYPES)
                type_cb.currentIndexChanged.connect(self.update_preview)
                type_cb.currentIndexChanged.connect(self._on_series_selection_changed)
                self.series_table.setCellWidget(row, 3, type_cb)
                plot_spin = QSpinBox(); plot_spin.setRange(1, max(1, self.subplot_rows * self.subplot_cols))
                plot_spin.setValue(1); plot_spin.valueChanged.connect(self.update_preview)
                self.series_table.setCellWidget(row, 4, plot_spin)
                y2_item = QTableWidgetItem()
                y2_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                y2_item.setCheckState(Qt.CheckState.Unchecked)
                self.series_table.setItem(row, 5, y2_item)

            self._update_confidence_band()
            self._refresh_fit_results_panel()
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

