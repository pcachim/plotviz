"""
Copyright (c) 2026 Paulo Cachim
ui/fit_mixin.py  –  plotviz
FitMixin: apply_fit(), confidence/prediction bands, fit results panel.
"""
import numpy as np
from PyQt6.QtWidgets import QMessageBox


class FitMixin:
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

            # ── Use the curve currently selected in curve_select ──────────────
            selected_label = self.curve_select.currentText() if hasattr(self, 'curve_select') else None
            matched = None
            matched_row = 0
            if selected_label:
                for row in range(self.series_table.rowCount()):
                    item = self.series_table.item(row, 2)
                    if item and item.text() == selected_label:
                        matched_row = row
                        break
                matched = next((s for s in series if s[2] == selected_label), None)
            if matched is None:
                matched = series[0]   # fallback to first

            xd, yd, lbl, xc, yc = matched

            # ── Find the subplot number for this series ────────────────────────
            source_subplot = 1
            for row in range(self.series_table.rowCount()):
                item = self.series_table.item(row, 2)
                if item and item.text() == lbl:
                    spin = self.series_table.cellWidget(row, 4)
                    if spin:
                        source_subplot = spin.value()
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
            nm = f'{lbl} ({model} fit)'\
            
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
                type_cb.currentTextChanged.connect(self._on_series_row_type_changed)
                self.series_table.setCellWidget(row, 3, type_cb)
                # ── Place fit curve on the same subplot as its source series ──
                plot_spin = QSpinBox(); plot_spin.setRange(1, max(1, self.subplot_rows * self.subplot_cols))
                plot_spin.setValue(source_subplot)
                plot_spin.valueChanged.connect(self.update_preview)
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

