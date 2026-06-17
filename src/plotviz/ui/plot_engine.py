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
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QApplication
from ui.helpers import _get_dir, _remember_dir
from PyQt6.QtCore import Qt


from ui.tab_builders import WHOLE_CHART_TYPES, _NO_X_TYPES


# LaTeX special characters that must be escaped when text.usetex is active.
_LATEX_SPECIAL = str.maketrans({
    '&':  r'\&',
    '%':  r'\%',
    '$':  r'\$',
    '#':  r'\#',
    '_':  r'\_',
    '{':  r'\{',
    '}':  r'\}',
    '~':  r'\textasciitilde{}',
    '^':  r'\textasciicircum{}',
    '\\': r'\textbackslash{}',
})

def _latex_safe(text: str) -> str:
    """Escape LaTeX special characters in user-supplied text when usetex is on.

    When matplotlib's ``text.usetex`` is True every string passed to
    set_title / set_xlabel / suptitle / etc. is fed verbatim to LaTeX.
    Characters like ``&``, ``%``, ``$`` … are LaTeX control characters and
    will cause a hard render error if left unescaped.  This helper is a
    no-op when usetex is off so it is safe to call unconditionally.
    """
    if not matplotlib.rcParams.get('text.usetex', False):
        return text
    return text.translate(_LATEX_SPECIAL)


from core.constants import _3D_TYPES, _NO_LEGEND_TYPES


class PlotEngineMixin:
    def _sp_opt(self, subplot_idx, key, fallback=None):
        """Return a per-subplot chart option, falling back to *fallback* when absent."""
        opts = getattr(self, 'subplot_chart_opts', {}).get(subplot_idx, {})
        return opts.get(key, fallback)

    def _plot_on(self, ax, series, ct, row_offset=0, subplot_idx=0):
        """
        series: list of (xd, yd, label, series_ct) tuples.
        ct: the global/whole-chart type (used for whole-chart types).
        For per-series types (Line/Scatter/Bar/Area/Errorbar) each tuple's
        series_ct is used instead.
        X/Y arrays are truncated to min(len(x), len(y)) so temporary column
        mismatches during editing never cause an exception.
        row_offset: ignored — colours restart from index 0 on every subplot.
        subplot_idx: which subplot's chart opts to use when rendering.
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

        def _cmap(type_attr, sp_key=None):
            """Return the cmap string for a given subplot, using per-subplot opts
            when available and falling back to the shared combo widget."""
            if sp_key:
                val = self._sp_opt(subplot_idx, sp_key, None)
                if val:
                    return val
            combo = getattr(self, type_attr, None) or getattr(self, 'cmap_combo', None)
            return combo.currentText() if combo else 'viridis'

        def _o(key, default):
            """Shorthand: read a per-subplot chart option with a default."""
            return self._sp_opt(subplot_idx, key, default)

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
                    o = s.get('opts', {})
                    ec_val = o.get('hist_edgecolor', _o('hist_edgecolor', 'white'))
                    if ec_val == 'auto': ec_val = s.get('color', C[i])
                    h_alpha = o.get('hist_alpha', _o('hist_alpha', 0.7))
                    if self._is_categorical(yd):
                        vals, counts = np.unique(yd, return_counts=True)
                        ax.bar(vals, counts, label=lbl, color=s.get('color', C[i]),
                               alpha=h_alpha,
                               edgecolor=ec_val if ec_val != 'none' else None)
                        ax.tick_params(axis='x', rotation=45)
                    else:
                        ax.hist(yd, bins=_o('hist_bins', 20),
                                density=_o('hist_density', False),
                                cumulative=_o('hist_cumulative', False),
                                histtype=_o('hist_histtype', 'bar'),
                                orientation=_o('hist_orientation', 'vertical'),
                                alpha=h_alpha,
                                edgecolor=ec_val if ec_val != 'none' else None,
                                label=lbl, color=s.get('color', C[i]))

            elif ct == 'Boxplot':
                num_series = [(k, v) for k, v in yd_dict.items() if not self._is_categorical(v)]
                if num_series:
                    bp = ax.boxplot(
                        [v for _, v in num_series], labels=[k for k, _ in num_series],
                        patch_artist=True, notch=_o('box_notch', False),
                        vert=_o('box_vert', True),
                        showmeans=_o('box_show_means', False),
                        showfliers=_o('box_showfliers', True),
                        whis=_o('box_whis', 1.5),
                        medianprops=dict(color='black', linewidth=2) if _o('box_show_medians', True) else dict(linewidth=0),
                    )
                    for patch, c in zip(bp['boxes'], C):
                        patch.set_facecolor(c)
                        patch.set_alpha(_o('box_alpha', 0.7))

            elif ct == 'Violin':
                num_series = [(k, v) for k, v in yd_dict.items() if not self._is_categorical(v)]
                if num_series:
                    parts = ax.violinplot(
                        [v for _, v in num_series],
                        showmeans=_o('violin_show_means', True),
                        showmedians=_o('violin_show_medians', True),
                        showextrema=_o('violin_show_extrema', False),
                        bw_method=_o('violin_bw', 'scott'),
                        points=int(_o('violin_points', '100')),
                        vert=_o('violin_vert', True),
                    )
                    for pc, c in zip(parts['bodies'], C):
                        pc.set_facecolor(c)
                        pc.set_alpha(0.7)
                    if _o('violin_vert', True):
                        ax.set_xticks(range(1, len(num_series)+1))
                        ax.set_xticklabels([k for k, _ in num_series])
                    else:
                        ax.set_yticks(range(1, len(num_series)+1))
                        ax.set_yticklabels([k for k, _ in num_series])

            elif ct == 'Pie':
                if series:
                    xd, yd, lbl, _ = series[0]
                    labels = list(xd) if self._is_categorical(xd) else [f'{v:.4g}' for v in xd]
                    explode = [0.08] + [0.0]*(len(yd)-1) if _o('pie_explode_first', False) else None
                    wedge_kw = {'width': 0.5} if _o('pie_donut', False) else {}
                    # Per-wedge colors: use curve_styles[segment] if present (set by the
                    # palette system or user edits), otherwise assign from palette and store
                    # so future palette changes have an entry to update.
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
                           autopct='%1.1f%%' if _o('pie_autopct', True) else None,
                           shadow=_o('pie_shadow', False),
                           startangle=_o('pie_startangle', 90.0),
                           labeldistance=_o('pie_labeldistance', 1.1),
                           pctdistance=_o('pie_pctdistance', 0.6),
                           explode=explode, wedgeprops=wedge_kw,
                           colors=wedge_colors)
                    ax.set_aspect('equal')

            elif ct == 'Heatmap':
                zc = self.combo_z.currentText()
                if zc != '(none)' and zc in self.datasets:
                    z = self.datasets[zc]
                    if series and len(series) > 0:
                        # Fix 1: use griddata onto a regular mesh instead of naive row-major reshape
                        from scipy.interpolate import griddata as _griddata
                        xd, yd, lbl, _ = series[0]
                        xf = xd.astype(float)
                        yf = yd.astype(float)
                        zf = np.array(z, dtype=float)
                        _mn = min(len(xf), len(yf), len(zf))
                        xf, yf, zf = xf[:_mn], yf[:_mn], zf[:_mn]
                        n = max(2, int(np.ceil(np.sqrt(_mn))))
                        xi = np.linspace(np.min(xf), np.max(xf), n)
                        yi = np.linspace(np.min(yf), np.max(yf), n)
                        XI, YI = np.meshgrid(xi, yi)
                        Z = _griddata((xf, yf), zf, (XI, YI), method='linear')
                        Z = np.where(np.isnan(Z), np.nanmean(zf), Z)
                        # Bug 18: pass extent so axis ticks show data values, not pixel indices
                        extent_kw = {'extent': [float(np.min(xf)), float(np.max(xf)),
                                                float(np.min(yf)), float(np.max(yf))]}
                    else:
                        n = int(np.ceil(np.sqrt(len(z))))
                        if n < 2: n = 2
                        Z = np.full((n, n), np.nan)
                        for k in range(len(z)): Z[k//n, k%n] = z[k]
                        extent_kw = {}
                    if n >= 2:
                        # Fix 4: optional vmin/vmax
                        _vm_kw = {}
                        if hasattr(self, 'heat_vminmax_enable') and self.heat_vminmax_enable.isChecked():
                            _vm_kw = {'vmin': self.heat_vmin.value(), 'vmax': self.heat_vmax.value()}
                        im = ax.imshow(Z, aspect='auto', cmap=_cmap('cmap_combo', 'cmap'), origin='lower',
                                       alpha=_o('heat_alpha', 1.0),
                                       interpolation=_o('heat_interpolation', 'nearest'),
                                       **extent_kw, **_vm_kw)
                        if _o('heat_colorbar', True):
                            _cb = self.canvas.figure.colorbar(im, ax=ax,
                                shrink=_o('heat_colorbar_shrink', 1.0))
                            _zlbl = self.subplot_zlabels.get(subplot_idx, '') or lbl
                            if _zlbl:
                                _cb.set_label(_latex_safe(_zlbl),
                                    fontsize=self.zlabel_size.value() if hasattr(self, 'zlabel_size') else 11,
                                    color=getattr(self, 'zlabel_color', '#000000'),
                                    fontfamily=self.zlabel_font.currentText() if hasattr(self, 'zlabel_font') else 'sans-serif')
            elif ct == 'Contour':
                zc = self.combo_z.currentText()
                if zc != '(none)' and zc in self.datasets and series:
                    xd, yd, lbl, _ = series[0]
                    z = self.datasets[zc]
                    if not self._is_categorical(xd) and not self._is_categorical(yd):
                        # Fix 1: use griddata onto a regular mesh instead of naive row-major reshape
                        from scipy.interpolate import griddata as _griddata
                        xf = xd.astype(float)
                        yf = yd.astype(float)
                        zf = np.array(z, dtype=float)
                        _mn = min(len(xf), len(yf), len(zf))
                        xf, yf, zf = xf[:_mn], yf[:_mn], zf[:_mn]
                        n = max(2, int(np.ceil(np.sqrt(_mn))))
                        xi = np.linspace(np.min(xf), np.max(xf), n)
                        yi = np.linspace(np.min(yf), np.max(yf), n)
                        X, Y = np.meshgrid(xi, yi)
                        Z = _griddata((xf, yf), zf, (X, Y), method='linear')
                        Z = np.where(np.isnan(Z), np.nanmean(zf), Z)
                        if n >= 2:
                            # Fix 6: explicit levels list overrides integer count
                            _lvl_raw = ''
                            if hasattr(self, 'contour_levels_explicit'):
                                _lvl_raw = self.contour_levels_explicit.text().strip()
                            if _lvl_raw:
                                try:
                                    lvl = [float(v) for v in _lvl_raw.split(',') if v.strip()]
                                except ValueError:
                                    lvl = _o('contour_levels', 10)
                            else:
                                lvl = _o('contour_levels', 10)
                            alp = _o('heat_alpha', 1.0)
                            # Fix 4: optional vmin/vmax
                            _vm_kw = {}
                            if hasattr(self, 'heat_vminmax_enable') and self.heat_vminmax_enable.isChecked():
                                _vm_kw = {'vmin': self.heat_vmin.value(), 'vmax': self.heat_vmax.value()}
                            # Fix 5: contour line colour/width from settings
                            _lc = _o('contour_line_color', '#000000')
                            _lw = _o('contour_line_width', 0.5)
                            # Bug 3: track last mappable so colorbar is drawn regardless of
                            # which combination of filled/line contour is active.
                            _last_contour_m = None
                            if _o('heat_filled_contour', True):
                                cf = ax.contourf(X, Y, Z, levels=lvl, cmap=_cmap('cmap_combo', 'cmap'), alpha=alp, **_vm_kw)
                                _last_contour_m = cf
                            if _o('heat_contour_lines', True):
                                cs = ax.contour(X, Y, Z, levels=lvl, colors=_lc, linewidths=_lw, alpha=0.5)
                                if _last_contour_m is None: _last_contour_m = cs
                            if _last_contour_m is not None and _o('heat_colorbar', True):
                                _cb = self.canvas.figure.colorbar(_last_contour_m, ax=ax,
                                    shrink=_o('heat_colorbar_shrink', 1.0))
                                _zlbl = self.subplot_zlabels.get(subplot_idx, '') or lbl
                                if _zlbl:
                                    _cb.set_label(_latex_safe(_zlbl),
                                        fontsize=self.zlabel_size.value() if hasattr(self, 'zlabel_size') else 11,
                                        color=getattr(self, 'zlabel_color', '#000000'),
                                        fontfamily=self.zlabel_font.currentText() if hasattr(self, 'zlabel_font') else 'sans-serif')
            elif ct == 'Tricontour':
                zc = self.combo_z.currentText()
                if zc != '(none)' and zc in self.datasets and series:
                    xd, yd, lbl, _ = series[0]
                    z = self.datasets[zc]
                    if not self._is_categorical(xd) and not self._is_categorical(yd):
                        x = xd.astype(float)
                        y = yd.astype(float)
                        z = np.array(z, dtype=float)
                        n = min(len(x), len(y), len(z))
                        x, y, z = x[:n], y[:n], z[:n]
                        lvl  = _o('tri_levels', 10)
                        alp  = _o('tri_alpha', 1.0)
                        cmap = _cmap('tri_cmap_combo', 'tri_cmap')
                        last_mappable = None
                        _fill_mode = _o('tri_fill_mode', 'Filled contour')
                        # Backward compat: old saves may have boolean tri_filled/tri_tripcolor
                        if _fill_mode not in ('Filled contour', 'Face colours', 'None'):
                            _fill_mode = 'Filled contour'
                        if _fill_mode == 'Face colours':
                            tc = ax.tripcolor(x, y, z, cmap=cmap, alpha=alp)
                            last_mappable = tc
                        elif _fill_mode == 'Filled contour':
                            cf = ax.tricontourf(x, y, z, levels=lvl, cmap=cmap, alpha=alp)
                            last_mappable = cf
                        if _o('tri_lines', True):
                            # Bug 4: assign to last_mappable so colorbar works when
                            # fill style is None and only contour lines are drawn.
                            tl = ax.tricontour(x, y, z, levels=lvl, colors='k', linewidths=0.5, alpha=0.5)
                            if last_mappable is None: last_mappable = tl
                        if _o('tri_triplot', False):
                            ax.triplot(x, y, color='k', linewidth=0.4, alpha=0.5)
                        if last_mappable is not None and _o('tri_colorbar', True):
                            _cb = self.canvas.figure.colorbar(last_mappable, ax=ax,
                                shrink=_o('tri_colorbar_shrink', 1.0))
                            _zlbl = self.subplot_zlabels.get(subplot_idx, '') or lbl
                            if _zlbl:
                                _cb.set_label(_latex_safe(_zlbl),
                                    fontsize=self.zlabel_size.value() if hasattr(self, 'zlabel_size') else 11,
                                    color=getattr(self, 'zlabel_color', '#000000'),
                                    fontfamily=self.zlabel_font.currentText() if hasattr(self, 'zlabel_font') else 'sans-serif')

            elif ct == '3D Surface':
                # Bug 1: this block was previously stranded inside the Tricontour elif,
                # causing 3D Surface to never render and Tricontour to crash on 2D axes.
                zc = self.combo_z.currentText()
                if zc != '(none)' and zc in self.datasets and series:
                    xd, yd, lbl, _ = series[0]
                    z = self.datasets[zc]
                    if not self._is_categorical(xd) and not self._is_categorical(yd):
                        # Fix 1: use griddata onto a regular mesh instead of naive row-major reshape
                        from scipy.interpolate import griddata as _griddata
                        xf = xd.astype(float)
                        yf = yd.astype(float)
                        zf = np.array(z, dtype=float)
                        _mn = min(len(xf), len(yf), len(zf))
                        xf, yf, zf = xf[:_mn], yf[:_mn], zf[:_mn]
                        n = max(2, int(np.ceil(np.sqrt(_mn))))
                        xi = np.linspace(np.min(xf), np.max(xf), n)
                        yi = np.linspace(np.min(yf), np.max(yf), n)
                        X, Y = np.meshgrid(xi, yi)
                        Z = _griddata((xf, yf), zf, (X, Y), method='linear')
                        Z = np.where(np.isnan(Z), np.nanmean(zf), Z)
                        if n >= 2:  # Bug 19: guard against empty Z
                            st = _o('surf_stride', 1)
                            alp = _o('heat_alpha', 1.0)
                            if _o('surf_wireframe', False):
                                ax.plot_wireframe(X, Y, Z, rstride=st, cstride=st, alpha=alp)
                            else:
                                surf = ax.plot_surface(X, Y, Z, cmap=_cmap('cmap_combo', 'cmap'),
                                                       alpha=alp, rstride=st, cstride=st)
                                # Fix 7: honour heat_colorbar for 3D Surface
                                if _o('heat_colorbar', True):
                                    _cb = self.canvas.figure.colorbar(surf, ax=ax,
                                        shrink=_o('heat_colorbar_shrink', 1.0))
                                    _zlbl = self.subplot_zlabels.get(subplot_idx, '') or lbl
                                    if _zlbl:
                                        _cb.set_label(_latex_safe(_zlbl),
                                            fontsize=self.zlabel_size.value() if hasattr(self, 'zlabel_size') else 11,
                                            color=getattr(self, 'zlabel_color', '#000000'),
                                            fontfamily=self.zlabel_font.currentText() if hasattr(self, 'zlabel_font') else 'sans-serif')


            elif ct == 'Hist2D':
                if series:
                    xd, yd, lbl, _ = series[0]
                    if not self._is_categorical(xd) and not self._is_categorical(yd):
                        norm = matplotlib.colors.LogNorm() if _o('hist2d_log', False) else None
                        _, _, _, img = ax.hist2d(
                            xd.astype(float), yd.astype(float),
                            bins=[_o('hist2d_bins_x', 20), _o('hist2d_bins_y', 20)],
                            cmap=_cmap('hist2d_cmap_combo', 'hist2d_cmap'), alpha=_o('hist2d_alpha', 1.0), norm=norm)
                        if _o('hist2d_colorbar', True):
                            self.canvas.figure.colorbar(img, ax=ax)

            elif ct == 'Hexbin':
                if series:
                    xd, yd, lbl, _ = series[0]
                    if not self._is_categorical(xd) and not self._is_categorical(yd):
                        hb = ax.hexbin(xd.astype(float), yd.astype(float),
                                       gridsize=_o('hexbin_gridsize', 20), cmap=_cmap('hexbin_cmap_combo', 'hexbin_cmap'),
                                       bins='log' if _o('hexbin_log', False) else None,
                                       alpha=_o('hexbin_alpha', 1.0))
                        if _o('hexbin_colorbar', True):
                            self.canvas.figure.colorbar(hb, ax=ax)

            elif ct == 'Polar':
                for i, (xd, yd, lbl, _) in enumerate(series):
                    if self._is_categorical(xd): continue
                    s = self.curve_styles.get(lbl, {})
                    o = s.get('opts', {})
                    color = s.get('color', C[i])
                    ls = s.get('linestyle', '-') or '-'
                    mk = s.get('marker', 'None')
                    mk = None if mk in ('None', 'none', '') else mk
                    theta = xd.astype(float)
                    r = yd.astype(float)
                    if ls != 'none':
                        ax.plot(theta, r, linestyle=ls, color=color,
                                linewidth=s.get('linewidth', 1.5), marker=mk, label=lbl)
                    if o.get('pol_fill', self.polar_fill.isChecked()):
                        ax.fill(theta, r, alpha=o.get('pol_fill_alpha', self.polar_fill_alpha.value()), color=color)

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
                        ax.set_yticks(np.linspace(0, vmax, _o('radar_gridlevels', 5)+1)[1:])
                        for i, (xd_s, yd_s, lbl_s, _) in enumerate(series):
                            s = self.curve_styles.get(lbl_s, {})
                            o_s = s.get('opts', {})
                            color = s.get('color', C[i])
                            vals = list(yd_s.astype(float)) + [float(yd_s[0])]
                            ax.plot(angles, vals, color=color, linewidth=s.get('linewidth', 1.8), label=lbl_s)
                            if o_s.get('rad_fill', _o('rad_fill', True)):
                                ax.fill(angles, vals, color=color, alpha=o_s.get('rad_fill_alpha', _o('rad_fill_alpha', 0.25)))

            elif ct == 'ECDF':
                for i, (xd, yd, lbl, _) in enumerate(series):
                    if self._is_categorical(yd): continue
                    s = self.curve_styles.get(lbl, {})
                    o = s.get('opts', {})
                    color = s.get('color', C[i])
                    sorted_d = np.sort(yd.astype(float))
                    ecdf = np.arange(1, len(sorted_d)+1) / len(sorted_d)
                    if _o('ecdf_complementary', False): ecdf = 1.0 - ecdf
                    ax.step(sorted_d, ecdf, color=color,
                            linewidth=s.get('linewidth', 1.8),
                            alpha=o.get('ecdf_alpha', _o('ecdf_alpha', 1.0)),
                            label=lbl, where='post')
                    if o.get('ecdf_markers', _o('ecdf_markers', False)):
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
                        sc = _o('quiver_scale', 1.0)
                        _x, _y = xd[:n].astype(float), yd[:n].astype(float)
                        _U, _V = U[:n].astype(float), V[:n].astype(float)
                        _kw = dict(scale=sc if sc != 1.0 else None,
                                   scale_units='xy' if sc != 1.0 else None,
                                   width=_o('quiver_width', 0.005), alpha=0.85)
                        if _o('quiver_color_by_mag', False):
                            ax.quiver(_x, _y, _U, _V, np.hypot(_U, _V),
                                      cmap=_cmap('quiver_cmap_combo', 'quiver_cmap'), **_kw)
                        else:
                            ax.quiver(_x, _y, _U, _V, **_kw)

            elif ct == 'Barbs':
                if series:
                    xd, yd, lbl, _ = series[0]
                    uc = self.barbs_u_combo.currentText()
                    vc = self.barbs_v_combo.currentText()
                    if uc != '(none)' and vc != '(none)' and uc in self.datasets and vc in self.datasets:
                        U = self.datasets[uc].astype(float)
                        V = self.datasets[vc].astype(float)
                        n = min(len(xd), len(yd), len(U), len(V))
                        _x, _y = xd[:n].astype(float), yd[:n].astype(float)
                        _U, _V = U[:n].astype(float), V[:n].astype(float)
                        _kw = dict(
                            length=_o('barbs_length', 7.0),
                            pivot=_o('barbs_pivot', 'tip'),
                            alpha=_o('barbs_alpha', 0.85),
                        )
                        if _o('barbs_color_by_mag', False):
                            mag = np.hypot(_U, _V)
                            ax.barbs(_x, _y, _U, _V, mag,
                                     cmap=_cmap('barbs_cmap_combo', 'barbs_cmap'), **_kw)
                        else:
                            ax.barbs(_x, _y, _U, _V, **_kw)

            elif ct == 'Streamplot':
                if series:
                    xd, yd, lbl, _ = series[0]
                    uc = self.stream_u_combo.currentText()
                    vc = self.stream_v_combo.currentText()
                    if uc != '(none)' and vc != '(none)' and uc in self.datasets and vc in self.datasets:
                        try:
                            U_flat = self.datasets[uc].astype(float)
                            V_flat = self.datasets[vc].astype(float)
                            _xf = xd.astype(float)
                            _yf = yd.astype(float)
                            n = min(len(_xf), len(_yf), len(U_flat), len(V_flat))
                            _xf = _xf[:n]
                            _yf = _yf[:n]
                            U_flat = U_flat[:n]
                            V_flat = V_flat[:n]
                            # Build a regular 2-D grid from the flat point columns.
                            xs_u = np.unique(_xf)
                            ys_u = np.unique(_yf)
                            nx, ny = len(xs_u), len(ys_u)
                            xi = np.searchsorted(xs_u, _xf)
                            yi = np.searchsorted(ys_u, _yf)
                            U_grid = np.zeros((ny, nx))
                            V_grid = np.zeros((ny, nx))
                            for k in range(n):
                                if xi[k] < nx and yi[k] < ny:
                                    U_grid[yi[k], xi[k]] = U_flat[k]
                                    V_grid[yi[k], xi[k]] = V_flat[k]
                            _kw = dict(
                                density=_o('stream_density', 1.0),
                                arrowsize=_o('stream_arrowsize', 1.0),
                                linewidth=_o('stream_linewidth', 1.5),
                            )
                            if _o('stream_color_by_mag', False):
                                speed = np.sqrt(U_grid**2 + V_grid**2)
                                _kw['color'] = speed
                                _kw['cmap'] = _cmap('stream_cmap_combo', 'stream_cmap')
                                del _kw['linewidth']  # can't combine with color array
                            ax.streamplot(xs_u, ys_u, U_grid, V_grid, **_kw)
                        except Exception:
                            pass  # silently skip if data is not grid-compatible

            return

        # ── Per-series mixable types ─────────────────────────────────────────
        bar_series  = [(i, xd, yd, lbl) for i, (xd, yd, lbl, sct) in enumerate(series) if sct == 'Bar']
        n_bar    = len(bar_series)
        bar_w    = _o('bar_width', 0.8)
        bar_stk  = _o('bar_stacked', False)
        bar_horiz= _o('bar_horizontal', False)
        bar_ec   = _o('bar_edgecolor', 'none')
        bar_elw  = _o('bar_edge_lw', 0.5)
        bar_al   = _o('bar_alpha', 1.0)

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
        # Range-bar Y-min column (draws bars from ymin to yd instead of 0 to yd)
        _bar_ymin_col = None
        if hasattr(self, 'combo_bar_ymin'):
            _raw = self.combo_bar_ymin.currentText()
            if _raw and _raw != '(none)' and _raw in self.datasets:
                _bar_ymin_col = _raw

        for i, (xd, yd, lbl, sct) in enumerate(series):
            s = self.curve_styles.get(lbl, {})
            color = s.get('color', C[i])
            is_cat = self._is_categorical(xd)
            # Per-series type options stored by _save_series_options
            o = s.get('opts', {})

            if sct == 'Line':
                ls = s.get('linestyle', '-') or '-'
                if ls in ('default', ''): ls = '-'
                mk = s.get('marker', 'None')
                if mk in ('default', 'None', 'none', ''): mk = None
                lw = s.get('linewidth', 1.5)
                mk_color = s.get('marker_color', color)
                xplot = _cat_xplot(xd) if is_cat else xd
                ds = o.get('line_drawstyle', self.line_drawstyle.currentText())
                plot_kw = dict(label=lbl, color=color, linestyle=ls, linewidth=lw,
                               markersize=s.get('markersize', 6),
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
                                    label=f'{lbl} PI')

            elif sct == 'Scatter':
                xplot = _cat_xplot(xd) if is_cat else xd
                mk = s.get('marker', 'o')
                mk = 'o' if mk in ('None', 'none', '') else mk
                mk_color = s.get('marker_color', color)
                sc_ec = o.get('sc_edgecolor', self.scatter_edgecolor.currentText())
                if sc_ec == 'auto': sc_ec = mk_color
                # Color by Z column if requested
                c_arg = None
                if o.get('sc_colorby', self.scatter_colorby_check.isChecked()):
                    zc = self.combo_z.currentText()
                    if zc != '(none)' and zc in self.datasets:
                        z = self.datasets[zc]
                        n = min(len(xplot), len(yd), len(z))
                        c_arg = z[:n]
                        xplot = xplot[:n]
                        yd = yd[:n]
                _sc = ax.scatter(xplot, yd, label=lbl,
                           s=o.get('sc_size', self.scatter_size.value()),
                           alpha=o.get('sc_alpha', self.scatter_alpha.value()),
                           c=c_arg if c_arg is not None else mk_color,
                           cmap=_cmap('scatter_cmap_combo') if c_arg is not None else None,
                           marker=mk,
                           edgecolors=sc_ec,
                           linewidths=o.get('sc_lw', self.scatter_lw.value()))
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
                                    label=f'{lbl} PI')

            elif sct == 'Bar':
                bi = bar_idx_counter
                bar_idx_counter += 1
                b_w   = o.get('bar_width',    bar_w)
                b_stk = o.get('bar_stacked',  bar_stk)
                b_hor = o.get('bar_horizontal', bar_horiz)
                b_ec  = o.get('bar_edgecolor', bar_ec)
                b_elw = o.get('bar_edge_lw',  bar_elw)
                b_al  = o.get('bar_alpha',    bar_al)
                b_cbv = o.get('bar_colorbyval', _o('bar_colorbyval', False))
                # Color bars by value if requested
                def _bar_colors(vals, base_color, _cbv=b_cbv):
                    if _cbv:
                        return [plt.cm.RdYlGn(0.8 if v >= 0 else 0.2) for v in vals]
                    return base_color
                # Per-series _bar helper using this series' opts
                def _bar_s(ax, positions, values, width, bottom=None,
                           _ec=b_ec, _elw=b_elw, _hor=b_hor, **kw):
                    ec_kw = {'edgecolor': _ec if _ec != 'none' else 'none',
                             'linewidth': _elw if _ec != 'none' else 0}
                    kw.update(ec_kw)
                    if _hor:
                        ax.barh(positions, values, height=width,
                                left=bottom if bottom is not None else 0, **kw)
                    else:
                        kw2 = dict(kw)
                        if bottom is not None: kw2['bottom'] = bottom
                        ax.bar(positions, values, width=width, **kw2)
                if bar_cat:
                    xd_s = [str(v) for v in xd]
                    positions = np.array([cat_pos.get(v, 0) for v in xd_s], dtype=float)
                    if _bar_ymin_col:
                        # Range-bar mode: bottom from ymin column, height = yd - ymin
                        ymin_d = np.asarray(self.datasets[_bar_ymin_col], dtype=float)
                        n = min(len(positions), len(yd), len(ymin_d))
                        bot = ymin_d[:n]
                        heights = np.asarray(yd[:n], dtype=float) - bot
                        _bar_s(ax, positions[:n], heights, b_w, bottom=bot, label=lbl,
                               color=_bar_colors(heights, color), alpha=b_al)
                    elif b_stk:
                        bot = np.array([bar_bottoms_cat.get(v, 0.0) for v in xd_s], dtype=float)
                        _bar_s(ax, positions, yd, b_w, bottom=bot, label=lbl,
                               color=_bar_colors(yd, color), alpha=b_al)
                        for v, y in zip(xd_s, yd): bar_bottoms_cat[v] = bar_bottoms_cat.get(v, 0.0) + float(y)
                    else:
                        _bar_s(ax, positions + bar_offs[bi], yd, b_w/max(n_bar,1), label=lbl,
                               color=_bar_colors(yd, color), alpha=b_al)
                else:
                    if is_cat or self._is_categorical(yd): continue
                    try:
                        xd_f = np.asarray(xd, dtype=float)
                        yd_f = np.asarray(yd, dtype=float)
                    except (ValueError, TypeError): continue
                    if _bar_ymin_col:
                        # Range-bar mode: bottom from ymin column, height = yd - ymin
                        ymin_d = np.asarray(self.datasets[_bar_ymin_col], dtype=float)
                        n = min(len(xd_f), len(yd_f), len(ymin_d))
                        bot = ymin_d[:n]
                        heights = yd_f[:n] - bot
                        _bar_s(ax, xd_f[:n] + bar_offs[bi], heights, b_w/max(n_bar,1),
                               bottom=bot, label=lbl,
                               color=_bar_colors(heights, color), alpha=b_al)
                    else:
                        if bar_bottoms_num is None:
                            bar_bottoms_num = np.zeros(len(xd_f))
                        elif len(bar_bottoms_num) < len(xd_f):
                            bar_bottoms_num = np.concatenate([bar_bottoms_num,
                                                              np.zeros(len(xd_f) - len(bar_bottoms_num))])
                        if b_stk:
                            _bar_s(ax, xd_f, yd_f, b_w, bottom=bar_bottoms_num[:len(yd_f)], label=lbl,
                                   color=_bar_colors(yd_f, color), alpha=b_al)
                            bar_bottoms_num[:len(yd_f)] += yd_f
                        else:
                            _bar_s(ax, xd_f + bar_offs[bi], yd_f, b_w/max(n_bar,1), label=lbl,
                                   color=_bar_colors(yd_f, color), alpha=b_al)

            elif sct == 'Area':
                al  = o.get('area_alpha',   _o('area_alpha', 0.4))
                lw  = o.get('area_lw',      _o('area_lw', 0.8))
                stk = o.get('area_stacked', _o('area_stacked', False))
                bl  = o.get('area_baseline', _o('area_baseline', 0.0))
                xplot = _cat_xplot(xd) if is_cat else xd
                base_key = '_area_base'
                base = getattr(ax, base_key, None)
                if base is None or len(base) != len(xplot):
                    base = np.full(len(xplot), bl)
                if stk:
                    ax.fill_between(xplot, base, base + yd, alpha=al, label=lbl, color=color)
                    if o.get('area_showline', _o('area_showline', True)):
                        ax.plot(xplot, base + yd, color=color, lw=lw)
                    setattr(ax, base_key, base + yd)
                else:
                    ax.fill_between(xplot, bl, yd, alpha=al, label=lbl, color=color)
                    if o.get('area_showline', _o('area_showline', True)):
                        ax.plot(xplot, yd, color=color, lw=lw)

            elif sct == 'Fill Between':
                if self._is_categorical(yd): continue
                xplot = _cat_xplot(xd) if is_cat else xd
                al        = o.get('fill_between_alpha',   _o('fill_between_alpha',   0.4))
                lw        = o.get('fill_between_lw',      _o('fill_between_lw',      0.8))
                show_line = o.get('fill_between_showline', True)
                y2_col = o.get('fill_between_y2_col') or None
                if not y2_col and hasattr(self, 'combo_fill_y2'):
                    raw = self.combo_fill_y2.currentText()
                    if raw and raw != '(none)': y2_col = raw
                if y2_col and y2_col in self.datasets:
                    y2d = self.datasets[y2_col]
                    n   = min(len(xplot), len(yd), len(y2d))
                    xp, y1, y2 = xplot[:n], yd[:n], y2d[:n]
                    ax.fill_between(xp, y1, y2, alpha=al, label=lbl, color=color)
                    if show_line:
                        ax.plot(xp, y1, color=color, lw=lw, alpha=0.8)
                        ax.plot(xp, y2, color=color, lw=lw, alpha=0.8)
                else:
                    n = min(len(xplot), len(yd))
                    xp, yp = xplot[:n], yd[:n]
                    ax.fill_between(xp, 0, yp, alpha=al, label=lbl, color=color)
                    if show_line:
                        ax.plot(xp, yp, color=color, lw=lw, alpha=0.8)

            elif sct == 'Errorbar':
                ec   = self.combo_err.currentText()
                xerr_c = self.err_xerr_combo.currentText()
                err  = self.datasets.get(ec)  if ec      != '(none)' else None
                xerr = self.datasets.get(xerr_c) if xerr_c != '(none)' else None
                xplot = _cat_xplot(xd) if is_cat else xd
                mk = s.get('marker', 'o')
                mk = 'o' if mk in ('None', 'none', '') else mk
                ax.errorbar(xplot, yd, yerr=err, xerr=xerr, label=lbl,
                            capsize=o.get('err_capsize',   self.err_capsize.value()),
                            capthick=o.get('err_capthick', self.err_capthick.value()),
                            elinewidth=o.get('err_elinewidth', self.err_elinewidth.value()),
                            barsabove=o.get('err_barsabove',   self.err_barsabove.isChecked()),
                            fmt=mk, color=color,
                            linewidth=s.get('linewidth', 1.5))

            elif sct == 'Step':
                if self._is_categorical(yd): continue
                xplot = _cat_xplot(xd) if is_cat else xd
                where = _o('step_where', 'pre')
                lw = s.get('linewidth', 1.5)
                ax.step(xplot, yd, where=where, label=lbl, color=color, linewidth=lw)
                if o.get('step_fill', _o('step_fill', False)):
                    ax.fill_between(xplot, yd, step=where,
                                    alpha=o.get('step_fill_alpha', _o('step_fill_alpha', 0.2)), color=color)

            elif sct == 'Stem':
                if self._is_categorical(yd): continue
                xplot = _cat_xplot(xd) if is_cat else xd
                baseline = _o('stem_baseline', 0.0)
                mk = s.get('marker', 'o')
                mk_color = s.get('marker_color', color)
                lw = s.get('linewidth', 1.2)
                ms = s.get('markersize', 8)
                markerline, stemlines, baseline_line = ax.stem(
                    xplot, yd, linefmt='-', markerfmt=mk,
                    basefmt='k-', label=lbl, bottom=baseline)
                plt.setp(stemlines, color=color, linewidth=lw)
                plt.setp(markerline, color=mk_color, markersize=ms)

            elif sct == 'Bubble':
                if self._is_categorical(yd): continue
                xplot = _cat_xplot(xd) if is_cat else xd
                sc_name = self.bubble_size_combo.currentText()
                b_scale = o.get('bubble_scale', self.bubble_scale.value())
                if sc_name != '(uniform)' and sc_name in self.datasets:
                    raw_s = self.datasets[sc_name].astype(float)
                    n = min(len(xplot), len(yd), len(raw_s))
                    raw_s = raw_s[:n]
                    mn, mx = np.nanmin(np.abs(raw_s)), np.nanmax(np.abs(raw_s))
                    if mx > mn:
                        sizes = 10 + (np.abs(raw_s) - mn) / (mx - mn) * b_scale
                    else:
                        sizes = np.full(n, b_scale / 2)
                else:
                    n = min(len(xplot), len(yd))
                    sizes = b_scale / 4
                mk_color = s.get('marker_color', color)
                mk = s.get('marker', 'o')
                mk = 'o' if mk in ('None', 'none', '') else mk
                b_ec = o.get('bubble_edgecolor', self.bubble_edgecolor.currentText())
                if b_ec == 'auto': b_ec = mk_color
                ax.scatter(xplot[:n], yd[:n], s=sizes, alpha=o.get('bubble_alpha', self.bubble_alpha.value()),
                           color=mk_color, edgecolors=b_ec if b_ec != 'none' else 'none',
                           marker=mk, label=lbl)

            elif sct == 'Waterfall':
                if self._is_categorical(yd): continue
                try:
                    yd_f = np.asarray(yd, dtype=float)
                except (ValueError, TypeError): continue
                # x can be categorical labels or numeric — always use integer positions
                # so string labels like "Revenue Start" never cause a float-cast failure
                is_cat_x = self._is_categorical(xd)
                if is_cat_x:
                    x_labels = list(xd)
                    xd_f = np.arange(len(x_labels), dtype=float)
                else:
                    try:
                        xd_f = np.asarray(xd, dtype=float)
                    except (ValueError, TypeError): continue
                    x_labels = None
                n = min(len(xd_f), len(yd_f))
                xd_f, yd_f = xd_f[:n], yd_f[:n]
                if x_labels is not None:
                    x_labels = x_labels[:n]
                w   = _o('waterfall_width', 0.6)
                al  = _o('waterfall_alpha', 1.0)
                pos_c = _o('waterfall_pos_color', None) or '#2ecc71'
                neg_c = _o('waterfall_neg_color', None) or '#e74c3c'
                running = 0.0
                prev_top = None
                for k in range(n):
                    val = float(yd_f[k])
                    fc = pos_c if val >= 0 else neg_c
                    ax.bar(xd_f[k], val, width=w, bottom=running,
                           color=fc, edgecolor='white', linewidth=0.5, alpha=al,
                           label=(lbl if k == 0 else '_nolegend_'))
                    top = running + val
                    if _o('waterfall_connector', True) and prev_top is not None:
                        ax.plot([xd_f[k-1]+w/2, xd_f[k]-w/2], [prev_top, prev_top],
                                color='#555', linewidth=0.8, linestyle='--')
                    prev_top = top
                    running = top
                # Apply string tick labels for categorical x after all bars are drawn
                if x_labels is not None:
                    ax.set_xticks(xd_f)
                    ax.set_xticklabels(x_labels, rotation=45, ha='right')

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

    def _apply_grid(self, ax, subplot_idx=0):
        """Apply major and minor grid styling to ax.

        Reads from the per-subplot dict (subplot_grid_opts[subplot_idx]) when
        available; falls back to the global Layout tab widgets so existing
        single-subplot charts keep working.
        """
        g = getattr(self, 'subplot_grid_opts', {}).get(subplot_idx, None)

        major_on  = g['enabled']        if g else self.grid_check.isChecked()
        maj_color = g['color']          if g else getattr(self, 'grid_color', '#cccccc')
        maj_ls    = g['ls']             if g else self.grid_linestyle.currentText()
        maj_lw    = g['lw']             if g else self.grid_linewidth.value()
        maj_alpha = g['alpha']          if g else self.grid_alpha.value()
        minor_on  = g['minor_enabled']  if g else self.minor_grid_check.isChecked()
        min_color = g['minor_color']    if g else getattr(self, 'minor_grid_color', '#e8e8e8')
        min_ls    = g['minor_ls']       if g else self.minor_grid_linestyle.currentText()
        min_lw    = g['minor_lw']       if g else self.minor_grid_linewidth.value()
        min_alpha = g['minor_alpha']    if g else self.minor_grid_alpha.value()

        if major_on:
            ax.grid(True, which='major',
                    color=maj_color, linestyle=maj_ls,
                    linewidth=maj_lw, alpha=maj_alpha)
        else:
            ax.grid(False, which='major')

        if minor_on:
            ax.minorticks_on()
            ax.grid(True, which='minor',
                    color=min_color, linestyle=min_ls,
                    linewidth=min_lw, alpha=min_alpha)
        else:
            ax.grid(False, which='minor')
            try: ax.minorticks_off()
            except Exception: pass

    def _apply_canvas_style(self, ax, subplot_idx=0):
        """Apply background color, tick styling and border visibility to an axes.

        Canvas/border values are read from the per-subplot dict
        (subplot_canvas_opts[subplot_idx]) when available; falls back to the
        global widget attrs so existing single-subplot charts keep working.
        """
        from matplotlib.ticker import (AutoMinorLocator, MultipleLocator,
                                       ScalarFormatter, PercentFormatter,
                                       NullLocator, StrMethodFormatter)
        from matplotlib.patches import Wedge
        c = getattr(self, 'subplot_canvas_opts', {}).get(subplot_idx, None)
        fg      = c['fg']       if c else getattr(self, 'chart_fg_color',  '#000000')
        plot_bg = c['plot_bg']  if c else getattr(self, 'plot_bg_color',   '#ffffff')
        ax.set_facecolor(plot_bg)

        # Pie axes: hide all ticks, tick labels, and spines — nothing to style
        _is_pie = any(isinstance(p, Wedge) for p in ax.patches)
        if _is_pie:
            ax.set_axis_off()
            return

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
        x_pos     = self.subplot_xaxis_pos.get(subplot_idx, 'bottom')
        y_pos     = self.subplot_yaxis_pos.get(subplot_idx, 'left')

        # ── Detect twin (secondary) y-axis ────────────────────────────────────
        # ax.twinx() places ticks on the RIGHT and leaves the left side off.
        # tick_params(left=..., labelleft=...) would re-enable left labels on
        # ax2, causing them to bleed over the primary axis area and appear as
        # "extra ticks".  Detect this case and keep left labels suppressed.
        _is_twinx = ax.yaxis.get_ticks_position() in ('right', 'unknown')

        # ── Major tick params ──────────────────────────────────────────────────
        if x_pos == 'top':
            ax.tick_params(axis='x', which='major', colors=fg, labelsize=xtick_sz,
                           direction=x_dir, labelrotation=x_rot,
                           top=x_show, labeltop=x_show, bottom=False, labelbottom=False)
        else:
            ax.tick_params(axis='x', which='major', colors=fg, labelsize=xtick_sz,
                           direction=x_dir, labelrotation=x_rot,
                           bottom=x_show, labelbottom=x_show)
        if _is_twinx:
            # Secondary axis: style right-side ticks only; never show left labels
            ax.tick_params(axis='y', which='major', colors=fg, labelsize=ytick_sz,
                           direction=y_dir, labelrotation=y_rot,
                           right=y_show, labelright=y_show,
                           left=False, labelleft=False)
        else:
            if y_pos == 'right':
                ax.tick_params(axis='y', which='major', colors=fg, labelsize=ytick_sz,
                               direction=y_dir, labelrotation=y_rot,
                               right=y_show, labelright=y_show, left=False, labelleft=False)
            else:
                ax.tick_params(axis='y', which='major', colors=fg, labelsize=ytick_sz,
                               direction=y_dir, labelrotation=y_rot,
                               left=y_show, labelleft=y_show)

        # ── Minor ticks ───────────────────────────────────────────────────────
        if x_minor:
            ax.xaxis.set_minor_locator(AutoMinorLocator())
            if x_pos == 'top':
                ax.tick_params(axis='x', which='minor', colors=fg, direction=x_dir,
                               top=x_show, bottom=False)
            else:
                ax.tick_params(axis='x', which='minor', colors=fg, direction=x_dir,
                               bottom=x_show)
        else:
            ax.xaxis.set_minor_locator(NullLocator())
        if y_minor:
            ax.yaxis.set_minor_locator(AutoMinorLocator())
            if _is_twinx:
                ax.tick_params(axis='y', which='minor', colors=fg, direction=y_dir,
                               right=y_show, left=False)
            elif y_pos == 'right':
                ax.tick_params(axis='y', which='minor', colors=fg, direction=y_dir,
                               right=y_show, left=False)
            else:
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
            if c:
                # Per-subplot border flags from canvas_opts dict
                border_flags = {
                    'top':    c.get('border_top',    True),
                    'bottom': c.get('border_bottom', True),
                    'left':   c.get('border_left',   True),
                    'right':  c.get('border_right',  True),
                }
                for spine_name, visible in border_flags.items():
                    spine = ax.spines[spine_name]
                    spine.set_visible(visible)
                    if visible:
                        spine.set_edgecolor(fg)
            else:
                for spine_name, chk in [('top',    self.border_top),
                                          ('bottom', self.border_bottom),
                                          ('left',   self.border_left),
                                          ('right',  self.border_right)]:
                    spine = ax.spines[spine_name]
                    spine.set_visible(chk.isChecked())
                    if chk.isChecked():
                        spine.set_edgecolor(fg)

        # ── Axis line positions (x on y / y on x) ────────────────────────────
        # Applied after border logic so spine visibility is already resolved.
        # Skip for polar/3D axes and secondary (twinx) axes.
        if not is_polar and not _is_twinx:
            if x_pos == 'top':
                ax.spines['bottom'].set_visible(False)
                ax.spines['top'].set_visible(True)
                ax.spines['top'].set_edgecolor(fg)
                ax.xaxis.set_label_position('top')
            elif x_pos == 'zero':
                ax.spines['bottom'].set_position('zero')
            # 'bottom': default — no extra action required

            if y_pos == 'right':
                ax.spines['left'].set_visible(False)
                ax.spines['right'].set_visible(True)
                ax.spines['right'].set_edgecolor(fg)
                ax.yaxis.set_label_position('right')
            elif y_pos == 'zero':
                ax.spines['left'].set_position('zero')
            # 'left': default — no extra action required

    @staticmethod
    def _align_twinx_ticks(ax, ax2, subplot_idx=0, y_step=0.0, y2_step=0.0):
        """Constrain the secondary y-axis tick count to match the primary.

        When ax.twinx() creates ax2, matplotlib's AutoLocator picks tick counts
        independently.  The secondary axis (ax2) routinely ends up with MORE
        ticks than the primary, which makes it look like the primary has gained
        extra ticks (the grid lines don't align and the right spine crowds up).

        Fix: read how many intervals the primary axis chose, then cap ax2 to
        the same nbins via MaxNLocator.  The primary axis is left untouched so
        its tick positions stay exactly as matplotlib intended.

        Skipped when the user has pinned a custom step (y_step / y2_step > 0).
        """
        if y_step > 0 or y2_step > 0:
            return  # user pinned a step — don't override
        from matplotlib.ticker import MaxNLocator
        try:
            primary_ticks = ax.yaxis.get_major_locator()()
            n_intervals = max(len(primary_ticks) - 1, 4)  # floor at 4
            # Only constrain the secondary; leave the primary untouched
            ax2.yaxis.set_major_locator(MaxNLocator(nbins=n_intervals,
                                                    steps=[1, 2, 2.5, 5, 10]))
        except Exception:
            pass  # never crash the render path

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
            kw['loc'] = loc
            kw['bbox_to_anchor'] = (lx, ly)
        return kw

    def _decorate(self, ax, xc, yd, is3d=False, subplot_idx=0, ct=None):
        """Apply titles, labels, limits, scale, legend for one subplot panel."""
        # Bug 12: accept ct as a parameter so callers can pass the per-subplot type
        # rather than always reading the global combo (which breaks in multi-subplot mode).
        if ct is None:
            ct = self.chart_type_combo.currentText()
        # ── Title ──
        # n==1: chart title = ax title, controlled from Style tab (title_input)
        # n>1: per-subplot title from Axes tab (sp_titles[idx])
        _n_subplots = self.subplot_rows * self.subplot_cols
        if _n_subplots == 1:
            # Title for single-subplot charts is rendered via suptitle() in the
            # render loop so that title_x/title_y controls work and the title
            # does not move when subplot margins are adjusted.
            ax.set_title('')
        else:
            show_title = self.subplot_title_show.get(subplot_idx, True)
            title_txt = (self.sp_titles.get(subplot_idx, '') or f'Subplot {subplot_idx+1}') if show_title else ''
            ax.set_title(_latex_safe(title_txt),
                         fontsize=self.subplot_title_size.get(subplot_idx, 11),
                         color=self.subplot_title_color.get(subplot_idx, '#000000'),
                         fontfamily=self.subplot_title_font.get(subplot_idx, 'sans-serif'),
                         pad=self.subplot_title_pad.get(subplot_idx, 6),
                         rotation=self.subplot_title_rotation.get(subplot_idx, 0),
                         loc=self.subplot_title_ha.get(subplot_idx, 'center'))
        # ── X label ──
        if self.subplot_xlabel_show.get(subplot_idx, True):
            xl = self.subplot_xlabels.get(subplot_idx, '') or ('' if ct in _NO_X_TYPES else xc)
            ax.set_xlabel(_latex_safe(xl),
                          fontsize=self.xlabel_size.value(),
                          color=self.xlabel_color,
                          fontfamily=self.xlabel_font.currentText(),
                          rotation=self.subplot_xlabel_rotation.get(subplot_idx, 0),
                          labelpad=self.subplot_xlabel_labelpad.get(subplot_idx, 4),
                          loc=self.subplot_xlabel_loc.get(subplot_idx, 'center'))
            ax.xaxis.label.set_ha(self.subplot_xlabel_ha.get(subplot_idx, 'center'))
        else:
            ax.set_xlabel('')
        # ── Y label ──
        _YCOLNAME_TYPES = {'Heatmap', 'Contour', 'Tricontour', '3D Surface'}
        if self.subplot_ylabel_show.get(subplot_idx, True):
            if ct in _YCOLNAME_TYPES and hasattr(self, 'series_table') and self.series_table.rowCount() > 0:
                # For heatmap/contour/3D types: default to the actual y-column name (col 1)
                _ycb = self.series_table.cellWidget(0, 1)
                _yc_default = _ycb.currentText() if _ycb else ''
                yl = self.subplot_ylabels.get(subplot_idx, '') or _yc_default
            else:
                yl = self.subplot_ylabels.get(subplot_idx, '') or ('' if ct in _NO_X_TYPES else ', '.join(yd.keys()))
            ax.set_ylabel(_latex_safe(yl),
                          fontsize=self.ylabel_size.value(),
                          color=self.ylabel_color,
                          fontfamily=self.ylabel_font.currentText(),
                          rotation=self.subplot_ylabel_rotation.get(subplot_idx, 90),
                          labelpad=self.subplot_ylabel_labelpad.get(subplot_idx, 4),
                          loc=self.subplot_ylabel_loc.get(subplot_idx, 'center'))
            ax.yaxis.label.set_ha(self.subplot_ylabel_ha.get(subplot_idx, 'center'))
        else:
            ax.set_ylabel('')

        # ── Z label (3D Surface only) ──
        # When the colorbar is visible it carries the label; ax.set_zlabel is
        # only used when the colorbar is hidden.
        if is3d and hasattr(ax, 'set_zlabel'):
            _colorbar_visible = self._sp_opt(subplot_idx, 'heat_colorbar', True)
            if not _colorbar_visible:
                if self.subplot_zlabel_show.get(subplot_idx, True):
                    _series_label_default = next(iter(yd), '') if yd else ''
                    zl = self.subplot_zlabels.get(subplot_idx, '') or _series_label_default
                    ax.set_zlabel(
                        _latex_safe(zl),
                        fontsize=self.zlabel_size.value() if hasattr(self, 'zlabel_size') else 11,
                        color=getattr(self, 'zlabel_color', '#000000'),
                        fontfamily=self.zlabel_font.currentText() if hasattr(self, 'zlabel_font') else 'sans-serif',
                        rotation=self.subplot_zlabel_rotation.get(subplot_idx, 90),
                        labelpad=self.subplot_zlabel_labelpad.get(subplot_idx, 4),
                    )
                else:
                    ax.set_zlabel('')

        # ── Secondary Y axis ──
        _y2_active = False
        _NO_Y2_TYPES = {'Heatmap', 'Contour', 'Tricontour', 'Hist2D', 'Hexbin', 'Pie', 'Polar', 'Radar'}
        if not is3d and ct not in _NO_Y2_TYPES:
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
                    xc_row = xcb.currentText()
                    yc_row = ycb.currentText()
                    if xc_row not in self.datasets or yc_row not in self.datasets: continue
                    label = lbl_item.text() if lbl_item and lbl_item.text() else yc_row
                    sct = self._get_series_type(row)
                    y2_series.append((self.datasets[xc_row], self.datasets[yc_row], label, sct))
                if y2_series:
                    self._plot_on(ax2, y2_series, ct, row_offset=self._get_series_row_offset(0), subplot_idx=0)
                if self.subplot_y2label_show.get(subplot_idx, True):
                    y2l = self.subplot_y2labels.get(subplot_idx, '') or ', '.join(y2_cols)
                    if y2l:
                        ax2.set_ylabel(_latex_safe(y2l),
                                       fontsize=self.y2label_size.value(),
                                       color=self.y2label_color,
                                       fontfamily=self.y2label_font.currentText(),
                                       rotation=self.y2label_rotation.value(),
                                       labelpad=self.y2label_labelpad.value(),
                                       loc=self.y2label_loc.currentText())
                        ax2.yaxis.label.set_ha(self.y2label_ha.currentText())
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
            # Types where the axes are not in standard data-coordinates:
            # Heatmap uses imshow pixel-space, Pie/Polar/Radar use non-Cartesian projections.
            # Contour, Tricontour, Hist2D, Hexbin all use data coordinates and CAN receive
            # set_xscale / set_xlim / set_ylim normally.
            _NO_SCALE_TYPES  = {'Pie', 'Heatmap', 'Polar', 'Radar', '3D Surface'}
            _NO_LIMITS_TYPES = _NO_X_TYPES | {'Pie', 'Heatmap'}
            _horiz    = ct == 'Bar' and self._sp_opt(subplot_idx, 'bar_horizontal', False)
            _protect_y = _x_is_cat and _horiz
            xs = self.subplot_xscales.get(subplot_idx, 'linear')
            ys = self.subplot_yscales.get(subplot_idx, 'linear')
            if ct not in _NO_SCALE_TYPES:
                if not _x_is_cat:  # never call set_xscale on categorical axes
                    try: ax.set_xscale(xs if xs != 'inverted' else 'linear')
                    except Exception: ax.set_xscale('linear')
                if not _protect_y:
                    try: ax.set_yscale(ys if ys != 'inverted' else 'linear')
                    except Exception: ax.set_yscale('linear')
            xlim = self.subplot_xlims.get(subplot_idx)
            if xlim and ct not in _NO_LIMITS_TYPES and not _x_is_cat:
                ax.set_xlim(xlim[0], xlim[1])
            ylim = self.subplot_ylims.get(subplot_idx)
            if ylim and ct not in _NO_LIMITS_TYPES:
                ax.set_ylim(ylim[0], ylim[1])
            # Bug 3 fix: apply axis inversion AFTER set_xlim/set_ylim so the
            # inversion is not silently undone by a subsequent set_xlim call.
            if ct not in _NO_SCALE_TYPES:
                if not _x_is_cat and xs == 'inverted': ax.invert_xaxis()
                if not _protect_y and ys == 'inverted': ax.invert_yaxis()
            if self.subplot_equal_aspect.get(subplot_idx, False) and ct not in ('Pie', 'Polar', 'Radar', '3D Surface'):
                try: ax.set_aspect('equal', adjustable='box' if (xlim or ylim) else 'datalim')
                except Exception: pass
        # ── Legend (no Y2) ──
        # Pie is in _NO_LEGEND_TYPES to suppress auto-legend, but if the user
        # explicitly enables "Show legend" we honour it via ax.legend().
        _legend_auto_types = _NO_LEGEND_TYPES - {'Pie'}
        if not _y2_active and self.subplot_legends.get(subplot_idx, True) and yd \
                and ct not in _legend_auto_types:
            ax.legend(**self._legend_kwargs(subplot_idx))
        if not is3d:
            self._apply_canvas_style(ax, subplot_idx)
            if ct not in {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Polar', 'Radar', '3D Surface', 'Tricontour'}:
                self._apply_grid(ax, subplot_idx)
            if _y2_active:
                self._align_twinx_ticks(
                    ax, ax2, subplot_idx,
                    y_step=self.subplot_ytick_step.get(subplot_idx, 0.0),
                    y2_step=self.subplot_ytick_step.get(subplot_idx, 0.0))

    def _margins_as_fractions(self):
        """Convert margin spinbox values (physical units) to figure fractions [0, 1].

        Divides directly by fig_width / fig_height — both are already in the current
        unit, so no conversion is needed and there is no floating-point round-trip
        error (e.g. value/2.54*2.54 != value exactly in IEEE 754).
        """
        w = self.fig_width.value()
        h = self.fig_height.value()
        if w <= 0 or h <= 0:
            return 0.10, 0.95, 0.10, 0.95
        return (
            self.fig_left.value()   / w,   # left   fraction
            self.fig_right.value()  / w,   # right  fraction
            self.fig_bottom.value() / h,   # bottom fraction
            self.fig_top.value()    / h,   # top    fraction
        )

    def _title_pos_as_fractions(self):
        """Convert title_x / title_y (physical units) to figure fractions.

        Returns (tx, ty) where each is in [0, 1] (or slightly beyond for right
        alignment). Divides directly by fig_width / fig_height — same no-round-trip
        rationale as _margins_as_fractions.
        """
        w = self.fig_width.value()
        h = self.fig_height.value()
        if w <= 0 or h <= 0:
            return 0.5, 0.97
        tx = self.title_x.value() / w if hasattr(self, 'title_x') else 0.5
        ty = self.title_y.value() / h if hasattr(self, 'title_y') else 0.97
        return tx, ty

    # ═══════════════════════════════════════════════════════════════════════════
    # UPDATE PREVIEW
    # ═══════════════════════════════════════════════════════════════════════════
    def _render_axes(self, fig):
        """Build every subplot axis on *fig*, plot all series, and apply
        per-subplot decoration (labels, scales, limits, grid, legend, twinx).

        This is the single source of truth for turning the current settings
        into rendered axes. Both the live preview (update_preview) and the
        image export (export_chart) call it so the on-screen chart and the
        exported file are guaranteed to render identically.

        The caller is responsible for the font rc-context, figure-level layout
        (margins / suptitle / border), and annotations, which differ between
        the preview (canvas-box coordinates) and export (figure coordinates).

        Returns (axes_list, ax2_map, is3d, n).
        """
        series = self._get_series(primary_only=True)
        ct = self.chart_type_combo.currentText()
        is3d = ct in _3D_TYPES
        rows, cols, n = self.subplot_rows, self.subplot_cols, self.subplot_rows * self.subplot_cols

        axes_list = []
        ax2_map = {}  # {subplot_idx: ax2} for twinx alignment

        if n == 1:
            _proj = 'polar' if ct in ('Polar', 'Radar') else ('3d' if is3d else None)
            ax = fig.add_subplot(111, projection=_proj)
            axes_list.append(ax)
            if is3d:
                _elev = self.view3d_elev_spin.value() if hasattr(self, 'view3d_elev_spin') else 30
                _azim = self.view3d_azim_spin.value() if hasattr(self, 'view3d_azim_spin') else -60
                ax.view_init(elev=_elev, azim=_azim)
            cat_info = self._plot_on(ax, series, ct, row_offset=self._get_series_row_offset(0), subplot_idx=0) if (series or ct in _NO_X_TYPES) else None
            yd = {s[2]: s[1] for s in series}
            xc = self.series_table.cellWidget(0, 0).currentText() if self.series_table.rowCount() > 0 and self.series_table.cellWidget(0, 0) else ''
            self._decorate(ax, xc, yd, is3d, subplot_idx=0)
            self._apply_cat_ticks(ax, cat_info)
        else:
            mosaic = getattr(self, '_subplot_mosaic', None)
            first = None

            if mosaic is not None:
                # ── Mosaic layout ──────────────────────────────────────
                ax_dict = fig.subplot_mosaic(mosaic)
                # Order axes by first appearance of each cell letter
                seen_order = list(dict.fromkeys(c for row in mosaic for c in row))
                axes_list = [ax_dict[k] for k in seen_order]
                for idx, ax in enumerate(axes_list):
                    sub_ct = self.subplot_chart_types.get(idx, 'Line')
                    sub_series, sub_y2_series = self._get_series_for_subplot(idx)
                    x_cols, y_cols, y2_cols = self._get_col_names_for_subplot(idx)
                    cat_info = self._plot_on(ax, sub_series, sub_ct, row_offset=self._get_series_row_offset(idx), subplot_idx=idx) if (sub_series or sub_ct in _NO_X_TYPES) else None
                    ax2 = None
                    if sub_y2_series and sub_ct not in _NO_LEGEND_TYPES:
                        ax2 = ax.twinx()
                        ax2_map[idx] = ax2
                        self._plot_on(ax2, sub_y2_series, sub_ct, row_offset=self._get_series_row_offset(idx), subplot_idx=idx)
                        if self.subplot_y2label_show.get(idx, True):
                            y2lbl = self.subplot_y2labels.get(idx, '') or ', '.join(y2_cols)
                            if y2lbl:
                                ax2.set_ylabel(_latex_safe(y2lbl), fontsize=self.y2label_size.value(),
                                               color=self.y2label_color,
                                               fontfamily=self.y2label_font.currentText(),
                                               rotation=self.y2label_rotation.value(),
                                               labelpad=self.y2label_labelpad.value(),
                                               loc=self.y2label_loc.currentText())
                                ax2.yaxis.label.set_ha(self.y2label_ha.currentText())
                        y2lim = self.subplot_y2lims.get(idx)
                        if y2lim: ax2.set_ylim(y2lim[0], y2lim[1])
                        self._apply_canvas_style(ax2, idx)
                    t = self.sp_titles.get(idx, '')
                    show_title = self.subplot_title_show.get(idx, True)
                    title_text = (t or f'Subplot {idx+1}') if show_title else ''
                    ax.set_title(_latex_safe(title_text),
                        fontfamily=self.subplot_title_font.get(idx, 'sans-serif'),
                        fontsize=self.subplot_title_size.get(idx, 11),
                        color=self.subplot_title_color.get(idx, '#000000'),
                        pad=self.subplot_title_pad.get(idx, 6),
                        rotation=self.subplot_title_rotation.get(idx, 0),
                        loc=self.subplot_title_ha.get(idx, 'center'))
                    if self.subplot_xlabel_show.get(idx, True):
                        xl = self.subplot_xlabels.get(idx, '') or ('' if sub_ct in _NO_X_TYPES else ', '.join(x_cols))
                        ax.set_xlabel(_latex_safe(xl), fontsize=self.xlabel_size.value(),
                                      color=self.xlabel_color,
                                      fontfamily=self.xlabel_font.currentText(),
                                      rotation=self.subplot_xlabel_rotation.get(idx, 0),
                                      labelpad=self.subplot_xlabel_labelpad.get(idx, 4),
                                      loc=self.subplot_xlabel_loc.get(idx, 'center'))
                        ax.xaxis.label.set_ha(self.subplot_xlabel_ha.get(idx, 'center'))
                    else:
                        ax.set_xlabel('')
                    if self.subplot_ylabel_show.get(idx, True):
                        yl = self.subplot_ylabels.get(idx, '') or ('' if sub_ct in _NO_X_TYPES else ', '.join(y_cols))
                        ax.set_ylabel(_latex_safe(yl), fontsize=self.ylabel_size.value(),
                                      color=self.ylabel_color,
                                      fontfamily=self.ylabel_font.currentText(),
                                      rotation=self.subplot_ylabel_rotation.get(idx, 90),
                                      labelpad=self.subplot_ylabel_labelpad.get(idx, 4),
                                      loc=self.subplot_ylabel_loc.get(idx, 'center'))
                        ax.yaxis.label.set_ha(self.subplot_ylabel_ha.get(idx, 'center'))
                    else:
                        ax.set_ylabel('')
                    xs = self.subplot_xscales.get(idx, 'linear')
                    ys = self.subplot_yscales.get(idx, 'linear')
                    _mosaic_no_scale  = {'Pie', 'Heatmap', 'Polar', 'Radar', '3D Surface'}
                    _mosaic_no_limits = {'Pie', 'Heatmap'}
                    if sub_ct not in _mosaic_no_scale:
                        if cat_info is None:  # don't set_xscale for categorical axes
                            try: ax.set_xscale(xs if xs != 'inverted' else 'linear')
                            except Exception: ax.set_xscale('linear')
                        try: ax.set_yscale(ys if ys != 'inverted' else 'linear')
                        except Exception: ax.set_yscale('linear')
                    xlim = self.subplot_xlims.get(idx)
                    ylim = self.subplot_ylims.get(idx)
                    if sub_ct not in _mosaic_no_limits:
                        if xlim: ax.set_xlim(xlim[0], xlim[1])
                        if ylim: ax.set_ylim(ylim[0], ylim[1])
                    # Bug 3 fix: invert after limits so set_xlim/ylim can't undo it
                    if sub_ct not in _mosaic_no_scale:
                        if cat_info is None and xs == 'inverted': ax.invert_xaxis()
                        if ys == 'inverted': ax.invert_yaxis()
                    if self.subplot_equal_aspect.get(idx, False) and sub_ct not in ('Pie', 'Polar', 'Radar', '3D Surface'):
                        try: ax.set_aspect('equal', adjustable='box' if (xlim or ylim) else 'datalim')
                        except Exception: pass
                    self._apply_canvas_style(ax, idx)
                    if sub_ct not in {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Polar', 'Radar', '3D Surface', 'Tricontour'}: self._apply_grid(ax, idx)
                    self._apply_cat_ticks(ax, cat_info)
                    if ax2 is not None:
                        self._align_twinx_ticks(ax, ax2, idx,
                            y_step=self.subplot_ytick_step.get(idx, 0.0),
                            y2_step=self.subplot_ytick_step.get(idx, 0.0))
                    show_leg = self.subplot_legends.get(idx, True)
                    if show_leg and sub_ct not in (_NO_LEGEND_TYPES - {'Pie'}):
                        if ax2 and (sub_series or sub_y2_series):
                            h1, l1 = ax.get_legend_handles_labels()
                            h2, l2 = ax2.get_legend_handles_labels()
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
                    _no_share = sub_is3d or sub_is_polar or sub_ct in {'Heatmap', 'Contour', 'Tricontour', 'Hist2D', 'Hexbin'}
                    if not _no_share and first:
                        if self.sp_sharex.isChecked(): kw['sharex'] = first
                        if self.sp_sharey.isChecked(): kw['sharey'] = first
                    ax = fig.add_subplot(rows, cols, idx+1, projection=sub_proj, **kw)
                    if sub_is3d:
                        _elev = self.view3d_elev_spin.value() if hasattr(self, 'view3d_elev_spin') else 30
                        _azim = self.view3d_azim_spin.value() if hasattr(self, 'view3d_azim_spin') else -60
                        ax.view_init(elev=_elev, azim=_azim)
                    if first is None: first = ax
                    axes_list.append(ax)
                    sub_series, sub_y2_series = self._get_series_for_subplot(idx)
                    x_cols, y_cols, y2_cols = self._get_col_names_for_subplot(idx)
                    default_xl  = ', '.join(x_cols)
                    default_yl  = ', '.join(y_cols)
                    default_y2l = ', '.join(y2_cols)
                    cat_info = self._plot_on(ax, sub_series, sub_ct, row_offset=self._get_series_row_offset(idx), subplot_idx=idx) if (sub_series or sub_ct in _NO_X_TYPES) else None
                    ax2 = None
                    if sub_y2_series and sub_ct not in _NO_LEGEND_TYPES:
                        ax2 = ax.twinx()
                        ax2_map[idx] = ax2
                        self._plot_on(ax2, sub_y2_series, sub_ct, row_offset=self._get_series_row_offset(idx), subplot_idx=idx)
                        if self.subplot_y2label_show.get(idx, True):
                            y2lbl = self.subplot_y2labels.get(idx, '') or default_y2l
                            if y2lbl:
                                ax2.set_ylabel(_latex_safe(y2lbl), fontsize=self.y2label_size.value(),
                                               color=self.y2label_color,
                                               fontfamily=self.y2label_font.currentText(),
                                               rotation=self.y2label_rotation.value(),
                                               labelpad=self.y2label_labelpad.value(),
                                               loc=self.y2label_loc.currentText())
                                ax2.yaxis.label.set_ha(self.y2label_ha.currentText())
                        y2lim = self.subplot_y2lims.get(idx)
                        if y2lim: ax2.set_ylim(y2lim[0], y2lim[1])
                        self._apply_canvas_style(ax2, idx)
                    t = self.sp_titles.get(idx, '')
                    show_title = self.subplot_title_show.get(idx, True)
                    title_text = (t or f'Subplot {idx+1}') if show_title else ''
                    ax.set_title(_latex_safe(title_text),
                        fontfamily=self.subplot_title_font.get(idx, 'sans-serif'),
                        fontsize=self.subplot_title_size.get(idx, 11),
                        color=self.subplot_title_color.get(idx, '#000000'),
                        pad=self.subplot_title_pad.get(idx, 6),
                        rotation=self.subplot_title_rotation.get(idx, 0),
                        loc=self.subplot_title_ha.get(idx, 'center'))
                    _horiz_bar = (sub_ct == 'Bar' and self._sp_opt(idx, 'bar_horizontal', False))
                    _default_xl_eff  = default_yl if _horiz_bar else default_xl
                    _default_yl_eff  = default_xl if _horiz_bar else default_yl
                    _custom_xl = self.subplot_xlabels.get(idx, '')
                    _custom_yl = self.subplot_ylabels.get(idx, '')
                    if self.subplot_xlabel_show.get(idx, True):
                        xl = _custom_xl or ('' if sub_ct in _NO_X_TYPES else _default_xl_eff)
                        ax.set_xlabel(_latex_safe(xl), fontsize=self.xlabel_size.value(),
                                      color=self.xlabel_color,
                                      fontfamily=self.xlabel_font.currentText(),
                                      rotation=self.subplot_xlabel_rotation.get(idx, 0),
                                      labelpad=self.subplot_xlabel_labelpad.get(idx, 4),
                                      loc=self.subplot_xlabel_loc.get(idx, 'center'))
                        ax.xaxis.label.set_ha(self.subplot_xlabel_ha.get(idx, 'center'))
                    else:
                        ax.set_xlabel('')
                    if self.subplot_ylabel_show.get(idx, True):
                        yl = _custom_yl or ('' if sub_ct in _NO_X_TYPES else _default_yl_eff)
                        ax.set_ylabel(_latex_safe(yl), fontsize=self.ylabel_size.value(),
                                      color=self.ylabel_color,
                                      fontfamily=self.ylabel_font.currentText(),
                                      rotation=self.subplot_ylabel_rotation.get(idx, 90),
                                      labelpad=self.subplot_ylabel_labelpad.get(idx, 4),
                                      loc=self.subplot_ylabel_loc.get(idx, 'center'))
                        ax.yaxis.label.set_ha(self.subplot_ylabel_ha.get(idx, 'center'))
                    else:
                        ax.set_ylabel('')
                    if not sub_is3d and sub_ct not in {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Polar', 'Radar', '3D Surface', 'Tricontour'}:
                        xs = self.subplot_xscales.get(idx, 'linear')
                        ys = self.subplot_yscales.get(idx, 'linear')
                        if cat_info is None:  # skip set_xscale for categorical
                            try: ax.set_xscale(xs if xs != 'inverted' else 'linear')
                            except Exception: ax.set_xscale('linear')
                        _sub_horiz = sub_ct == 'Bar' and self._sp_opt(idx, 'bar_horizontal', False)
                        _sub_x_is_cat = cat_info is not None
                        _protect_y = _sub_x_is_cat and _sub_horiz
                        if not _protect_y:
                            try: ax.set_yscale(ys if ys != 'inverted' else 'linear')
                            except Exception: ax.set_yscale('linear')
                    else:
                        xs = self.subplot_xscales.get(idx, 'linear')
                        ys = self.subplot_yscales.get(idx, 'linear')
                        _protect_y = False
                    _grid_no_limits = {'Pie', 'Heatmap'}
                    xlim = self.subplot_xlims.get(idx, None)
                    if xlim and sub_ct not in _grid_no_limits: ax.set_xlim(xlim[0], xlim[1])
                    ylim = self.subplot_ylims.get(idx, None)
                    if ylim and sub_ct not in _grid_no_limits: ax.set_ylim(ylim[0], ylim[1])
                    # Bug 3 fix: invert after limits so set_xlim/ylim can't undo it
                    if not sub_is3d and sub_ct not in {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Polar', 'Radar', '3D Surface', 'Tricontour'}:
                        if cat_info is None and xs == 'inverted': ax.invert_xaxis()
                        if not _protect_y and ys == 'inverted': ax.invert_yaxis()
                    if self.subplot_equal_aspect.get(idx, False) and sub_ct not in ('Pie', 'Polar', 'Radar', '3D Surface'):
                        try: ax.set_aspect('equal', adjustable='box' if (xlim or ylim) else 'datalim')
                        except Exception: pass
                    self._apply_cat_ticks(ax, cat_info)
                    show_leg = self.subplot_legends.get(idx, True)
                    if show_leg and sub_ct not in (_NO_LEGEND_TYPES - {'Pie'}):
                        if ax2 and (sub_series or sub_y2_series):
                            h1, l1 = ax.get_legend_handles_labels()
                            h2, l2 = ax2.get_legend_handles_labels()
                            if h1 or h2: ax.legend(h1+h2, l1+l2, **self._legend_kwargs(idx))
                        elif sub_series:
                            ax.legend(**self._legend_kwargs(idx))

        # ── Late canvas-style / grid / twinx pass (multi-subplot) ───────────
        if n > 1:
            for _ax_i, _ax in enumerate(axes_list):
                _ax_ct = self.subplot_chart_types.get(_ax_i, 'Line')
                if _ax_ct not in _3D_TYPES:
                    self._apply_canvas_style(_ax, _ax_i)
                    if _ax_ct not in {'Pie', 'Heatmap', 'Hist2D', 'Hexbin', 'Polar', 'Radar', '3D Surface', 'Tricontour'}: self._apply_grid(_ax, _ax_i)
            for _ax_i, _ax2 in ax2_map.items():
                _ax_primary = axes_list[_ax_i] if _ax_i < len(axes_list) else None
                if _ax_primary is not None:
                    self._align_twinx_ticks(_ax_primary, _ax2, _ax_i,
                        y_step=self.subplot_ytick_step.get(_ax_i, 0.0),
                        y2_step=self.subplot_ytick_step.get(_ax_i, 0.0))

        return axes_list, ax2_map, is3d, n

    def update_preview(self):
        try:
            # Guard: bail silently if core widgets aren't built yet
            if not hasattr(self, 'canvas') or not hasattr(self, 'chart_type_combo'):
                return
            # Guard: suppress intermediate redraws while _apply_settings is running.
            if getattr(self, '_applying_settings', False):
                return
            # Schedule snapshot on a debounce timer so it never blocks the render path.
            # _snapshot() calls _collect_settings() + deepcopy(datasets) which is expensive.
            if hasattr(self, '_snapshot'):
                if not hasattr(self, '_snapshot_timer'):
                    from PyQt6.QtCore import QTimer
                    self._snapshot_timer = QTimer(self)
                    self._snapshot_timer.setSingleShot(True)
                    self._snapshot_timer.timeout.connect(self._snapshot)
                self._snapshot_timer.start(400)   # 400 ms after last change
            # Mark dirty (unsaved changes)
            if hasattr(self, '_undo_stack') and not getattr(self, '_undo_suspended', False):
                self._is_dirty = True
            # Refresh placeholder text so it always reflects the current series columns
            if hasattr(self, '_update_label_placeholders'):
                self._update_label_placeholders()
            # Persist current chart-option widgets into the active subplot's dict so
            # plot_engine always reads up-to-date per-subplot values when rendering.
            if hasattr(self, '_save_chart_opts') and hasattr(self, 'series_sp_active'):
                _active_sp = self.series_sp_active.currentIndex()
                if _active_sp >= 0:
                    self._save_chart_opts(_active_sp)
            # Persist current canvas/grid widgets into the active subplot's dict.
            if hasattr(self, '_save_canvas_grid_opts') and hasattr(self, 'layout_sp_active'):
                _layout_sp = self.layout_sp_active.currentIndex()
                if _layout_sp >= 0:
                    self._save_canvas_grid_opts(_layout_sp)
            series = self._get_series(primary_only=True)
            ct = self.chart_type_combo.currentText()
            is3d = ct in _3D_TYPES
            rows, cols, n = self.subplot_rows, self.subplot_cols, self.subplot_rows*self.subplot_cols
            # Use title_font as the global chart font (applies to tick labels too)
            chart_font = self.title_font.currentText()

            with matplotlib.rc_context({'font.family': chart_font, 'text.usetex': False}):
                self.canvas.figure.clear()
                self.canvas._border_rect = None   # figure.clear() removes all artists
                self.canvas.figure.patch.set_facecolor(self.chart_bg_color)

                axes_list, ax2_map, is3d, n = self._render_axes(self.canvas.figure)

                self.canvas.axes_list = axes_list
                if axes_list: self.canvas.axes = axes_list[0]

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

                ul, ur, ub, ut = self._margins_as_fractions()

                adj_left   = box_left   + ul * box_w
                adj_right  = box_left   + ur * box_w
                adj_bottom = box_bottom + ub * box_h
                adj_top    = box_bottom + ut * box_h

                _n_sp = self.subplot_rows * self.subplot_cols

                # ── Suptitle (all layouts, including single-subplot) ─────────────────
                # Using suptitle for n==1 too ensures title_x/title_y controls work
                # and the title stays fixed when subplot margins are adjusted.
                _show_sup = self.title_check.isChecked()
                # For a single subplot, fall back to the placeholder text so the
                # title field always shows something when the input is empty.
                _sup_raw = self.title_input.text().strip()
                if not _sup_raw and _n_sp == 1:
                    _sup_raw = self.title_input.placeholderText()
                _sup_text = _latex_safe(_sup_raw) if _show_sup else ''
                _tx_frac, _ty_frac = self._title_pos_as_fractions()

                if _show_sup and _sup_text:
                    # Place suptitle at the user-set position mapped into the
                    # canvas box so that X and Y use the same coordinate frame.
                    # The box is the region of the preview canvas that shows the
                    # export-aspect content; both axes must be mapped through it
                    # so "centre of figure" in the spinbox = centre of that box.
                    title_x_canvas = box_left + _tx_frac * box_w
                    title_y_canvas = box_bottom + _ty_frac * box_h
                    suptitle_pt = self.title_size.value()
                    self.canvas.figure.suptitle(_sup_text,
                        fontsize=suptitle_pt, color=self.title_color,
                        fontfamily=self.title_font.currentText(),
                        x=title_x_canvas,
                        y=title_y_canvas,
                        ha=self.title_ha.currentText(),
                        rotation=self.title_rotation.value(),
                        va='top', transform=self.canvas.figure.transFigure)
                else:
                    self.canvas.figure.suptitle('')

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
                self.canvas.repaint()
                QApplication.processEvents()
                self.refresh_annotation_list()

        except Exception as e:
            traceback.print_exc()

    # ═══════════════════════════════════════════════════════════════════════════
    # EXPORT
    # ═══════════════════════════════════════════════════════════════════════════
    def _copy_image_to_clipboard(self):
        """Show a small DPI picker then copy the chart as PNG to the system clipboard."""
        try:
            import io
            from PyQt6.QtGui import QImage, QPixmap, QClipboard
            from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout,
                                         QHBoxLayout, QLabel, QSpinBox,
                                         QPushButton, QDialogButtonBox)

            if not hasattr(self, 'canvas') or self.canvas.figure is None:
                return

            fig_dpi = int(self.canvas.figure.get_dpi())

            # ── DPI picker dialog ─────────────────────────────────────────────
            dlg = QDialog(self)
            dlg.setWindowTitle('Copy Image to Clipboard')
            dlg.setFixedWidth(300)
            vlay = QVBoxLayout(dlg)
            vlay.setSpacing(10)

            row = QHBoxLayout()
            row.addWidget(QLabel('Resolution (DPI):'))
            dpi_spin = QSpinBox()
            dpi_spin.setRange(36, 600)
            dpi_spin.setValue(getattr(self, '_clipboard_dpi', fig_dpi))
            dpi_spin.setSuffix(' dpi')
            dpi_spin.setFixedWidth(90)
            row.addWidget(dpi_spin)
            row.addStretch()
            vlay.addLayout(row)

            # Live pixel-size hint
            def _update_hint():
                d = dpi_spin.value()
                fw = self.canvas.figure.get_figwidth()
                fh = self.canvas.figure.get_figheight()
                px_w = int(fw * d)
                px_h = int(fh * d)
                hint_lbl.setText(f'Output size: {px_w} × {px_h} px')
            hint_lbl = QLabel()
            hint_lbl.setStyleSheet('color:#666; font-size:11px;')
            vlay.addWidget(hint_lbl)
            dpi_spin.valueChanged.connect(_update_hint)
            _update_hint()

            btns = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok |
                QDialogButtonBox.StandardButton.Cancel)
            btns.accepted.connect(dlg.accept)
            btns.rejected.connect(dlg.reject)
            vlay.addWidget(btns)

            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

            chosen_dpi = dpi_spin.value()
            self._clipboard_dpi = chosen_dpi   # remember for next time

            # ── Render and copy (hide page-boundary indicator temporarily) ───
            border_rect = getattr(self.canvas, '_border_rect', None)
            if border_rect is not None:
                border_rect.set_visible(False)
            try:
                buf = io.BytesIO()
                self.canvas.figure.savefig(buf, format='png', dpi=chosen_dpi,
                                           bbox_inches='tight')
                buf.seek(0)
            finally:
                if border_rect is not None:
                    border_rect.set_visible(True)
            img = QImage.fromData(buf.read())
            if img.isNull():
                return
            QApplication.clipboard().setPixmap(
                QPixmap.fromImage(img), QClipboard.Mode.Clipboard)

            if hasattr(self, 'statusBar'):
                fw = self.canvas.figure.get_figwidth()
                fh = self.canvas.figure.get_figheight()
                px_w = int(fw * chosen_dpi)
                px_h = int(fh * chosen_dpi)
                self.statusBar().showMessage(
                    f'Image copied to clipboard  ({px_w}×{px_h} px, {chosen_dpi} dpi).', 4000)
        except Exception as e:
            import logging
            logging.getLogger('plotviz').warning('Copy to clipboard failed: %s', e)

    def export_chart(self, fmt=None):
        try:
            import os
            from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QGridLayout,
                                         QLabel, QComboBox, QSpinBox,
                                         QDialogButtonBox)
            from PyQt6.QtCore import Qt

            # ── Default filename from saved project file stem ──────────────
            fp_project = getattr(self, '_current_filepath', None)
            default_stem = (os.path.splitext(os.path.basename(fp_project))[0]
                            if fp_project else 'chart')

            wi, hi      = self._fig_size_in_inches()
            current_fmt = (fmt or self._export_fmt_combo.currentText()).upper()
            current_dpi = self.dpi_spin.value()

            # ── Compact pre-dialog: format + DPI only ──────────────────────
            _FORMATS     = ['PNG', 'SVG', 'PDF', 'JPEG', 'TIFF', 'EPS']
            _VECTOR_FMTS = {'SVG', 'EPS', 'PDF'}
            _DPI_PRESETS = [('96 dpi — screen', 96), ('150 dpi — low print', 150),
                            ('300 dpi — print',  300), ('600 dpi — hi-res',   600)]

            pre = QDialog(self)
            pre.setWindowTitle('Export Image')
            pre.setFixedWidth(320)
            vbox = QVBoxLayout(pre)
            vbox.setSpacing(10)
            vbox.setContentsMargins(16, 14, 16, 14)

            grid = QGridLayout()
            grid.setSpacing(8)
            grid.setColumnMinimumWidth(0, 64)

            fmt_combo = QComboBox()
            fmt_combo.addItems(_FORMATS)
            fidx = fmt_combo.findText(current_fmt)
            if fidx >= 0:
                fmt_combo.setCurrentIndex(fidx)
            grid.addWidget(QLabel('Format:'), 0, 0, Qt.AlignmentFlag.AlignRight)
            grid.addWidget(fmt_combo, 0, 1)

            dpi_combo = QComboBox()
            for lbl, val in _DPI_PRESETS:
                dpi_combo.addItem(lbl, val)
            dpi_spin = QSpinBox()
            dpi_spin.setRange(36, 1200)
            dpi_spin.setValue(current_dpi)
            dpi_spin.setSuffix(' dpi')
            dpi_spin.setFixedWidth(80)

            from PyQt6.QtWidgets import QHBoxLayout
            dpi_row = QHBoxLayout()
            dpi_row.setSpacing(6)
            dpi_row.addWidget(dpi_combo, 1)
            dpi_row.addWidget(dpi_spin)
            grid.addWidget(QLabel('Resolution:'), 1, 0, Qt.AlignmentFlag.AlignRight)
            grid.addLayout(dpi_row, 1, 1)

            px_label = QLabel()
            px_label.setStyleSheet('color: palette(mid); font-size: 10px;')
            grid.addWidget(px_label, 2, 1)

            vbox.addLayout(grid)

            btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                    QDialogButtonBox.StandardButton.Cancel)
            btns.button(QDialogButtonBox.StandardButton.Ok).setText('Save…')
            btns.accepted.connect(pre.accept)
            btns.rejected.connect(pre.reject)
            vbox.addWidget(btns)

            def _update_px():
                f   = fmt_combo.currentText()
                vec = f in _VECTOR_FMTS
                dpi_combo.setEnabled(not vec)
                dpi_spin.setEnabled(not vec)
                px_label.setText(
                    'Vector format — DPI not applied' if vec
                    else f'{round(wi * dpi_spin.value())} × {round(hi * dpi_spin.value())} px')

            def _preset_picked(i):
                dpi_spin.blockSignals(True)
                dpi_spin.setValue(dpi_combo.itemData(i))
                dpi_spin.blockSignals(False)
                _update_px()

            def _spin_edited():
                v = dpi_spin.value()
                match = next((i for i in range(dpi_combo.count())
                              if dpi_combo.itemData(i) == v), -1)
                dpi_combo.blockSignals(True)
                dpi_combo.setCurrentIndex(match)   # -1 → no selection = custom
                dpi_combo.blockSignals(False)
                _update_px()

            dpi_combo.currentIndexChanged.connect(_preset_picked)
            dpi_spin.valueChanged.connect(_spin_edited)
            fmt_combo.currentTextChanged.connect(lambda _: _update_px())

            # Seed preset selection
            for i in range(dpi_combo.count()):
                if dpi_combo.itemData(i) == current_dpi:
                    dpi_combo.blockSignals(True)
                    dpi_combo.setCurrentIndex(i)
                    dpi_combo.blockSignals(False)
                    break

            _update_px()

            if pre.exec() != QDialog.DialogCode.Accepted:
                return

            fmt     = fmt_combo.currentText().lower()
            dpi     = dpi_spin.value()
            ext     = 'jpg' if fmt == 'jpeg' else fmt
            mpl_fmt = 'jpeg' if fmt == 'jpeg' else fmt

            # ── Native file dialog with pre-filled name ────────────────────
            suggested = os.path.join(_get_dir(), f'{default_stem}.{ext}')
            fp, _ = QFileDialog.getSaveFileName(
                self, 'Export Image', suggested,
                f'{fmt.upper()} (*.{ext})'
            )
            if not fp:
                return

            if not fp.lower().endswith(f'.{ext}'):
                fp = os.path.splitext(fp)[0] + f'.{ext}'

            # Sync hidden sidebar widgets so settings persistence works
            self.dpi_spin.blockSignals(True)
            self.dpi_spin.setValue(dpi)
            self.dpi_spin.blockSignals(False)
            _fi = self._export_fmt_combo.findText(fmt.upper())
            if _fi >= 0:
                self._export_fmt_combo.blockSignals(True)
                self._export_fmt_combo.setCurrentIndex(_fi)
                self._export_fmt_combo.blockSignals(False)

            # Build a fresh Figure at the exact export size — never touches the screen figure
            exp_fig = MplFigure(figsize=(wi, hi), dpi=dpi)
            exp_fig.patch.set_facecolor(self.chart_bg_color)

            # Re-run plotting on a fresh export figure via the shared renderer
            # so the exported image matches the on-screen preview exactly.
            chart_font = self.title_font.currentText()
            _old_font = matplotlib.rcParams.get('font.family', ['sans-serif'])
            matplotlib.rcParams['font.family'] = chart_font

            axes_list, ax2_map, is3d, n = self._render_axes(exp_fig)

            # Apply margins — convert physical-unit spinbox values to fractions
            _ml, _mr, _mb, _mt = self._margins_as_fractions()
            _n_sp_exp = self.subplot_rows * self.subplot_cols
            _exp_title_raw = self.title_input.text().strip()
            # For a single subplot, fall back to the placeholder just like the preview does.
            if not _exp_title_raw and _n_sp_exp == 1:
                _exp_title_raw = self.title_input.placeholderText()
            _exp_title_text = _latex_safe(_exp_title_raw)
            _exp_tx_frac, _exp_ty_frac = self._title_pos_as_fractions()
            if self.title_check.isChecked() and _exp_title_text:
                suptitle_pt = self.title_size.value()
                # title_y positions the suptitle text; do not clamp exp_top by it.
                exp_fig.suptitle(_exp_title_text,
                                 fontsize=suptitle_pt, color=self.title_color,
                                 fontfamily=self.title_font.currentText(),
                                 x=_exp_tx_frac,
                                 ha=self.title_ha.currentText(),
                                 rotation=self.title_rotation.value(),
                                 va='top',
                                 y=_exp_ty_frac)
            _hspace_exp = self.sp_hspace.value() if hasattr(self, 'sp_hspace') else 0.35
            _wspace_exp = self.sp_wspace.value() if hasattr(self, 'sp_wspace') else 0.35
            exp_fig.subplots_adjust(
                left=_ml, right=_mr,
                bottom=_mb, top=_mt,
                hspace=_hspace_exp,
                wspace=_wspace_exp,
            )

            # Replay annotations (text / arrow / image) onto the export axes.
            # The export figure is built fresh, so annotations drawn on the
            # live canvas must be re-created here or they are lost from the file.
            # Must run after subplots_adjust so axes limits/positions are final.
            if not is3d:
                try:
                    self.canvas.draw_annotations_on(axes_list)
                except Exception:
                    traceback.print_exc()

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

