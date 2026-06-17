"""
Copyright (c) 2026 Paulo Cachim
ui/subplots.py  –  plotviz

SubplotMixin: subplot layout management (grid + mosaic), per-subplot series and
column resolution, the subplot configuration UI, and the manual/function data
entry helpers. Split out of main_window; mixed into PlotVizApp so its methods
share the series table, subplot dicts and widgets via `self`.
"""
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QTabWidget,
    QVBoxLayout, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from ui.helpers import _show_color_dialog


class SubplotMixin:
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
            xc = xcb.currentText()
            yc = ycb.currentText()
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
                xc = xcb.currentText()
                yc = ycb.currentText()
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
            xc = xcb.currentText()
            yc = ycb.currentText()
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
            self.subplot_title_pad.setdefault(i, 6)
            self.subplot_title_rotation.setdefault(i, 0)
            self.subplot_title_ha.setdefault(i, 'center')
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
            self.subplot_canvas_opts.setdefault(i, self._default_canvas_opts())
            self.subplot_grid_opts.setdefault(i, self._default_grid_opts())
            self.subplot_xaxis_pos.setdefault(i, 'bottom')
            self.subplot_yaxis_pos.setdefault(i, 'left')
            self.subplot_xlabel_rotation.setdefault(i, 0)
            self.subplot_xlabel_labelpad.setdefault(i, 4)
            self.subplot_xlabel_loc.setdefault(i, 'center')
            self.subplot_xlabel_ha.setdefault(i, 'center')
            self.subplot_ylabel_rotation.setdefault(i, 90)
            self.subplot_ylabel_labelpad.setdefault(i, 4)
            self.subplot_ylabel_loc.setdefault(i, 'center')
            self.subplot_ylabel_ha.setdefault(i, 'center')
        # Prune entries beyond current grid
        all_dicts = (self.subplot_chart_types, self.subplot_plot_modes, self.subplot_chart_opts,
                     self.sp_titles, self.subplot_title_show,
                     self.subplot_title_font, self.subplot_title_size, self.subplot_title_color,
                     self.subplot_title_pad, self.subplot_title_rotation, self.subplot_title_ha,
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
                     self.subplot_ann_visible,
                     self.subplot_canvas_opts, self.subplot_grid_opts,
                     self.subplot_xaxis_pos, self.subplot_yaxis_pos,
                     self.subplot_xlabel_rotation, self.subplot_xlabel_labelpad,
                     self.subplot_xlabel_loc, self.subplot_xlabel_ha,
                     self.subplot_ylabel_rotation, self.subplot_ylabel_labelpad,
                     self.subplot_ylabel_loc, self.subplot_ylabel_ha)
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
            (self.layout_sp_active,       '_layout_sp_row_widget'),
        ]:
            combo.blockSignals(True)
            combo.clear()
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
        for combo in (self.ann_sp_active, self.series_sp_active,
                      self.series_curve_sp_active, self.layout_sp_active):
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
        _load(self.sp_title_font,     self.subplot_title_font.get(idx, 'sans-serif'))
        _load(self.sp_title_size,     self.subplot_title_size.get(idx, 11))
        _load(self.sp_title_pad,      self.subplot_title_pad.get(idx, 6))
        _load(self.sp_title_rotation, self.subplot_title_rotation.get(idx, 0))
        _load(self.sp_title_ha,       self.subplot_title_ha.get(idx, 'center'))
        sp_tc = self.subplot_title_color.get(idx, '#000000')
        self.sp_title_color = sp_tc
        if hasattr(self, 'sp_title_color_label'):
            self.sp_title_color_label.setStyleSheet(
                f'background-color:{sp_tc};border:1px solid #888;border-radius:2px;')
        # X axis
        _load(self.xlabel_show_check, self.subplot_xlabel_show.get(idx, True))
        _load(self.xlabel_input,      self.subplot_xlabels.get(idx, ''))
        xlim = self.subplot_xlims.get(idx)
        _load(self.x_auto,  xlim is None)
        _load(self.x_min,   xlim[0] if xlim else 0.0)
        _load(self.x_max,   xlim[1] if xlim else 1.0)
        self.x_min.setEnabled(xlim is not None)   # Bug 4: restore enabled state
        self.x_max.setEnabled(xlim is not None)
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
        self.y_min.setEnabled(ylim is not None)   # Bug 4: restore enabled state
        self.y_max.setEnabled(ylim is not None)
        self._set_scale_rb(self.yscale_group, self.subplot_yscales.get(idx, 'linear'))
        _load(self.ytick_size, self.subplot_ytick_sizes.get(idx, 9))
        _load(self.ytick_dir,      self.subplot_ytick_dir.get(idx, 'out'))
        _load(self.ytick_minor,    self.subplot_ytick_minor.get(idx, False))
        _load(self.ytick_rotation, self.subplot_ytick_rotation.get(idx, 0))
        _load(self.ytick_step,     self.subplot_ytick_step.get(idx, 0.0))
        _load(self.y_formatter,    self.subplot_y_formatter.get(idx, 'auto'))
        _load(self.yticks_show,    self.subplot_yticks_show.get(idx, True))
        _load(self.equal_scale_check, self.subplot_equal_aspect.get(idx, False))
        _load(self.xaxis_pos, self.subplot_xaxis_pos.get(idx, 'bottom'))
        _load(self.yaxis_pos, self.subplot_yaxis_pos.get(idx, 'left'))
        _load(self.xlabel_rotation, self.subplot_xlabel_rotation.get(idx, 0))
        _load(self.xlabel_labelpad, self.subplot_xlabel_labelpad.get(idx, 4))
        _load(self.xlabel_loc,      self.subplot_xlabel_loc.get(idx, 'center'))
        _load(self.xlabel_ha,       self.subplot_xlabel_ha.get(idx, 'center'))
        _load(self.ylabel_rotation, self.subplot_ylabel_rotation.get(idx, 90))
        _load(self.ylabel_labelpad, self.subplot_ylabel_labelpad.get(idx, 4))
        _load(self.ylabel_loc,      self.subplot_ylabel_loc.get(idx, 'center'))
        _load(self.ylabel_ha,       self.subplot_ylabel_ha.get(idx, 'center'))
        # Z axis (3D Surface only)
        _load(self.zlabel_show_check, self.subplot_zlabel_show.get(idx, True))
        _load(self.zlabel_input,      self.subplot_zlabels.get(idx, ''))
        _load(self.zlabel_rotation,   self.subplot_zlabel_rotation.get(idx, 90))
        _load(self.zlabel_labelpad,   self.subplot_zlabel_labelpad.get(idx, 4))
        zcolor = getattr(self, 'zlabel_color', '#000000')
        self.zlabel_color_label.setStyleSheet(
            f'background-color:{zcolor};border:1px solid #888;border-radius:2px;')
        # Y2 axis
        _load(self.y2label_show_check, self.subplot_y2label_show.get(idx, True))
        _load(self.y2label_input,      self.subplot_y2labels.get(idx, ''))
        y2lim = self.subplot_y2lims.get(idx)
        _load(self.y2_auto, y2lim is None)
        _load(self.y2_min,  y2lim[0] if y2lim else 0.0)
        _load(self.y2_max,  y2lim[1] if y2lim else 1.0)
        self.y2_min.setEnabled(y2lim is not None)  # Bug 4: restore enabled state
        self.y2_max.setEnabled(y2lim is not None)
        # Legend
        _load(self.legend_show_check, self.subplot_legends.get(idx, True))
        loc = self.subplot_legend_locs.get(idx, 'best')
        is_auto = (loc == 'best')
        self.legend_auto_pos.blockSignals(True)
        self.legend_auto_pos.setChecked(is_auto)
        self.legend_auto_pos.blockSignals(False)
        self.legend_pos.blockSignals(True)
        if not is_auto:
            i_loc = self.legend_pos.findText(loc)
            self.legend_pos.setCurrentIndex(i_loc if i_loc >= 0 else 0)
        self.legend_pos.blockSignals(False)
        self._update_legend_pos_enabled()
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
            if sw: sw.setStyleSheet(
                f'background-color:{val};border:1px solid #888;border-radius:2px;')
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
        # Load per-subplot canvas/grid values into Layout tab widgets
        self._load_canvas_grid_opts(idx)

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
        self.subplot_title_font[ann_idx]     = self.sp_title_font.currentText()
        self.subplot_title_size[ann_idx]     = self.sp_title_size.value()
        self.subplot_title_color[ann_idx]    = self.sp_title_color
        self.subplot_title_pad[ann_idx]      = self.sp_title_pad.value()
        self.subplot_title_rotation[ann_idx] = self.sp_title_rotation.value()
        self.subplot_title_ha[ann_idx]       = self.sp_title_ha.currentText()
        self.subplot_legends[ann_idx]      = self.legend_show_check.isChecked()
        self.subplot_legend_locs[ann_idx]  = (
            'best' if self.legend_auto_pos.isChecked() else self.legend_pos.currentText())
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
        self.subplot_xaxis_pos[idx]     = self.xaxis_pos.currentText()
        self.subplot_yaxis_pos[idx]     = self.yaxis_pos.currentText()
        self.subplot_xlabel_rotation[idx] = self.xlabel_rotation.value()
        self.subplot_xlabel_labelpad[idx] = self.xlabel_labelpad.value()
        self.subplot_xlabel_loc[idx]      = self.xlabel_loc.currentText()
        self.subplot_xlabel_ha[idx]       = self.xlabel_ha.currentText()
        self.subplot_ylabel_rotation[idx] = self.ylabel_rotation.value()
        self.subplot_ylabel_labelpad[idx] = self.ylabel_labelpad.value()
        self.subplot_ylabel_loc[idx]      = self.ylabel_loc.currentText()
        self.subplot_ylabel_ha[idx]       = self.ylabel_ha.currentText()
        self.subplot_zlabels[idx]         = self.zlabel_input.text().strip()
        self.subplot_zlabel_show[idx]     = self.zlabel_show_check.isChecked()
        self.subplot_zlabel_rotation[idx] = self.zlabel_rotation.value()
        self.subplot_zlabel_labelpad[idx] = self.zlabel_labelpad.value()
        self.update_preview()

    # Legacy aliases kept so existing signal connections don't need changes
    def _on_sp_chart_type_changed(self, ct):
        idx = self.sp_active.currentIndex()
        if idx < 0: idx = 0
        self.subplot_chart_types[idx] = ct
        self._update_margin_ranges()
        self.update_preview()

    def _pick_sp_title_color(self):
        cur = getattr(self, 'sp_title_color', '#000000')
        col = _show_color_dialog(QColor(cur), self, palette_colors=self._active_palette_colors())
        if col.isValid():
            self.sp_title_color = col.name()
            self.sp_title_color_label.setStyleSheet(
                f'background-color:{col.name()};border:1px solid #888;border-radius:2px;')
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
                sw.setStyleSheet(
                    f'background-color:{col.name()};border:1px solid #888;border-radius:2px;')
            self._on_sp_legend_changed()

    def _on_sp_title_changed(self):
        self._save_axes_state()
        self.update_preview()
    def _on_sp_title_show_changed(self):  self._save_axes_state()
    def _on_sp_xlabel_changed(self):      self._save_axes_state()
    def _on_sp_xlabel_show_changed(self): self._save_axes_state()
    def _on_sp_ylabel_changed(self):      self._save_axes_state()
    def _on_sp_ylabel_show_changed(self): self._save_axes_state()
    def _on_sp_y2label_changed(self):     self._save_axes_state()
    def _on_sp_y2label_show_changed(self):self._save_axes_state()
    def _on_sp_zlabel_changed(self):      self._save_axes_state()
    def _on_sp_zlabel_show_changed(self): self._save_axes_state()
    def _update_legend_pos_enabled(self, *_):
        """Enable/disable position combo, X and Y based on the Auto position checkbox."""
        auto = self.legend_auto_pos.isChecked()
        for w in (self.legend_pos, self.legend_x, self.legend_y,
                  self._legend_x_label, self._legend_y_label):
            w.setEnabled(not auto)

    def _on_sp_legend_changed(self):      self._save_axes_state()
    def _on_sp_lim_changed(self):
        """Handle auto/manual limit checkbox toggles and spinbox edits.

        When an auto checkbox is unchecked for the first time, read the current
        matplotlib axis limits from the live canvas and pre-populate the spinboxes
        so the user has a meaningful starting point rather than the 0/1 defaults.
        """
        # ── X limits ──────────────────────────────────────────────────────────
        x_manual = not self.x_auto.isChecked()
        if x_manual and not self.x_min.isEnabled():
            # Switching auto → manual: seed spinboxes from the live plot
            try:
                ax = self.canvas.figure.axes[0]
                lo, hi = ax.get_xlim()
                self.x_min.blockSignals(True)
                self.x_min.setValue(lo)
                self.x_min.blockSignals(False)
                self.x_max.blockSignals(True)
                self.x_max.setValue(hi)
                self.x_max.blockSignals(False)
            except Exception:
                pass
        self.x_min.setEnabled(x_manual)
        self.x_max.setEnabled(x_manual)

        # ── Y limits ──────────────────────────────────────────────────────────
        y_manual = not self.y_auto.isChecked()
        if y_manual and not self.y_min.isEnabled():
            try:
                ax = self.canvas.figure.axes[0]
                lo, hi = ax.get_ylim()
                self.y_min.blockSignals(True)
                self.y_min.setValue(lo)
                self.y_min.blockSignals(False)
                self.y_max.blockSignals(True)
                self.y_max.setValue(hi)
                self.y_max.blockSignals(False)
            except Exception:
                pass
        self.y_min.setEnabled(y_manual)
        self.y_max.setEnabled(y_manual)

        # ── Y2 limits ─────────────────────────────────────────────────────────
        y2_manual = not self.y2_auto.isChecked()
        if y2_manual and not self.y2_min.isEnabled():
            try:
                axes = self.canvas.figure.axes
                ax2 = axes[1] if len(axes) > 1 else axes[0]
                lo, hi = ax2.get_ylim()
                self.y2_min.blockSignals(True)
                self.y2_min.setValue(lo)
                self.y2_min.blockSignals(False)
                self.y2_max.blockSignals(True)
                self.y2_max.setValue(hi)
                self.y2_max.blockSignals(False)
            except Exception:
                pass
        self.y2_min.setEnabled(y2_manual)
        self.y2_max.setEnabled(y2_manual)

        self._save_axes_state()

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
        dlg.setMinimumWidth(620)
        dlg.setMinimumHeight(520)
        dlg_lay = QVBoxLayout(dlg)

        inner_tabs = QTabWidget()
        dlg_lay.addWidget(inner_tabs)

        # ══════════════════════════════════════════════════════════════════════
        # TAB 1 — Presets gallery
        # ══════════════════════════════════════════════════════════════════════
        presets_w = QWidget()
        presets_lay = QVBoxLayout(presets_w)

        def _make_preview(rows, cols, mosaic, size=(88,60)):
            w = QWidget()
            w.setFixedSize(*size)
            g = QGridLayout(w)
            g.setSpacing(2)
            g.setContentsMargins(3,3,3,3)
            style = 'background:#cce;border:1px solid #77a;font-size:8px;border-radius:2px;'
            if mosaic is None:
                for r in range(rows):
                    for c in range(cols):
                        lbl = QLabel(str(r*cols+c+1))
                        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        lbl.setStyleSheet(style)
                        g.addWidget(lbl, r, c)
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
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(10)

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
            cly = QVBoxLayout(cell)
            cly.setSpacing(2)
            cly.setContentsMargins(0,0,0,0)
            cly.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            # Clickable preview container
            prev_widget = _make_preview(rows, cols, mosaic)
            prev_btn = QPushButton()
            prev_btn.setFixedSize(96, 68)
            prev_btn.setFlat(True)
            inner = QVBoxLayout(prev_btn)
            inner.setContentsMargins(4,4,4,4)
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
        scroll_presets = QScrollArea()
        scroll_presets.setWidgetResizable(True)
        scroll_presets.setWidget(grid_w)
        presets_lay.addWidget(scroll_presets)
        inner_tabs.addTab(presets_w, '🗂 Presets')

        # ══════════════════════════════════════════════════════════════════════
        # TAB 2 — Custom mosaic editor
        # ══════════════════════════════════════════════════════════════════════
        custom_w = QWidget()
        custom_lay = QVBoxLayout(custom_w)

        # Grid size controls
        size_row = QHBoxLayout()
        size_row.setSpacing(8)
        size_row.addWidget(QLabel('Rows:'))
        custom_rows = QSpinBox()
        custom_rows.setRange(1, 8)
        custom_rows.setValue(2)
        custom_rows.setFixedWidth(52)
        size_row.addWidget(custom_rows)
        size_row.addWidget(QLabel('Cols:'))
        custom_cols = QSpinBox()
        custom_cols.setRange(1, 8)
        custom_cols.setValue(2)
        custom_cols.setFixedWidth(52)
        size_row.addWidget(custom_cols)
        btn_rebuild = QPushButton('↺ Rebuild grid')
        btn_rebuild.setFixedWidth(110)
        size_row.addWidget(btn_rebuild)
        size_row.addStretch()
        custom_lay.addLayout(size_row)

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
        palette_row = QHBoxLayout()
        palette_row.setSpacing(4)
        palette_row.addWidget(QLabel('Active panel:'))
        palette_btns = {}

        def _letter_colour(letter):
            idx = ord(letter) - ord('A')
            return CELL_COLOURS[idx % len(CELL_COLOURS)]

        for letter in ALL_LETTERS[:8]:
            pb = QPushButton(letter)
            pb.setFixedSize(30, 28)
            pb.setCheckable(True)
            pb.setStyleSheet(f'background:{_letter_colour(letter)};border-radius:4px;font-weight:bold;')
            palette_btns[letter] = pb
            def _sel_letter(checked, l=letter):
                custom_state['paint_letter'] = l
                for ll, bb in palette_btns.items():
                    bb.setChecked(ll == l)
            pb.clicked.connect(_sel_letter)
            palette_row.addWidget(pb)
        palette_btns['A'].setChecked(True)
        palette_row.addStretch()
        custom_lay.addLayout(palette_row)

        # The cell grid container
        grid_frame = QFrame()
        grid_frame.setFrameShape(QFrame.Shape.StyledPanel)
        grid_frame_lay = QGridLayout(grid_frame)
        grid_frame_lay.setSpacing(3)
        grid_frame_lay.setContentsMargins(6,6,6,6)
        custom_lay.addWidget(grid_frame)

        cell_btns = {}   # (r,c) → QPushButton

        # Live preview container — a QWidget with a QGridLayout that mirrors the mosaic
        preview_container = QWidget()
        preview_container.setFixedSize(180, 120)
        preview_grid_lay = QGridLayout(preview_container)
        preview_grid_lay.setSpacing(3)
        preview_grid_lay.setContentsMargins(4,4,4,4)
        preview_cells = {}  # (r,c) → QLabel

        def _update_preview_widget():
            """Rebuild the small preview to mirror current grid state."""
            for lbl in preview_cells.values():
                preview_grid_lay.removeWidget(lbl)
                lbl.deleteLater()
            preview_cells.clear()
            rows = custom_state['rows']
            cols = custom_state['cols']
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
                grid_frame_lay.removeWidget(btn)
                btn.deleteLater()
            cell_btns.clear()
            rows = custom_state['rows']
            cols = custom_state['cols']
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
            rows = custom_rows.value()
            cols = custom_cols.value()
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
                                row_data.append(l)
                                break
                        else:
                            row_data.append('A')
                new_grid.append(row_data)
            custom_state['rows'] = rows
            custom_state['cols'] = cols
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
        share_x = QCheckBox('Share X axis')
        share_x.setChecked(self.sp_sharex.isChecked())
        share_y = QCheckBox('Share Y axis')
        share_y.setChecked(self.sp_sharey.isChecked())
        share_row.addWidget(share_x)
        share_row.addWidget(share_y)
        share_row.addStretch()
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
            rows = custom_state['rows']
            cols = custom_state['cols']
            raw_grid = custom_state['grid']
            # Validate: every cell must have same letter = forms a contiguous block
            # (matplotlib mosaic just needs the list-of-lists, contiguity checked at render)
            mosaic = raw_grid

        self._subplot_mosaic = mosaic

        # Block signals on both spinboxes so we control exactly when
        # on_subplot_layout_changed fires (once, with both values correct).
        self.sp_rows.blockSignals(True)
        self.sp_cols.blockSignals(True)
        self.sp_rows.setValue(rows)
        self.sp_cols.setValue(cols)
        self.sp_rows.blockSignals(False)
        self.sp_cols.blockSignals(False)
        self.subplot_rows = rows
        self.subplot_cols = cols

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
