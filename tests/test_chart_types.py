"""Render every chart type through the real GUI render path.

Parametrised over PLOT_MODE_GROUPS so a newly added chart type is covered
automatically. Each type is loaded from a minimal .pviz project and rendered
with ``_render_axes`` (the path shared by preview and export), which raises on
errors instead of swallowing them like ``update_preview`` does.

Runs only where a real PyQt6 is installed; skipped otherwise.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "src", "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:  # noqa: BLE001 - any import failure means "no usable Qt"
        return False
    return hasattr(QApplication, "instance")


HAVE_QT = _have_real_qt()

if HAVE_QT:
    import numpy as np
    from matplotlib.figure import Figure
    from PyQt6.QtWidgets import QApplication
    from core.serialize import encode_datasets, write_project_zip

    _app = QApplication.instance() or QApplication([])

    def _write_pviz(path, chart_type, mode):
        settings = {
            "_app": "plotviz", "_version": "1.2", "_file_type": "project",
            "chart_type": chart_type, "subplot_rows": 1, "subplot_cols": 1,
            "title_show": True, "title_text": chart_type, "title_font": "DejaVu Sans",
            "title_size": 14, "title_color": "#000", "title_x": 0.5, "title_y": 0.98,
            "title_pos_format": "fractions", "title_ha": "center", "title_rotation": 0,
            "fig_unit": "cm", "fig_width": 20.0, "fig_height": 15.0, "dpi": 100,
            "chart_bg_color": "#fff", "plot_bg_color": "#fff", "chart_fg_color": "#000",
            "grid_on": True,
        }
        series = [{"x_col": "x", "y_col": "y", "label": "s", "series_type": chart_type,
                   "plot_num": 1, "y2": False}]
        # The chart-type combo only lists the types of the active plot mode, so
        # the mode must be saved alongside the type or it falls back to 'Line'.
        meta = {"series": series, "z_col": "z", "err_col": "e",
                "subplot_plot_modes": {"0": mode},
                "subplot_chart_types": {"0": chart_type}}
        settings["subplot_chart_types"] = {"0": chart_type}
        x = np.linspace(0, 10, 40)
        datasets = {"x": list(x), "y": list(np.sin(x) + 1.5),
                    "z": list(np.cos(x) + 1.5), "e": [0.1] * len(x)}
        write_project_zip(path, settings, meta, encode_datasets(datasets))


    def _write_multi_pviz(path, types):
        """Project with one series per subplot; *types* is a list of chart types."""
        from ui.tab_builders import TYPE_TO_PLOT_MODE
        n = len(types)
        by_idx = {str(i): t for i, t in enumerate(types)}
        settings = {
            "_app": "plotviz", "_version": "1.2", "_file_type": "project",
            "chart_type": types[0], "subplot_rows": 2, "subplot_cols": 2,
            "title_show": True, "title_text": "mosaic", "title_font": "DejaVu Sans",
            "title_size": 14, "title_color": "#000", "title_x": 0.5, "title_y": 0.98,
            "title_pos_format": "fractions", "title_ha": "center", "title_rotation": 0,
            "fig_unit": "cm", "fig_width": 20.0, "fig_height": 15.0, "dpi": 100,
            "chart_bg_color": "#fff", "plot_bg_color": "#fff", "chart_fg_color": "#000",
            "grid_on": True, "subplot_chart_types": by_idx,
        }
        series = [{"x_col": "x", "y_col": "y", "label": "s%d" % i, "series_type": t,
                   "plot_num": i + 1, "y2": False} for i, t in enumerate(types)]
        meta = {"series": series, "z_col": "z", "err_col": "e",
                "subplot_chart_types": by_idx,
                "subplot_plot_modes": {k: TYPE_TO_PLOT_MODE.get(t, "Standard")
                                       for k, t in by_idx.items()}}
        x = np.linspace(0, 10, 40)
        datasets = {"x": list(x), "y": list(np.sin(x) + 1.5),
                    "z": list(np.cos(x) + 1.5), "e": [0.1] * len(x)}
        write_project_zip(path, settings, meta, encode_datasets(datasets))


def _chart_types():
    if not HAVE_QT:
        return []
    from ui.tab_builders import PLOT_MODE_GROUPS
    return [(t, mode) for mode, types in PLOT_MODE_GROUPS.items() for t in types]


@unittest.skipUnless(HAVE_QT, "real PyQt6 not available")
class TestChartTypes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ui.main_window import PlotVizApp
        cls.PlotVizApp = PlotVizApp
        # Same startup auto-load neutralisation as test_gui_smoke.
        cls._orig = PlotVizApp._load_on_startup
        PlotVizApp._load_on_startup = lambda self: None

    @classmethod
    def tearDownClass(cls):
        cls.PlotVizApp._load_on_startup = cls._orig

    def test_every_chart_type_renders(self):
        types = _chart_types()
        self.assertGreater(len(types), 0)
        for ct, mode in types:
            with self.subTest(chart_type=ct):
                w = self.PlotVizApp()
                _app.processEvents()
                with tempfile.TemporaryDirectory() as d:
                    fp = os.path.join(d, "p.pviz")
                    _write_pviz(fp, ct, mode)
                    w._load_project_inner(fp, silent=True)
                    self.assertEqual(w.chart_type_combo.currentText(), ct)
                    fig = Figure(figsize=(6, 4))
                    axes_list, _ax2, _is3d, _n = w._render_axes(fig)
                    self.assertGreaterEqual(len(axes_list), 1)
                    fig.savefig(os.path.join(d, "out.png"))
                    self.assertGreater(os.path.getsize(os.path.join(d, "out.png")), 0)

    def test_hist2d_log_color_scale_renders(self):
        # Regression: LogNorm used to raise NameError (missing import).
        w = self.PlotVizApp()
        _app.processEvents()
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "p.pviz")
            _write_pviz(fp, "Hist2D", "Heatmap & Contour")
            w._load_project_inner(fp, silent=True)
            w.hist2d_log.setChecked(True)
            axes_list, _ax2, _is3d, _n = w._render_axes(Figure(figsize=(6, 4)))
            self.assertGreaterEqual(len(axes_list), 1)

    def test_mosaic_gives_polar_and_3d_cells_their_projection(self):
        # Regression: subplot_mosaic created plain axes, so a 3D Surface cell
        # raised "no attribute 'plot_surface'" and a Polar cell was not polar.
        w = self.PlotVizApp()
        _app.processEvents()
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "p.pviz")
            _write_multi_pviz(fp, ["3D Surface", "Polar", "Line"])
            w._load_project_inner(fp, silent=True)
            w._subplot_mosaic = [["A", "B"], ["C", "C"]]
            axes_list, _ax2, _is3d, _n = w._render_axes(Figure(figsize=(6, 4)))
            self.assertEqual([a.name for a in axes_list],
                             ["3d", "polar", "rectilinear"])


if __name__ == "__main__":
    unittest.main()
