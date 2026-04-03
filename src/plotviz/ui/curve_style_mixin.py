"""
Copyright (c) 2026 Paulo Cachim
ui/curve_style_mixin.py  –  plotviz
CurveStyleMixin: per-curve style load/save, series query helpers.
"""
from PyQt6.QtCore import Qt


class CurveStyleMixin:
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

        Switches to the Series tab and sets the curve selector to the
        matching series so the user can immediately edit its style.
        """
        idx = self.curve_select.findText(label)
        if idx < 0:
            return
        # Switch to Series tab (index 4: Chart/Data/Axes/Style/Series/Annotations/Advanced)
        self.tabs.setCurrentIndex(4)
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

