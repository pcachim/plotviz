"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.

ui/plot_engine.py  –  plotviz
Mixin providing all matplotlib plotting, decorating, preview and export methods.
"""
import traceback
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # side-effect: registers the 3D projection
from matplotlib.figure import Figure as MplFigure
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from ui.helpers import _get_dir, _remember_dir
from PyQt6.QtCore import Qt


from ui.tab_builders import WHOLE_CHART_TYPES, _NO_X_TYPES

_3D_TYPES = {'3D Surface'}
_NO_LEGEND_TYPES = {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Contour', '3D Surface', 'Violin', 'Boxplot', 'Radar', 'Quiver'}


class PlotEngineMixin:
    def _plot_on(self, ax, series, ct, row_offset=0):
        """
        series: list of (xd, yd, label, series_ct) tuples.
        ct: the global/whole-chart type (used for whole-chart types).
        For per-series types (Line/Scatter/Bar/Area/Errorbar) each tuple's
        series_ct is used instead.
        X/Y arrays are truncated to min(len(x), len(y)) so temporary column
        mismatches during editing never cause an exception.
        row_offset: ignored — colours restart from index 0 on every subplot.
        """

        # Truncate every series to the shorter of its two arrays
        def _trim(xd, yd):
            n = min(len(xd), len(yd))
            return xd[:n], yd[:n]
        series = [_trim(xd, yd) + (lbl, sct) for xd, yd, lbl, sct in series]
        # Drop any series that ended up empty after trimming
        series = [(xd, yd, lbl, sct) for xd, yd, lbl, sct in series if len(xd) > 0]

        yd_dict = {lbl: yd for xd, yd, lbl, _ in series}
        # Build colour list for this subplot — colours restart at index 0
        # so every subplot's first series gets the first palette colour.
        C = self._tab10(max(len(series), 1))
        cmap = self.cmap_combo.currentText()

        # Guard: all series must agree on X categorical vs numeric.
        # Use the majority type so one stray numeric series doesn't drop all categoricals.
        if series:
            cat_count = sum(1 for xd, yd, lbl, sct in series if self._is_categorical(xd))
            use_cat = cat_count >= len(series) / 2
            series = [(xd, yd, lbl, sct) for xd, yd, lbl, sct in series
                      if self._is_categorical(xd) == use_cat]

        # ── Whole-chart types (all series treated the same way) ──────────────
        if ct in WHOLE_CHART_TYPES:
            if ct == 'Histogram':
                for i, (xd, yd, lbl, _) in enumerate(series):
                    s = self.curve_styles.get(lbl, {})
                    ec_val = self.hist_edgecolor.currentText()
                    if ec_val == 'auto': ec_val = s.get('color', C[i])
                    if self._is_categorical(yd):
                        vals, counts = np.unique(yd, return_counts=True)
                        ax.bar(vals, counts, label=lbl, color=s.get('color', C[i]),
                               alpha=self.hist_alpha.value(),
                               edgecolor=ec_val if ec_val != 'none' else None)
                        ax.tick_params(axis='x', rotation=45)
                    else:
                        ax.hist(yd, bins=self.hist_bins.value(),
                                density=self.hist_density.isChecked(),
                                cumulative=self.hist_cumulative.isChecked(),
                                histtype=self.hist_histtype.currentText(),
                                orientation=self.hist_orientation.currentText(),
                                alpha=self.hist_alpha.value(),
                                edgecolor=ec_val if ec_val != 'none' else None,
                                label=lbl, color=s.get('color', C[i]))

            elif ct == 'Boxplot':
                num_series = [(k, v) for k, v in yd_dict.items() if not self._is_categorical(v)]
                if num_series:
                    bp = ax.boxplot(
                        [v for _, v in num_series], labels=[k for k, _ in num_series],
                        patch_artist=True, notch=self.box_notch.isChecked(),
                        vert=self.box_vert.isChecked(),
                        showmeans=self.box_show_means.isChecked(),
                        showfliers=self.box_showfliers.isChecked(),
                        whis=self.box_whis.value(),
                        medianprops=dict(color='black', linewidth=2) if self.box_show_medians.isChecked() else dict(linewidth=0),
                    )
                    for patch, c in zip(bp['boxes'], C):
                        patch.set_facecolor(c); patch.set_alpha(self.box_alpha.value())

            elif ct == 'Violin':
                num_series = [(k, v) for k, v in yd_dict.items() if not self._is_categorical(v)]
                if num_series:
                    parts = ax.violinplot(
                        [v for _, v in num_series],
                        showmeans=self.violin_show_means.isChecked(),
                        showmedians=self.violin_show_medians.isChecked(),
                        showextrema=self.violin_show_extrema.isChecked(),
                        bw_method=self.violin_bw.currentText(),
                        points=int(self.violin_points.currentText()),
                        vert=self.violin_vert.isChecked(),
                    )
                    for pc, c in zip(parts['bodies'], C): pc.set_facecolor(c); pc.set_alpha(0.7)
                    if self.violin_vert.isChecked():
                        ax.set_xticks(range(1, len(num_series)+1))
                        ax.set_xticklabels([k for k, _ in num_series])
                    else:
                        ax.set_yticks(range(1, len(num_series)+1))
                        ax.set_yticklabels([k for k, _ in num_series])

            elif ct == 'Pie':
                if series:
                    xd, yd, lbl, _ = series[0]
                    labels = list(xd) if self._is_categorical(xd) else [f'{v:.4g}' for v in xd]
                    explode = [0.08] + [0.0]*(len(yd)-1) if self.pie_explode_first.isChecked() else None
                    wedge_kw = {'width': 0.5} if self.pie_donut.isChecked() else {}
                    ax.pie(np.abs(yd), labels=labels,
                           autopct='%1.1f%%' if self.pie_autopct.isChecked() else None,
                           shadow=self.pie_shadow.isChecked(),
                           startangle=self.pie_startangle.value(),
                           labeldistance=self.pie_labeldistance.value(),
                           pctdistance=self.pie_pctdistance.value(),
                           explode=explode, wedgeprops=wedge_kw,
                           colors=self._tab10(len(yd)))
                    ax.set_aspect('equal')

            elif ct == 'Heatmap':
                zc = self.combo_z.currentText()
                if zc != '(none)' and zc in self.datasets and series:
                    z = self.datasets[zc]
                    n = int(np.ceil(np.sqrt(len(z))))
                    Z = np.full((n, n), np.nan)
                    for k in range(len(z)): Z[k//n, k%n] = z[k]
                    im = ax.imshow(Z, aspect='auto', cmap=cmap, origin='lower',
                                   alpha=self.heat_alpha.value(),
                                   interpolation=self.heat_interpolation.currentText())
                    if self.heat_colorbar.isChecked(): self.canvas.figure.colorbar(im, ax=ax)

            elif ct == 'Contour':
                zc = self.combo_z.currentText()
                if zc != '(none)' and zc in self.datasets and series:
                    xd, yd, lbl, _ = series[0]; z = self.datasets[zc]
                    if not self._is_categorical(xd) and not self._is_categorical(yd):
                        n = int(np.ceil(np.sqrt(len(z))))
                        Z = np.full((n, n), np.nan)
                        for k in range(len(z)): Z[k//n, k%n] = z[k]
                        Z = np.where(np.isnan(Z), np.nanmean(Z), Z)
                        xi = np.linspace(np.min(xd), np.max(xd), n)
                        yi = np.linspace(np.min(yd), np.max(yd), n)
                        X, Y = np.meshgrid(xi, yi)
                        lvl = self.contour_levels.value()
                        alp = self.heat_alpha.value()
                        if self.heat_filled_contour.isChecked():
                            cf = ax.contourf(X, Y, Z, levels=lvl, cmap=cmap, alpha=alp)
                            if self.heat_colorbar.isChecked(): self.canvas.figure.colorbar(cf, ax=ax)
                        if self.heat_contour_lines.isChecked():
                            ax.contour(X, Y, Z, levels=lvl, colors='k', linewidths=0.5, alpha=0.5)

            elif ct == '3D Surface':
                zc = self.combo_z.currentText()
                if zc != '(none)' and zc in self.datasets and series:
                    xd, yd, lbl, _ = series[0]; z = self.datasets[zc]
                    if not self._is_categorical(xd) and not self._is_categorical(yd):
                        n = int(np.ceil(np.sqrt(min(len(xd), len(yd), len(z)))))
                        Z = np.full((n, n), np.nanmean(z))
                        for k in range(min(len(z), n*n)): Z[k//n, k%n] = z[k]
                        xi = np.linspace(np.min(xd), np.max(xd), n)
                        yi = np.linspace(np.min(yd), np.max(yd), n)
                        X, Y = np.meshgrid(xi, yi)
                        st = self.surf_stride.value(); alp = self.heat_alpha.value()
                        if self.surf_wireframe.isChecked():
                            ax.plot_wireframe(X, Y, Z, rstride=st, cstride=st, alpha=alp)
                        else:
                            ax.plot_surface(X, Y, Z, cmap=cmap, alpha=alp, rstride=st, cstride=st)

            elif ct == 'Hist2D':
                if series:
                    xd, yd, lbl, _ = series[0]
                    if not self._is_categorical(xd) and not self._is_categorical(yd):
                        norm = matplotlib.colors.LogNorm() if self.hist2d_log.isChecked() else None
                        _, _, _, img = ax.hist2d(
                            xd.astype(float), yd.astype(float),
                            bins=[self.hist2d_bins_x.value(), self.hist2d_bins_y.value()],
                            cmap=cmap, alpha=self.hist2d_alpha.value(), norm=norm)
                        if self.hist2d_colorbar.isChecked():
                            self.canvas.figure.colorbar(img, ax=ax)

            elif ct == 'Hexbin':
                if series:
                    xd, yd, lbl, _ = series[0]
                    if not self._is_categorical(xd) and not self._is_categorical(yd):
                        hb = ax.hexbin(xd.astype(float), yd.astype(float),
                                       gridsize=self.hexbin_gridsize.value(), cmap=cmap,
                                       bins='log' if self.hexbin_log.isChecked() else None,
                                       alpha=self.hexbin_alpha.value())
                        if self.hexbin_colorbar.isChecked():
                            self.canvas.figure.colorbar(hb, ax=ax)

            elif ct == 'Polar':
                for i, (xd, yd, lbl, _) in enumerate(series):
                    if self._is_categorical(xd): continue
                    s = self.curve_styles.get(lbl, {})
                    color = s.get('color', C[i])
                    ls = self.polar_linestyle.currentText()
                    mk = self.polar_marker.currentText(); mk = None if mk == 'None' else mk
                    theta = xd.astype(float); r = yd.astype(float)
                    if ls != 'none':
                        ax.plot(theta, r, linestyle=ls, color=color,
                                linewidth=self.polar_lw.value(), marker=mk, label=lbl)
                    if self.polar_fill.isChecked():
                        ax.fill(theta, r, alpha=self.polar_fill_alpha.value(), color=color)

            elif ct == 'Radar':
                if series:
                    xd, yd, lbl, _ = series[0]
                    n_cat = len(yd)
                    if n_cat >= 3:
                        angles = np.linspace(0, 2*np.pi, n_cat, endpoint=False).tolist() + [0]
                        labels = list(xd) if self._is_categorical(xd) else [str(round(v,3)) for v in xd]
                        ax.set_theta_offset(np.pi/2); ax.set_theta_direction(-1)
                        ax.set_xticks(angles[:-1]); ax.set_xticklabels(labels, size=8)
                        all_vals = np.concatenate([s[1].astype(float) for s in series])
                        vmax = np.nanmax(np.abs(all_vals)) if len(all_vals) else 1
                        ax.set_ylim(0, vmax*1.1)
                        ax.set_yticks(np.linspace(0, vmax, self.radar_gridlevels.value()+1)[1:])
                        for i, (xd_s, yd_s, lbl_s, _) in enumerate(series):
                            s = self.curve_styles.get(lbl_s, {})
                            color = s.get('color', C[i])
                            vals = list(yd_s.astype(float)) + [float(yd_s[0])]
                            ax.plot(angles, vals, color=color, linewidth=self.radar_lw.value(), label=lbl_s)
                            if self.radar_fill.isChecked():
                                ax.fill(angles, vals, color=color, alpha=self.radar_fill_alpha.value())

            elif ct == 'ECDF':
                for i, (xd, yd, lbl, _) in enumerate(series):
                    if self._is_categorical(yd): continue
                    s = self.curve_styles.get(lbl, {})
                    color = s.get('color', C[i])
                    sorted_d = np.sort(yd.astype(float))
                    ecdf = np.arange(1, len(sorted_d)+1) / len(sorted_d)
                    if self.ecdf_complementary.isChecked(): ecdf = 1.0 - ecdf
                    ax.step(sorted_d, ecdf, color=color,
                            linewidth=self.ecdf_lw.value(), alpha=self.ecdf_alpha.value(),
                            label=lbl, where='post')
                    if self.ecdf_markers.isChecked():
                        ax.scatter(sorted_d, ecdf, color=color, s=12, zorder=4)
                ax.set_ylim(-0.02, 1.02); ax.set_ylabel('F(x)')

            elif ct == 'Quiver':
                if series:
                    xd, yd, lbl, _ = series[0]
                    uc = self.quiver_u_combo.currentText()
                    vc = self.quiver_v_combo.currentText()
                    if uc != '(none)' and vc != '(none)' and uc in self.datasets and vc in self.datasets:
                        U = self.datasets[uc].astype(float)
                        V = self.datasets[vc].astype(float)
                        n = min(len(xd), len(yd), len(U), len(V))
                        sc = self.quiver_scale.value()
                        ax.quiver(xd[:n].astype(float), yd[:n].astype(float), U[:n], V[:n],
                                  np.hypot(U[:n], V[:n]) if self.quiver_color_by_mag.isChecked() else None,
                                  cmap=cmap if self.quiver_color_by_mag.isChecked() else None,
                                  scale=sc if sc != 1.0 else None,
                                  scale_units='xy' if sc != 1.0 else None,
                                  width=self.quiver_width.value(), alpha=0.85)
            return

        # ── Per-series mixable types ─────────────────────────────────────────
        bar_series  = [(i, xd, yd, lbl) for i, (xd, yd, lbl, sct) in enumerate(series) if sct == 'Bar']
        n_bar    = len(bar_series)
        bar_w    = self.bar_width.value()
        bar_stk  = self.bar_stacked.isChecked()
        bar_horiz= self.bar_horizontal.isChecked()
        bar_ec   = self.bar_edgecolor.currentText()
        bar_elw  = self.bar_edge_lw.value()
        bar_al   = self.bar_alpha.value()

        def _bar(ax, positions, values, width, bottom=None, **kw):
            ec_kw = {'edgecolor': bar_ec if bar_ec != 'none' else 'none',
                     'linewidth': bar_elw if bar_ec != 'none' else 0}
            kw.update(ec_kw)
            if bar_horiz:
                ax.barh(positions, values, height=width,
                        left=bottom if bottom is not None else 0, **kw)
            else:
                kw2 = dict(kw)
                if bottom is not None: kw2['bottom'] = bottom
                ax.bar(positions, values, width=width, **kw2)

        any_cat_x = any(self._is_categorical(xd) for xd, yd, lbl, sct in series)
        if any_cat_x:
            all_x_cats = list(dict.fromkeys(
                str(v) for xd, yd, lbl, sct in series
                if self._is_categorical(xd) for v in xd
            ))
            cat_pos = {c: i for i, c in enumerate(all_x_cats)}
        else:
            all_x_cats = []
            cat_pos = {}

        def _cat_xplot(xd):
            """Convert categorical xd to integer positions using the global cat_pos map."""
            return np.array([cat_pos.get(str(v), 0) for v in xd], dtype=float)

        bar_cat = any_cat_x and bool(bar_series)
        all_cats = list(dict.fromkeys(str(v) for _, xd, _, _ in bar_series for v in xd)) if bar_cat else []
        for c in all_cats:
            if c not in cat_pos:
                cat_pos[c] = len(cat_pos)
                all_x_cats.append(c)
        bar_bottoms_cat = {c: 0.0 for c in all_cats}
        bar_bottoms_num = None
        bar_offs = np.linspace(-(n_bar-1)/2, (n_bar-1)/2, n_bar) * (bar_w / max(n_bar, 1)) if n_bar else []
        bar_idx_counter = 0

        for i, (xd, yd, lbl, sct) in enumerate(series):
            s = self.curve_styles.get(lbl, {})
            color = s.get('color', C[i])
            is_cat = self._is_categorical(xd)

            if sct == 'Line':
                is_fit = lbl.endswith(' fit)') and lbl not in (self.curve_styles or {})
                if is_fit:
                    ls = self.fit_linestyle; color = self.fit_color
                    lw = self.fit_linewidth; mk = None; mk_color = color
                else:
                    ls = s.get('linestyle') or self.line_default_style.currentText()
                    if ls in ('default', ''): ls = '-'
                    mk = s.get('marker') or self.line_default_marker.currentText()
                    if mk in ('default', 'None', 'none', ''): mk = None
                    if ls == 'none' and mk is None: mk = 'o'
                    lw = s.get('linewidth', self.line_default_lw.value())
                    mk_color = s.get('marker_color', color)
                xplot = _cat_xplot(xd) if is_cat else xd
                ds = self.line_drawstyle.currentText()
                plot_kw = dict(label=lbl, color=color, linestyle=ls, linewidth=lw,
                               markersize=s.get('markersize', self.line_default_markersize.value()),
                               drawstyle=ds if ds != 'default' else 'default')
                if mk:
                    plot_kw['marker'] = mk
                    plot_kw['markerfacecolor'] = mk_color
                    plot_kw['markeredgecolor'] = mk_color
                _lines = ax.plot(xplot, yd, **plot_kw)
                for _l in _lines: _l.set_pickradius(6)
                upper_key = lbl + ' CI upper'; lower_key = lbl + ' CI lower'
                if upper_key in self.datasets and lower_key in self.datasets and not is_cat:
                    ax.fill_between(xd, self.datasets[lower_key], self.datasets[upper_key],
                                    alpha=self.fit_ci_alpha_spin.value(), color=color, linewidth=0, label=f'{lbl} CI')

            elif sct == 'Scatter':
                xplot = _cat_xplot(xd) if is_cat else xd
                mk = self.scatter_marker.currentText(); mk = 'o' if mk == 'None' else mk
                mk_color = s.get('marker_color', color)
                sc_ec = self.scatter_edgecolor.currentText()
                if sc_ec == 'auto': sc_ec = mk_color
                # Color by Z column if requested
                c_arg = None
                if self.scatter_colorby_check.isChecked():
                    zc = self.combo_z.currentText()
                    if zc != '(none)' and zc in self.datasets:
                        z = self.datasets[zc]
                        n = min(len(xplot), len(yd), len(z))
                        c_arg = z[:n]
                        xplot = xplot[:n]; yd = yd[:n]
                _sc = ax.scatter(xplot, yd, label=lbl,
                           s=self.scatter_size.value(),
                           alpha=self.scatter_alpha.value(),
                           c=c_arg if c_arg is not None else mk_color,
                           cmap=cmap if c_arg is not None else None,
                           marker=mk,
                           edgecolors=sc_ec,
                           linewidths=self.scatter_lw.value())
                _sc.set_picker(True)
                upper_key = lbl + ' CI upper'; lower_key = lbl + ' CI lower'
                if upper_key in self.datasets and lower_key in self.datasets and not is_cat:
                    ax.fill_between(xd, self.datasets[lower_key], self.datasets[upper_key],
                                    alpha=self.fit_ci_alpha_spin.value(), color=color, linewidth=0, label=f'{lbl} CI')

            elif sct == 'Bar':
                bi = bar_idx_counter; bar_idx_counter += 1
                # Color bars by value if requested
                def _bar_colors(vals, base_color):
                    if self.bar_colorbyval.isChecked():
                        return [plt.cm.RdYlGn(0.8 if v >= 0 else 0.2) for v in vals]
                    return base_color
                if bar_cat:
                    xd_s = [str(v) for v in xd]
                    positions = np.array([cat_pos.get(v, 0) for v in xd_s], dtype=float)
                    if bar_stk:
                        bot = np.array([bar_bottoms_cat.get(v, 0.0) for v in xd_s], dtype=float)
                        _bar(ax, positions, yd, bar_w, bottom=bot, label=lbl,
                             color=_bar_colors(yd, color), alpha=bar_al)
                        for v, y in zip(xd_s, yd): bar_bottoms_cat[v] = bar_bottoms_cat.get(v, 0.0) + float(y)
                    else:
                        _bar(ax, positions + bar_offs[bi], yd, bar_w/max(n_bar,1), label=lbl,
                             color=_bar_colors(yd, color), alpha=bar_al)
                else:
                    if is_cat or self._is_categorical(yd): continue
                    try:
                        xd_f = np.asarray(xd, dtype=float); yd_f = np.asarray(yd, dtype=float)
                    except (ValueError, TypeError): continue
                    if bar_bottoms_num is None: bar_bottoms_num = np.zeros(len(xd_f))
                    if bar_stk:
                        _bar(ax, xd_f, yd_f, bar_w, bottom=bar_bottoms_num[:len(yd_f)], label=lbl,
                             color=_bar_colors(yd_f, color), alpha=bar_al)
                        bar_bottoms_num[:len(yd_f)] += yd_f
                    else:
                        _bar(ax, xd_f + bar_offs[bi], yd_f, bar_w/max(n_bar,1), label=lbl,
                             color=_bar_colors(yd_f, color), alpha=bar_al)

            elif sct == 'Area':
                al  = self.area_alpha.value()
                lw  = self.area_lw.value()
                stk = self.area_stacked.isChecked()
                bl  = self.area_baseline.value()
                xplot = _cat_xplot(xd) if is_cat else xd
                base_key = '_area_base'
                base = getattr(ax, base_key, None)
                if base is None or len(base) != len(xplot):
                    base = np.full(len(xplot), bl)
                if stk:
                    ax.fill_between(xplot, base, base + yd, alpha=al, label=lbl, color=color)
                    if self.area_showline.isChecked():
                        ax.plot(xplot, base + yd, color=color, lw=lw)
                    setattr(ax, base_key, base + yd)
                else:
                    ax.fill_between(xplot, bl, yd, alpha=al, label=lbl, color=color)
                    if self.area_showline.isChecked():
                        ax.plot(xplot, yd, color=color, lw=lw)

            elif sct == 'Errorbar':
                ec   = self.combo_err.currentText()
                xerr_c = self.err_xerr_combo.currentText()
                err  = self.datasets.get(ec)  if ec      != '(none)' else None
                xerr = self.datasets.get(xerr_c) if xerr_c != '(none)' else None
                xplot = _cat_xplot(xd) if is_cat else xd
                mk = self.err_fmt_marker.currentText(); mk = 'o' if mk == 'None' else mk
                ax.errorbar(xplot, yd, yerr=err, xerr=xerr, label=lbl,
                            capsize=self.err_capsize.value(),
                            capthick=self.err_capthick.value(),
                            elinewidth=self.err_elinewidth.value(),
                            barsabove=self.err_barsabove.isChecked(),
                            fmt=mk, color=color,
                            linewidth=s.get('linewidth', 1.5))

            elif sct == 'Step':
                if self._is_categorical(yd): continue
                xplot = _cat_xplot(xd) if is_cat else xd
                where = self.step_where.currentText()
                lw = s.get('linewidth', self.step_lw.value())
                ax.step(xplot, yd, where=where, label=lbl, color=color, linewidth=lw)
                if self.step_fill.isChecked():
                    ax.fill_between(xplot, yd, step=where,
                                    alpha=self.step_fill_alpha.value(), color=color)

            elif sct == 'Stem':
                if self._is_categorical(yd): continue
                xplot = _cat_xplot(xd) if is_cat else xd
                baseline = self.stem_baseline.value()
                mk = self.stem_markfmt.currentText()
                mk_color = s.get('marker_color', color)
                lw = self.stem_lw.value()
                ms = self.stem_markersize.value()
                markerline, stemlines, baseline_line = ax.stem(
                    xplot, yd, linefmt='-', markerfmt=mk,
                    basefmt='k-', label=lbl, bottom=baseline)
                plt.setp(stemlines, color=color, linewidth=lw)
                plt.setp(markerline, color=mk_color, markersize=ms)

            elif sct == 'Bubble':
                if self._is_categorical(yd): continue
                xplot = _cat_xplot(xd) if is_cat else xd
                sc_name = self.bubble_size_combo.currentText()
                if sc_name != '(uniform)' and sc_name in self.datasets:
                    raw_s = self.datasets[sc_name].astype(float)
                    n = min(len(xplot), len(yd), len(raw_s))
                    raw_s = raw_s[:n]
                    mn, mx = np.nanmin(np.abs(raw_s)), np.nanmax(np.abs(raw_s))
                    if mx > mn:
                        sizes = 10 + (np.abs(raw_s) - mn) / (mx - mn) * self.bubble_scale.value()
                    else:
                        sizes = np.full(n, self.bubble_scale.value() / 2)
                else:
                    n = min(len(xplot), len(yd))
                    sizes = self.bubble_scale.value() / 4
                mk_color = s.get('marker_color', color)
                mk = self.bubble_marker.currentText(); mk = 'o' if mk == 'None' else mk
                b_ec = self.bubble_edgecolor.currentText()
                if b_ec == 'auto': b_ec = mk_color
                ax.scatter(xplot[:n], yd[:n], s=sizes, alpha=self.bubble_alpha.value(),
                           color=mk_color, edgecolors=b_ec if b_ec != 'none' else 'none',
                           marker=mk, label=lbl)

            elif sct == 'Waterfall':
                if self._is_categorical(yd): continue
                try:
                    xd_f = np.asarray(xd, dtype=float)
                    yd_f = np.asarray(yd, dtype=float)
                except (ValueError, TypeError): continue
                n = min(len(xd_f), len(yd_f))
                xd_f, yd_f = xd_f[:n], yd_f[:n]
                w   = self.waterfall_width.value()
                al  = self.waterfall_alpha.value()
                pos_c = getattr(self, 'waterfall_pos_color', '#2ecc71')
                neg_c = getattr(self, 'waterfall_neg_color', '#e74c3c')
                running = 0.0; prev_top = None
                for k in range(n):
                    val = float(yd_f[k])
                    fc = pos_c if val >= 0 else neg_c
                    ax.bar(xd_f[k], val, width=w, bottom=running,
                           color=fc, edgecolor='white', linewidth=0.5, alpha=al,
                           label=(lbl if k == 0 else '_nolegend_'))
                    top = running + val
                    if self.waterfall_connector.isChecked() and prev_top is not None:
                        ax.plot([xd_f[k-1]+w/2, xd_f[k]-w/2], [prev_top, prev_top],
                                color='#555', linewidth=0.8, linestyle='--')
                    prev_top = top; running = top

        # Return categorical tick info — caller must apply AFTER set_xscale/set_yscale
        # so scale changes don't wipe out the FixedLocator set here.
        if any_cat_x and all_x_cats:
            return (all_x_cats, bar_horiz)
        return None

    @staticmethod
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

    def _legend_kwargs(self, subplot_idx: int) -> dict:
        """Build the kwargs dict for ax.legend() from per-subplot legend style state."""
        loc = self.subplot_legend_locs.get(subplot_idx, 'best')
        lx  = self.subplot_legend_x.get(subplot_idx, 0.01)
        ly  = self.subplot_legend_y.get(subplot_idx, 0.99)
        kw = dict(
            fontsize    = self.subplot_legend_fontsize.get(subplot_idx, 9),
            ncols       = self.subplot_legend_ncols.get(subplot_idx, 1),
            frameon     = self.subplot_legend_frameon.get(subplot_idx, True),
            facecolor   = self.subplot_legend_facecolor.get(subplot_idx, '#ffffff'),
            edgecolor   = self.subplot_legend_edgecolor.get(subplot_idx, '#cccccc'),
            framealpha  = self.subplot_legend_alpha.get(subplot_idx, 0.8),
            labelcolor  = self.subplot_legend_color.get(subplot_idx, '#000000'),
        )
        if loc == 'best':
            # 'best' is automatic — X/Y have no effect, let matplotlib decide
            kw['loc'] = 'best'
        else:
            # For every named location, X/Y fine-tune the anchor point via bbox_to_anchor.
            # 'manual' means the dropdown is just a helper label; treat as upper left.
            kw['loc'] = 'upper left' if loc == 'manual' else loc
            kw['bbox_to_anchor'] = (lx, ly)
        return kw

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
                    h1, l1 = ax.get_legend_handles_labels()
                    h2, l2 = ax2.get_legend_handles_labels()
                    if h1 or h2:
                        ax.legend(h1+h2, l1+l2, **self._legend_kwargs(subplot_idx))
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
            ax.legend(**self._legend_kwargs(subplot_idx))
        if not is3d:
            self._apply_canvas_style(ax, subplot_idx)

    # ═══════════════════════════════════════════════════════════════════════════
    # UPDATE PREVIEW
    # ═══════════════════════════════════════════════════════════════════════════
    def update_preview(self):
        try:
            # Guard: bail silently if core widgets aren't built yet
            if not hasattr(self, 'canvas') or not hasattr(self, 'chart_type_combo'):
                return
            # Guard: suppress intermediate redraws while _apply_settings is running.
            if getattr(self, '_applying_settings', False):
                return
            if hasattr(self, '_snapshot'):
                self._snapshot()
            # Mark dirty (unsaved changes)
            if hasattr(self, '_undo_stack') and not getattr(self, '_undo_suspended', False):
                self._is_dirty = True
            # Refresh placeholder text so it always reflects the current series columns
            if hasattr(self, '_update_label_placeholders'):
                self._update_label_placeholders()
            series = self._get_series(primary_only=True)
            ct = self.chart_type_combo.currentText()
            is3d = ct in _3D_TYPES
            rows, cols, n = self.subplot_rows, self.subplot_cols, self.subplot_rows*self.subplot_cols
            # Use title_font as the global chart font (applies to tick labels too)
            chart_font = self.title_font.currentText()

            with matplotlib.rc_context({'font.family': chart_font}):
                self.canvas.figure.clear()
                self.canvas.figure.patch.set_facecolor(self.chart_bg_color)

                axes_list = []

                if n == 1:
                    _proj = 'polar' if ct in ('Polar', 'Radar') else ('3d' if is3d else None)
                    ax = self.canvas.figure.add_subplot(111, projection=_proj)
                    axes_list.append(ax)
                    if series or ct in _NO_X_TYPES:
                        cat_info = self._plot_on(ax, series, ct)
                    else:
                        cat_info = None
                    # For _decorate compat: build yd dict and use first x col name
                    yd = {s[2]: s[1] for s in series}
                    xc = self.series_table.cellWidget(0, 0).currentText() if self.series_table.rowCount() > 0 and self.series_table.cellWidget(0, 0) else ''
                    self._decorate(ax, xc, yd, is3d, subplot_idx=0)
                    # Apply categorical ticks AFTER _decorate (which calls set_xscale)
                    self._apply_cat_ticks(ax, cat_info)
                else:
                    mosaic = getattr(self, '_subplot_mosaic', None)
                    first = None

                    if mosaic is not None:
                        # ── Mosaic layout ──────────────────────────────────────
                        ax_dict = self.canvas.figure.subplot_mosaic(mosaic)
                        # Order axes by first appearance of each cell letter
                        seen_order = list(dict.fromkeys(c for row in mosaic for c in row))
                        axes_list = [ax_dict[k] for k in seen_order]
                        n_mosaic = len(axes_list)
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
                                                              color=self.y2label_color,
                                                              fontfamily=self.y2label_font.currentText())
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
                                                     color=self.xlabel_color,
                                                     fontfamily=self.xlabel_font.currentText())
                            if self.subplot_ylabel_show.get(idx, True):
                                yl = self.subplot_ylabels.get(idx,'') or ', '.join(y_cols)
                                if yl: ax.set_ylabel(yl, fontsize=self.ylabel_size.value(),
                                                     color=self.ylabel_color,
                                                     fontfamily=self.ylabel_font.currentText())
                            xs = self.subplot_xscales.get(idx, 'linear')
                            ys = self.subplot_yscales.get(idx, 'linear')
                            if cat_info is None:  # don't set_xscale for categorical axes
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
                                    if h1 or h2: ax.legend(h1+h2, l1+l2, **self._legend_kwargs(idx))
                                elif sub_series:
                                    ax.legend(**self._legend_kwargs(idx))
                    else:
                        # ── Regular grid layout ────────────────────────────────
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
                            ax = self.canvas.figure.add_subplot(rows, cols, idx+1,
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
                            _default_xl_eff  = default_yl if _horiz_bar else default_xl
                            _default_yl_eff  = default_xl if _horiz_bar else default_yl
                            _custom_xl = self.subplot_xlabels.get(idx, '')
                            _custom_yl = self.subplot_ylabels.get(idx, '')
                            if r == rows-1 and sub_ct not in _NO_X_TYPES:
                                if self.subplot_xlabel_show.get(idx, True):
                                    xl = _custom_xl or _default_xl_eff
                                    ax.set_xlabel(xl, fontsize=self.xlabel_size.value(),
                                                  color=self.xlabel_color,
                                                  fontfamily=self.xlabel_font.currentText())
                                else:
                                    ax.set_xlabel('')
                            if self.subplot_ylabel_show.get(idx, True):
                                yl = _custom_yl or _default_yl_eff
                                ax.set_ylabel(yl, fontsize=self.ylabel_size.value(),
                                              color=self.ylabel_color,
                                              fontfamily=self.ylabel_font.currentText())
                            else:
                                ax.set_ylabel('')
                            if not sub_is3d and sub_ct not in {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Polar', 'Radar', '3D Surface'}:
                                xs = self.subplot_xscales.get(idx, 'linear')
                                ys = self.subplot_yscales.get(idx, 'linear')
                                if cat_info is None:  # skip set_xscale for categorical
                                    try: ax.set_xscale(xs if xs != 'inverted' else 'linear')
                                    except Exception: ax.set_xscale('linear')
                                    if xs == 'inverted': ax.invert_xaxis()
                                _sub_horiz = sub_ct == 'Bar' and self.bar_horizontal.isChecked()
                                _sub_x_is_cat = cat_info is not None
                                _protect_y = _sub_x_is_cat and _sub_horiz
                                if not _protect_y:
                                    try: ax.set_yscale(ys if ys != 'inverted' else 'linear')
                                    except Exception: ax.set_yscale('linear')
                                    if ys == 'inverted': ax.invert_yaxis()
                            xlim = self.subplot_xlims.get(idx, None)
                            if xlim: ax.set_xlim(xlim[0], xlim[1])
                            ylim = self.subplot_ylims.get(idx, None)
                            if ylim: ax.set_ylim(ylim[0], ylim[1])
                            if sub_ct not in {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Polar', 'Radar', '3D Surface'}: self._apply_grid(ax)
                            self._apply_cat_ticks(ax, cat_info)
                            show_leg = self.subplot_legends.get(idx, True)
                            sp_leg_loc = self.subplot_legend_locs.get(idx, 'best')
                            if show_leg and sub_ct not in _NO_LEGEND_TYPES:
                                if ax2 and (sub_series or sub_y2_series):
                                    h1,l1 = ax.get_legend_handles_labels()
                                    h2,l2 = ax2.get_legend_handles_labels()
                                    if h1 or h2: ax.legend(h1+h2, l1+l2, **self._legend_kwargs(idx))
                                elif sub_series:
                                    ax.legend(**self._legend_kwargs(idx))

                self.canvas.axes_list = axes_list
                if axes_list: self.canvas.axes = axes_list[0]

                # Apply canvas style to every subplot (multi-subplot path)
                if n > 1:
                    for _ax_i, _ax in enumerate(axes_list):
                        _ax_ct = self.subplot_chart_types.get(_ax_i, 'Line')
                        if _ax_ct not in _3D_TYPES:
                            self._apply_canvas_style(_ax, _ax_i)

                # ── Margins / centering ────────────────────────────────────────────
                wi, hi = self._fig_size_in_inches()   # export size in inches
                screen_w = self.canvas.figure.get_figwidth()
                screen_h = self.canvas.figure.get_figheight()
                aspect = wi / hi   # export aspect ratio

                if screen_w / screen_h > aspect:
                    box_h = 0.90
                    box_w = box_h * aspect * screen_h / screen_w
                else:
                    box_w = 0.90
                    box_h = box_w / aspect * screen_w / screen_h

                box_left   = (1.0 - box_w) / 2.0
                box_bottom = (1.0 - box_h) / 2.0

                ul = self.fig_left.value()
                ur = self.fig_right.value()
                ub = self.fig_bottom.value()
                ut = self.fig_top.value()

                adj_left   = box_left   + ul * box_w
                adj_right  = box_left   + ur * box_w
                adj_bottom = box_bottom + ub * box_h
                adj_top    = box_bottom + ut * box_h

                _n_sp = self.subplot_rows * self.subplot_cols

                # ── Suptitle (n>1 only; single-subplot title lives inside the axes) ──
                _show_sup = _n_sp > 1 and self.title_check.isChecked()
                _sup_text = self.title_input.text().strip() if _show_sup else ''
                _title_y_fig = getattr(self, 'title_y', self.title_y_offset if hasattr(self, 'title_y_offset') else None)
                _ty = _title_y_fig.value() if _title_y_fig else 0.97

                if _show_sup and _sup_text:
                    # Place suptitle at the user-set position (in canvas-box coords).
                    # Do NOT clamp adj_top here — title_y only controls where the text
                    # sits; subplot margins are controlled independently by fig_top.
                    title_y_canvas = box_bottom + _ty * box_h
                    suptitle_pt = self.title_size.value()
                    self.canvas.figure.suptitle(_sup_text,
                        fontsize=suptitle_pt, color=self.title_color,
                        fontfamily=self.title_font.currentText(),
                        x=self.title_x.value() if hasattr(self, 'title_x') else 0.5,
                        y=title_y_canvas,
                        ha='center', va='top', transform=self.canvas.figure.transFigure)

                _hspace = self.sp_hspace.value() if hasattr(self, 'sp_hspace') else 0.35
                _wspace = self.sp_wspace.value() if hasattr(self, 'sp_wspace') else 0.35
                self.canvas.figure.subplots_adjust(
                    left=adj_left, right=adj_right,
                    bottom=adj_bottom, top=adj_top,
                    hspace=_hspace, wspace=_wspace,
                )

                # Draw the page-boundary rectangle
                self.canvas.draw_border_rect(
                    box_left, box_bottom, box_w, box_h,
                    color=self.chart_fg_color, linewidth=1.0,
                )

                # Redraw annotations AFTER layout is finalised so axes limits are set
                if not is3d:
                    self.canvas.redraw_annotations()

                self.canvas.draw()
                self.refresh_annotation_list()

        except Exception as e:
            print(f'Preview error: {e}'); traceback.print_exc()

    # ═══════════════════════════════════════════════════════════════════════════
    # EXPORT
    # ═══════════════════════════════════════════════════════════════════════════
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
                                    if h1 or h2: ax.legend(h1+h2, l1+l2, **self._legend_kwargs(idx))
                                elif sub_series:
                                    ax.legend(**self._legend_kwargs(idx))
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
                                    if h1 or h2: ax.legend(h1+h2, l1+l2, **self._legend_kwargs(idx))
                                elif sub_series:
                                    ax.legend(**self._legend_kwargs(idx))

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
                # title_y positions the suptitle text; do not clamp exp_top by it.
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

