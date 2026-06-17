"""Generate sample .pviz projects for manual GUI testing.

Run from the repo root:   python tests/fixtures/make_fixtures.py
Writes test*.pviz into this folder. Pure (uses core.serialize), no Qt needed.
"""
import os
import sys
import tempfile

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "src", "plotviz"))
from core.serialize import encode_datasets, write_project_zip  # noqa: E402

BASE = dict(
    _app="plotviz", _version="1.2", _file_type="project",
    title_show=True, title_font="DejaVu Sans", title_size=14, title_color="#222222",
    title_x=0.5, title_y=0.98, title_pos_format="fractions", title_ha="center", title_rotation=0,
    fig_unit="cm", fig_width=20.0, fig_height=14.0, dpi=300,
    chart_bg_color="#ffffff", plot_bg_color="#fbfbfb", chart_fg_color="#333333",
    border_top=True, border_bottom=True, border_left=True, border_right=True,
    sp_hspace=0.35, sp_wspace=0.35,
)


def series(x, y, label, t="Line", plot=1, y2=False):
    return dict(x_col=x, y_col=y, label=label, series_type=t, plot_num=plot, y2=y2)


def meta(series_list, **extra):
    m = dict(series=series_list, z_col="(none)", err_col="(none)",
             fill_y2_col="(none)", bar_ymin_col="(none)",
             bubble_size_col="(uniform)", err_xerr_col="(none)")
    m.update(extra)
    return m


def save(name, settings, m, datasets, images=()):
    fp = os.path.join(_HERE, name)
    write_project_zip(fp, settings, m, encode_datasets(datasets), image_paths=list(images))
    print("wrote", name)


def main():
    # Build the annotation image in a temp dir so no stray file is left behind.
    logo = os.path.join(tempfile.mkdtemp(prefix="pviz_fixture_"), "_logo.png")
    fig, ax = plt.subplots(figsize=(1, 1))
    ax.add_patch(plt.Circle((.5, .5), .4, color="tab:red")); ax.axis("off")
    fig.savefig(logo, dpi=40, transparent=True); plt.close(fig)

    # A) annotations / grid / log-Y / xlim
    x = np.linspace(0.2, 10, 60)
    save("test1_annotations.pviz",
         dict(BASE, chart_type="Line", subplot_rows=1, subplot_cols=1,
              title_text="Test 1 - annotations / grid / log-Y / xlim",
              grid_on=True, grid_color="#cccccc", grid_linestyle="--",
              grid_linewidth=0.7, grid_alpha=0.6,
              minor_grid_on=True, minor_grid_color="#eeeeee",
              minor_grid_linestyle=":", minor_grid_linewidth=0.4, minor_grid_alpha=0.5,
              subplot_yscales={"0": "log"}, subplot_xlims={"0": [0, 10]},
              subplot_ann_visible={"0": True},
              annotations=[
                  {"type": "text", "axes_index": 0, "x": 5.0, "y": 5.0, "label": "peak region",
                   "style": {"fontsize": 11, "bg_alpha": 0.9, "bg_color": "#ffffcc",
                             "edge_color": "#aaaaaa", "fontcolor": "#000000", "fontfamily": "DejaVu Sans"}},
                  {"type": "arrow", "axes_index": 0, "x0": 2.0, "y0": 10.0, "x1": 4.0, "y1": 3.0,
                   "label": "look", "style": {"fontcolor": "#cc3300", "fontsize": 10}},
                  {"type": "image", "axes_index": 0, "x": 8.0, "y": 2.0,
                   "image_file": "images/_logo.png", "zoom": 0.5, "style": {}},
              ]),
         meta([series("x", "y", "exp", "Line", 1)]),
         {"x": list(x), "y": list(np.exp(x * 0.3)), "y2": list(2 + np.sin(x))},
         images=[logo])

    # B) 2x2 subplots, mixed types, twinx
    x = np.linspace(0, 10, 40)
    save("test2_subplots_twinx.pviz",
         dict(BASE, chart_type="Line", subplot_rows=2, subplot_cols=2,
              title_text="Test 2 - 2x2 subplots, mixed types, twinx",
              grid_on=True, grid_color="#dddddd", grid_linestyle="-",
              grid_linewidth=0.6, grid_alpha=0.6,
              subplot_chart_types={"0": "Line", "1": "Bar", "2": "Scatter", "3": "Area"},
              sp_titles={"0": "line + twinx", "1": "bar", "2": "scatter", "3": "area"},
              subplot_title_show={"0": True, "1": True, "2": True, "3": True}),
         meta([series("x", "a", "sin", "Line", 1),
               series("x", "e", "scale", "Line", 1, y2=True),
               series("x", "b", "cos", "Bar", 2),
               series("x", "c", "ramp", "Scatter", 3),
               series("x", "d", "sqrt", "Area", 4)],
              subplot_chart_types={"0": "Line", "1": "Bar", "2": "Scatter", "3": "Area"}),
         {"x": list(x), "a": list(np.sin(x)), "b": list(np.cos(x)),
          "c": list(x * 0.5), "d": list(np.sqrt(x)), "e": list(20 + 5 * np.sin(x))})

    # C) 1x2: Line + Heatmap
    n = 12
    xs = np.repeat(np.arange(n), n); ys = np.tile(np.arange(n), n)
    zs = np.sin(xs / 2.0) * np.cos(ys / 2.0)
    save("test3_heatmap_grid.pviz",
         dict(BASE, chart_type="Line", subplot_rows=1, subplot_cols=2,
              title_text="Test 3 - Line + Heatmap (sharex/colorbar guards)",
              subplot_chart_types={"0": "Line", "1": "Heatmap"},
              subplot_plot_modes={"0": "Standard", "1": "Heatmap & Contour"},
              sp_titles={"0": "line", "1": "heatmap"},
              subplot_title_show={"0": True, "1": True}),
         meta([series("lx", "ly", "wave", "Line", 1),
               series("hx", "hy", "field", "Heatmap", 2)],
              z_col="hz",
              subplot_chart_types={"0": "Line", "1": "Heatmap"},
              subplot_plot_modes={"0": "Standard", "1": "Heatmap & Contour"}),
         {"lx": list(np.linspace(0, 10, 50)), "ly": list(np.sin(np.linspace(0, 10, 50))),
          "hx": list(xs.astype(float)), "hy": list(ys.astype(float)), "hz": list(zs)})

    # D) categorical x (Bar) + image annotation
    save("test4_categorical_roundtrip.pviz",
         dict(BASE, chart_type="Bar", subplot_rows=1, subplot_cols=1,
              title_text="Test 4 - categorical x + image annotation (roundtrip)",
              grid_on=True, grid_color="#dddddd", grid_linestyle="-",
              grid_linewidth=0.6, grid_alpha=0.5, subplot_ann_visible={"0": True},
              annotations=[{"type": "image", "axes_index": 0, "x": 3.0, "y": 8.0,
                            "image_file": "images/_logo.png", "zoom": 0.5, "style": {}}]),
         meta([series("cat", "val", "counts", "Bar", 1)]),
         {"cat": np.array(["alpha", "beta", "gamma", "delta", "epsilon"], dtype=object),
          "val": np.array([3.0, 7.0, 2.0, 9.0, 5.0])},
         images=[logo])

    print("done ->", _HERE)


if __name__ == "__main__":
    main()
