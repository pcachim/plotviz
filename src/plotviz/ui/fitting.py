"""
Copyright (c) 2026 Paulo Cachim
ui/fitting.py  –  plotviz

FitPresetMixin: chart presets and the curve-fitting workflow (fit dialog,
running fits, fit-result display/export). Split out of main_window; mixed into
PlotVizApp so its methods share the series table, fit state and widgets via
`self`.
"""
import csv
import io
import math

import numpy as np

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSizePolicy, QSpinBox, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)
from data.scientific import CurveFitter
from styling.presets import ChartPresets
from ui.tab_builders import PLOT_MODE_GROUPS, PER_SERIES_TYPES


class FitPresetMixin:
    def apply_preset(self, name):
        ChartPresets.apply(name)
        self.update_preview()

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
            spacing = self.gen_x_spacing.currentText() if hasattr(self, 'gen_x_spacing') else 'linspace'
            if spacing != 'logspace' and x_min >= x_max:
                self.gen_status.setText('❌  x_min must be less than x_max')
                return
            if spacing == 'logspace' and x_min >= x_max:
                self.gen_status.setText('❌  exponent start must be less than stop')
                return

            if spacing == 'linspace':
                xarr = np.linspace(x_min, x_max, n)
            elif spacing == 'logspace':
                xarr = np.logspace(x_min, x_max, n)
            elif spacing == 'geomspace':
                if x_min <= 0 or x_max <= 0:
                    self.gen_status.setText('❌  geomspace requires start and stop > 0')
                    return
                xarr = np.geomspace(x_min, x_max, n)
            elif spacing == 'random':
                mid   = (x_min + x_max) / 2
                sigma = (x_max - x_min) / 6
                xarr  = np.sort(np.random.normal(mid, sigma, n))
            elif spacing == 'uniform':
                xarr = np.sort(np.random.uniform(x_min, x_max, n))
            else:
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
                while base in self.datasets:
                    base = f'{nm}_{cnt}'
                    cnt += 1
                self.datasets[base] = arr
                if attr == 'stored_x': stored_x = base
                else: stored_y = base
            self.update_lists()
            self.gen_status.setText(f'✓  Created "{stored_x}" and "{stored_y}"  ({n} points)')
        except Exception as e:
            self.gen_status.setText(f'❌  {e}')

    # ── Apply function to column ───────────────────────────────────────────────
    def _generate_fxy(self):
        """Generate z = f(x, y) — supports per-axis range/column input and meshgrid."""
        try:
            expr   = self.fxy_expr.text().strip()           if hasattr(self, 'fxy_expr')   else ''
            z_name = self.fxy_z_name.text().strip() or 'z' if hasattr(self, 'fxy_z_name') else 'z'
            if not expr:
                self.fxy_status.setText('❌  Expression is empty')
                return
            meshgrid = getattr(self, 'fxy_meshgrid', None) and self.fxy_meshgrid.isChecked()

            def _make_spacing(arr_min, arr_max, n, spacing):
                """Build a 1-D array from range params and spacing mode."""
                if spacing == 'linspace':
                    return np.linspace(arr_min, arr_max, n)
                elif spacing == 'logspace':
                    if arr_min >= arr_max:
                        raise ValueError('logspace: start exponent must be < stop')
                    return np.logspace(arr_min, arr_max, n)
                elif spacing == 'geomspace':
                    if arr_min <= 0 or arr_max <= 0:
                        raise ValueError('geomspace: start and stop must be > 0')
                    return np.geomspace(arr_min, arr_max, n)
                elif spacing == 'random':
                    mid = (arr_min + arr_max) / 2
                    sigma = (arr_max - arr_min) / 6
                    return np.sort(np.random.normal(mid, sigma, n))
                elif spacing == 'uniform':
                    return np.sort(np.random.uniform(arr_min, arr_max, n))
                return np.linspace(arr_min, arr_max, n)

            # ── Resolve x array ────────────────────────────────────────────────
            x_use_range = getattr(self, 'fxy_x_mode_range', None) and self.fxy_x_mode_range.isChecked()
            if x_use_range:
                x_min = self.fxy_x_min.value()
                x_max = self.fxy_x_max.value()
                if x_min >= x_max and getattr(self, 'fxy_x_spacing', None) and self.fxy_x_spacing.currentText() not in ('logspace',):
                    self.fxy_status.setText('❌  x: min must be < max')
                    return
                x_arr = _make_spacing(x_min, x_max, self.fxy_x_n.value(),
                                      self.fxy_x_spacing.currentText() if hasattr(self, 'fxy_x_spacing') else 'linspace')
                x_var = self.fxy_x_col_name.text().strip() or 'x' if hasattr(self, 'fxy_x_col_name') else 'x'
                x_col_out = x_var
            else:
                x_col = self.fxy_x_combo.currentText() if hasattr(self, 'fxy_x_combo') else ''
                if x_col not in self.datasets:
                    self.fxy_status.setText('❌  x column not found')
                    return
                x_arr = self.datasets[x_col].astype(float)
                x_var = self.fxy_x_var.text().strip() or 'x' if hasattr(self, 'fxy_x_var') else 'x'
                x_col_out = x_col

            # ── Resolve y array ────────────────────────────────────────────────
            y_use_range = getattr(self, 'fxy_y_mode_range', None) and self.fxy_y_mode_range.isChecked()
            if y_use_range:
                y_min = self.fxy_y_min.value()
                y_max = self.fxy_y_max.value()
                if y_min >= y_max and getattr(self, 'fxy_y_spacing', None) and self.fxy_y_spacing.currentText() not in ('logspace',):
                    self.fxy_status.setText('❌  y: min must be < max')
                    return
                y_arr = _make_spacing(y_min, y_max, self.fxy_y_n.value(),
                                      self.fxy_y_spacing.currentText() if hasattr(self, 'fxy_y_spacing') else 'linspace')
                y_var = self.fxy_y_col_name.text().strip() or 'y' if hasattr(self, 'fxy_y_col_name') else 'y'
                y_col_out = y_var
            else:
                y_col = self.fxy_y_combo.currentText() if hasattr(self, 'fxy_y_combo') else ''
                if y_col not in self.datasets:
                    self.fxy_status.setText('❌  y column not found')
                    return
                y_arr = self.datasets[y_col].astype(float)
                y_var = self.fxy_y_var.text().strip() or 'y' if hasattr(self, 'fxy_y_var') else 'y'
                y_col_out = y_col

            # ── Meshgrid expansion ─────────────────────────────────────────────
            if meshgrid:
                X, Y = np.meshgrid(x_arr, y_arr)
                x_eval = X.ravel()
                y_eval = Y.ravel()
                n = len(x_eval)
            else:
                n = min(len(x_arr), len(y_arr))
                x_eval = x_arr[:n]
                y_eval = y_arr[:n]

            # ── Evaluate expression ────────────────────────────────────────────
            ns = {k: getattr(np, k) for k in dir(np) if not k.startswith('_')}
            ns.update({x_var: x_eval, y_var: y_eval,
                       'pi': np.pi, 'e': np.e,
                       'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
                       'exp': np.exp, 'log': np.log, 'log10': np.log10,
                       'sqrt': np.sqrt, 'abs': np.abs})
            z_arr = eval(expr, {'__builtins__': {}}, ns)
            z_arr = np.asarray(z_arr, dtype=float)
            if z_arr.shape == (): z_arr = np.full(n, float(z_arr))

            # ── Store datasets ─────────────────────────────────────────────────
            def _store(name, arr):
                base, cnt, nm = name, 1, name
                while nm in self.datasets:
                    nm = f'{base}_{cnt}'
                    cnt += 1
                self.datasets[nm] = arr
                return nm

            stored_x = _store(x_col_out, x_eval) if x_use_range or meshgrid else x_col_out
            if x_use_range: self.datasets[stored_x] = x_eval
            stored_y = _store(y_col_out, y_eval) if y_use_range or meshgrid else y_col_out
            if y_use_range: self.datasets[stored_y] = y_eval
            stored_z = _store(z_name, z_arr)
            self.update_lists()
            mode_str = 'meshgrid ' if meshgrid else ''
            self.fxy_status.setText(f'\u2713  {mode_str}Created x={stored_x}, y={stored_y}, z={stored_z}  ({n} pts)')
        except Exception as e:
            if hasattr(self, 'fxy_status'):
                self.fxy_status.setText(f'\u274c  {e}')

    def _generate_fuv(self):
        """Generate (u, v) = f(x, y) — vector-field components over a 2-D grid."""
        try:
            u_expr = self.fuv_u_expr.text().strip() if hasattr(self, 'fuv_u_expr') else ''
            v_expr = self.fuv_v_expr.text().strip() if hasattr(self, 'fuv_v_expr') else ''
            u_name = self.fuv_u_name.text().strip() or 'u' if hasattr(self, 'fuv_u_name') else 'u'
            v_name = self.fuv_v_name.text().strip() or 'v' if hasattr(self, 'fuv_v_name') else 'v'
            if not u_expr:
                self.fuv_status.setText('❌  u expression is empty')
                return
            if not v_expr:
                self.fuv_status.setText('❌  v expression is empty')
                return
            meshgrid = getattr(self, 'fuv_meshgrid', None) and self.fuv_meshgrid.isChecked()

            def _make_spacing(arr_min, arr_max, n, spacing):
                if spacing == 'linspace':
                    return np.linspace(arr_min, arr_max, n)
                elif spacing == 'logspace':
                    if arr_min >= arr_max:
                        raise ValueError('logspace: start exponent must be < stop')
                    return np.logspace(arr_min, arr_max, n)
                elif spacing == 'geomspace':
                    if arr_min <= 0 or arr_max <= 0:
                        raise ValueError('geomspace: start and stop must be > 0')
                    return np.geomspace(arr_min, arr_max, n)
                elif spacing == 'random':
                    mid = (arr_min + arr_max) / 2
                    sigma = (arr_max - arr_min) / 6
                    return np.sort(np.random.normal(mid, sigma, n))
                elif spacing == 'uniform':
                    return np.sort(np.random.uniform(arr_min, arr_max, n))
                return np.linspace(arr_min, arr_max, n)

            # ── Resolve x array ────────────────────────────────────────────────
            x_use_range = getattr(self, 'fuv_x_mode_range', None) and self.fuv_x_mode_range.isChecked()
            if x_use_range:
                x_min = self.fuv_x_min.value()
                x_max = self.fuv_x_max.value()
                if x_min >= x_max and self.fuv_x_spacing.currentText() not in ('logspace',):
                    self.fuv_status.setText('❌  x: min must be < max')
                    return
                x_arr = _make_spacing(x_min, x_max, self.fuv_x_n.value(), self.fuv_x_spacing.currentText())
                x_var = self.fuv_x_col_name.text().strip() or 'x'
                x_col_out = x_var
            else:
                x_col = self.fuv_x_combo.currentText() if hasattr(self, 'fuv_x_combo') else ''
                if x_col not in self.datasets:
                    self.fuv_status.setText('❌  x column not found')
                    return
                x_arr = self.datasets[x_col].astype(float)
                x_var = self.fuv_x_var.text().strip() or 'x' if hasattr(self, 'fuv_x_var') else 'x'
                x_col_out = x_col

            # ── Resolve y array ────────────────────────────────────────────────
            y_use_range = getattr(self, 'fuv_y_mode_range', None) and self.fuv_y_mode_range.isChecked()
            if y_use_range:
                y_min = self.fuv_y_min.value()
                y_max = self.fuv_y_max.value()
                if y_min >= y_max and self.fuv_y_spacing.currentText() not in ('logspace',):
                    self.fuv_status.setText('❌  y: min must be < max')
                    return
                y_arr = _make_spacing(y_min, y_max, self.fuv_y_n.value(), self.fuv_y_spacing.currentText())
                y_var = self.fuv_y_col_name.text().strip() or 'y'
                y_col_out = y_var
            else:
                y_col = self.fuv_y_combo.currentText() if hasattr(self, 'fuv_y_combo') else ''
                if y_col not in self.datasets:
                    self.fuv_status.setText('❌  y column not found')
                    return
                y_arr = self.datasets[y_col].astype(float)
                y_var = self.fuv_y_var.text().strip() or 'y' if hasattr(self, 'fuv_y_var') else 'y'
                y_col_out = y_col

            # ── Meshgrid expansion ─────────────────────────────────────────────
            if meshgrid:
                X, Y = np.meshgrid(x_arr, y_arr)
                x_eval = X.ravel()
                y_eval = Y.ravel()
                n = len(x_eval)
            else:
                n = min(len(x_arr), len(y_arr))
                x_eval = x_arr[:n]
                y_eval = y_arr[:n]

            # ── Evaluate expressions ───────────────────────────────────────────
            ns = {k: getattr(np, k) for k in dir(np) if not k.startswith('_')}
            ns.update({x_var: x_eval, y_var: y_eval,
                       'pi': np.pi, 'e': np.e,
                       'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
                       'exp': np.exp, 'log': np.log, 'log10': np.log10,
                       'sqrt': np.sqrt, 'abs': np.abs})
            u_arr = np.asarray(eval(u_expr, {'__builtins__': {}}, ns), dtype=float)
            v_arr = np.asarray(eval(v_expr, {'__builtins__': {}}, ns), dtype=float)
            if u_arr.shape == (): u_arr = np.full(n, float(u_arr))
            if v_arr.shape == (): v_arr = np.full(n, float(v_arr))

            # ── Store datasets ─────────────────────────────────────────────────
            def _store(name, arr):
                base, cnt, nm = name, 1, name
                while nm in self.datasets:
                    nm = f'{base}_{cnt}'
                    cnt += 1
                self.datasets[nm] = arr
                return nm

            stored_x = _store(x_col_out, x_eval) if x_use_range or meshgrid else x_col_out
            if x_use_range: self.datasets[stored_x] = x_eval
            stored_y = _store(y_col_out, y_eval) if y_use_range or meshgrid else y_col_out
            if y_use_range: self.datasets[stored_y] = y_eval
            stored_u = _store(u_name, u_arr)
            stored_v = _store(v_name, v_arr)
            self.update_lists()
            mode_str = 'meshgrid ' if meshgrid else ''
            self.fuv_status.setText(
                f'\u2713  {mode_str}Created x={stored_x}, y={stored_y}, '
                f'u={stored_u}, v={stored_v}  ({n} pts)')
        except Exception as e:
            if hasattr(self, 'fuv_status'):
                self.fuv_status.setText(f'\u274c  {e}')

    def _apply_col_function(self):
        try:
            src_col = self.fn_source_combo.currentText()
            var     = self.fn_var_name.text().strip() or 'x'
            expr    = self.fn_expr.text().strip()
            out_nm  = self.fn_out_name.text().strip() or 'result'
            if src_col not in self.datasets:
                self.fn_status.setText('❌  No source column selected')
                return
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
            while stored_nm in self.datasets:
                stored_nm = f'{base}_{cnt}'
                cnt += 1
            self.datasets[stored_nm] = result
            self.update_lists()
            self.fn_status.setText(f'✓  Created "{stored_nm}"  ({len(result)} points)')
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

        form = QFormLayout()
        form.setSpacing(7)
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
                                     QLineEdit, QFrame)
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
        dlg.resize(min(140 + 110 * len(cols), 1100), 600)
        vlay = QVBoxLayout(dlg)

        info = QLabel(
            f'{len(cols)} column(s)   ·   up to {n_rows} row(s)   —   '
            '<b>double-click a cell to edit</b>')
        info.setStyleSheet('color:#555; font-size:11px;')
        vlay.addWidget(info)

        # ── Column rename row ──────────────────────────────────────────────────
        rename_frame = QFrame()
        rename_frame.setFrameShape(QFrame.Shape.StyledPanel)
        rename_layout = QHBoxLayout(rename_frame)
        rename_layout.setContentsMargins(6, 4, 6, 4)
        rename_layout.setSpacing(6)
        rename_layout.addWidget(QLabel('<b>Column name:</b>'))
        name_edits = []   # one QLineEdit per column, same order as cols
        for col in cols:
            ed = QLineEdit(col)
            ed.setPlaceholderText('column name')
            ed.setMinimumWidth(90)
            name_edits.append(ed)
            rename_layout.addWidget(ed, 1)
        vlay.addWidget(rename_frame)

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

        # Keep table header in sync as user types a new name
        def _sync_header(ci, text):
            tbl.setHorizontalHeaderItem(ci, QTableWidgetItem(text or cols[ci]))
        for ci, ed in enumerate(name_edits):
            ed.textChanged.connect(lambda text, ci=ci: _sync_header(ci, text))

        vlay.addWidget(tbl)

        note2 = QLabel('Changes are written back when you click Apply or OK.')
        note2.setStyleSheet('color:#888; font-size:10px;')
        vlay.addWidget(note2)

        def _apply_edits():
            # ── 1. Apply column renames first ─────────────────────────────────
            renamed = {}   # old_name -> new_name for changed names
            for ci, (old_col, ed) in enumerate(zip(cols, name_edits)):
                new_name = ed.text().strip()
                if not new_name or new_name == old_col:
                    continue
                if new_name in self.datasets and new_name != old_col:
                    info.setText(f'⚠  Column "{new_name}" already exists — rename skipped.')
                    continue
                # Rename: preserve insertion order by rebuilding the dict
                self.datasets = {
                    (new_name if k == old_col else k): v
                    for k, v in self.datasets.items()
                }
                renamed[old_col] = new_name
                cols[ci] = new_name   # update working list for the data-write step

            # ── 2. Write edited cell values back ──────────────────────────────
            for ci, col in enumerate(cols):
                arr = self.datasets[col]
                is_cat = self._is_categorical(arr)
                new_vals = []
                for ri in range(n_rows):
                    cell = tbl.item(ri, ci)
                    if cell is None or cell.text().strip() == '':
                        new_vals.append('' if is_cat else np.nan)
                        continue
                    txt = cell.text().strip()
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

            # ── 3. Refresh all column pickers if any rename happened ──────────
            if renamed:
                # update_lists() snapshots currentText() at the very top before
                # clearing, so we must make each combo report the *new* name
                # before update_lists() runs.  setCurrentText() only works when
                # the text already exists as an item, so we rename the matching
                # item in-place with setItemText() instead.
                def _rename_item(cb, old_new):
                    for i in range(cb.count()):
                        txt = cb.itemText(i)
                        if txt in old_new:
                            cb.setItemText(i, old_new[txt])

                # Series table X / Y combos (cols 0 and 1)
                for row in range(self.series_table.rowCount()):
                    for col_idx in (0, 1):
                        cb = self.series_table.cellWidget(row, col_idx)
                        if cb is not None:
                            _rename_item(cb, renamed)

                # Single-select combos that update_lists() snapshots at the top
                for attr in ('combo_z', 'combo_err', 'combo_fill_y2',
                             'quiver_u_combo', 'quiver_v_combo',
                             'barbs_u_combo',  'barbs_v_combo',
                             'stream_u_combo', 'stream_v_combo',
                             'bubble_size_combo', 'fn_source_combo',
                             'err_xerr_combo'):
                    cb = getattr(self, attr, None)
                    if cb is not None:
                        _rename_item(cb, renamed)

                self.update_lists()
                parts = ', '.join(f'"{o}" → "{n}"' for o, n in renamed.items())
                info.setText(f'✓  Renamed: {parts}')
            else:
                info.setText(f'✓  Applied edits to: {", ".join(cols)}')
            self.update_preview()

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
            self.table_status.setText('❌  Clipboard is empty')
            return
        # Detect delimiter
        delim = '\t' if '\t' in text.split('\n')[0] else ','
        reader = list(csv.reader(io.StringIO(text), delimiter=delim))
        if not reader:
            self.table_status.setText('❌  No data found')
            return
        # Check if first row looks like a header
        first = reader[0]
        def _is_num(v):
            try:
                float(v)
                return True
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
                while base in self.datasets:
                    base = f'{col_name}_{cnt}'
                    cnt += 1
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
        label = self.curve_select.currentText() if hasattr(self, 'curve_select') else ''
        if label and label in self._fits:
            self._fits[label]['ci_idx'] = self.fit_ci_combo.currentIndex()
            self._fits[label]['pi_idx'] = self.fit_pi_combo.currentIndex()
        self._update_confidence_band_for(label)
        self.update_preview()

    def apply_fit(self):
        try:
            model = self.fit_combo.currentText()
            if model == 'None': return
            series = self._get_series_full()
            if not series:
                QMessageBox.warning(self, 'Warning', 'Add at least one series in the Data tab first.')
                return

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
                QMessageBox.warning(self, 'Fit Failed', f'Could not fit {model} to the data.')
                return

            # Full statistics
            stats = CurveFitter.full_stats(xd, yd, popt, pcov, func, model)

            # Store everything for CI/PI plotting and serialization
            self._last_fit = dict(xd=xd, yd=yd, popt=popt, pcov=pcov, func=func,
                                  model=model, xc=xc, yc=yc, lbl=lbl,
                                  eq_str=eq_str, r2=r2, stats=stats)

            # Add fit curve as a new dataset
            nm = f'{lbl} ({model} fit)'
            self.datasets[nm] = func(xd, *popt)

            # Store per-series fit for independent CI/PI bands
            existing = self._fits.get(nm, {})
            self._fits[nm] = dict(xd=xd, yd=yd, popt=popt, pcov=pcov, func=func,
                                  model=model, xc=xc, yc=yc, lbl=lbl,
                                  eq_str=eq_str, r2=r2, stats=stats,
                                  ci_idx=existing.get('ci_idx', 0),
                                  pi_idx=existing.get('pi_idx', 0))
            self._last_fit = self._fits[nm]

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
                    cb = QComboBox()
                    cb.addItems(sorted(self.datasets))
                    idx = cb.findText(col_name)
                    if idx >= 0: cb.setCurrentIndex(idx)
                    handler = self._on_x_col_changed if col_idx == 0 else self.update_preview
                    cb.currentIndexChanged.connect(handler)
                    self.series_table.setCellWidget(row, col_idx, cb)
                self.series_table.setItem(row, 2, QTableWidgetItem(nm))
                _mode = self.plot_mode_combo.currentText() if hasattr(self, 'plot_mode_combo') else 'Standard'
                _allowed = list(PLOT_MODE_GROUPS.get(_mode, PER_SERIES_TYPES))
                type_cb = QComboBox()
                type_cb.addItems(_allowed)
                type_cb.currentTextChanged.connect(self._on_series_row_type_changed)
                self.series_table.setCellWidget(row, 3, type_cb)
                plot_spin = QSpinBox()
                plot_spin.setRange(1, max(1, self.subplot_rows * self.subplot_cols))
                plot_spin.setValue(source_plot_num)
                plot_spin.valueChanged.connect(self.update_preview)
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

            self._update_confidence_band_for(nm)
            self._refresh_fit_results_panel(nm)
            if hasattr(self, '_fit_export_widget'):
                self._fit_export_widget.setEnabled(True)
            # Switch the Per-Curve selector to the fit curve so the user can
            # immediately style it — no ambiguity about which curve is active.
            if hasattr(self, 'curve_select'):
                idx = self.curve_select.findText(nm)
                if idx >= 0:
                    self.curve_select.setCurrentIndex(idx)
            self._load_fit_combos_for(nm)
            self.update_preview()
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _refresh_fit_results_panel(self, label=None):
        """Populate the fit results QTextEdit with full regression output."""
        if label is None:
            label = self.curve_select.currentText() if hasattr(self, 'curve_select') else ''
        fit = self._fits.get(label) or self._last_fit
        if fit is None:
            return
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
            pv = pvals[i]
            tv = tstats[i]
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
        """Legacy shim — delegates to the per-series implementation."""
        label = self.curve_select.currentText() if hasattr(self, 'curve_select') else ''
        self._update_confidence_band_for(label)

    def _update_confidence_band_for(self, label):
        """Recompute CI/PI band datasets for one fit-curve label."""
        if not label:
            return
        fit = self._fits.get(label)
        if fit is None:
            return
        base = label
        ci_idx = fit.get('ci_idx', 0)
        pi_idx = fit.get('pi_idx', 0)
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

    def _load_fit_combos_for(self, label):
        """Sync CI/PI combos to the stored state for a given fit-curve label."""
        fit = self._fits.get(label)
        self.fit_ci_combo.blockSignals(True)
        self.fit_pi_combo.blockSignals(True)
        self.fit_ci_combo.setCurrentIndex(fit['ci_idx'] if fit else 0)
        self.fit_pi_combo.setCurrentIndex(fit['pi_idx'] if fit else 0)
        self.fit_ci_combo.blockSignals(False)
        self.fit_pi_combo.blockSignals(False)

    def _on_fit_series_changed(self):
        """Called when curve_select changes — refresh CI/PI combos and results panel."""
        label = self.curve_select.currentText() if hasattr(self, 'curve_select') else ''
        is_fit = label in self._fits
        has_any_fits = bool(self._fits)
        if hasattr(self, '_fit_controls_widget'):
            self._fit_controls_widget.setEnabled(is_fit)
        if hasattr(self, '_fit_export_widget'):
            self._fit_export_widget.setEnabled(has_any_fits)
        if not is_fit:
            if hasattr(self, 'fit_results_text'):
                self.fit_results_text.setPlainText('Run a fit to see results.')
            self._load_fit_combos_for('')
            return
        self._load_fit_combos_for(label)
        self._refresh_fit_results_panel(label)

    def _remove_fits_for_labels(self, source_labels):
        """Remove all fitted curves whose source series is in source_labels.

        Does NOT call update_preview — callers are responsible for that.
        Returns True if anything was removed.
        """
        targets = []
        for lbl in source_labels:
            if lbl in self._fits:
                targets.append(lbl)          # fit curve itself selected
            else:
                targets += [nm for nm in list(self._fits) if self._fits[nm].get('lbl') == lbl]

        if not targets:
            return False

        for nm in targets:
            for suffix in ('', ' CI upper', ' CI lower', ' PI upper', ' PI lower'):
                self.datasets.pop(nm + suffix, None)
            self._fits.pop(nm, None)
            self.curve_styles.pop(nm, None)
            for row in range(self.series_table.rowCount() - 1, -1, -1):
                item = self.series_table.item(row, 2)
                if item and item.text() == nm:
                    self.series_table.removeRow(row)
                    break

        if hasattr(self, 'fit_results_text'):
            self.fit_results_text.setPlainText('Run a fit to see results.')
        return True

    def _remove_fit(self):
        """Remove the fitted curve(s) associated with the currently selected series."""
        label = self.curve_select.currentText() if hasattr(self, 'curve_select') else ''
        if not label:
            return

        removed = self._remove_fits_for_labels([label])
        if not removed:
            QMessageBox.information(self, 'No Fit', 'No fitted curve found for the selected series.')
            return

        self.update_lists()
        self.update_preview()

    def _export_fit_results(self):
        """Save fit results to .txt — either the current fit or all fits if the checkbox is ticked."""
        import math
        from PyQt6.QtWidgets import QFileDialog

        # ── Glossary tables (shared) ──────────────────────────────────────────
        _MODEL_GLOSSARY = {
            'Linear': [
                ('a', 'Slope — change in y per unit change in x'),
                ('b', 'Intercept — value of y when x = 0'),
            ],
            'Quadratic': [
                ('a', 'Coefficient of x² — controls the curvature and opening direction'),
                ('b', 'Coefficient of x — controls the tilt of the parabola'),
                ('c', 'Constant — value of y when x = 0'),
            ],
            'Cubic': [
                ('a', 'Coefficient of x³ — controls the dominant curvature at large |x|'),
                ('b', 'Coefficient of x² — controls secondary curvature'),
                ('c', 'Coefficient of x — controls the slope near x = 0'),
                ('d', 'Constant — value of y when x = 0'),
            ],
            'Exponential': [
                ('a', 'Amplitude — scaling factor / value of y when x = 0'),
                ('b', 'Rate — positive = growth, negative = decay; half-life = ln(2)/|b|'),
            ],
            'Power Law': [
                ('a', 'Coefficient — scaling factor'),
                ('b', 'Exponent — b > 1: super-linear, 0 < b < 1: sub-linear, b < 0: inverse'),
            ],
            'Logarithmic': [
                ('a', 'Log coefficient — steepness of the log curve'),
                ('b', 'Offset — vertical shift'),
            ],
            'Sigmoid': [
                ('a', 'Ceiling — upper asymptote (maximum value the curve approaches)'),
                ('b (midpoint)', 'Midpoint — x value at 50% of the ceiling (inflection point)'),
                ('c (scale)', 'Scale — steepness; small |c| = steep, large |c| = gradual'),
            ],
        }
        _STATS_GLOSSARY = [
            ('n',           'Number of data points used in the fit'),
            ('Parameters',  'Number of free parameters estimated by the model'),
            ('DoF',         'Degrees of freedom = n − Parameters'),
            ('R²',          'Coefficient of determination — fraction of variance explained (0–1; closer to 1 is better)'),
            ('Adj. R²',     'R² penalised for extra parameters; more reliable for comparing models with different complexity'),
            ('RMSE',        'Root Mean Squared Error — typical size of residuals in y-units (lower is better)'),
            ('MSE',         'Mean Squared Error = RMSE²'),
            ('SSE',         'Sum of Squared Errors — total squared deviation of fitted values from data'),
            ('SST',         'Total Sum of Squares — total squared deviation of data from its mean'),
            ('F-statistic', 'Tests whether the model explains significantly more variance than a flat mean'),
            ('F p-value',   'Probability of observing this F under the null hypothesis; < 0.05 is conventionally significant'),
            ('AIC',         'Akaike Information Criterion — lower = better trade-off of fit quality vs. model complexity'),
            ('BIC',         'Bayesian Information Criterion — like AIC but penalises complexity more heavily'),
        ]
        _PARAM_STATS_GLOSSARY = [
            ('value ± SE',  'Estimated parameter value and its standard error'),
            ('t',           't-statistic for H₀: parameter = 0 (larger |t| = stronger evidence the parameter matters)'),
            ('p',           'p-value for the t-test; < 0.05 suggests the parameter is statistically significant'),
            ('CI',          'Confidence interval — range likely to contain the true parameter value at the stated confidence level'),
        ]

        def _build_glossary(models_used):
            gl = ['', '═' * 52, 'GLOSSARY', '═' * 52]
            shown = set()
            for model in models_used:
                if model in _MODEL_GLOSSARY and model not in shown:
                    shown.add(model)
                    gl.append('')
                    gl.append(f'── Model parameters  ({model}) ──────────────')
                    for name, meaning in _MODEL_GLOSSARY[model]:
                        gl.append(f'  {name:<20}  {meaning}')
            gl.append('')
            gl.append('── Goodness-of-fit statistics ────────────────')
            for name, meaning in _STATS_GLOSSARY:
                gl.append(f'  {name:<16}  {meaning}')
            gl.append('')
            gl.append('── Per-parameter statistics ──────────────────')
            for name, meaning in _PARAM_STATS_GLOSSARY:
                gl.append(f'  {name:<16}  {meaning}')
            return gl

        def _fit_block(nm, fit):
            """Return lines for one fit result, including series/axis context."""
            st = fit.get('stats', {})
            if not st:
                return [f'  (no statistics available for {nm})']
            ci_pct = int((1 - st.get('alpha', 0.05)) * 100)
            lines = []
            lines.append(f'Series:    {fit.get("lbl", nm)}')
            lines.append(f'X column:  {fit.get("xc", "—")}')
            lines.append(f'Y column:  {fit.get("yc", "—")}')
            lines.append(f'Fit name:  {nm}')
            lines.append(f'Model:     {fit["model"]}')
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
                pv = pvals[i]
                tv = tstats[i]
                pv_str = f'{pv:.4g}' if not math.isnan(pv) else '—'
                tv_str = f'{tv:.4g}' if not math.isnan(tv) else '—'
                lo_str = f'{cilo[i]:.4g}' if not math.isnan(cilo[i]) else '—'
                hi_str = f'{cihi[i]:.4g}' if not math.isnan(cihi[i]) else '—'
                lines.append(f'  {names[i]}')
                lines.append(f'    value  = {vals[i]:.6g}  ±{ses[i]:.4g}')
                lines.append(f'    t      = {tv_str}    p = {pv_str}')
                lines.append(f'    CI     = [{lo_str}, {hi_str}]')
            return lines

        # ── Determine what to export ──────────────────────────────────────────
        export_all = (hasattr(self, 'fit_export_all_check') and
                      self.fit_export_all_check.isChecked())

        if export_all:
            if not self._fits:
                QMessageBox.information(self, 'No Results', 'No fitted curves found.')
                return
            fits_to_export = list(self._fits.items())
            default_name = 'all_fits_results.txt'
        else:
            label = self.curve_select.currentText() if hasattr(self, 'curve_select') else ''
            fit = self._fits.get(label) or self._last_fit
            if fit is None or not fit.get('stats'):
                QMessageBox.information(self, 'No Results', 'Run a fit first.')
                return
            fits_to_export = [(label, fit)]
            safe = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in label).strip() or 'fit'
            default_name = f'{safe}_results.txt'

        path, _ = QFileDialog.getSaveFileName(
            self, 'Export Fit Results', default_name, 'Text files (*.txt);;All files (*)')
        if not path:
            return

        # ── Build full output ─────────────────────────────────────────────────
        all_lines = []
        models_used = []
        sep = '─' * 52

        if export_all:
            all_lines.append('═' * 52)
            all_lines.append(f'  CURVE FIT RESULTS  —  {len(fits_to_export)} fit(s)')
            all_lines.append('═' * 52)

        for i, (nm, fit) in enumerate(fits_to_export):
            if export_all and i > 0:
                all_lines.append('')
                all_lines.append(sep)
            all_lines += _fit_block(nm, fit)
            model = fit.get('model', '')
            if model and model not in models_used:
                models_used.append(model)

        all_lines += _build_glossary(models_used)

        try:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('\n'.join(all_lines))
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage(f'Fit results saved to {path}', 4000)
        except Exception as e:
            QMessageBox.critical(self, 'Export Failed', str(e))

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
