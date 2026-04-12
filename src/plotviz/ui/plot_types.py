"""
Copyright (c) 2026 Paulo Cachim
ui/plot_types.py  –  plotviz
PlotTypesMixin: _plot_on() — dispatches all 22 chart types onto a single axes.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from ui.tab_builders import WHOLE_CHART_TYPES, _NO_X_TYPES


class PlotTypesMixin:
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
                        patch.set_facecolor(c)
                        patch.set_alpha(self.box_alpha.value())

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
                    for pc, c in zip(parts['bodies'], C):
                        pc.set_facecolor(c)
                        pc.set_alpha(0.7)
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
                    palette_colors = self._tab10(len(yd))
                    wedge_colors = []
                    for i, seg in enumerate(labels):
                        key = str(seg)
                        s = self.curve_styles.get(key, {})
                        if s.get('color'):
                            # Entry exists (from file, palette change, or prior render) — use it
                            wedge_colors.append(s['color'])
                        else:
                            # No entry yet: seed from palette and store for future updates
                            c = palette_colors[i]
                            s['color'] = c
                            s['marker_color'] = c
                            self.curve_styles[key] = s
                            wedge_colors.append(c)
                    ax.pie(np.abs(yd), labels=labels,
                           autopct='%1.1f%%' if self.pie_autopct.isChecked() else None,
                           shadow=self.pie_shadow.isChecked(),
                           startangle=self.pie_startangle.value(),
                           labeldistance=self.pie_labeldistance.value(),
                           pctdistance=self.pie_pctdistance.value(),
                           explode=explode, wedgeprops=wedge_kw,
                           colors=wedge_colors)
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
                    xd, yd, lbl, _ = series[0]
                    z = self.datasets[zc]
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
                    xd, yd, lbl, _ = series[0]
                    z = self.datasets[zc]
                    if not self._is_categorical(xd) and not self._is_categorical(yd):
                        n = int(np.ceil(np.sqrt(min(len(xd), len(yd), len(z)))))
                        Z = np.full((n, n), np.nanmean(z))
                        for k in range(min(len(z), n*n)): Z[k//n, k%n] = z[k]
                        xi = np.linspace(np.min(xd), np.max(xd), n)
                        yi = np.linspace(np.min(yd), np.max(yd), n)
                        X, Y = np.meshgrid(xi, yi)
                        st = self.surf_stride.value()
                        alp = self.heat_alpha.value()
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
                    mk = self.polar_marker.currentText()
                    mk = None if mk == 'None' else mk
                    theta = xd.astype(float)
                    r = yd.astype(float)
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
                        ax.set_theta_offset(np.pi/2)
                        ax.set_theta_direction(-1)
                        ax.set_xticks(angles[:-1])
                        ax.set_xticklabels(labels, size=8)
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
                ax.set_ylim(-0.02, 1.02)
                ax.set_ylabel('F(x)')

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
                upper_key = lbl + ' CI upper'
                lower_key = lbl + ' CI lower'
                if upper_key in self.datasets and lower_key in self.datasets and not is_cat:
                    ax.fill_between(xd, self.datasets[lower_key], self.datasets[upper_key],
                                    alpha=self.fit_ci_alpha_spin.value(), color=color, linewidth=0, label=f'{lbl} CI')
                pi_upper_key = lbl + ' PI upper'
                pi_lower_key = lbl + ' PI lower'
                if pi_upper_key in self.datasets and pi_lower_key in self.datasets and not is_cat:
                    ax.fill_between(xd, self.datasets[pi_lower_key], self.datasets[pi_upper_key],
                                    alpha=self.fit_ci_alpha_spin.value() * 0.5, color=color, linewidth=0,
                                    linestyle='--', label=f'{lbl} PI')

            elif sct == 'Scatter':
                xplot = _cat_xplot(xd) if is_cat else xd
                mk = self.scatter_marker.currentText()
                mk = 'o' if mk == 'None' else mk
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
                        xplot = xplot[:n]
                        yd = yd[:n]
                _sc = ax.scatter(xplot, yd, label=lbl,
                           s=self.scatter_size.value(),
                           alpha=self.scatter_alpha.value(),
                           c=c_arg if c_arg is not None else mk_color,
                           cmap=cmap if c_arg is not None else None,
                           marker=mk,
                           edgecolors=sc_ec,
                           linewidths=self.scatter_lw.value())
                _sc.set_picker(True)
                upper_key = lbl + ' CI upper'
                lower_key = lbl + ' CI lower'
                if upper_key in self.datasets and lower_key in self.datasets and not is_cat:
                    ax.fill_between(xd, self.datasets[lower_key], self.datasets[upper_key],
                                    alpha=self.fit_ci_alpha_spin.value(), color=color, linewidth=0, label=f'{lbl} CI')
                pi_upper_key = lbl + ' PI upper'
                pi_lower_key = lbl + ' PI lower'
                if pi_upper_key in self.datasets and pi_lower_key in self.datasets and not is_cat:
                    ax.fill_between(xd, self.datasets[pi_lower_key], self.datasets[pi_upper_key],
                                    alpha=self.fit_ci_alpha_spin.value() * 0.5, color=color, linewidth=0,
                                    linestyle='--', label=f'{lbl} PI')

            elif sct == 'Bar':
                bi = bar_idx_counter
                bar_idx_counter += 1
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
                        xd_f = np.asarray(xd, dtype=float)
                        yd_f = np.asarray(yd, dtype=float)
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
                mk = self.err_fmt_marker.currentText()
                mk = 'o' if mk == 'None' else mk
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
                mk = self.bubble_marker.currentText()
                mk = 'o' if mk == 'None' else mk
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
                pos_c = getattr(self, 'waterfall_pos_color', None) or '#2ecc71'
                neg_c = getattr(self, 'waterfall_neg_color', None) or '#e74c3c'
                running = 0.0
                prev_top = None
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
                    prev_top = top
                    running = top

        # Return categorical tick info — caller must apply AFTER set_xscale/set_yscale
        # so scale changes don't wipe out the FixedLocator set here.
        if any_cat_x and all_x_cats:
            return (all_x_cats, bar_horiz)
        return None
