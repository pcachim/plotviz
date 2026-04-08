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


def _col_ref(col, use_combined=True, datasets=None):
    """Return a Python expression to reference a dataset column.

    When all columns share the same length (use_combined=True) they are read
    into a single combined ``df``, so we emit ``df['col']``.
    When columns differ in length each is in its own ``_df_<safe>`` frame and
    we emit ``_df_<safe>['col']`` to avoid NaN-padding from pd.concat.
    """
    if use_combined or datasets is None:
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
            lines.append(f"{ax_var}.bar({xexpr}, {yexpr}, label='{lbl}', color={col})")
        elif ct == 'Area':
            lines.append(f"{ax_var}.fill_between({xexpr}, {yexpr}, label='{lbl}', color={col}, alpha={aal})")
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
    for i, s in enumerate(series):
        yc  = s.get('y_col', '')
        lbl = _esc(s.get('label', f'Series {i+1}'))
        st  = _series_style(settings, s, i, palette)
        col = f"'{st['color']}'"
        if yc:
            lines.append(f"{ax_var}.hist({_col_ref(yc)}.dropna(), bins=25, label='{lbl}', color={col}, alpha=0.7)")
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
        xc = s.get('x_col', ''); yc = s.get('y_col', '')
        lbl = _esc(s.get('label', f'Series {i+1}'))
        st  = _series_style(settings, s, i, palette)
        col = f"'{st['color']}'"
        lw  = st['linewidth']
        ls  = st['linestyle']
        if xc and yc:
            lines.append(f"{ax_var}.plot({_col_ref(xc)}, {_col_ref(yc)}, label='{lbl}', color={col}, linestyle='{ls}', linewidth={lw})")
    return lines


def _gen_heatmap(settings, series, datasets, palette, ax_var):
    # Build from all numeric datasets
    cols = [k for k, v in datasets.items()
            if hasattr(v, 'dtype') and v.dtype.kind not in ('U', 'S', 'O')]
    if len(cols) < 2:
        return [f"# Not enough numeric columns for heatmap"]
    return [
        f"import numpy as np",
        f"_hm_cols = {[_esc(c) for c in cols]!r}",
        f"_hm_corr = df[_hm_cols].corr()",
        f"_hm_im = {ax_var}.imshow(_hm_corr.values, cmap='coolwarm', vmin=-1, vmax=1)",
        f"{ax_var}.set_xticks(range(len(_hm_cols))); {ax_var}.set_xticklabels(_hm_cols, rotation=45, ha='right')",
        f"{ax_var}.set_yticks(range(len(_hm_cols))); {ax_var}.set_yticklabels(_hm_cols)",
        f"plt.colorbar(_hm_im, ax={ax_var})",
        f"# Annotate cells",
        f"for _r in range(len(_hm_cols)):",
        f"    for _c in range(len(_hm_cols)):",
        f"        {ax_var}.text(_c, _r, f'{{_hm_corr.values[_r, _c]:.2f}}', ha='center', va='center', fontsize=8)",
    ]


def _gen_contour(settings, series, datasets, palette, ax_var):
    lines = []
    if series:
        s = series[0]
        xc = s.get('x_col', '')
        yc = s.get('y_col', '')
        zc = settings.get('_z_col', '')   # top-level z from series_meta
        if xc and yc and zc:
            lines += [
                f"from scipy.interpolate import griddata",
                f"import numpy as np",
                f"_xi = np.linspace({_col_ref(xc)}.min(), {_col_ref(xc)}.max(), 100)",
                f"_yi = np.linspace({_col_ref(yc)}.min(), {_col_ref(yc)}.max(), 100)",
                f"_xi, _yi = np.meshgrid(_xi, _yi)",
                f"_zi = griddata(({_col_ref(xc)}, {_col_ref(yc)}), {_col_ref(zc)}, (_xi, _yi), method='cubic')",
                f"_ct = {ax_var}.contourf(_xi, _yi, _zi, levels=15, cmap='coolwarm')",
                f"plt.colorbar(_ct, ax={ax_var})",
            ]
        else:
            lines.append(f"# Contour: assign X, Y and Z columns in plotviz to render.")
    return lines


def _gen_surface3d(settings, series, datasets, palette, ax_var):
    lines = [
        f"# Note: 3D Surface requires projection='3d' — see fig.add_subplot below",
        f"from scipy.interpolate import griddata",
        f"import numpy as np",
    ]
    if series:
        s = series[0]
        xc = s.get('x_col', '')
        yc = s.get('y_col', '')
        zc = settings.get('_z_col', '')   # top-level z from series_meta
        if xc and yc and zc:
            lines += [
                f"_xi = np.linspace({_col_ref(xc)}.min(), {_col_ref(xc)}.max(), 50)",
                f"_yi = np.linspace({_col_ref(yc)}.min(), {_col_ref(yc)}.max(), 50)",
                f"_xi, _yi = np.meshgrid(_xi, _yi)",
                f"_zi = griddata(({_col_ref(xc)}, {_col_ref(yc)}), {_col_ref(zc)}, (_xi, _yi), method='cubic')",
                f"{ax_var}.plot_surface(_xi, _yi, _zi, cmap='viridis', alpha=0.9)",
            ]
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
    lines = []
    ct = settings.get('chart_type', 'Hist2D')
    if series:
        s = series[0]
        xc, yc = s.get('x_col',''), s.get('y_col','')
        if xc and yc:
            if ct == 'Hexbin':
                lines.append(f"{ax_var}.hexbin({_col_ref(xc)}, {_col_ref(yc)}, gridsize=30, cmap='viridis')")
            else:
                lines.append(f"{ax_var}.hist2d({_col_ref(xc)}, {_col_ref(yc)}, bins=30, cmap='viridis')")
            lines.append(f"plt.colorbar({ax_var}.collections[0] if {ax_var}.collections else plt.cm.ScalarMappable(), ax={ax_var})")
    return lines


def _gen_quiver(settings, series, datasets, palette, ax_var):
    lines = []
    if series:
        s = series[0]
        xc, yc = s.get('x_col',''), s.get('y_col','')
        if xc and yc:
            lines.append(f"# Quiver: dx and dy should be separate columns; adjust as needed")
            lines.append(f"{ax_var}.quiver({_col_ref(xc)}, {_col_ref(yc)}, "
                         f"{_col_ref(xc)}.diff().fillna(0), {_col_ref(yc)}.diff().fillna(0))")
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
    'Heatmap':    _gen_heatmap,
    'Contour':    _gen_contour,
    '3D Surface': _gen_surface3d,
    'ECDF':       _gen_ecdf,
    'Quiver':     _gen_quiver,
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
    settings['_z_col']   = series_meta.get('z_col', '')
    settings['_err_col'] = series_meta.get('err_col', '')
    # subplot_chart_types lives in series_meta, not settings — merge it in
    if not settings.get('subplot_chart_types'):
        settings['subplot_chart_types'] = series_meta.get('subplot_chart_types', {})
    # per-subplot z columns (if stored separately)
    if not settings.get('subplot_z_cols'):
        settings['subplot_z_cols'] = series_meta.get('subplot_z_cols', {})

    # ── Collect dataset filenames ──────────────────────────────────────────────
    used_cols = {s.get('x_col') for s in series_list} | {s.get('y_col') for s in series_list}
    used_cols.discard(''); used_cols.discard(None)
    ds_names  = sorted(datasets.keys())
    # All datasets go into data/ as CSVs; build a combined CSV if they share length
    lengths = {len(v) for v in datasets.values() if v is not None}
    use_combined = len(lengths) == 1   # all same length → one CSV

    # Rebind _col_ref so every generator in this script uses the right frame
    def _col_ref(col, _uc=use_combined, _ds=datasets):  # noqa: F811
        if _uc or _ds is None:
            return f"df['{_esc(col)}']"
        safe = col.replace(' ', '_').replace('-', '_')
        return f"_df_{safe}['{_esc(col)}']"

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
    if fig_unit == 'cm':
        fig_w = fig_w_raw / 2.54
        fig_h = fig_h_raw / 2.54
    elif fig_unit == 'pixels':
        _dpi = settings.get('dpi', 300)
        fig_w = fig_w_raw / _dpi
        fig_h = fig_h_raw / _dpi
    else:  # inches
        fig_w, fig_h = fig_w_raw, fig_h_raw
    fig_w = round(max(fig_w, 4.0), 2)
    fig_h = round(max(fig_h, 3.0), 2)
    lines += [
        "# ── Figure ───────────────────────────────────────────────────────────",
        f"fig = plt.figure(figsize=({fig_w:.1f}, {fig_h:.1f}))",
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
                    sub_z = settings.get('_z_col', '') if sub_ct in ('Contour', 'Surface3D', 'Hist2D', 'Hexbin') else ''
                sub_settings = dict(settings)
                sub_settings['chart_type'] = sub_ct
                sub_settings['_z_col']     = sub_z
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
                    sub_z = settings.get('_z_col', '') if sub_ct in ('Contour', 'Surface3D', 'Hist2D', 'Hexbin') else ''
                sub_settings = dict(settings)
                sub_settings['chart_type'] = sub_ct
                sub_settings['_z_col']     = sub_z
                lines.append(f"# Subplot {idx+1}: {sub_ct}")
                gen = _GENERATORS.get(sub_ct, _gen_line_scatter_step_stem_area_errorbar)
                for l in gen(sub_settings, sub_series, datasets, palette, ax_var):
                    lines.append(l)
                sp_title = settings.get('sp_titles', {}).get(str(idx), f'Subplot {idx+1}')
                if sp_title: lines.append(f"{ax_var}.set_title('{_esc(sp_title)}')")
                lines.append(_legend_call(settings, idx, ax_var))
                lines.append("")

    # ── Final touches ─────────────────────────────────────────────────────────
    hspace = settings.get('sp_hspace', 0.35)
    wspace = settings.get('sp_wspace', 0.35)
    # Figure-level title (suptitle)
    title_show  = settings.get('title_show', True)
    title_font  = settings.get('title_font', 'sans-serif')
    title_size  = settings.get('title_size', 14)
    title_color = settings.get('title_color', '#000000')
    title_x     = settings.get('title_x', 0.5)
    title_y     = settings.get('title_y', 0.98)
    suptitle_lines = []
    if title_show and title_text:
        suptitle_lines = [
            f"fig.suptitle('{_esc(title_text)}', "
            f"fontsize={title_size}, "
            f"fontfamily='{_esc(title_font)}', "
            f"color='{_esc(title_color)}', "
            f"x={title_x}, y={title_y})",
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
            f"df['_x'] = df['{_esc(xn)}'].astype(str)",
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
            f"df['_x'] = df['{_esc(xn)}'].astype(str)",
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
            f'_cols = {[_esc(c) for c in num_cols]!r}',
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
        lines += [
            f'_cols = {[_esc(c) for c in num_cols]!r}',
            'pg = sns.pairplot(df[_cols],',
            f'    diag_kind={repr(explorer._pair_diag.currentText())},',
            f'    kind={repr(explorer._pair_kind.currentText())},',
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
            eb = "('sd', None)"
        else:
            eb = 'None'
        lines += [
            f"df['_x'] = df['{_esc(xn)}'].astype(str)",
            "fg = sns.catplot(",
            f"    data=df, x='_x', y='{_esc(yn)}',",
            f'    kind={repr(kind)},',
            f'    color={col},',
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
        series_meta = self._collect_series_meta()
        series_list = series_meta.get('series', [])

        # Determine which columns are used
        used_cols: set[str] = set()
        for s in series_list:
            for k in ('x_col', 'y_col'):
                c = s.get(k, '')
                if c and c in self.datasets:
                    used_cols.add(c)
        for attr in ('combo_z', 'combo_err'):
            cb = getattr(self, attr, None)
            if cb:
                txt = cb.currentText()
                if txt and txt != '(none)' and txt in self.datasets:
                    used_cols.add(txt)
        # Fall back to all columns if nothing is explicitly assigned
        export_cols = used_cols if used_cols else set(self.datasets.keys())
        datasets_to_export = {k: self.datasets[k] for k in export_cols if k in self.datasets}

        if not datasets_to_export:
            QMessageBox.warning(self, 'No data', 'No datasets are loaded — nothing to export.')
            return

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
