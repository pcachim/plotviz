"""
Copyright (c) 2026 Paulo Cachim
ui/python_export.py  –  plotviz

PythonExportMixin: _export_python_bundle()
Generates a .pvizx zip that contains:
  - plot.py        standalone matplotlib script (no plotviz dependency)
  - data/          one CSV per dataset used
  - README.md      quick-start instructions
"""

from __future__ import annotations
import io, json, os, textwrap, zipfile
from PyQt6.QtWidgets import QFileDialog, QMessageBox

# ── Chart-type → code-generation function ─────────────────────────────────────
# Each generator receives (settings, series_list, datasets, palette) and returns
# a list of code-line strings that go inside the axes setup block.



def _esc(s):
    """Escape a string for embedding in a Python string literal."""
    return str(s).replace('\\', '\\\\').replace("'", "\\'")


# Context flag set by generate_plot_script before invoking any generator so that
# module-level generator functions emit the correct column reference style even
# when datasets have different lengths (multi-CSV mode).
_USE_COMBINED: bool = True


def _col_ref(col, use_combined=None, datasets=None):
    """Return a Python expression to reference a dataset column.

    When all columns share the same length (use_combined=True) they are read
    into a single combined ``df``, so we emit ``df['col']``.
    When columns differ in length each is in its own ``_df_<safe>`` frame and
    we emit ``_df_<safe>['col']`` to avoid NaN-padding from pd.concat.
    """
    uc = _USE_COMBINED if use_combined is None else use_combined
    if uc or datasets is None:
        return f"df['{_esc(col)}']"
    safe = col.replace(' ', '_').replace('-', '_')
    return f"_df_{safe}['{_esc(col)}']"


def _color(palette, i):
    return f"'{palette[i % len(palette)]}'"


def _series_style(settings, series, i, palette):
    """Return resolved style properties for one series.

    Prefers curve_styles[label] stored in settings; falls back to palette index.
    """
    lbl   = series.get("label", f"Series {i+1}")
    curve = (settings.get("curve_styles") or {}).get(lbl, {})
    color = curve.get("color") or palette[i % len(palette)]
    return {
        "color":         color,
        "linestyle":     curve.get("linestyle",   "-"),
        "linewidth":     curve.get("linewidth",    1.5),
        "marker":        curve.get("marker",      "None"),
        "markersize":    curve.get("markersize",   6),
        "marker_color":  curve.get("marker_color") or color,
        "scatter_alpha": settings.get("scatter_alpha", 0.6),
        "area_alpha":    settings.get("area_alpha",    0.35),
    }



def _gen_line_scatter_step_stem_area_errorbar(settings, series, datasets, palette, ax_var):
    lines = []
    chart_type = settings.get('chart_type', 'Line')

    # ── Bar chart-level options (injected from subplot_chart_opts by generate_plot_script) ──
    bar_ymin_col = settings.get('_bar_ymin_col', '')
    bar_stacked  = settings.get('bar_stacked',  False)
    bar_horiz    = settings.get('bar_horizontal', False)

    # Emit stacking state initialisation once, before the per-series loop,
    # so every bar series in this subplot can share the running-bottom vars.
    bar_any = any(s.get('series_type', chart_type) == 'Bar' for s in series)
    _range_mode = bool(bar_ymin_col and bar_ymin_col in datasets)
    if bar_stacked and bar_any and not _range_mode:
        lines += [
            "_bar_cat_bots = {}   # accumulated bottom per category (stacked bars)",
            "_bar_num_bots = None  # accumulated bottom array (numeric stacked bars)",
        ]

    for i, s in enumerate(series):
        xc, yc = s.get('x_col', ''), s.get('y_col', '')
        lbl = _esc(s.get('label', f'Series {i+1}'))
        ct  = s.get('series_type', chart_type)
        if not yc:
            continue
        st  = _series_style(settings, s, i, palette)
        col = f"'{st['color']}'"
        ls  = st['linestyle']
        lw  = st['linewidth']
        mk  = st['marker']
        ms  = st['markersize']
        mkc = f"'{st['marker_color']}'"
        sal = st['scatter_alpha']
        aal = st['area_alpha']
        xexpr = _col_ref(xc) if xc else f'range(len({_col_ref(yc)}))'
        yexpr = _col_ref(yc)

        mk_arg  = f", marker='{mk}', markersize={ms}, markerfacecolor={mkc}" if mk not in ('None', '', None) else ''
        if ct == 'Line':
            lines.append(f"{ax_var}.plot({xexpr}, {yexpr}, label='{lbl}', color={col}, linestyle='{ls}', linewidth={lw}{mk_arg})")
        elif ct == 'Scatter':
            lines.append(f"{ax_var}.scatter({xexpr}, {yexpr}, label='{lbl}', color={col}, alpha={sal}, s={ms**2})")
        elif ct == 'Bar':
            # Resolve per-series bar opts (fall back to chart-level values from settings)
            curve_opts = ((settings.get('curve_styles') or {}).get(s.get('label', '')) or {}).get('opts', {})
            b_w  = curve_opts.get('bar_width',    settings.get('bar_width',    0.8))
            b_al = curve_opts.get('bar_alpha',    settings.get('bar_alpha',    1.0))
            b_ec = curve_opts.get('bar_edgecolor', settings.get('bar_edgecolor', 'none'))
            b_hor = curve_opts.get('bar_horizontal', bar_horiz)
            b_stk = curve_opts.get('bar_stacked',  bar_stacked)
            ec_kw = f", edgecolor='{_esc(b_ec)}'" if b_ec != 'none' else ''

            if _range_mode:
                # ── Range-bar mode: each bar spans ymin_col (bottom) → y_col (top) ──
                ymin_expr = _col_ref(bar_ymin_col)
                lines.append(f"# Range bar: '{lbl}' — bottom='{_esc(bar_ymin_col)}', top=y column")
                lines.append(f"_rb_n   = min(len(list({xexpr})), len({yexpr}), len({ymin_expr}))")
                lines.append(f"_rb_x   = list({xexpr})[:_rb_n]")
                lines.append(f"_rb_bot = np.asarray(list({ymin_expr}), dtype=float)[:_rb_n]")
                lines.append(f"_rb_h   = np.asarray(list({yexpr}),    dtype=float)[:_rb_n] - _rb_bot")
                if b_hor:
                    lines.append(
                        f"{ax_var}.barh(_rb_x, _rb_h, height={b_w}, left=_rb_bot, "
                        f"label='{lbl}', color={col}, alpha={b_al}{ec_kw})")
                else:
                    lines.append(
                        f"{ax_var}.bar(_rb_x, _rb_h, width={b_w}, bottom=_rb_bot, "
                        f"label='{lbl}', color={col}, alpha={b_al}{ec_kw})")

            elif b_stk:
                # ── Stacked mode: accumulate running bottom across series ──
                lines.append(f"# Stacked bar: '{lbl}'")
                lines.append(f"_bs_x = list({xexpr})")
                lines.append(f"_bs_y = list({yexpr})")
                lines.append(f"_bs_n = min(len(_bs_x), len(_bs_y))")
                lines.append(f"_bs_x, _bs_y = _bs_x[:_bs_n], _bs_y[:_bs_n]")
                lines.append(f"_bs_is_cat = isinstance(_bs_x[0], str) if _bs_x else False")
                lines.append(f"if _bs_is_cat:")
                lines.append(f"    _bs_bot = [_bar_cat_bots.get(str(v), 0.0) for v in _bs_x]")
                if b_hor:
                    lines.append(
                        f"    {ax_var}.barh(_bs_x, _bs_y, height={b_w}, left=_bs_bot, "
                        f"label='{lbl}', color={col}, alpha={b_al}{ec_kw})")
                else:
                    lines.append(
                        f"    {ax_var}.bar(_bs_x, _bs_y, width={b_w}, bottom=_bs_bot, "
                        f"label='{lbl}', color={col}, alpha={b_al}{ec_kw})")
                lines.append(f"    for _bv, _by in zip(_bs_x, _bs_y): _bar_cat_bots[str(_bv)] = _bar_cat_bots.get(str(_bv), 0.0) + float(_by)")
                lines.append(f"else:")
                lines.append(f"    _bs_xf = np.asarray(_bs_x, dtype=float)")
                lines.append(f"    _bs_yf = np.asarray(_bs_y, dtype=float)")
                lines.append(f"    if _bar_num_bots is None: _bar_num_bots = np.zeros(len(_bs_xf))")
                lines.append(f"    elif len(_bar_num_bots) < len(_bs_xf): _bar_num_bots = np.concatenate([_bar_num_bots, np.zeros(len(_bs_xf) - len(_bar_num_bots))])")
                if b_hor:
                    lines.append(
                        f"    {ax_var}.barh(_bs_xf, _bs_yf, height={b_w}, left=_bar_num_bots[:len(_bs_yf)], "
                        f"label='{lbl}', color={col}, alpha={b_al}{ec_kw})")
                else:
                    lines.append(
                        f"    {ax_var}.bar(_bs_xf, _bs_yf, width={b_w}, bottom=_bar_num_bots[:len(_bs_yf)], "
                        f"label='{lbl}', color={col}, alpha={b_al}{ec_kw})")
                lines.append(f"    _bar_num_bots[:len(_bs_yf)] += _bs_yf")

            elif b_hor:
                # ── Horizontal bars ──
                lines.append(
                    f"{ax_var}.barh({xexpr}, {yexpr}, height={b_w}, "
                    f"label='{lbl}', color={col}, alpha={b_al}{ec_kw})")
            else:
                # ── Normal vertical bars ──
                lines.append(
                    f"{ax_var}.bar({xexpr}, {yexpr}, width={b_w}, "
                    f"label='{lbl}', color={col}, alpha={b_al}{ec_kw})")
        elif ct == 'Area':
            lines.append(f"{ax_var}.fill_between({xexpr}, {yexpr}, label='{lbl}', color={col}, alpha={aal})")
        elif ct == 'Fill Between':
            curve_opts  = ((settings.get('curve_styles') or {}).get(s.get('label', '')) or {}).get('opts', {})
            fb_al       = curve_opts.get('fill_between_alpha',   settings.get('fill_between_alpha',   0.4))
            fb_lw       = curve_opts.get('fill_between_lw',      settings.get('fill_between_lw',      0.8))
            fb_showline = curve_opts.get('fill_between_showline', settings.get('fill_between_showline', True))
            y2_col      = curve_opts.get('fill_between_y2_col') or settings.get('_fill_y2_col', '')
            if y2_col and y2_col in datasets:
                y2expr = _col_ref(y2_col)
                lines.append(f"# Fill Between: '{lbl}' vs '{y2_col}'")
                lines.append(f"{ax_var}.fill_between({xexpr}, {yexpr}, {y2expr}, label='{lbl}', color={col}, alpha={fb_al})")
                if fb_showline:
                    lines.append(f"{ax_var}.plot({xexpr}, {yexpr}, color={col}, lw={fb_lw}, alpha=0.8)")
                    lines.append(f"{ax_var}.plot({xexpr}, {y2expr}, color={col}, lw={fb_lw}, alpha=0.8)")
            else:
                lines.append(f"# Fill Between: '{lbl}' vs y=0")
                lines.append(f"{ax_var}.fill_between({xexpr}, 0, {yexpr}, label='{lbl}', color={col}, alpha={fb_al})")
                if fb_showline:
                    lines.append(f"{ax_var}.plot({xexpr}, {yexpr}, color={col}, lw={fb_lw}, alpha=0.8)")
        elif ct == 'Step':
            lines.append(f"{ax_var}.step({xexpr}, {yexpr}, label='{lbl}', color={col}, linewidth={lw}, where='mid')")
        elif ct == 'Stem':
            lines.append(f"markerline, stemlines, baseline = {ax_var}.stem({xexpr}, {yexpr}, label='{lbl}')")
            lines.append(f"plt.setp(stemlines, color={col}, linewidth={lw}); plt.setp(markerline, color={col})")
        elif ct == 'Errorbar':
            lines.append(f"{ax_var}.errorbar({xexpr}, {yexpr}, fmt='o', label='{lbl}', color={col}, linewidth={lw})")
        elif ct == 'Bubble':
            lines.append(f"{ax_var}.scatter({xexpr}, {yexpr}, label='{lbl}', color={col}, alpha={sal})")
        elif ct == 'Waterfall':
            pos_c = settings.get('waterfall_pos_color', '#2ecc71')
            neg_c = settings.get('waterfall_neg_color', '#e74c3c')
            wf_w  = settings.get('waterfall_width', 0.8)
            wf_al = settings.get('waterfall_alpha', 0.85)
            lines.append(f"# Waterfall: '{lbl}'")
            lines.append(f"_wf_x = list({xexpr})")
            lines.append(f"_wf_y = list({yexpr})")
            lines.append(f"_wf_n = min(len(_wf_x), len(_wf_y))")
            lines.append(f"_wf_x, _wf_y = _wf_x[:_wf_n], _wf_y[:_wf_n]")
            lines.append(f"_wf_is_cat = isinstance(_wf_x[0], str) if _wf_x else False")
            lines.append(f"_running = 0.0")
            lines.append(f"for _wi, _wv in enumerate(_wf_y):")
            lines.append(f"    _fc = {repr(pos_c)} if _wv >= 0 else {repr(neg_c)}")
            lines.append(f"    _xi = _wi if _wf_is_cat else _wf_x[_wi]")
            lines.append(f"    {ax_var}.bar(_xi, _wv, bottom=_running, width={wf_w}, color=_fc, edgecolor='white', linewidth=0.5, alpha={wf_al}, label=('{lbl}' if _wi == 0 else '_nolegend_'))")
            lines.append(f"    _running += _wv")
            lines.append(f"if _wf_is_cat:")
            lines.append(f"    {ax_var}.set_xticks(range(len(_wf_x)))")
            lines.append(f"    {ax_var}.set_xticklabels(_wf_x, rotation=45, ha='right')")
        else:
            lines.append(f"{ax_var}.plot({xexpr}, {yexpr}, label='{lbl}', color={col}, linestyle='{ls}', linewidth={lw}{mk_arg})")
    return lines


def _gen_histogram(settings, series, datasets, palette, ax_var):
    lines = []
    bins      = settings.get('hist_bins', 20)
    histtype  = settings.get('hist_histtype', 'bar')
    orient    = settings.get('hist_orientation', 'vertical')
    alpha     = settings.get('heat_alpha', 0.7)
    edgecolor = settings.get('hist_edgecolor', 'white')
    for i, s in enumerate(series):
        yc  = s.get('y_col', '')
        lbl = _esc(s.get('label', f'Series {i+1}'))
        st  = _series_style(settings, s, i, palette)
        col = f"'{st['color']}'"
        if yc:
            lines.append(
                f"{ax_var}.hist({_col_ref(yc)}.dropna(), bins={bins}, label='{lbl}', "
                f"color={col}, alpha={alpha}, histtype='{_esc(histtype)}', "
                f"orientation='{_esc(orient)}', edgecolor='{_esc(edgecolor)}')"
            )
    return lines


def _gen_boxplot(settings, series, datasets, palette, ax_var):
    cols  = [s.get('y_col','') for s in series if s.get('y_col','')]
    lbls  = [s.get('label', c) for s, c in zip(series, cols)]
    exprs = [_col_ref(c) + '.dropna()' for c in cols]
    if not exprs:
        return []
    return [
        f"_bx_data = [{', '.join(exprs)}]",
        f"{ax_var}.boxplot(_bx_data, labels={[_esc(l) for l in lbls]!r})",
    ]


def _gen_violin(settings, series, datasets, palette, ax_var):
    cols  = [s.get('y_col','') for s in series if s.get('y_col','')]
    lbls  = [s.get('label', c) for s, c in zip(series, cols)]
    exprs = [_col_ref(c) + '.dropna()' for c in cols]
    if not exprs:
        return []
    return [
        f"_vl_data = [{', '.join(exprs)}]",
        f"_vl = {ax_var}.violinplot(_vl_data, showmeans=True, showmedians=True)",
        f"{ax_var}.set_xticks(range(1, len({lbls!r}) + 1)); {ax_var}.set_xticklabels({[_esc(l) for l in lbls]!r})",
    ]


def _gen_pie(settings, series, datasets, palette, ax_var):
    lines = []
    if series:
        s   = series[0]
        xc  = s.get('x_col', '')
        yc  = s.get('y_col', '')
        if yc:
            lblexpr      = f"{_col_ref(xc)}.astype(str)" if xc else 'None'
            autopct      = "'%1.1f%%'" if settings.get('pie_autopct', True) else 'None'
            shadow       = settings.get('pie_shadow', False)
            startangle   = settings.get('pie_startangle', 90.0)
            labeldist    = settings.get('pie_labeldistance', 1.1)
            pctdist      = settings.get('pie_pctdistance', 0.6)
            donut        = settings.get('pie_donut', False)
            explode_first = settings.get('pie_explode_first', False)
            wedge_arg    = ", wedgeprops={'width': 0.5}" if donut else ''
            # Build colors list: look up each x-label in curve_styles, fall back to palette
            curve_styles = settings.get('curve_styles', {})
            x_vals = list(datasets.get(xc, [])) if xc and datasets else []
            if x_vals:
                colors = [curve_styles.get(str(v), {}).get('color') or palette[i % len(palette)]
                          for i, v in enumerate(x_vals)]
                colors_arg = f", colors={colors!r}"
            else:
                colors_arg = ''
            # explode: runtime because slice count comes from data
            if explode_first:
                lines.append(f"_pie_n = len({_col_ref(yc)})")
                lines.append(f"_pie_explode = [0.08] + [0.0] * (_pie_n - 1)")
                explode_arg = ", explode=_pie_explode"
            else:
                explode_arg = ''
            lines.append(
                f"{ax_var}.pie({_col_ref(yc)}, labels={lblexpr}, autopct={autopct}, "
                f"shadow={shadow}, startangle={startangle}, "
                f"labeldistance={labeldist}, pctdistance={pctdist}"
                f"{colors_arg}{explode_arg}{wedge_arg})"
            )
            lines.append(f"{ax_var}.axis('equal')")
    return lines


def _gen_polar(settings, series, datasets, palette, ax_var):
    lines = [f"# Note: polar axes require projection='polar' — see fig.add_subplot below"]
    for i, s in enumerate(series):
        xc = s.get('x_col', '')
        yc = s.get('y_col', '')
        lbl = _esc(s.get('label', f'Series {i+1}'))
        st  = _series_style(settings, s, i, palette)
        col = f"'{st['color']}'"
        lw  = st['linewidth']
        ls  = st['linestyle']
        if xc and yc:
            lines.append(f"{ax_var}.plot({_col_ref(xc)}, {_col_ref(yc)}, label='{lbl}', color={col}, linestyle='{ls}', linewidth={lw})")
    return lines


def _gen_heatmap(settings, series, datasets, palette, ax_var):
    # Bug 6: the old implementation generated a df.corr() correlation heatmap, which is
    # completely different from what plot_engine renders (Z column on a regular grid via imshow).
    # Fix 1: use scipy.interpolate.griddata for correct scatter-point reconstruction.
    zc = settings.get('_z_col', '')
    if not zc:
        return [f"# Heatmap: assign a Z column in plotviz to render."]
    cmap    = settings.get('cmap', 'rainbow')
    alpha   = settings.get('heat_alpha', 1.0)
    interp  = settings.get('heat_interpolation', 'nearest')
    show_cb = settings.get('heat_colorbar', True)
    pin_range = settings.get('heat_vminmax_enable', False)
    vmin_v  = settings.get('heat_vmin', 0.0)
    vmax_v  = settings.get('heat_vmax', 1.0)
    lines = [
        f"from scipy.interpolate import griddata as _griddata",
        f"import numpy as np",
    ]
    if series:
        s0 = series[0]
        xc = s0.get('x_col', '')
        yc = s0.get('y_col', '')
        if xc and yc:
            lines += [
                f"_hx = np.array({_col_ref(xc)}, dtype=float)",
                f"_hy = np.array({_col_ref(yc)}, dtype=float)",
                f"_hz = np.array({_col_ref(zc)}, dtype=float)",
                f"_hmn = min(len(_hx), len(_hy), len(_hz)); _hx, _hy, _hz = _hx[:_hmn], _hy[:_hmn], _hz[:_hmn]",
                f"_hn = max(2, int(np.ceil(np.sqrt(_hmn))))",
                f"_hxi = np.linspace(_hx.min(), _hx.max(), _hn)",
                f"_hyi = np.linspace(_hy.min(), _hy.max(), _hn)",
                f"_hXI, _hYI = np.meshgrid(_hxi, _hyi)",
                f"_hZ = _griddata((_hx, _hy), _hz, (_hXI, _hYI), method='linear')",
                f"_hZ = np.where(np.isnan(_hZ), np.nanmean(_hz), _hZ)",
                f"_hext = [float(_hx.min()), float(_hx.max()), float(_hy.min()), float(_hy.max())]",
            ]
            vm_str = f", vmin={vmin_v}, vmax={vmax_v}" if pin_range else ""
            lines.append(
                f"_him = {ax_var}.imshow(_hZ, aspect='auto', cmap='{_esc(cmap)}', "
                f"origin='lower', alpha={alpha}, interpolation='{_esc(interp)}', extent=_hext{vm_str})"
            )
        else:
            lines += [
                f"_hz = np.array({_col_ref(zc)}, dtype=float)",
                f"_hn = max(2, int(np.ceil(np.sqrt(len(_hz)))))",
                f"_hZ = np.full((_hn, _hn), np.nan)",
                f"for _hk in range(len(_hz)): _hZ[_hk // _hn, _hk % _hn] = _hz[_hk]",
            ]
            vm_str = f", vmin={vmin_v}, vmax={vmax_v}" if pin_range else ""
            lines.append(
                f"_him = {ax_var}.imshow(_hZ, aspect='auto', cmap='{_esc(cmap)}', "
                f"origin='lower', alpha={alpha}, interpolation='{_esc(interp)}'{vm_str})"
            )
    if show_cb:
        lines.append(f"plt.colorbar(_him, ax={ax_var})")
    return lines
def _gen_contour(settings, series, datasets, palette, ax_var):
    # Bug 7: was hardcoding levels=15, cmap='coolwarm' and ignoring all user settings.
    # Fix 1: use griddata for correct scatter reconstruction (dead import removed).
    # Fix 4: vmin/vmax support. Fix 5: line colour/width. Fix 6: explicit levels list.
    lines = []
    if series:
        s = series[0]
        xc = s.get('x_col', '')
        yc = s.get('y_col', '')
        zc = settings.get('_z_col', '')   # top-level z from series_meta
        if xc and yc and zc:
            # Fix 6: explicit levels list overrides integer count
            lvl_explicit = settings.get('contour_levels_explicit', '').strip()
            if lvl_explicit:
                try:
                    lvl = [float(v) for v in lvl_explicit.split(',') if v.strip()]
                except ValueError:
                    lvl = settings.get('contour_levels', 10)
            else:
                lvl = settings.get('contour_levels', 10)
            cmap    = settings.get('cmap', 'rainbow')
            alpha   = settings.get('heat_alpha', 1.0)
            filled  = settings.get('heat_filled_contour', True)
            lines_  = settings.get('heat_contour_lines', True)
            show_cb = settings.get('heat_colorbar', True)
            # Fix 5: contour line colour/width
            line_color = settings.get('contour_line_color', '#000000')
            line_width = settings.get('contour_line_width', 0.5)
            # Fix 4: vmin/vmax
            pin_range = settings.get('heat_vminmax_enable', False)
            vmin_v  = settings.get('heat_vmin', 0.0)
            vmax_v  = settings.get('heat_vmax', 1.0)
            vm_str  = f", vmin={vmin_v}, vmax={vmax_v}" if pin_range else ""
            lines += [
                f"from scipy.interpolate import griddata as _griddata",
                f"import numpy as np",
                f"_cx = np.array({_col_ref(xc)}, dtype=float)",
                f"_cy = np.array({_col_ref(yc)}, dtype=float)",
                f"_cz = np.array({_col_ref(zc)}, dtype=float)",
                f"_cmn = min(len(_cx), len(_cy), len(_cz)); _cx, _cy, _cz = _cx[:_cmn], _cy[:_cmn], _cz[:_cmn]",
                f"_cn = max(2, int(np.ceil(np.sqrt(_cmn))))",
                f"_cxi = np.linspace(_cx.min(), _cx.max(), _cn)",
                f"_cyi = np.linspace(_cy.min(), _cy.max(), _cn)",
                f"_cX, _cY = np.meshgrid(_cxi, _cyi)",
                f"_cZ = _griddata((_cx, _cy), _cz, (_cX, _cY), method='linear')",
                f"_cZ = np.where(np.isnan(_cZ), np.nanmean(_cz), _cZ)",
                f"_last_cm = None",
            ]
            if filled:
                lines.append(
                    f"_cf = {ax_var}.contourf(_cX, _cY, _cZ, levels={lvl}, "
                    f"cmap='{_esc(cmap)}', alpha={alpha}{vm_str})"
                )
                lines.append(f"_last_cm = _cf")
            if lines_:
                lines.append(
                    f"_cs = {ax_var}.contour(_cX, _cY, _cZ, levels={lvl}, "
                    f"colors='{_esc(line_color)}', linewidths={line_width}, alpha=0.5)"
                )
                lines.append(f"_last_cm = _last_cm if _last_cm is not None else _cs")
            if show_cb:
                lines.append(f"if _last_cm is not None: plt.colorbar(_last_cm, ax={ax_var})")
        else:
            lines.append(f"# Contour: assign X, Y and Z columns in plotviz to render.")
    return lines
def _gen_tricontour(settings, series, datasets, palette, ax_var):
    # Bug 7: was hardcoding levels=10, cmap='rainbow' and ignoring all user settings.
    lines = []
    if series:
        s = series[0]
        xc = s.get('x_col', '')
        yc = s.get('y_col', '')
        zc = settings.get('_z_col', '')
        if xc and yc and zc:
            lvl       = settings.get('tri_levels', 10)
            cmap      = settings.get('tri_cmap', 'rainbow')
            alpha     = settings.get('tri_alpha', 1.0)
            fill_mode = settings.get('tri_fill_mode', 'Filled contour')
            # Backward compat: old saves used boolean tri_filled / tri_tripcolor
            if fill_mode not in ('Filled contour', 'Face colours', 'None'):
                if settings.get('tri_tripcolor', False):
                    fill_mode = 'Face colours'
                elif settings.get('tri_filled', True):
                    fill_mode = 'Filled contour'
                else:
                    fill_mode = 'None'
            tri_lines = settings.get('tri_lines', True)
            triplot   = settings.get('tri_triplot', False)
            show_cb   = settings.get('tri_colorbar', True)
            lines += [
                f"import numpy as np",
                f"_tx = np.array({_col_ref(xc)}, dtype=float)",
                f"_ty = np.array({_col_ref(yc)}, dtype=float)",
                f"_tz = np.array({_col_ref(zc)}, dtype=float)",
                f"_tn = min(len(_tx), len(_ty), len(_tz)); _tx, _ty, _tz = _tx[:_tn], _ty[:_tn], _tz[:_tn]",
                f"_last_tm = None",
            ]
            if fill_mode == 'Face colours':
                lines.append(
                    f"_tc = {ax_var}.tripcolor(_tx, _ty, _tz, cmap='{_esc(cmap)}', alpha={alpha})"
                )
                lines.append(f"_last_tm = _tc")
            elif fill_mode == 'Filled contour':
                lines.append(
                    f"_tcf = {ax_var}.tricontourf(_tx, _ty, _tz, levels={lvl}, "
                    f"cmap='{_esc(cmap)}', alpha={alpha})"
                )
                lines.append(f"_last_tm = _tcf")
            if tri_lines:
                lines.append(
                    f"_tcs = {ax_var}.tricontour(_tx, _ty, _tz, levels={lvl}, "
                    f"colors='k', linewidths=0.5, alpha=0.5)"
                )
                lines.append(f"_last_tm = _last_tm if _last_tm is not None else _tcs")
            if triplot:
                lines.append(
                    f"{ax_var}.triplot(_tx, _ty, color='k', linewidth=0.4, alpha=0.5)"
                )
            if show_cb:
                lines.append(f"if _last_tm is not None: plt.colorbar(_last_tm, ax={ax_var})")
        else:
            lines.append(f"# Tricontour: assign X, Y and Z columns in plotviz to render.")
    return lines


def _gen_surface3d(settings, series, datasets, palette, ax_var):
    # Fix 3: was hardcoding cmap='viridis', alpha=0.9 and ignoring surf_stride / surf_wireframe.
    # Fix 1: now uses griddata (matching the live renderer) instead of a different approach.
    # Fix 7: honours heat_colorbar.
    lines = [
        f"# Note: 3D Surface requires projection='3d' — see fig.add_subplot below",
        f"from scipy.interpolate import griddata as _griddata",
        f"import numpy as np",
    ]
    if series:
        s0 = series[0]
        xc = s0.get('x_col', '')
        yc = s0.get('y_col', '')
        zc = settings.get('_z_col', '')   # top-level z from series_meta
        if xc and yc and zc:
            cmap      = settings.get('cmap', 'rainbow')
            alpha     = settings.get('heat_alpha', 1.0)
            stride    = settings.get('surf_stride', 1)
            wireframe = settings.get('surf_wireframe', False)
            show_cb   = settings.get('heat_colorbar', True)
            lines += [
                f"_sx = np.array({_col_ref(xc)}, dtype=float)",
                f"_sy = np.array({_col_ref(yc)}, dtype=float)",
                f"_sz = np.array({_col_ref(zc)}, dtype=float)",
                f"_smn = min(len(_sx), len(_sy), len(_sz)); _sx, _sy, _sz = _sx[:_smn], _sy[:_smn], _sz[:_smn]",
                f"_sn = max(2, int(np.ceil(np.sqrt(_smn))))",
                f"_sxi = np.linspace(_sx.min(), _sx.max(), _sn)",
                f"_syi = np.linspace(_sy.min(), _sy.max(), _sn)",
                f"_sX, _sY = np.meshgrid(_sxi, _syi)",
                f"_sZ = _griddata((_sx, _sy), _sz, (_sX, _sY), method='linear')",
                f"_sZ = np.where(np.isnan(_sZ), np.nanmean(_sz), _sZ)",
            ]
            if wireframe:
                lines.append(
                    f"{ax_var}.plot_wireframe(_sX, _sY, _sZ, rstride={stride}, cstride={stride}, alpha={alpha})"
                )
            else:
                lines.append(
                    f"_ssurf = {ax_var}.plot_surface(_sX, _sY, _sZ, cmap='{_esc(cmap)}', "
                    f"alpha={alpha}, rstride={stride}, cstride={stride})"
                )
                if show_cb:
                    lines.append(f"plt.colorbar(_ssurf, ax={ax_var}, shrink=0.5, aspect=10)")
        else:
            lines.append(f"# 3D Surface: assign X, Y and Z columns in plotviz to render.")
    return lines
def _gen_ecdf(settings, series, datasets, palette, ax_var):
    lines = []
    for i, s in enumerate(series):
        yc  = s.get('y_col', '')
        lbl = _esc(s.get('label', f'Series {i+1}'))
        st  = _series_style(settings, s, i, palette)
        col = f"'{st['color']}'"
        lw  = st['linewidth']
        if yc:
            lines += [
                f"_ecdf_d = np.sort({_col_ref(yc)}.dropna())",
                f"_ecdf_y = np.arange(1, len(_ecdf_d)+1) / len(_ecdf_d)",
                f"{ax_var}.plot(_ecdf_d, _ecdf_y, label='{lbl}', color={col}, linewidth={lw})",
            ]
    return lines


def _gen_hist2d_hexbin(settings, series, datasets, palette, ax_var):
    # Bug 20: was hardcoding gridsize=30, bins=30, cmap='viridis' and always adding a colorbar.
    lines = []
    ct = settings.get('chart_type', 'Hist2D')
    if series:
        s = series[0]
        xc, yc = s.get('x_col',''), s.get('y_col','')
        if xc and yc:
            if ct == 'Hexbin':
                gridsize = settings.get('hexbin_gridsize', 20)
                cmap     = settings.get('hexbin_cmap', 'viridis')
                alpha    = settings.get('hexbin_alpha', 1.0)
                show_cb  = settings.get('hexbin_colorbar', True)
                lines.append(
                    f"_hb = {ax_var}.hexbin({_col_ref(xc)}, {_col_ref(yc)}, "
                    f"gridsize={gridsize}, cmap='{_esc(cmap)}', alpha={alpha})"
                )
                if show_cb:
                    lines.append(f"plt.colorbar(_hb, ax={ax_var})")
            else:  # Hist2D
                bins_x  = settings.get('hist2d_bins_x', 20)
                bins_y  = settings.get('hist2d_bins_y', 20)
                cmap    = settings.get('hist2d_cmap', 'viridis')
                alpha   = settings.get('hist2d_alpha', 1.0)
                log     = settings.get('hist2d_log', False)
                show_cb = settings.get('hist2d_colorbar', True)
                norm_arg = ", norm=matplotlib.colors.LogNorm()" if log else ""
                lines += [
                    f"import matplotlib",
                    f"_, _, _, _h2img = {ax_var}.hist2d({_col_ref(xc)}, {_col_ref(yc)}, "
                    f"bins=[{bins_x}, {bins_y}], cmap='{_esc(cmap)}', alpha={alpha}{norm_arg})",
                ]
                if show_cb:
                    lines.append(f"plt.colorbar(_h2img, ax={ax_var})")
    return lines


def _gen_quiver(settings, series, datasets, palette, ax_var):
    lines = []
    if series:
        s = series[0]
        xc, yc = s.get('x_col',''), s.get('y_col','')
        uc = settings.get('quiver_u_col', '(none)')
        vc = settings.get('quiver_v_col', '(none)')
        if xc and yc and uc != '(none)' and vc != '(none)':
            sc    = settings.get('quiver_scale', 1.0)
            width = settings.get('quiver_width', 0.005)
            color_by_mag = settings.get('quiver_color_by_mag', False)
            cmap  = settings.get('quiver_cmap', 'viridis')
            # Truncate all four arrays to their common minimum length,
            # mirroring the plot engine's n = min(len(xd), len(yd), len(U), len(V)).
            lines.append(f"_qx = {_col_ref(xc)}.values.astype(float)")
            lines.append(f"_qy = {_col_ref(yc)}.values.astype(float)")
            lines.append(f"_qU = {_col_ref(uc)}.values.astype(float)")
            lines.append(f"_qV = {_col_ref(vc)}.values.astype(float)")
            lines.append(f"_qn = min(len(_qx), len(_qy), len(_qU), len(_qV))")
            lines.append(f"_qx, _qy, _qU, _qV = _qx[:_qn], _qy[:_qn], _qU[:_qn], _qV[:_qn]")
            scale_kw = f', scale={sc}, scale_units="xy"' if sc != 1.0 else ''
            if color_by_mag:
                lines.append(f"{ax_var}.quiver(_qx, _qy, _qU, _qV, np.hypot(_qU, _qV)"
                             f", cmap='{_esc(cmap)}', width={width}, alpha=0.85{scale_kw})")
            else:
                lines.append(f"{ax_var}.quiver(_qx, _qy, _qU, _qV"
                             f", width={width}, alpha=0.85{scale_kw})")
        elif xc and yc:
            lines.append(f"# Quiver: set U/V columns in app; shown as placeholder")
            lines.append(f"# {ax_var}.quiver({_col_ref(xc)}, {_col_ref(yc)}, U, V)")
    return lines


def _gen_barbs(settings, series, datasets, palette, ax_var):
    lines = []
    if series:
        s = series[0]
        xc, yc = s.get('x_col',''), s.get('y_col','')
        uc = settings.get('barbs_u_col', '(none)')
        vc = settings.get('barbs_v_col', '(none)')
        if xc and yc and uc != '(none)' and vc != '(none)':
            length = settings.get('barbs_length', 7.0)
            pivot  = settings.get('barbs_pivot',  'tip')
            alpha  = settings.get('barbs_alpha',  0.85)
            color_by_mag = settings.get('barbs_color_by_mag', False)
            cmap   = settings.get('barbs_cmap', 'viridis')
            # Truncate to common minimum length
            lines.append(f"_bx = {_col_ref(xc)}.values.astype(float)")
            lines.append(f"_by = {_col_ref(yc)}.values.astype(float)")
            lines.append(f"_bU = {_col_ref(uc)}.values.astype(float)")
            lines.append(f"_bV = {_col_ref(vc)}.values.astype(float)")
            lines.append(f"_bn = min(len(_bx), len(_by), len(_bU), len(_bV))")
            lines.append(f"_bx, _by, _bU, _bV = _bx[:_bn], _by[:_bn], _bU[:_bn], _bV[:_bn]")
            if color_by_mag:
                lines.append(f"_bmag = np.hypot(_bU, _bV)")
                lines.append(f"{ax_var}.barbs(_bx, _by, _bU, _bV, _bmag"
                             f", cmap='{_esc(cmap)}', length={length}, pivot='{pivot}', alpha={alpha})")
            else:
                lines.append(f"{ax_var}.barbs(_bx, _by, _bU, _bV"
                             f", length={length}, pivot='{pivot}', alpha={alpha})")
        elif xc and yc:
            lines.append(f"# Barbs: set U/V columns in app")
            lines.append(f"# {ax_var}.barbs({_col_ref(xc)}, {_col_ref(yc)}, U, V)")
    return lines


def _gen_streamplot(settings, series, datasets, palette, ax_var):
    lines = []
    if series:
        s = series[0]
        xc, yc = s.get('x_col',''), s.get('y_col','')
        uc = settings.get('stream_u_col', '(none)')
        vc = settings.get('stream_v_col', '(none)')
        if xc and yc and uc != '(none)' and vc != '(none)':
            density      = settings.get('stream_density',   1.0)
            arrowsize    = settings.get('stream_arrowsize', 1.0)
            linewidth    = settings.get('stream_linewidth', 1.5)
            color_by_mag = settings.get('stream_color_by_mag', False)
            cmap         = settings.get('stream_cmap', 'viridis')
            # Truncate to common minimum length then re-grid onto a 2-D mesh.
            # streamplot() requires 1-D xs/ys axes and (ny, nx) U/V grids.
            lines.append(f"_sf = {_col_ref(xc)}.values.astype(float)")
            lines.append(f"_sg = {_col_ref(yc)}.values.astype(float)")
            lines.append(f"_sU = {_col_ref(uc)}.values.astype(float)")
            lines.append(f"_sV = {_col_ref(vc)}.values.astype(float)")
            lines.append(f"_sn = min(len(_sf), len(_sg), len(_sU), len(_sV))")
            lines.append(f"_sf, _sg, _sU, _sV = _sf[:_sn], _sg[:_sn], _sU[:_sn], _sV[:_sn]")
            lines.append(f"_xs, _ys = np.unique(_sf), np.unique(_sg)")
            lines.append(f"_UG = np.zeros((len(_ys), len(_xs)))")
            lines.append(f"_VG = np.zeros((len(_ys), len(_xs)))")
            lines.append(f"_xi = np.searchsorted(_xs, _sf)")
            lines.append(f"_yi = np.searchsorted(_ys, _sg)")
            lines.append(f"for _k in range(_sn):")
            lines.append(f"    if _xi[_k] < len(_xs) and _yi[_k] < len(_ys):")
            lines.append(f"        _UG[_yi[_k], _xi[_k]] = _sU[_k]")
            lines.append(f"        _VG[_yi[_k], _xi[_k]] = _sV[_k]")
            if color_by_mag:
                # When coloring by magnitude, matplotlib requires color= to be a
                # 2-D array and must not receive linewidth at the same time.
                lines.append(f"_speed = np.sqrt(_UG**2 + _VG**2)")
                lines.append(f"{ax_var}.streamplot(_xs, _ys, _UG, _VG"
                             f", color=_speed, cmap='{_esc(cmap)}'"
                             f", density={density}, arrowsize={arrowsize})")
            else:
                lines.append(f"{ax_var}.streamplot(_xs, _ys, _UG, _VG"
                             f", density={density}, arrowsize={arrowsize}, linewidth={linewidth})")
        elif xc and yc:
            lines.append(f"# Streamplot: set U/V columns and build 2-D grids")
    return lines


def _gen_radar(settings, series, datasets, palette, ax_var):
    lines = [
        f"import numpy as np",
        f"_rad_cols = [c for c in df.columns if df[c].dtype.kind in 'iuf'][:8]",
        f"_rad_N = len(_rad_cols)",
        f"_rad_angles = np.linspace(0, 2*np.pi, _rad_N, endpoint=False).tolist()",
        f"_rad_angles += _rad_angles[:1]",
    ]
    for i, s in enumerate(series):
        lbl = _esc(s.get('label', f'Series {i+1}'))
        st  = _series_style(settings, s, i, palette)
        col = f"'{st['color']}'"
        lines += [
            f"_rad_vals_{i} = df[_rad_cols].iloc[{i}].tolist() if {i} < len(df) else [0]*_rad_N",
            f"_rad_vals_{i} += _rad_vals_{i}[:1]",
            f"{ax_var}.plot(_rad_angles, _rad_vals_{i}, color={col}, label='{lbl}')",
            f"{ax_var}.fill(_rad_angles, _rad_vals_{i}, alpha=0.1, color={col})",
        ]
    lines += [
        f"{ax_var}.set_xticks(_rad_angles[:-1])",
        f"{ax_var}.set_xticklabels(_rad_cols)",
    ]
    return lines


_GENERATORS = {
    'Line':       _gen_line_scatter_step_stem_area_errorbar,
    'Scatter':    _gen_line_scatter_step_stem_area_errorbar,
    'Bar':        _gen_line_scatter_step_stem_area_errorbar,
    'Errorbar':   _gen_line_scatter_step_stem_area_errorbar,
    'Area':       _gen_line_scatter_step_stem_area_errorbar,
    'Step':       _gen_line_scatter_step_stem_area_errorbar,
    'Stem':       _gen_line_scatter_step_stem_area_errorbar,
    'Bubble':     _gen_line_scatter_step_stem_area_errorbar,
    'Waterfall':  _gen_line_scatter_step_stem_area_errorbar,
    'Histogram':  _gen_histogram,
    'Hist2D':     _gen_hist2d_hexbin,
    'Hexbin':     _gen_hist2d_hexbin,
    'Boxplot':    _gen_boxplot,
    'Violin':     _gen_violin,
    'Pie':        _gen_pie,
    'Polar':      _gen_polar,
    'Radar':      _gen_radar,
    'Heatmap':      _gen_heatmap,
    'Contour':      _gen_contour,
    'Tricontour':   _gen_tricontour,
    '3D Surface':   _gen_surface3d,
    'ECDF':       _gen_ecdf,
    'Quiver':     _gen_quiver,
    'Barbs':      _gen_barbs,
    'Streamplot': _gen_streamplot,
}

_3D_TYPES    = {'3D Surface'}
_POLAR_TYPES = {'Polar', 'Radar'}


def _legend_call(settings, idx, ax_var):
    """Return a fully-qualified ax.legend(...) line for subplot `idx`,
    mirroring exactly what plot_engine._legend_kwargs() produces."""
    # idx can be int or str key — normalise to str for settings dicts
    k = str(idx)
    loc        = (settings.get('subplot_legend_locs') or {}).get(k, 'best')
    lx         = (settings.get('subplot_legend_x')    or {}).get(k, 0.01)
    ly         = (settings.get('subplot_legend_y')    or {}).get(k, 0.99)
    fontsize   = (settings.get('subplot_legend_fontsize')  or {}).get(k, 9)
    ncols      = (settings.get('subplot_legend_ncols')     or {}).get(k, 1)
    frameon    = (settings.get('subplot_legend_frameon')   or {}).get(k, True)
    facecolor  = (settings.get('subplot_legend_facecolor') or {}).get(k, '#ffffff')
    edgecolor  = (settings.get('subplot_legend_edgecolor') or {}).get(k, '#cccccc')
    framealpha = (settings.get('subplot_legend_alpha')     or {}).get(k, 0.8)
    labelcolor = (settings.get('subplot_legend_color')     or {}).get(k, '#000000')

    common = (f"fontsize={fontsize}, ncols={ncols}, frameon={frameon}, "
              f"facecolor='{_esc(facecolor)}', edgecolor='{_esc(edgecolor)}', "
              f"framealpha={framealpha}, labelcolor='{_esc(labelcolor)}'")

    if loc == 'best':
        return f"{ax_var}.legend(loc='best', {common})"
    else:
        real_loc = 'upper left' if loc == 'manual' else loc
        return f"{ax_var}.legend(loc='{_esc(real_loc)}', bbox_to_anchor=({lx}, {ly}), {common})"


def _projection_for(ct):
    if ct in _3D_TYPES:    return "'3d'"
    if ct in _POLAR_TYPES: return "'polar'"
    return 'None'


def _gen_annotations(settings, n_subplots):
    """Emit code that reproduces text / arrow / image annotations.

    Mirrors canvas.redraw_annotations(). Honours the per-subplot visibility
    toggle (subplot_ann_visible). Image annotations are loaded from
    images/<basename> relative to the generated plot.py.
    """
    anns = settings.get('annotations') or []
    if not anns:
        return []

    vis = settings.get('subplot_ann_visible') or {}

    def _visible(idx):
        return vis.get(str(idx), vis.get(idx, True))

    def _ax_name(idx):
        return 'ax' if n_subplots == 1 else f'ax{idx}'

    lines = ["", "# ── Annotations ──────────────────────────────────────────────────"]
    if any(a.get('type') == 'image' for a in anns):
        lines += [
            "import matplotlib.image as _mpimg",
            "from matplotlib.offsetbox import OffsetImage, AnnotationBbox",
            "_HERE = os.path.dirname(os.path.abspath(__file__))",
        ]
    for a in anns:
        idx = a.get('axes_index', 0)
        if n_subplots == 1 and idx != 0:
            continue
        if not _visible(idx):
            continue
        axn = _ax_name(idx)
        s = a.get('style', {}) or {}
        fs = s.get('fontsize', 10)
        fc = _esc(s.get('fontcolor', '#000000'))
        ff = _esc(s.get('fontfamily', 'sans-serif'))
        t = a.get('type')
        if t == 'text':
            if s.get('bg_alpha', 0.9) == 0:
                bbox = "None"
            else:
                bbox = ("dict(boxstyle='round,pad=0.3', facecolor='%s', "
                        "edgecolor='%s', alpha=%s)" % (
                            _esc(s.get('bg_color', '#ffffcc')),
                            _esc(s.get('edge_color', '#aaaaaa')),
                            s.get('bg_alpha', 0.9)))
            lines.append(
                f"{axn}.annotate('{_esc(a.get('label', ''))}', "
                f"xy=({a['x']!r}, {a['y']!r}), xytext=({a['x']!r}, {a['y']!r}), "
                f"fontsize={fs}, color='{fc}', fontfamily='{ff}', "
                f"bbox={bbox}, zorder=50, annotation_clip=False)")
        elif t == 'arrow':
            lines.append(
                f"{axn}.annotate('{_esc(a.get('label', ''))}', "
                f"xy=({a['x1']!r}, {a['y1']!r}), xytext=({a['x0']!r}, {a['y0']!r}), "
                f"fontsize={fs}, color='{fc}', "
                f"arrowprops=dict(arrowstyle='->', color='{fc}', lw=1.8), "
                f"zorder=50, annotation_clip=False)")
        elif t == 'image':
            imgfile = a.get('image_file', '')
            lines += [
                "try:",
                f"    _img = _mpimg.imread(os.path.join(_HERE, {imgfile!r}))",
                f"    _ib = OffsetImage(_img, zoom={a.get('zoom', 0.15)})",
                f"    _ab = AnnotationBbox(_ib, ({a['x']!r}, {a['y']!r}), frameon=True, "
                "bboxprops=dict(edgecolor='#aaaaaa', linewidth=1.0), zorder=50, "
                "annotation_clip=False)",
                f"    {axn}.add_artist(_ab)",
                "except Exception as _e:",
                "    print('Image annotation error:', _e)",
            ]
    return lines


def generate_plot_script(settings: dict, series_meta: dict,
                         datasets: dict, palette: list[str],
                         chart_title: str) -> str:
    """
    Build a complete standalone Python script that reproduces the chart
    using matplotlib only (no plotviz dependency).
    """
    series_list = series_meta.get('series', [])
    ct          = settings.get('chart_type', 'Line')
    rows        = settings.get('subplot_rows', 1)
    cols_       = settings.get('subplot_cols', 1)
    n_subplots  = rows * cols_
    title_text  = settings.get('title_text', chart_title) or chart_title
    bg_color    = settings.get('chart_bg_color', '#ffffff')

    # Inject top-level z/err columns so generators can access them via settings
    settings = dict(settings)
    settings['_z_col']       = series_meta.get('z_col', '')
    settings['_err_col']     = series_meta.get('err_col', '')
    settings['_fill_y2_col'] = series_meta.get('fill_y2_col', '')
    settings['_bar_ymin_col'] = series_meta.get('bar_ymin_col', '')
    # subplot_chart_types lives in series_meta, not settings — merge it in
    if not settings.get('subplot_chart_types'):
        settings['subplot_chart_types'] = series_meta.get('subplot_chart_types', {})
    # per-subplot z columns (if stored separately)
    if not settings.get('subplot_z_cols'):
        settings['subplot_z_cols'] = series_meta.get('subplot_z_cols', {})
    # U/V column assignments for quiver, barbs, and streamplot live in series_meta
    # (set from UI combos in _collect_series_meta, not _collect_settings).
    # Merge them into settings so the generator functions can read them.
    for _uv_key in ('quiver_u_col', 'quiver_v_col',
                    'barbs_u_col',  'barbs_v_col',
                    'stream_u_col', 'stream_v_col'):
        if _uv_key in series_meta:
            settings[_uv_key] = series_meta[_uv_key]
    # Per-subplot chart opts (bar_stacked, bar_horizontal, bar_width, bar_alpha,
    # bar_edgecolor, etc.) are stored in series_meta['subplot_chart_opts'].
    # For single-subplot charts, flatten subplot 0's opts into settings so
    # generators can read them as plain keys.  For multi-subplot, they are merged
    # per-subplot into sub_settings below.
    _all_sp_chart_opts = series_meta.get('subplot_chart_opts', {})
    if n_subplots == 1:
        _sp0 = _all_sp_chart_opts.get('0', _all_sp_chart_opts.get(0, {}))
        for _k, _v in _sp0.items():
            settings.setdefault(_k, _v)

    # ── Collect dataset filenames ──────────────────────────────────────────────
    used_cols = {s.get('x_col') for s in series_list} | {s.get('y_col') for s in series_list}
    used_cols.discard('')
    used_cols.discard(None)
    ds_names  = sorted(datasets.keys())
    # All datasets go into data/ as CSVs; build a combined CSV if they share length
    lengths = {len(v) for v in datasets.values() if v is not None}
    use_combined = len(lengths) == 1   # all same length → one CSV

    # Propagate use_combined to the module-level _col_ref so every generator
    # function (which closes over the module scope) emits the correct reference.
    global _USE_COMBINED
    _USE_COMBINED = use_combined

    # ── Imports ───────────────────────────────────────────────────────────────
    lines = [
        "#!/usr/bin/env python3",
        '"""',
        f'Auto-generated by plotviz — standalone matplotlib chart script.',
        f'Chart: {title_text}',
        '"""',
        "",
        "import os",
        "import numpy as np",
        "import pandas as pd",
        "import matplotlib",
        "import matplotlib.pyplot as plt",
        "from matplotlib.figure import Figure",
        "",
        "# ── Data loading ─────────────────────────────────────────────────────",
    ]

    if use_combined:
        lines += [
            "_here = os.path.dirname(os.path.abspath(__file__))",
            "df = pd.read_csv(os.path.join(_here, 'data', 'data.csv'))",
            "",
        ]
    else:
        lines += [
            "_here = os.path.dirname(os.path.abspath(__file__))",
            "# Each dataset is in its own CSV file in the data/ folder.",
            "# They are loaded into individual series; combine as needed.",
        ]
        for col in ds_names:
            safe_var = col.replace(' ', '_').replace('-', '_')
            lines.append(f"_df_{safe_var} = pd.read_csv(os.path.join(_here, 'data', '{col}.csv'))")
        lines += [
            "# Build a combined df from all single-column frames for convenience:",
            "df = pd.concat([" +
                ", ".join(f"_df_{c.replace(' ','_').replace('-','_')}" for c in ds_names) +
                "], axis=1)",
            "",
        ]

    # ── Figure size (convert serialised value to inches) ──────────────────────
    fig_unit = settings.get('fig_unit', 'cm')
    fig_w_raw = settings.get('fig_width',  20.0)
    fig_h_raw = settings.get('fig_height', 15.0)
    _dpi = settings.get('dpi', 300)   # always read; only emitted for pixel-unit figures
    if fig_unit == 'cm':
        fig_w = fig_w_raw / 2.54
        fig_h = fig_h_raw / 2.54
    elif fig_unit == 'pixels':
        fig_w = fig_w_raw / _dpi
        fig_h = fig_h_raw / _dpi
    else:  # inches
        fig_w, fig_h = fig_w_raw, fig_h_raw
    fig_w = round(max(fig_w, 4.0), 2)
    fig_h = round(max(fig_h, 3.0), 2)
    # For pixel-unit figures emit dpi= so the rendered pixel dimensions match the app.
    _figsize_dpi = f', dpi={_dpi}' if fig_unit == 'pixels' else ''
    lines += [
        "# ── Figure ───────────────────────────────────────────────────────────",
        f"fig = plt.figure(figsize=({fig_w:.1f}, {fig_h:.1f}){_figsize_dpi})",
        f"fig.patch.set_facecolor('{_esc(bg_color)}')",
        "",
    ]

    # ── Subplots ──────────────────────────────────────────────────────────────
    if n_subplots == 1:
        proj = _projection_for(ct)
        lines += [
            f"ax = fig.add_subplot(111{',' if proj != 'None' else ''}{'projection=' + proj if proj != 'None' else ''})",
            f"ax.set_facecolor('{_esc(bg_color)}')",
            "",
            "# ── Plot ──────────────────────────────────────────────────────────",
        ]
        gen = _GENERATORS.get(ct, _gen_line_scatter_step_stem_area_errorbar)
        plot_lines = gen(settings, series_list, datasets, palette, 'ax')
        lines += plot_lines
        lines += [
            "",
            "# ── Decoration ───────────────────────────────────────────────────",
        ]
        xl = settings.get('subplot_xlabels', {}).get('0', '')
        yl = settings.get('subplot_ylabels', {}).get('0', '')
        if xl: lines.append(f"ax.set_xlabel('{_esc(xl)}')")
        if yl: lines.append(f"ax.set_ylabel('{_esc(yl)}')")
        sp_title = (settings.get('sp_titles') or {}).get('0', '')
        if sp_title: lines.append(f"ax.set_title('{_esc(sp_title)}')")
        lines.append(_legend_call(settings, 0, 'ax'))
    else:
        subplot_types = settings.get('subplot_chart_types') or {}
        mosaic = settings.get('subplot_mosaic')

        if mosaic is not None:
            # ── Mosaic layout ─────────────────────────────────────────────────
            seen_order = list(dict.fromkeys(c for row in mosaic for c in row))
            n_mosaic   = len(seen_order)
            lines.append(f"# Mosaic layout: {mosaic!r}")
            lines.append(f"_ax_dict = fig.subplot_mosaic({mosaic!r})")
            for ki, key in enumerate(seen_order):
                lines.append(f"ax{ki} = _ax_dict[{key!r}]")
                lines.append(f"ax{ki}.set_facecolor('{_esc(bg_color)}')")
            lines.append("")
            lines.append("# ── Per-subplot plotting ─────────────────────────────────")
            for idx in range(n_mosaic):
                sub_ct     = subplot_types.get(str(idx), ct)
                sub_series = [s for s in series_list if s.get('plot_num', 1) == idx + 1]
                ax_var     = f"ax{idx}"
                sub_z      = (settings.get('subplot_z_cols') or {}).get(str(idx), '')
                if not sub_z:
                    sub_z = settings.get('_z_col', '') if sub_ct in ('Contour', 'Tricontour', '3D Surface', 'Hist2D', 'Hexbin') else ''
                sub_settings = dict(settings)
                sub_settings['chart_type'] = sub_ct
                sub_settings['_z_col']     = sub_z
                # Merge per-subplot chart opts (bar_stacked, bar_horizontal, etc.)
                _sp_opts = _all_sp_chart_opts.get(str(idx), _all_sp_chart_opts.get(idx, {}))
                for _k, _v in _sp_opts.items():
                    sub_settings.setdefault(_k, _v)
                lines.append(f"# Subplot {idx+1} ({seen_order[idx]}): {sub_ct}")
                gen = _GENERATORS.get(sub_ct, _gen_line_scatter_step_stem_area_errorbar)
                for l in gen(sub_settings, sub_series, datasets, palette, ax_var):
                    lines.append(l)
                sp_title = settings.get('sp_titles', {}).get(str(idx), f'Subplot {idx+1}')
                xl = settings.get('subplot_xlabels', {}).get(str(idx), '')
                yl = settings.get('subplot_ylabels', {}).get(str(idx), '')
                if sp_title: lines.append(f"{ax_var}.set_title('{_esc(sp_title)}')")
                if xl: lines.append(f"{ax_var}.set_xlabel('{_esc(xl)}')")
                if yl: lines.append(f"{ax_var}.set_ylabel('{_esc(yl)}')")
                lines.append(_legend_call(settings, idx, ax_var))
                lines.append("")
        else:
            # ── Regular grid layout ───────────────────────────────────────────
            lines.append(f"axes = []")
            for idx in range(n_subplots):
                sub_ct = subplot_types.get(str(idx), ct)
                proj   = _projection_for(sub_ct)
                proj_arg = f", projection={proj}" if proj != 'None' else ''
                lines.append(f"ax{idx} = fig.add_subplot({rows}, {cols_}, {idx+1}{proj_arg})")
                lines.append(f"ax{idx}.set_facecolor('{_esc(bg_color)}')")
                lines.append(f"axes.append(ax{idx})")
            lines.append("")
            lines.append("# ── Per-subplot plotting ─────────────────────────────────")
            for idx in range(n_subplots):
                sub_ct      = subplot_types.get(str(idx), ct)
                sub_series  = [s for s in series_list if s.get('plot_num', 1) == idx + 1]
                ax_var      = f"ax{idx}"
                sub_z       = (settings.get('subplot_z_cols') or {}).get(str(idx), '')
                if not sub_z:
                    sub_z = settings.get('_z_col', '') if sub_ct in ('Contour', 'Tricontour', '3D Surface', 'Hist2D', 'Hexbin') else ''
                sub_settings = dict(settings)
                sub_settings['chart_type'] = sub_ct
                sub_settings['_z_col']     = sub_z
                # Merge per-subplot chart opts (bar_stacked, bar_horizontal, etc.)
                _sp_opts = _all_sp_chart_opts.get(str(idx), _all_sp_chart_opts.get(idx, {}))
                for _k, _v in _sp_opts.items():
                    sub_settings.setdefault(_k, _v)
                lines.append(f"# Subplot {idx+1}: {sub_ct}")
                gen = _GENERATORS.get(sub_ct, _gen_line_scatter_step_stem_area_errorbar)
                for l in gen(sub_settings, sub_series, datasets, palette, ax_var):
                    lines.append(l)
                sp_title = settings.get('sp_titles', {}).get(str(idx), f'Subplot {idx+1}')
                if sp_title: lines.append(f"{ax_var}.set_title('{_esc(sp_title)}')")
                lines.append(_legend_call(settings, idx, ax_var))
                lines.append("")

    # ── Annotations (text / arrow / image) ─────────────────────────────────────
    lines += _gen_annotations(settings, n_subplots)

    # ── Final touches ─────────────────────────────────────────────────────────
    hspace = settings.get('sp_hspace', 0.35)
    wspace = settings.get('sp_wspace', 0.35)
    # Figure-level title (suptitle)
    title_show  = settings.get('title_show', True)
    title_font  = settings.get('title_font', 'sans-serif')
    title_size  = settings.get('title_size', 14)
    title_color = settings.get('title_color', '#000000')
    # title_x/title_y stored as physical units (fig_unit) since v2.5.8;
    # divide by the fig dimension in that same unit to get fractions [0,1].
    _tx_raw = settings.get('title_x', 0.5)
    _ty_raw = settings.get('title_y', 0.98)
    if settings.get('title_pos_format') == 'physical' and fig_w_raw > 0 and fig_h_raw > 0:
        title_x = _tx_raw / fig_w_raw
        title_y = _ty_raw / fig_h_raw
    else:
        title_x, title_y = _tx_raw, _ty_raw   # old save: already fractions
    suptitle_lines = []
    if title_show and title_text:
        suptitle_lines = [
            f"fig.suptitle('{_esc(title_text)}', "
            f"fontsize={title_size}, "
            f"fontfamily='{_esc(title_font)}', "
            f"color='{_esc(title_color)}', "
            f"x={title_x:.4f}, y={title_y:.4f})",
        ]
    # When there is a suptitle, reserve space at the top for it so that
    # tight_layout() does not push subplot content over the title.
    # We derive the top rect from title_y — subtract a small font-height margin.
    if title_show and title_text:
        font_frac = (title_size / 72) / fig_h * 1.8   # approx line height as fig fraction
        tight_top = min(title_y - font_frac, 0.96)
        tight_layout_line = f"plt.tight_layout(rect=[0, 0, 1, {tight_top:.3f}])"
    else:
        tight_layout_line = "plt.tight_layout()"
    lines += [
        "",
        "# ── Layout ───────────────────────────────────────────────────────────",
    ] + suptitle_lines + [
        f"fig.subplots_adjust(hspace={hspace}, wspace={wspace})",
        tight_layout_line,
        "plt.show()",
        "",
    ]
    return "\n".join(lines)


def _build_readme(chart_title: str, datasets: dict, n_subplots: int) -> str:
    return textwrap.dedent(f"""\
    # {chart_title} — Python Export

    This bundle was exported from **plotviz** and contains a standalone
    matplotlib script that reproduces your chart without needing plotviz.

    ## Contents

    | File | Description |
    |------|-------------|
    | `plot.py` | Standalone Python script |
    | `data/` | CSV files with the chart datasets |
    | `README.md` | This file |

    ## Requirements

        pip install matplotlib numpy pandas scipy

    ## Running

        python plot.py

    The script loads data from the `data/` folder relative to its own location,
    so keep `plot.py` and `data/` together.

    ## Datasets ({len(datasets)} column(s))

    {"".join(f"- `{k}` ({len(v)} rows){chr(10)}" for k, v in datasets.items())}

    ## Subplots

    This chart has **{n_subplots}** subplot(s).

    ---
    *Generated by plotviz*
    """)


def generate_sns_plot_script(explorer, chart_name: str, datasets: dict) -> str:
    """
    Build a complete standalone seaborn script for the given chart type,
    mirroring the current SeabornExplorer widget state.
    """

    def _esc(s):
        return str(s).replace('\\', '\\\\').replace("'", "\\'")

    def _col(combo):
        """Return (array, col_name) from a combo, or (None, '') if unset."""
        if combo is None:
            return None, ''
        txt = combo.currentText()
        if not txt or txt == '(none)' or txt not in datasets:
            return None, ''
        return datasets[txt], txt

    def _color():
        pal = explorer._sns_palette()
        return repr(pal[0]) if pal else "'steelblue'"

    lengths = {len(v) for v in datasets.values() if v is not None}
    use_combined = len(lengths) == 1

    # ── Header + imports ──────────────────────────────────────────────────────
    lines = [
        '#!/usr/bin/env python3',
        '"""',
        f'Auto-generated by plotviz Seaborn Explorer — {chart_name} chart.',
        '"""',
        '',
        'import os',
        'import numpy as np',
        'import pandas as pd',
        'import matplotlib.pyplot as plt',
        'import seaborn as sns',
        '',
        '# ── Data loading ─────────────────────────────────────────────────────',
        "_here = os.path.dirname(os.path.abspath(__file__))",
    ]

    if use_combined:
        lines += [
            "df = pd.read_csv(os.path.join(_here, 'data', 'data.csv'))",
        ]
    else:
        col_names = list(datasets.keys())
        for col in col_names:
            safe = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in col)
            lines.append(
                f"_s_{safe} = pd.read_csv(os.path.join(_here, 'data', '{safe}.csv'))['{_esc(col)}']"
            )
        lines += [
            "df = pd.concat([" +
            ", ".join(
                f"_s_{''.join(c if c.isalnum() or c in '-_.' else '_' for c in col)}.rename('{_esc(col)}')"
                for col in col_names
            ) + "], axis=1)",
        ]

    lines += ['', '# ── Plot ─────────────────────────────────────────────────────']

    _, xn = _col(explorer._x_combo)
    _, yn = _col(explorer._y_combo)
    col   = _color()

    if chart_name == 'KDE':
        lines += [
            'fig, ax = plt.subplots()',
            f'sns.kdeplot(',
            f"    x=df['{_esc(yn)}'].astype(float), ax=ax,",
            f'    fill={explorer._kde_fill.isChecked()},',
            f'    alpha={explorer._kde_alpha.value()},',
            f'    linewidth={explorer._kde_lw.value()},',
            f'    bw_adjust={explorer._kde_bw.value()},',
            f'    cumulative={explorer._kde_cumul.isChecked()},',
            f'    common_norm={explorer._kde_common.isChecked()},',
            f'    color={col},',
            ')',
            f"ax.set_xlabel('{_esc(yn)}'); ax.set_ylabel('Density')",
        ]

    elif chart_name == 'Regression':
        lowess = explorer._reg_lowess.isChecked()
        robust = explorer._reg_robust.isChecked()
        order  = 1 if (lowess or robust) else explorer._reg_order.value()
        ci_val = None if (lowess or robust) else (explorer._reg_ci.value() or None)
        lines += [
            'fig, ax = plt.subplots()',
            'sns.regplot(',
            f"    x=df['{_esc(xn)}'].astype(float), y=df['{_esc(yn)}'].astype(float), ax=ax,",
            f'    scatter_kws={{"s": {explorer._reg_size.value()}, "alpha": {explorer._reg_alpha.value()}}},',
            f'    line_kws={{"linewidth": 1.8}},',
            f'    ci={repr(ci_val)},',
            f'    order={order}, robust={robust}, lowess={lowess},',
            f'    scatter={explorer._reg_scatter.isChecked()},',
            f'    color={col},',
            ')',
            f"ax.set_xlabel('{_esc(xn)}'); ax.set_ylabel('{_esc(yn)}')",
        ]

    elif chart_name == 'Strip':
        lines += [
            f"df['_x'] = df['{_esc(xn)}'].astype(str) if df['{_esc(xn)}'].dtype.kind not in 'biufc' else df['{_esc(xn)}'].copy()",
            'fig, ax = plt.subplots()',
            "sns.stripplot(data=df, x='_x', y='" + _esc(yn) + "', ax=ax,",
            f'    color={col},',
            f'    size={explorer._strip_size.value()},',
            f'    alpha={explorer._strip_alpha.value()},',
            f'    jitter={explorer._strip_jitter.value()},',
            ')',
            f"ax.set_xlabel('{_esc(xn)}'); ax.set_ylabel('{_esc(yn)}')",
        ]

    elif chart_name == 'Swarm':
        lines += [
            f"df['_x'] = df['{_esc(xn)}'].astype(str) if df['{_esc(xn)}'].dtype.kind not in 'biufc' else df['{_esc(xn)}'].copy()",
            'fig, ax = plt.subplots()',
            "sns.swarmplot(data=df, x='_x', y='" + _esc(yn) + "', ax=ax,",
            f'    color={col},',
            f'    size={explorer._swarm_size.value()},',
            f'    alpha={explorer._swarm_alpha.value()},',
            ')',
            f"ax.set_xlabel('{_esc(xn)}'); ax.set_ylabel('{_esc(yn)}')",
        ]

    elif chart_name == 'Heatmap':
        fmt = explorer._heat_fmt.currentText()
        num_cols = list(datasets.keys())
        lines += [
            f'_cols = {repr(num_cols)}',
            'corr = df[_cols].corr()',
            'fig, ax = plt.subplots(figsize=(max(6, len(_cols)), max(5, len(_cols))))',
            'sns.heatmap(corr, ax=ax,',
            f'    cmap={repr(explorer._heat_cmap.currentText())},',
            f'    annot={explorer._heat_annot.isChecked()},',
            f'    fmt={repr(fmt) if explorer._heat_annot.isChecked() else repr("")},',
            f'    linewidths={explorer._heat_lw.value()},',
            f'    square={explorer._heat_square.isChecked()},',
            f'    cbar={explorer._heat_cbar.isChecked()},',
            f'    robust={explorer._heat_robust.isChecked()},',
            ')',
            "ax.set_title('Correlation Heatmap', fontsize=11, pad=8)",
        ]

    elif chart_name == 'Pairplot':
        num_cols = list(datasets.keys())
        _pair_hue_name = explorer._hue_combo.currentText()
        _pair_hue = None if _pair_hue_name in ('', '(none)') else _pair_hue_name
        _pair_pal_name = explorer._sns_palette_name()
        _pair_pal = _pair_pal_name if _pair_pal_name else repr(explorer._sns_palette(len(num_cols)))
        _pair_hue_lines = []
        if _pair_hue and _pair_hue in datasets:
            _pair_hue_lines = [
                f"df[{repr(_pair_hue)}] = df[{repr(_pair_hue)}].astype(str)",
            ]
        lines += _pair_hue_lines + [
            f'_cols = {repr(num_cols)}',
            'pg = sns.pairplot(df[_cols' + (f' + [{repr(_pair_hue)}]' if _pair_hue else '') + '],',
            f'    hue={repr(_pair_hue)},',
            f'    diag_kind={repr(explorer._pair_diag.currentText())},',
            f'    kind={repr(explorer._pair_kind.currentText())},',
            f'    palette={repr(_pair_pal_name) if _pair_pal_name else _pair_pal},',
            f'    plot_kws={{"alpha": {explorer._pair_alpha.value()}}},',
            ')',
            'fig = pg.figure',
        ]

    elif chart_name == 'Joint':
        lines += [
            'jg = sns.jointplot(',
            f"    x=df['{_esc(xn)}'].astype(float), y=df['{_esc(yn)}'].astype(float),",
            f'    kind={repr(explorer._joint_kind.currentText())},',
            f'    ratio={explorer._joint_ratio.value()},',
            f'    marginal_kws={{"fill": {explorer._joint_margkde.isChecked()}}},',
            f'    alpha={explorer._joint_alpha.value()},',
            f'    color={col},',
            ')',
            f"jg.set_axis_labels('{_esc(xn)}', '{_esc(yn)}')",
            'fig = jg.figure',
        ]

    elif chart_name == 'Catplot':
        kind   = explorer._cat_kind.currentText()
        ci_str = explorer._cat_ci.currentText()
        if ci_str in ('95', '99'):
            eb = f"('ci', {ci_str})"
        elif ci_str == 'sd':
            eb = "'sd'"
        else:
            eb = 'None'
        _cat_pal_name = explorer._sns_palette_name()
        _cat_pal_line = (
            f'    palette={repr(_cat_pal_name)},'
            if _cat_pal_name else
            f'    palette={repr(explorer._sns_palette(10))},'
        )
        lines += [
            f"df['_x'] = df['{_esc(xn)}'].astype(str)",
            "fg = sns.catplot(",
            f"    data=df, x='_x', y='{_esc(yn)}',",
            f'    kind={repr(kind)},',
            _cat_pal_line,
            f'    alpha={explorer._cat_alpha.value()},',
            f'    saturation={explorer._cat_sat.value()},',
        ]
        if kind in ('bar', 'point'):
            lines.append(f'    errorbar={eb},')
        lines += [
            ')',
            f"fg.set_axis_labels('{_esc(xn)}', '{_esc(yn)}')",
            'fig = fg.figure',
        ]

    else:
        lines += ['fig, ax = plt.subplots()', "ax.set_title('No chart type matched')"]

    lines += ['', 'plt.tight_layout()', 'plt.show()', '']
    return '\n'.join(lines)



def _build_pyproject_toml(chart_title: str, script: str) -> str:
    """Generate a pyproject.toml with dependencies inferred from the script."""
    import re
    safe_name = re.sub(r'[^a-z0-9]+', '-', chart_title.lower()).strip('-') or 'plotviz-chart'

    deps = [
        'matplotlib>=3.7',
        'numpy>=1.24',
        'pandas>=2.0',
    ]
    if 'scipy' in script:
        deps.append('scipy>=1.10')
    if 'seaborn' in script:
        deps.append('seaborn>=0.12')

    deps_toml = '\n'.join(f'    "{d}",' for d in deps)

    return f'''[project]
name = "{safe_name}"
version = "1.0.0"
description = "Standalone chart script exported from plotviz"
requires-python = ">=3.10"
dependencies = [
{deps_toml}
]

[project.scripts]
run = "plot:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
# Run with: uv run plot.py
'''


class PythonExportMixin:
    """Mixin that adds _export_python_bundle() to PlotVizApp."""

    def _export_python_bundle(self):
        """Export a .pvizx zip: plot.py + data CSVs + README."""
        import csv as _csv
        import numpy as np

        # ── Collect state ──────────────────────────────────────────────────────
        settings    = self._collect_settings()
        # Annotations (text / arrow / image) are not part of _collect_settings();
        # add them so the generated script can reproduce them.
        settings['annotations'] = self._collect_annotations_meta()
        series_meta = self._collect_series_meta()
        series_list = series_meta.get('series', [])

        # Determine which columns are used
        used_cols: set[str] = set()
        for s in series_list:
            for k in ('x_col', 'y_col'):
                c = s.get(k, '')
                if c and c in self.datasets:
                    used_cols.add(c)
        for attr in ('combo_z', 'combo_err', 'combo_bar_ymin'):
            cb = getattr(self, attr, None)
            if cb:
                txt = cb.currentText()
                if txt and txt != '(none)' and txt in self.datasets:
                    used_cols.add(txt)
        # U/V columns for quiver, barbs, and streamplot live in series_meta,
        # not in the series rows — add them so they are written to the CSV.
        for _uv_key in ('quiver_u_col', 'quiver_v_col',
                        'barbs_u_col',  'barbs_v_col',
                        'stream_u_col', 'stream_v_col'):
            c = series_meta.get(_uv_key, '')
            if c and c != '(none)' and c in self.datasets:
                used_cols.add(c)
        # Fall back to all columns if nothing is explicitly assigned
        export_cols = used_cols if used_cols else set(self.datasets.keys())
        datasets_to_export = {k: self.datasets[k] for k in export_cols if k in self.datasets}

        # ── Palette ────────────────────────────────────────────────────────────
        palette = [self._palette_color(i) for i in range(16)]

        # ── Chart title for filename ───────────────────────────────────────────
        chart_title = (settings.get('title_text') or
                       getattr(self, '_current_filepath', None) and
                       os.path.splitext(os.path.basename(self._current_filepath))[0] or
                       'chart')

        # ── File dialog ────────────────────────────────────────────────────────
        from ui.helpers import _get_dir, _remember_dir
        _stem = (os.path.splitext(os.path.basename(self._current_filepath))[0]
                 if getattr(self, '_current_filepath', None) else chart_title or 'untitled')
        fp, _ = QFileDialog.getSaveFileName(
            self, 'Export Python Bundle', os.path.join(_get_dir(), _stem + '.pvizx'),
            'plotviz Python Bundle (*.pvizx);;All Files (*)')
        if not fp:
            return
        _remember_dir(fp)
        if not fp.endswith('.pvizx'):
            fp += '.pvizx'

        try:
            # ── Generate script ────────────────────────────────────────────────
            n_subplots = settings.get('subplot_rows', 1) * settings.get('subplot_cols', 1)
            script = generate_plot_script(
                settings, series_meta, datasets_to_export, palette, chart_title)

            # ── Build CSVs ─────────────────────────────────────────────────────
            lengths   = {len(v) for v in datasets_to_export.values() if v is not None}
            use_combined = len(lengths) == 1

            with zipfile.ZipFile(fp, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('plot.py', script)
                zf.writestr('README.md', _build_readme(chart_title, datasets_to_export, n_subplots))
                zf.writestr('pyproject.toml', _build_pyproject_toml(chart_title, script))

                # Embed any image-annotation files referenced by the script
                # (script loads them from images/<basename> relative to plot.py).
                for _ann in self.canvas.annotations:
                    if _ann.get('type') != 'image':
                        continue
                    _src = _ann.get('filepath', '')
                    if _src and os.path.isfile(_src):
                        try:
                            zf.write(_src, 'images/' + os.path.basename(_src))
                        except Exception:
                            pass

                if use_combined:
                    # Single CSV with all columns
                    buf = io.StringIO()
                    writer = _csv.writer(buf)
                    col_names = list(datasets_to_export.keys())
                    writer.writerow(col_names)
                    n_rows = len(next(iter(datasets_to_export.values())))
                    for row_idx in range(n_rows):
                        writer.writerow([
                            datasets_to_export[c][row_idx]
                            if row_idx < len(datasets_to_export[c]) else ''
                            for c in col_names
                        ])
                    zf.writestr('data/data.csv', buf.getvalue())
                else:
                    # One CSV per column
                    for col_name, arr in datasets_to_export.items():
                        buf = io.StringIO()
                        writer = _csv.writer(buf)
                        writer.writerow([col_name])
                        for v in arr:
                            writer.writerow([v])
                        # Sanitise filename
                        safe = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in col_name)
                        zf.writestr(f'data/{safe}.csv', buf.getvalue())

            QMessageBox.information(self, 'Exported',
                f'Python bundle saved to:\n{fp}\n\n'
                f'Extract the zip and run: python plot.py')

        except Exception as e:
            import traceback as _tb
            QMessageBox.critical(self, 'Export error', f'{e}\n\n{_tb.format_exc()}')

    def _export_to_code_runner(self):
        """Build a .pvizx bundle from the current chart and open it directly in Code Runner.

        Unlike _export_python_bundle(), this method skips the Save dialog and
        writes the bundle to a temporary file, then hands it off to the Code
        Runner so the user can inspect and tweak the generated script immediately.
        """
        import csv as _csv
        import tempfile
        import numpy as np

        # ── Collect state ──────────────────────────────────────────────────────
        settings    = self._collect_settings()
        series_meta = self._collect_series_meta()
        series_list = series_meta.get('series', [])

        # Determine which columns are used (mirrors _export_python_bundle logic)
        used_cols: set[str] = set()
        for s in series_list:
            for k in ('x_col', 'y_col'):
                c = s.get(k, '')
                if c and c in self.datasets:
                    used_cols.add(c)
        for attr in ('combo_z', 'combo_err', 'combo_bar_ymin'):
            cb = getattr(self, attr, None)
            if cb:
                txt = cb.currentText()
                if txt and txt != '(none)' and txt in self.datasets:
                    used_cols.add(txt)
        # U/V columns for quiver, barbs, and streamplot live in series_meta,
        # not in the series rows — add them so they are written to the CSV.
        for _uv_key in ('quiver_u_col', 'quiver_v_col',
                        'barbs_u_col',  'barbs_v_col',
                        'stream_u_col', 'stream_v_col'):
            c = series_meta.get(_uv_key, '')
            if c and c != '(none)' and c in self.datasets:
                used_cols.add(c)
        export_cols = used_cols if used_cols else set(self.datasets.keys())
        datasets_to_export = {k: self.datasets[k] for k in export_cols if k in self.datasets}

        if not datasets_to_export:
            QMessageBox.warning(self, 'No data',
                'No datasets are loaded — cannot open in Code Runner.')
            return

        # ── Palette & title ────────────────────────────────────────────────────
        palette = [self._palette_color(i) for i in range(16)]
        chart_title = (settings.get('title_text') or
                       getattr(self, '_current_filepath', None) and
                       os.path.splitext(os.path.basename(self._current_filepath))[0] or
                       'chart')

        try:
            # ── Generate script ────────────────────────────────────────────────
            n_subplots = settings.get('subplot_rows', 1) * settings.get('subplot_cols', 1)
            script = generate_plot_script(
                settings, series_meta, datasets_to_export, palette, chart_title)

            # ── Build CSVs ─────────────────────────────────────────────────────
            lengths      = {len(v) for v in datasets_to_export.values() if v is not None}
            use_combined = len(lengths) == 1

            # Write to a named temp file that persists until the Code Runner
            # extracts and runs it (Code Runner manages its own cleanup via
            # _pvizx_tmpdir, so we only need to ensure the zip itself survives
            # long enough to be read by load_pvizx).
            tmp_fd, tmp_fp = tempfile.mkstemp(suffix='.pvizx', prefix='plotviz_cr_')
            os.close(tmp_fd)

            with zipfile.ZipFile(tmp_fp, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('plot.py', script)
                zf.writestr('README.md', _build_readme(chart_title, datasets_to_export, n_subplots))
                zf.writestr('pyproject.toml', _build_pyproject_toml(chart_title, script))

                if use_combined:
                    buf = io.StringIO()
                    writer = _csv.writer(buf)
                    col_names = list(datasets_to_export.keys())
                    writer.writerow(col_names)
                    n_rows = len(next(iter(datasets_to_export.values())))
                    for row_idx in range(n_rows):
                        writer.writerow([
                            datasets_to_export[c][row_idx]
                            if row_idx < len(datasets_to_export[c]) else ''
                            for c in col_names
                        ])
                    zf.writestr('data/data.csv', buf.getvalue())
                else:
                    for col_name, arr in datasets_to_export.items():
                        buf = io.StringIO()
                        writer = _csv.writer(buf)
                        writer.writerow([col_name])
                        for v in arr:
                            writer.writerow([v])
                        safe = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in col_name)
                        zf.writestr(f'data/{safe}.csv', buf.getvalue())

            # ── Hand off to Code Runner ────────────────────────────────────────
            self._open_pvizx_in_code_runner(tmp_fp)

        except Exception as e:
            import traceback as _tb
            QMessageBox.critical(self, 'Code Runner export error', f'{e}\n\n{_tb.format_exc()}')
