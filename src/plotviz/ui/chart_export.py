"""
Copyright (c) 2026 Paulo Cachim
ui/chart_export.py  –  plotviz
ChartExportMixin: export_chart() — renders and saves chart to file.
"""
import io, os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from ui.tab_builders import WHOLE_CHART_TYPES


class ChartExportMixin:
    def export_chart(self, fmt):
        try:
            ext     = 'jpg'   if fmt == 'jpeg' else fmt
            mpl_fmt = 'jpeg'  if fmt == 'jpeg' else fmt
            fp, _ = QFileDialog.getSaveFileName(
                self, f'Export {fmt.upper()}', _get_dir(), f'{fmt.upper()} (*.{ext})')
            if not fp:
                return

            dpi = self.dpi_spin.value()
            wi, hi = self._fig_size_in_inches()

            # Build a fresh Figure at the exact export size — never touches the screen figure
            exp_fig = MplFigure(figsize=(wi, hi), dpi=dpi)
            exp_fig.patch.set_facecolor(self.chart_bg_color)

            # Re-run plotting on the export figure
            series = self._get_series(primary_only=True)
            ct = self.chart_type_combo.currentText()
            is3d = ct in _3D_TYPES
            rows, cols, n = self.subplot_rows, self.subplot_cols, self.subplot_rows*self.subplot_cols
            xc = self.series_table.cellWidget(0, 0).currentText() if series and self.series_table.cellWidget(0, 0) else ''
            chart_font = self.title_font.currentText()
            _old_font = matplotlib.rcParams.get('font.family', ['sans-serif'])
            matplotlib.rcParams['font.family'] = chart_font

            axes_list = []
            if n == 1:
                _proj = 'polar' if ct in ('Polar', 'Radar') else ('3d' if is3d else None)
                ax = exp_fig.add_subplot(111, projection=_proj)
                axes_list.append(ax)
                cat_info = self._plot_on(ax, series, ct, row_offset=self._get_series_row_offset(0)) if (series or ct in _NO_X_TYPES) else None
                yd = {s[2]: s[1] for s in series}
                self._decorate(ax, xc, yd, is3d, subplot_idx=0)
                self._apply_cat_ticks(ax, cat_info)
            else:
                    mosaic = getattr(self, '_subplot_mosaic', None)
                    if mosaic is not None:
                        # ── Mosaic layout ──────────────────────────────────────
                        ax_dict = exp_fig.subplot_mosaic(mosaic)
                        seen_order = list(dict.fromkeys(c for row in mosaic for c in row))
                        axes_list = [ax_dict[k] for k in seen_order]
                        for idx, ax in enumerate(axes_list):
                            sub_ct = self.subplot_chart_types.get(idx, 'Line')
                            sub_series, sub_y2_series = self._get_series_for_subplot(idx)
                            x_cols, y_cols, y2_cols = self._get_col_names_for_subplot(idx)
                            cat_info = self._plot_on(ax, sub_series, sub_ct, row_offset=self._get_series_row_offset(idx)) if (sub_series or sub_ct in _NO_X_TYPES) else None
                            ax2 = None
                            if sub_y2_series and sub_ct not in _NO_LEGEND_TYPES:
                                ax2 = ax.twinx()
                                self._plot_on(ax2, sub_y2_series, sub_ct, row_offset=self._get_series_row_offset(idx))
                                if self.subplot_y2label_show.get(idx, True):
                                    y2lbl = self.subplot_y2labels.get(idx,'') or ', '.join(y2_cols)
                                    if y2lbl: ax2.set_ylabel(y2lbl, fontsize=self.y2label_size.value(),
                                                              color=self.y2label_color, fontfamily=self.y2label_font.currentText())
                                y2lim = self.subplot_y2lims.get(idx)
                                if y2lim: ax2.set_ylim(y2lim[0], y2lim[1])
                                self._apply_canvas_style(ax2, idx)
                            t = self.sp_titles.get(idx,'')
                            show_title = self.subplot_title_show.get(idx, True)
                            title_text = (t or f'Subplot {idx+1}') if show_title else ''
                            if title_text: ax.set_title(title_text,
                                fontfamily=self.subplot_title_font.get(idx, 'sans-serif'),
                                fontsize=self.subplot_title_size.get(idx, 11),
                                color=self.subplot_title_color.get(idx, '#000000'))
                            if self.subplot_xlabel_show.get(idx, True):
                                xl = self.subplot_xlabels.get(idx,'') or ', '.join(x_cols)
                                if xl: ax.set_xlabel(xl, fontsize=self.xlabel_size.value(),
                                    color=self.xlabel_color, fontfamily=self.xlabel_font.currentText())
                            if self.subplot_ylabel_show.get(idx, True):
                                yl = self.subplot_ylabels.get(idx,'') or ', '.join(y_cols)
                                if yl: ax.set_ylabel(yl, fontsize=self.ylabel_size.value(),
                                    color=self.ylabel_color, fontfamily=self.ylabel_font.currentText())
                            xs = self.subplot_xscales.get(idx, 'linear')
                            ys = self.subplot_yscales.get(idx, 'linear')
                            if cat_info is None:
                                try: ax.set_xscale(xs if xs != 'inverted' else 'linear')
                                except Exception: ax.set_xscale('linear')
                                if xs == 'inverted': ax.invert_xaxis()
                            try: ax.set_yscale(ys if ys != 'inverted' else 'linear')
                            except Exception: ax.set_yscale('linear')
                            if ys == 'inverted': ax.invert_yaxis()
                            xlim = self.subplot_xlims.get(idx)
                            if xlim: ax.set_xlim(xlim[0], xlim[1])
                            ylim = self.subplot_ylims.get(idx)
                            if ylim: ax.set_ylim(ylim[0], ylim[1])
                            if sub_ct not in {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Polar', 'Radar', '3D Surface'}: self._apply_grid(ax)
                            self._apply_canvas_style(ax, idx)
                            self._apply_cat_ticks(ax, cat_info)
                            show_leg = self.subplot_legends.get(idx, True)
                            sp_leg_loc = self.subplot_legend_locs.get(idx, 'best')
                            if show_leg and sub_ct not in _NO_LEGEND_TYPES:
                                if ax2 and (sub_series or sub_y2_series):
                                    h1,l1 = ax.get_legend_handles_labels()
                                    h2,l2 = ax2.get_legend_handles_labels()
                                    if h1 or h2: ax.legend(h1+h2, l1+l2, fontsize=8, loc=sp_leg_loc)
                                elif sub_series:
                                    ax.legend(fontsize=8, loc=sp_leg_loc)
                    else:
                    # ── Regular grid layout ────────────────────────────────────
                        first = None
                        for idx in range(n):
                            r, c = divmod(idx, cols)
                            sub_ct = self.subplot_chart_types.get(idx, 'Line')
                            sub_is3d = sub_ct in _3D_TYPES
                            sub_is_polar = sub_ct in ('Polar', 'Radar')
                            sub_proj = 'polar' if sub_is_polar else ('3d' if sub_is3d else None)
                            kw = {}
                            if not sub_is3d and not sub_is_polar and first:
                                if self.sp_sharex.isChecked(): kw['sharex'] = first
                                if self.sp_sharey.isChecked(): kw['sharey'] = first
                            ax = exp_fig.add_subplot(rows, cols, idx+1,
                                                     projection=sub_proj, **kw)
                            if first is None: first = ax
                            axes_list.append(ax)
                            sub_series, sub_y2_series = self._get_series_for_subplot(idx)
                            x_cols, y_cols, y2_cols = self._get_col_names_for_subplot(idx)
                            default_xl  = ', '.join(x_cols)
                            default_yl  = ', '.join(y_cols)
                            default_y2l = ', '.join(y2_cols)
                            cat_info = self._plot_on(ax, sub_series, sub_ct, row_offset=self._get_series_row_offset(idx)) if (sub_series or sub_ct in _NO_X_TYPES) else None
                            ax2 = None
                            if sub_y2_series and sub_ct not in _NO_LEGEND_TYPES:
                                ax2 = ax.twinx()
                                self._plot_on(ax2, sub_y2_series, sub_ct, row_offset=self._get_series_row_offset(idx))
                                if self.subplot_y2label_show.get(idx, True):
                                    y2lbl = self.subplot_y2labels.get(idx, '') or default_y2l
                                    if y2lbl:
                                        ax2.set_ylabel(y2lbl, fontsize=self.y2label_size.value(),
                                                       color=self.y2label_color,
                                                       fontfamily=self.y2label_font.currentText())
                                y2lim = self.subplot_y2lims.get(idx)
                                if y2lim: ax2.set_ylim(y2lim[0], y2lim[1])
                                self._apply_canvas_style(ax2, idx)
                            t = self.sp_titles.get(idx, '')
                            show_title = self.subplot_title_show.get(idx, True)
                            title_text = (t or f'Subplot {idx+1}') if show_title else ''
                            if title_text: ax.set_title(title_text,
                                fontfamily=self.subplot_title_font.get(idx, 'sans-serif'),
                                fontsize=self.subplot_title_size.get(idx, 11),
                                color=self.subplot_title_color.get(idx, '#000000'))
                            _horiz_bar = (sub_ct == 'Bar' and self.bar_horizontal.isChecked())
                            _default_xl_eff = default_yl if _horiz_bar else default_xl
                            _default_yl_eff = default_xl if _horiz_bar else default_yl
                            _custom_xl = self.subplot_xlabels.get(idx, '')
                            _custom_yl = self.subplot_ylabels.get(idx, '')
                            if r == rows-1 and sub_ct not in _NO_X_TYPES:
                                if self.subplot_xlabel_show.get(idx, True):
                                    xl = _custom_xl or _default_xl_eff
                                    ax.set_xlabel(xl, fontsize=self.xlabel_size.value(),
                                                  color=self.xlabel_color, fontfamily=self.xlabel_font.currentText())
                                else:
                                    ax.set_xlabel('')
                            if self.subplot_ylabel_show.get(idx, True):
                                yl = _custom_yl or _default_yl_eff
                                ax.set_ylabel(yl, fontsize=self.ylabel_size.value(),
                                              color=self.ylabel_color, fontfamily=self.ylabel_font.currentText())
                            else:
                                ax.set_ylabel('')
                            if not sub_is3d and sub_ct not in {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Polar', 'Radar', '3D Surface'}:
                                xs = self.subplot_xscales.get(idx, 'linear')
                                ys = self.subplot_yscales.get(idx, 'linear')
                                if cat_info is None:
                                    try: ax.set_xscale(xs if xs != 'inverted' else 'linear')
                                    except Exception: ax.set_xscale('linear')
                                    if xs == 'inverted': ax.invert_xaxis()
                                _sub_horiz = sub_ct == 'Bar' and self.bar_horizontal.isChecked()
                                _protect_y = (cat_info is not None) and _sub_horiz
                                if not _protect_y:
                                    try: ax.set_yscale(ys if ys != 'inverted' else 'linear')
                                    except Exception: ax.set_yscale('linear')
                                    if ys == 'inverted': ax.invert_yaxis()
                            xlim = self.subplot_xlims.get(idx)
                            if xlim: ax.set_xlim(xlim[0], xlim[1])
                            ylim = self.subplot_ylims.get(idx)
                            if ylim: ax.set_ylim(ylim[0], ylim[1])
                            if sub_ct not in {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Polar', 'Radar', '3D Surface'}: self._apply_grid(ax)
                            self._apply_cat_ticks(ax, cat_info)
                            show_leg = self.subplot_legends.get(idx, True)
                            sp_leg_loc = self.subplot_legend_locs.get(idx, 'best')
                            if show_leg and sub_ct not in _NO_LEGEND_TYPES:
                                if ax2 and (sub_series or sub_y2_series):
                                    h1,l1 = ax.get_legend_handles_labels()
                                    h2,l2 = ax2.get_legend_handles_labels()
                                    if h1 or h2: ax.legend(h1+h2, l1+l2, fontsize=8, loc=sp_leg_loc)
                                elif sub_series:
                                    ax.legend(fontsize=8, loc=sp_leg_loc)

            if n > 1:
                for _ax_i, _ax in enumerate(axes_list):
                    _ax_ct = self.subplot_chart_types.get(_ax_i, 'Line')
                    if _ax_ct not in _3D_TYPES:
                        self._apply_canvas_style(_ax, _ax_i)

            # Apply margins (user values map directly to the export figure)
            exp_top = self.fig_top.value()
            _n_sp_exp = self.subplot_rows * self.subplot_cols
            _exp_title_text = self.title_input.text().strip() if _n_sp_exp > 1 else ''
            _ty_widget = getattr(self, 'title_y', getattr(self, 'title_y_offset', None))
            _exp_ty = _ty_widget.value() if _ty_widget else 0.97
            if _n_sp_exp > 1 and self.title_check.isChecked() and _exp_title_text:
                suptitle_pt = self.title_size.value()
                title_h_frac = (suptitle_pt * 1.6) / (hi * 72)
                exp_top = min(exp_top, _exp_ty - title_h_frac)
                exp_top = max(exp_top, self.fig_bottom.value() + 0.05)
                exp_fig.suptitle(_exp_title_text,
                                 fontsize=suptitle_pt, color=self.title_color,
                                 fontfamily=self.title_font.currentText(),
                                 x=self.title_x.value() if hasattr(self, 'title_x') else 0.5,
                                 ha='center', va='top',
                                 y=_exp_ty)
            _hspace_exp = self.sp_hspace.value() if hasattr(self, 'sp_hspace') else 0.35
            _wspace_exp = self.sp_wspace.value() if hasattr(self, 'sp_wspace') else 0.35
            exp_fig.subplots_adjust(
                left=self.fig_left.value(),
                right=self.fig_right.value(),
                bottom=self.fig_bottom.value(),
                top=exp_top,
                hspace=_hspace_exp,
                wspace=_wspace_exp,
            )

            exp_fig.savefig(fp, dpi=dpi, format=mpl_fmt, bbox_inches=None)
            plt.close(exp_fig)
            matplotlib.rcParams['font.family'] = _old_font

            _remember_dir(fp)
            QMessageBox.information(self, 'Success', f'Exported to {fp}')
        except Exception as e:
            try: matplotlib.rcParams['font.family'] = _old_font
            except Exception: pass
            QMessageBox.critical(self, 'Error', str(e))

    # ═══════════════════════════════════════════════════════════════════════════
    # SETTINGS SERIALIZATION
    # ═══════════════════════════════════════════════════════════════════════════

