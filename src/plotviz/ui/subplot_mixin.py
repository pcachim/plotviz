"""
Copyright (c) 2026 Paulo Cachim
ui/subplot_mixin.py — subplot layout, axes state, per-subplot handlers
"""
from PyQt6.QtCore import Qt


from ui.subplot_config import SubplotConfigMixin

class SubplotMixin(SubplotConfigMixin):
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
            self.subplot_chart_types.setdefault(i, 'Line')
            self.sp_titles.setdefault(i, '')
            self.subplot_title_show.setdefault(i, True)
            self.subplot_title_font.setdefault(i, 'sans-serif')
            self.subplot_title_size.setdefault(i, 11)
            self.subplot_title_color.setdefault(i, '#000000')
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
                     self.subplot_title_font, self.subplot_title_size, self.subplot_title_color,
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
        _load(self.sp_title_font, self.subplot_title_font.get(idx, 'sans-serif'))
        _load(self.sp_title_size, self.subplot_title_size.get(idx, 11))
        sp_tc = self.subplot_title_color.get(idx, '#000000')
        self.sp_title_color = sp_tc
        if hasattr(self, 'sp_title_color_label'):
            self.sp_title_color_label.setStyleSheet(f'color:{sp_tc};font-size:16px;')
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
        self.subplot_title_font[idx]   = self.sp_title_font.currentText()
        self.subplot_title_size[idx]   = self.sp_title_size.value()
        self.subplot_title_color[idx]  = self.sp_title_color
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

    def _pick_sp_title_color(self):
        cur = getattr(self, 'sp_title_color', '#000000')
        col = PaletteColorDialog.getColor(QColor(cur), self, palette_colors=self._active_palette_colors())
        if col.isValid():
            self.sp_title_color = col.name()
            self.sp_title_color_label.setStyleSheet(f'color:{col.name()};font-size:16px;')
            self._save_axes_state()
            self.update_preview()

    def _on_sp_title_changed(self):       self._save_axes_state(); self.update_preview()
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

