"""
Copyright (c) 2026 Paulo Cachim
ui/series_mixin.py — dataset loading, series table management, curve styles
"""
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QComboBox
from PyQt6.QtCore import Qt
from ui.helpers import _get_dir, _remember_dir
from ui.dialogs import DataImportDialog


from ui.curve_style_mixin import CurveStyleMixin

class SeriesMixin(CurveStyleMixin):
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
        cb_y.currentIndexChanged.connect(lambda _: self._update_label_placeholders())
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

