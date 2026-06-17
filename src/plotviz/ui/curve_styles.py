"""
Copyright (c) 2026 Paulo Cachim
ui/curve_styles.py  –  plotviz

CurveStyleMixin: per-series style editing (colour, marker, line) and the
canvas->Series-tab selection bridge. Split out of main_window; mixed into
PlotVizApp so it shares the series table and curve widgets via `self`.
"""


class CurveStyleMixin:
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
            # Navigate to Plots tab (2) → Series inner tab (1)
            self.tabs.setCurrentIndex(2)
            if hasattr(self, 'plots_inner_tabs'):
                self.plots_inner_tabs.setCurrentIndex(1)
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
        _sw_css = 'background-color:{};border:1px solid #888;border-radius:2px;'
        self.curve_color_label.setStyleSheet(_sw_css.format(self.curve_color))
        self.curve_marker_color_label.setStyleSheet(_sw_css.format(self.curve_marker_color))
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
