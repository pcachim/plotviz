"""Render one example figure per chart type for the documentation.

Each figure is a sample chart of data/plots, opened in the real app and written through
the export path, so the pictures are what plotviz draws. Run it from the repository root
whenever a chart type changes:

    uv run python util/make_doc_images.py            # all types
    uv run python util/make_doc_images.py Line Pie   # only some

The files go to docs/images/charts/<slug>.png (see CHART_SAMPLES for the sample of each type).
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "plotviz"))

OUT = ROOT / "docs" / "images" / "charts"
DPI = 90

# chart type -> sample project in data/plots
CHART_SAMPLES = {
    "Line": "plot_xy.pviz",
    "Scatter": "scatter_xy.pviz",
    "Bar": "bar.pviz",
    "Errorbar": "errorbar.pviz",
    "Area": "stackplot.pviz",
    "Fill Between": "fill_between.pviz",
    "Step": "step.pviz",
    "Stem": "stem.pviz",
    "Bubble": "bubble.pviz",
    "Waterfall": "waterfall.pviz",
    "Histogram": "hist.pviz",
    "Hist2D": "hist2d.pviz",
    "Hexbin": "hexbin.pviz",
    "Boxplot": "boxplot.pviz",
    "Violin": "violinplot.pviz",
    "ECDF": "ecdf.pviz",
    "Pie": "pie.pviz",
    "Polar": "polar.pviz",
    "Radar": "radar.pviz",
    "Heatmap": "pcolormesh.pviz",
    "Contour": "contourf.pviz",
    "Tricontour": "tricontourf.pviz",
    "3D Surface": "plot_surface.pviz",
    "Quiver": "quiver.pviz",
    "Barbs": "barbs.pviz",
    "Streamplot": "streamplot.pviz",
}


def slug(chart_type: str) -> str:
    return chart_type.lower().replace(" ", "-")


def main(only: list[str]) -> int:
    import matplotlib
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ui.main_window import PlotVizApp
    PlotVizApp._load_on_startup = lambda self: None
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = [t for t in CHART_SAMPLES if not only or t in only]
    unknown = [t for t in only if t not in CHART_SAMPLES]
    if unknown:
        print("unknown chart type(s):", ", ".join(unknown), "| known:", ", ".join(CHART_SAMPLES))
        return 2
    w = PlotVizApp()
    matplotlib.rcParams["text.usetex"] = False
    for chart_type in wanted:
        w._load_project_inner(str(ROOT / "data" / "plots" / CHART_SAMPLES[chart_type]), silent=True)
        app.processEvents()
        if chart_type == "Bar":       # the sample is dark: the manual uses the default (white) scheme
            w._apply_color_scheme_dict(w._COLOR_SCHEME_REGISTRY["Default (white)"])
        if chart_type == "Barbs":     # the sample's winds are all calm (circles): scale to a strong breeze
            for combo in (w.barbs_u_combo, w.barbs_v_combo):
                w.datasets[combo.currentText()] = w.datasets[combo.currentText()] * 15.0
        wi, hi = w._fig_size_in_inches()
        old = matplotlib.rcParams.get("font.family")
        matplotlib.rcParams["font.family"] = w.title_font.currentText()
        try:
            fig = w._build_export_figure(wi, hi, DPI)
            path = OUT / f"{slug(chart_type)}.png"
            fig.savefig(path, dpi=DPI, facecolor=fig.get_facecolor())
        finally:
            matplotlib.rcParams["font.family"] = old
        print(f"{chart_type:<12} {(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)}  {path.stat().st_size // 1024} KB")
    w.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
