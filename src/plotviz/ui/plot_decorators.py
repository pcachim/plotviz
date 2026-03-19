"""
Copyright (c) 2026 Paulo Cachim
ui/plot_decorators.py  –  plotviz
PlotDecoratorsMixin: axis styling, grid, tick labels, legends and labels.
"""
import numpy as np
import matplotlib.ticker as mticker


class PlotDecoratorsMixin:
    def _apply_cat_ticks(ax, cat_info):
        """Apply categorical tick labels to ax. cat_info is (all_x_cats, bar_horiz) or None."""
        if cat_info is None:
            return
        all_x_cats, bar_horiz = cat_info
        tick_positions = list(range(len(all_x_cats)))
        if bar_horiz:
            ax.set_yticks(tick_positions)
            ax.set_yticklabels(all_x_cats)
        else:
            ax.set_xticks(tick_positions)
            ax.set_xticklabels(all_x_cats, rotation=45, ha='right')

    def _apply_grid(self, ax):
        """Apply major and minor grid styling to ax."""
        if self.grid_check.isChecked():
            ax.grid(True, which='major',
                    color=self.grid_color,
                    linestyle=self.grid_linestyle.currentText(),
                    linewidth=self.grid_linewidth.value(),
                    alpha=self.grid_alpha.value())
        else:
            ax.grid(False, which='major')

        if self.minor_grid_check.isChecked():
            ax.minorticks_on()
            ax.grid(True, which='minor',
                    color=self.minor_grid_color,
                    linestyle=self.minor_grid_linestyle.currentText(),
                    linewidth=self.minor_grid_linewidth.value(),
                    alpha=self.minor_grid_alpha.value())
        else:
            ax.grid(False, which='minor')
            try: ax.minorticks_off()
            except Exception: pass

    def _apply_canvas_style(self, ax, subplot_idx=0):
        """Apply background color, tick styling and border visibility to an axes."""
        from matplotlib.ticker import (AutoMinorLocator, MultipleLocator,
                                       ScalarFormatter, PercentFormatter,
                                       NullLocator, StrMethodFormatter)
        fg      = self.chart_fg_color
        plot_bg = self.plot_bg_color
        ax.set_facecolor(plot_bg)

        xtick_sz  = self.subplot_xtick_sizes.get(subplot_idx, self.xtick_size.value())
        ytick_sz  = self.subplot_ytick_sizes.get(subplot_idx, self.ytick_size.value())
        x_dir     = self.subplot_xtick_dir.get(subplot_idx, 'out')
        y_dir     = self.subplot_ytick_dir.get(subplot_idx, 'out')
        x_rot     = self.subplot_xtick_rotation.get(subplot_idx, 0)
        y_rot     = self.subplot_ytick_rotation.get(subplot_idx, 0)
        x_minor   = self.subplot_xtick_minor.get(subplot_idx, False)
        y_minor   = self.subplot_ytick_minor.get(subplot_idx, False)
        x_step    = self.subplot_xtick_step.get(subplot_idx, 0.0)
        y_step    = self.subplot_ytick_step.get(subplot_idx, 0.0)
        x_fmt     = self.subplot_x_formatter.get(subplot_idx, 'auto')
        y_fmt     = self.subplot_y_formatter.get(subplot_idx, 'auto')
        x_show    = self.subplot_xticks_show.get(subplot_idx, True)
        y_show    = self.subplot_yticks_show.get(subplot_idx, True)

        # ── Major tick params ──────────────────────────────────────────────────
        ax.tick_params(axis='x', which='major', colors=fg, labelsize=xtick_sz,
                       direction=x_dir, labelrotation=x_rot,
                       bottom=x_show, labelbottom=x_show)
        ax.tick_params(axis='y', which='major', colors=fg, labelsize=ytick_sz,
                       direction=y_dir, labelrotation=y_rot,
                       left=y_show, labelleft=y_show)

        # ── Minor ticks ───────────────────────────────────────────────────────
        if x_minor:
            ax.xaxis.set_minor_locator(AutoMinorLocator())
            ax.tick_params(axis='x', which='minor', colors=fg, direction=x_dir,
                           bottom=x_show)
        else:
            ax.xaxis.set_minor_locator(NullLocator())
        if y_minor:
            ax.yaxis.set_minor_locator(AutoMinorLocator())
            ax.tick_params(axis='y', which='minor', colors=fg, direction=y_dir,
                           left=y_show)
        else:
            ax.yaxis.set_minor_locator(NullLocator())

        # ── Major tick step ───────────────────────────────────────────────────
        if x_step > 0:
            ax.xaxis.set_major_locator(MultipleLocator(x_step))
        if y_step > 0:
            ax.yaxis.set_major_locator(MultipleLocator(y_step))

        # ── Tick formatters ───────────────────────────────────────────────────
        def _apply_fmt(axis_obj, fmt_str):
            if fmt_str == 'auto':
                pass  # leave matplotlib default
            elif fmt_str == 'plain':
                f = ScalarFormatter(useOffset=False, useMathText=False)
                f.set_scientific(False)
                axis_obj.set_major_formatter(f)
            elif fmt_str == 'sci':
                f = ScalarFormatter(useMathText=True)
                f.set_scientific(True)
                axis_obj.set_major_formatter(f)
            elif fmt_str == 'percent':
                axis_obj.set_major_formatter(PercentFormatter(xmax=1.0))
            elif '{x' in fmt_str:
                try: axis_obj.set_major_formatter(StrMethodFormatter(fmt_str))
                except Exception: pass
        _apply_fmt(ax.xaxis, x_fmt)
        _apply_fmt(ax.yaxis, y_fmt)

        # ── Polar axes don't have the standard spine set — skip ───────────────
        is_polar = getattr(ax, 'name', '') == 'polar'
        if not is_polar:
            for spine_name, chk in [('top',    self.border_top),
                                      ('bottom', self.border_bottom),
                                      ('left',   self.border_left),
                                      ('right',  self.border_right)]:
                spine = ax.spines[spine_name]
                spine.set_visible(chk.isChecked())
                if chk.isChecked():
                    spine.set_edgecolor(fg)

    def _decorate(self, ax, xc, yd, is3d=False, subplot_idx=0):
        """Apply titles, labels, limits, scale, legend for one subplot panel."""
        ct = self.chart_type_combo.currentText()
        # ── Title ──
        # n==1: chart title = ax title, controlled from Style tab (title_input)
        # n>1: per-subplot title from Axes tab (sp_titles[idx])
        _n_subplots = self.subplot_rows * self.subplot_cols
        if _n_subplots == 1:
            title_txt = self.title_input.text().strip() or self.title_input.placeholderText()
            show_title = self.title_check.isChecked()
            if show_title and title_txt:
                ax.set_title(title_txt,
                             fontsize=self.title_size.value(),
                             color=self.title_color,
                             fontfamily=self.title_font.currentText())
        else:
            title_txt = self.sp_titles.get(subplot_idx, '') or f'Subplot {subplot_idx+1}'
            show_title = self.subplot_title_show.get(subplot_idx, True)
            if show_title and title_txt:
                ax.set_title(title_txt,
                             fontsize=self.subplot_title_size.get(subplot_idx, 11),
                             color=self.subplot_title_color.get(subplot_idx, '#000000'),
                             fontfamily=self.subplot_title_font.get(subplot_idx, 'sans-serif'))
        # ── X label ──
        if self.subplot_xlabel_show.get(subplot_idx, True) and ct not in _NO_X_TYPES:
            xl = self.subplot_xlabels.get(subplot_idx, '') or xc
            if xl:
                ax.set_xlabel(xl,
                              fontsize=self.xlabel_size.value(),
                              color=self.xlabel_color,
                              fontfamily=self.xlabel_font.currentText())
        # ── Y label ──
        if self.subplot_ylabel_show.get(subplot_idx, True):
            yl = self.subplot_ylabels.get(subplot_idx, '') or ', '.join(yd.keys())
            if yl:
                ax.set_ylabel(yl,
                              fontsize=self.ylabel_size.value(),
                              color=self.ylabel_color,
                              fontfamily=self.ylabel_font.currentText())

        # ── Secondary Y axis ──
        _y2_active = False
        if not is3d:
            y2_cols = self._get_y2_cols_from_table()
            if y2_cols:
                _y2_active = True
                ax2 = ax.twinx()
                y2_series = []
                for row in range(self.series_table.rowCount()):
                    y2_item = self.series_table.item(row, 5)
                    if not (y2_item and y2_item.checkState() == Qt.CheckState.Checked):
                        continue
                    xcb = self.series_table.cellWidget(row, 0)
                    ycb = self.series_table.cellWidget(row, 1)
                    lbl_item = self.series_table.item(row, 2)
                    if xcb is None or ycb is None: continue
                    xc_row = xcb.currentText(); yc_row = ycb.currentText()
                    if xc_row not in self.datasets or yc_row not in self.datasets: continue
                    label = lbl_item.text() if lbl_item and lbl_item.text() else yc_row
                    sct = self._get_series_type(row)
                    y2_series.append((self.datasets[xc_row], self.datasets[yc_row], label, sct))
                if y2_series:
                    self._plot_on(ax2, y2_series, ct, row_offset=self._get_series_row_offset(0))
                if self.subplot_y2label_show.get(subplot_idx, True):
                    y2l = self.subplot_y2labels.get(subplot_idx, '') or ', '.join(y2_cols)
                    if y2l:
                        ax2.set_ylabel(y2l,
                                       fontsize=self.y2label_size.value(),
                                       color=self.y2label_color,
                                       fontfamily=self.y2label_font.currentText())
                y2lim = self.subplot_y2lims.get(subplot_idx)
                if y2lim:
                    ax2.set_ylim(y2lim[0], y2lim[1])
                if self.subplot_legends.get(subplot_idx, True):
                    leg_loc = self.subplot_legend_locs.get(subplot_idx, 'best')
                    h1, l1 = ax.get_legend_handles_labels()
                    h2, l2 = ax2.get_legend_handles_labels()
                    if h1 or h2: ax.legend(h1+h2, l1+l2, loc=leg_loc)
                self._apply_canvas_style(ax2, subplot_idx)

        # ── Scale & limits ──
        _series = self._get_series(primary_only=True)
        _x_is_cat = bool(_series) and self._is_categorical(_series[0][0])
        if not is3d:
            if ct not in {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Polar', 'Radar', '3D Surface'}:
                _horiz = ct == 'Bar' and self.bar_horizontal.isChecked()
                _protect_y = _x_is_cat and _horiz
                xs = self.subplot_xscales.get(subplot_idx, 'linear')
                ys = self.subplot_yscales.get(subplot_idx, 'linear')
                if not _x_is_cat:  # never call set_xscale on categorical axes
                    try: ax.set_xscale(xs if xs != 'inverted' else 'linear')
                    except Exception: ax.set_xscale('linear')
                    if xs == 'inverted': ax.invert_xaxis()
                if not _protect_y:
                    try: ax.set_yscale(ys if ys != 'inverted' else 'linear')
                    except Exception: ax.set_yscale('linear')
                    if ys == 'inverted': ax.invert_yaxis()
            xlim = self.subplot_xlims.get(subplot_idx)
            if xlim and ct not in (_NO_X_TYPES | {'Pie'}) and not _x_is_cat:
                ax.set_xlim(xlim[0], xlim[1])
            ylim = self.subplot_ylims.get(subplot_idx)
            if ylim and ct != 'Pie':
                ax.set_ylim(ylim[0], ylim[1])
            if ct not in {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Polar', 'Radar', '3D Surface'}:
                self._apply_grid(ax)

        # ── Legend (no Y2) ──
        if not _y2_active and self.subplot_legends.get(subplot_idx, True) and yd \
                and ct not in _NO_LEGEND_TYPES:
            leg_loc = self.subplot_legend_locs.get(subplot_idx, 'best')
            ax.legend(loc=leg_loc)
        if not is3d:
            self._apply_canvas_style(ax, subplot_idx)

    # ═══════════════════════════════════════════════════════════════════════════
    # UPDATE PREVIEW
    # ═══════════════════════════════════════════════════════════════════════════
