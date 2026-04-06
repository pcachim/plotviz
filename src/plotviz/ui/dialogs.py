"""
Copyright (c) 2026 Paulo Cachim
ui/dialogs.py — AnnotationEditDialog and DataImportDialog
"""
import os, csv
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox, QPushButton, QDialogButtonBox, QComboBox,
    QGroupBox, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QWidget, QMessageBox, QApplication,
)
from PyQt6.QtCore import Qt
from ui.helpers import _show_color_dialog

class PaletteColorDialog:
    @staticmethod
    def getColor(initial=None, parent=None, palette_colors=None):
        return _show_color_dialog(initial, parent, palette_colors)

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


