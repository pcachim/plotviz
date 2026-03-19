"""
Copyright (c) 2026 Paulo Cachim
ui/advanced_mixin.py — Advanced tab handlers: function generator, curve fitting,
                        data table, series inspection
"""
import numpy as np
from PyQt6.QtWidgets import QMessageBox, QDialog, QInputDialog
from PyQt6.QtCore import Qt


from ui.fit_mixin import FitMixin

class AdvancedMixin(FitMixin):
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

