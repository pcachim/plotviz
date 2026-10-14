"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

core/settings_types.py  –  plotviz

TypedDict descriptions of the JSON-like dicts that flow into core/: the project
settings, the series table and the per-series entries. They exist so mypy can
reject a mistyped key (settings.get("xlabel_sizee")) in core/.

The key sets mirror what the UI writes (PlotVizApp._collect_settings,
_collect_series_meta and the CHART_OPT_FIELDS table). tests/test_settings_types.py
fails if the UI and these definitions drift apart.

No Qt, no ui/ imports.
"""
from __future__ import annotations

from typing import Any, TypedDict

class SeriesEntry(TypedDict, total=False):
    """One row of the series table (series.json -> "series")."""
    x_col: str
    y_col: str
    label: str
    series_type: str
    plot_num: int
    y2: bool


class SeriesMeta(TypedDict, total=False):
    """series.json: the series table plus the extra column pickers."""
    series: list[SeriesEntry]
    z_col: str
    err_col: str
    fill_y2_col: str
    bar_ymin_col: str
    quiver_u_col: str
    quiver_v_col: str
    barbs_u_col: str
    barbs_v_col: str
    stream_u_col: str
    stream_v_col: str
    bubble_size_col: str
    err_xerr_col: str
    subplot_chart_types: dict[str | int, str]
    subplot_plot_modes: dict[str | int, str]
    subplot_legend_locs: dict[str | int, str]
    subplot_chart_opts: dict[str | int, dict[str, Any]]
    subplot_z_cols: dict[str | int, str]


class ChartOpts(TypedDict, total=False):
    """Per-subplot chart options (CHART_OPT_FIELDS). Stored per subplot and also as
    global keys; core merges the per-subplot ones into the settings."""
    bar_stacked: bool
    bar_horizontal: bool
    hist_bins: int
    hist_density: bool
    hist_cumulative: bool
    hist_histtype: str
    hist_orientation: str
    cmap: str
    contour_levels: int
    heat_alpha: float
    heat_interpolation: str
    heat_colorbar: bool
    heat_colorbar_shrink: float
    heat_filled_contour: bool
    heat_contour_lines: bool
    surf_stride: int
    surf_wireframe: bool
    heat_vminmax_enable: bool
    heat_vmin: float
    heat_vmax: float
    contour_line_width: float
    contour_line_color: str
    tri_cmap: str
    tri_levels: int
    tri_alpha: float
    tri_fill_mode: str
    tri_lines: bool
    tri_triplot: bool
    tri_colorbar: bool
    tri_colorbar_shrink: float
    pie_autopct: bool
    pie_shadow: bool
    pie_donut: bool
    pie_explode_first: bool
    pie_startangle: float
    pie_labeldistance: float
    pie_pctdistance: float
    area_stacked: bool
    area_baseline: float
    violin_show_means: bool
    violin_show_medians: bool
    violin_show_extrema: bool
    violin_points: str
    violin_bw: str
    violin_vert: bool
    box_show_means: bool
    box_show_medians: bool
    box_notch: bool
    box_showfliers: bool
    box_vert: bool
    box_whis: float
    box_alpha: float
    step_where: str
    stem_baseline: float
    waterfall_connector: bool
    waterfall_width: float
    waterfall_alpha: float
    waterfall_pos_color: str
    waterfall_neg_color: str
    hist2d_bins_x: int
    hist2d_bins_y: int
    hist2d_alpha: float
    hist2d_cmap: str
    hist2d_colorbar: bool
    hist2d_log: bool
    hexbin_gridsize: int
    hexbin_alpha: float
    hexbin_cmap: str
    hexbin_colorbar: bool
    hexbin_log: bool
    radar_gridlevels: int
    ecdf_complementary: bool
    quiver_scale: float
    quiver_width: float
    quiver_color_by_mag: bool
    quiver_cmap: str
    barbs_length: float
    barbs_pivot: str
    barbs_alpha: float
    barbs_color_by_mag: bool
    barbs_cmap: str
    stream_density: float
    stream_arrowsize: float
    stream_linewidth: float
    stream_color_by_mag: bool
    stream_cmap: str


class UiSettings(TypedDict, total=False):
    """All other keys written by PlotVizApp._collect_settings() (plus annotations)."""
    _app: str
    _version: str
    chart_type: str
    title_show: bool
    title_text: str
    title_font: str
    title_size: int
    title_color: str
    title_rotation: int
    title_ha: str
    sp_titles: dict[str, Any]
    subplot_title_show: dict[str, Any]
    subplot_title_font: dict[str, Any]
    subplot_title_size: dict[str, Any]
    subplot_title_color: dict[str, Any]
    subplot_title_pad: dict[str, Any]
    subplot_title_rotation: dict[str, Any]
    subplot_title_ha: dict[str, Any]
    title_x: float
    title_y: float
    title_pos_format: str
    sp_hspace: float
    sp_wspace: float
    subplot_xlabels: dict[str, Any]
    subplot_xlabel_show: dict[str, Any]
    subplot_ylabels: dict[str, Any]
    subplot_ylabel_show: dict[str, Any]
    subplot_y2labels: dict[str, Any]
    subplot_y2label_show: dict[str, Any]
    subplot_legends: dict[str, Any]
    subplot_legend_locs: dict[str, Any]
    subplot_legend_x: dict[str, Any]
    subplot_legend_y: dict[str, Any]
    subplot_legend_fontsize: dict[str, Any]
    subplot_legend_ncols: dict[str, Any]
    subplot_legend_frameon: dict[str, Any]
    subplot_legend_color: dict[str, Any]
    subplot_legend_facecolor: dict[str, Any]
    subplot_legend_alpha: dict[str, Any]
    subplot_legend_edgecolor: dict[str, Any]
    subplot_xlims: dict[str, Any]
    subplot_ylims: dict[str, Any]
    subplot_y2lims: dict[str, Any]
    subplot_xscales: dict[str, Any]
    subplot_yscales: dict[str, Any]
    subplot_xtick_sizes: dict[str, Any]
    subplot_ytick_sizes: dict[str, Any]
    subplot_xtick_dir: dict[str, Any]
    subplot_ytick_dir: dict[str, Any]
    subplot_xtick_minor: dict[str, Any]
    subplot_ytick_minor: dict[str, Any]
    subplot_xtick_rotation: dict[str, Any]
    subplot_ytick_rotation: dict[str, Any]
    subplot_xtick_step: dict[str, Any]
    subplot_ytick_step: dict[str, Any]
    subplot_x_formatter: dict[str, Any]
    subplot_y_formatter: dict[str, Any]
    subplot_xticks_show: dict[str, Any]
    subplot_yticks_show: dict[str, Any]
    subplot_equal_aspect: dict[str, Any]
    subplot_xaxis_pos: dict[str, Any]
    subplot_yaxis_pos: dict[str, Any]
    subplot_ann_visible: dict[str, Any]
    xlabel_font: str
    xlabel_size: int
    xlabel_color: str
    subplot_xlabel_rotation: dict[str, Any]
    subplot_xlabel_labelpad: dict[str, Any]
    subplot_xlabel_loc: dict[str, Any]
    subplot_xlabel_ha: dict[str, Any]
    ylabel_font: str
    ylabel_size: int
    ylabel_color: str
    subplot_ylabel_rotation: dict[str, Any]
    subplot_ylabel_labelpad: dict[str, Any]
    subplot_ylabel_loc: dict[str, Any]
    subplot_ylabel_ha: dict[str, Any]
    y2label_font: str
    y2label_size: int
    y2label_color: str
    y2label_rotation: int
    y2label_labelpad: int
    y2label_loc: str
    y2label_ha: str
    zlabel_font: str
    zlabel_size: int
    zlabel_color: str
    subplot_zlabels: dict[str, Any]
    subplot_zlabel_show: dict[str, Any]
    subplot_zlabel_rotation: dict[str, Any]
    subplot_zlabel_labelpad: dict[str, Any]
    color_palette: str
    preset: str
    chart_bg_color: str
    chart_fg_color: str
    plot_bg_color: str
    border_top: bool
    border_bottom: bool
    border_left: bool
    border_right: bool
    curve_styles: dict[str, Any]
    fig_preset: str
    fig_unit: str
    fig_width: float
    fig_height: float
    fig_left: float
    fig_right: float
    fig_bottom: float
    fig_top: float
    margin_format: str
    grid_on: bool
    grid_color: str
    grid_linestyle: str
    grid_linewidth: float
    grid_alpha: float
    minor_grid_on: bool
    minor_grid_color: str
    minor_grid_linestyle: str
    minor_grid_linewidth: float
    minor_grid_alpha: float
    dpi: int
    fit_ci_index: int
    fit_pi_index: int
    fit_ci_alpha: float
    fits: dict[str, Any]
    fit_result: Any
    subplot_rows: int
    subplot_cols: int
    subplot_mosaic: list[list[str]] | None
    sp_sharex: bool
    sp_sharey: bool
    contour_levels_explicit: str
    ann_fontcolor: str
    ann_fontsize: int
    ann_font: str
    ann_bgcolor: str
    ann_bg_alpha: float
    ann_edgecolor: str
    annotations: list[Any]


class DerivedSettings(TypedDict, total=False):
    """Keys that core/ or the exporters add to the settings before generating a script
    (copied in from series.json, which is where the UI stores them)."""
    _err_col: str
    quiver_u_col: str
    quiver_v_col: str
    barbs_u_col: str
    barbs_v_col: str
    stream_u_col: str
    stream_v_col: str
    subplot_chart_types: dict[str | int, str]
    _z_col: str
    _fill_y2_col: str
    _bar_ymin_col: str
    subplot_z_cols: dict[str | int, str]


class PlotSettings(UiSettings, ChartOpts, DerivedSettings, total=False):
    """The complete settings dict as seen by core.script_gen."""
