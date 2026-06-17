"""Headless Qt smoke tests for the plotviz main window.

These exercise the real GUI flows that unit tests can't reach — app
construction, loading a .pviz, the shared render path, annotations, and
multi-subplot layout — asserting only that they run without raising. They
catch the class of regressions that previously only showed up in manual
testing (e.g. a missing import in a dialog, a broken render path).

Runs only where a real PyQt6 is installed; skipped otherwise (e.g. local dev
without Qt). Requires an offscreen Qt platform and the Agg matplotlib backend,
both set below before any Qt/matplotlib import.
"""
import os
import sys
import tempfile
import unittest

# Must be set before PyQt6 / matplotlib are imported anywhere.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "src", "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:
        return False
    # Guard against the _bootstrap stub (a bare object without .instance).
    return hasattr(QApplication, "instance")


HAVE_QT = _have_real_qt()

if HAVE_QT:
    from PyQt6.QtWidgets import QApplication
    import numpy as np
    from matplotlib.figure import Figure
    from core.serialize import encode_datasets, write_project_zip

    _app = QApplication.instance() or QApplication([])

    def _write_pviz(path, rows=1, cols=1):
        settings = {
            "_app": "plotviz", "_version": "1.2", "_file_type": "project",
            "chart_type": "Line", "subplot_rows": rows, "subplot_cols": cols,
            "title_show": True, "title_text": "smoke", "title_font": "DejaVu Sans",
            "title_size": 14, "title_color": "#000", "title_x": 0.5, "title_y": 0.98,
            "title_pos_format": "fractions", "title_ha": "center", "title_rotation": 0,
            "fig_unit": "cm", "fig_width": 20.0, "fig_height": 15.0, "dpi": 150,
            "chart_bg_color": "#fff", "plot_bg_color": "#fff", "chart_fg_color": "#000",
            "grid_on": True,
        }
        series = [{"x_col": "x", "y_col": "y", "label": "s", "series_type": "Line",
                   "plot_num": 1, "y2": False}]
        if rows * cols > 1:
            series.append({"x_col": "x", "y_col": "z", "label": "s2",
                           "series_type": "Bar", "plot_num": 2, "y2": False})
            settings["subplot_chart_types"] = {"0": "Line", "1": "Bar"}
        meta = {"series": series, "z_col": "(none)", "err_col": "(none)"}
        if rows * cols > 1:
            meta["subplot_chart_types"] = {"0": "Line", "1": "Bar"}
        x = np.linspace(0, 10, 40)
        datasets = {"x": list(x), "y": list(np.sin(x)), "z": list(np.cos(x))}
        write_project_zip(path, settings, meta, encode_datasets(datasets))


@unittest.skipUnless(HAVE_QT, "real PyQt6 not available")
class TestGuiSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ui.main_window import PlotVizApp
        cls.PlotVizApp = PlotVizApp
        # Disable the deferred startup auto-load. The window schedules
        # QTimer.singleShot(0, self._load_on_startup) in __init__; that bound
        # method is resolved from the class when scheduled, so patching the
        # class method *before* constructing any window neutralises it. Left
        # active, it would later fire via processEvents() inside update_preview
        # and load the user's last recent file, clobbering test state.
        cls._orig_load_on_startup = PlotVizApp._load_on_startup
        PlotVizApp._load_on_startup = lambda self: None

    @classmethod
    def tearDownClass(cls):
        cls.PlotVizApp._load_on_startup = cls._orig_load_on_startup

    def _make_window(self):
        # A fresh window per test keeps state isolated.
        w = self.PlotVizApp()
        _app.processEvents()  # drain any other one-shot startup work
        return w

    def test_app_constructs_and_renders(self):
        w = self._make_window()
        self.assertTrue(hasattr(w, "canvas"))
        w.update_preview()
        self.assertTrue(len(w.canvas.axes_list) >= 1)

    def test_load_pviz_populates_and_renders(self):
        w = self._make_window()
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "p.pviz")
            _write_pviz(fp)
            w._load_project_inner(fp, silent=True)
            self.assertIn("x", w.datasets)
            self.assertIn("y", w.datasets)
            self.assertTrue(len(w.canvas.axes_list) >= 1)

    def test_shared_render_path_to_figure(self):
        # Exercises _render_axes (the path shared by preview + export).
        w = self._make_window()
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "p.pviz")
            _write_pviz(fp)
            w._load_project_inner(fp, silent=True)
            fig = Figure(figsize=(6, 4))
            axes_list, ax2_map, is3d, n = w._render_axes(fig)
            self.assertEqual(len(axes_list), 1)
            out = os.path.join(d, "out.png")
            fig.savefig(out)
            self.assertGreater(os.path.getsize(out), 0)

    def test_multi_subplot_layout(self):
        w = self._make_window()
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "p.pviz")
            _write_pviz(fp, rows=2, cols=1)
            w._load_project_inner(fp, silent=True)
            self.assertEqual(len(w.canvas.axes_list), 2)

    def test_annotations_render(self):
        w = self._make_window()
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "p.pviz")
            _write_pviz(fp)
            w._load_project_inner(fp, silent=True)
            ax = w.canvas.axes_list[0]
            w.canvas._place_text_annotation(ax, 0, 5.0, 0.5, label="note")
            w.canvas._place_arrow_annotation(ax, 0, 1.0, 0.0, 3.0, 0.5, label="arr")
            w.update_preview()
            kinds = {a["type"] for a in w.canvas.annotations}
            self.assertEqual(kinds, {"text", "arrow"})
            for a in w.canvas.annotations:
                self.assertIn("artist", a)


if __name__ == "__main__":
    unittest.main()
