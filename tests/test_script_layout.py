"""The exported Python script must lay the chart out like the exported image.

Each case builds the figure two ways from the same app state - the app's export
figure and the generated plot.py, executed in-process - and compares the figure
size, where the axes sit on the page and where the title is drawn. Before the
generator used the app's margins (it called tight_layout) and ignored the title's
alignment, these differed by 10% of the page or more.

Runs only where a real PyQt6 is installed; skipped otherwise.
"""
import csv
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

import _bootstrap  # noqa: F401,E402
from core.script_gen import _margin_fractions  # noqa: E402


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:  # noqa: BLE001 - any import failure means "no usable Qt"
        return False
    return hasattr(QApplication, "instance")


HAVE_QT = _have_real_qt()


class TestMarginFractions(unittest.TestCase):
    """Pure: how the generator reads the margins out of the settings."""

    def test_exact_fractions_win(self):
        s = {"margin_fractions": [0.2, 0.9, 0.15, 0.8], "fig_left": 99, "margin_format": "physical"}
        self.assertEqual(_margin_fractions(s, 20, 15), (0.2, 0.9, 0.15, 0.8))

    def test_physical_values_are_divided_by_the_figure_size(self):
        s = {"fig_left": 3.0, "fig_right": 27.0, "fig_bottom": 2.0, "fig_top": 9.0,
             "margin_format": "physical"}
        self.assertEqual(_margin_fractions(s, 30.0, 10.0), (0.1, 0.9, 0.2, 0.9))

    def test_old_files_hold_plain_fractions(self):
        s = {"fig_left": 0.12, "fig_right": 0.88, "fig_bottom": 0.11, "fig_top": 0.93}
        self.assertEqual(_margin_fractions(s, 20, 15), (0.12, 0.88, 0.11, 0.93))

    def test_defaults(self):
        self.assertEqual(_margin_fractions({}, 20, 15), (0.10, 0.95, 0.10, 0.95))

    def test_degenerate_margins_are_nudged_apart_like_the_live_chart(self):
        left, right, bottom, top = _margin_fractions(
            {"margin_fractions": [0.9, 0.2, 0.8, 0.1]}, 20, 15)
        self.assertLess(left, right)
        self.assertLess(bottom, top)


@unittest.skipUnless(HAVE_QT, "real PyQt6 not available")
class TestScriptLayoutMatchesExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import matplotlib
        from PyQt6.QtWidgets import QApplication
        import test_chart_types as tc
        from ui.main_window import PlotVizApp
        cls._app = QApplication.instance() or QApplication([])
        cls._orig = PlotVizApp._load_on_startup
        PlotVizApp._load_on_startup = lambda self: None
        cls.PlotVizApp, cls.tc, cls.matplotlib = PlotVizApp, tc, matplotlib

    @classmethod
    def tearDownClass(cls):
        cls.PlotVizApp._load_on_startup = cls._orig

    # ── helpers ───────────────────────────────────────────────────────────────
    def _window(self, types=None, chart="Line", mode="Standard"):
        w = self.PlotVizApp()
        self._app.processEvents()
        self.matplotlib.rcParams["text.usetex"] = False      # as in the packaged app
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "p.pviz")
            if types:
                self.tc._write_multi_pviz(fp, types)
            else:
                self.tc._write_pviz(fp, chart, mode)
            w._load_project_inner(fp, silent=True)
        return w

    def _export_figure(self, w):
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        wi, hi = w._fig_size_in_inches()
        old = self.matplotlib.rcParams.get("font.family")
        self.matplotlib.rcParams["font.family"] = w.title_font.currentText()
        try:
            fig = w._build_export_figure(wi, hi, 100)
            FigureCanvasAgg(fig).draw()
        finally:
            self.matplotlib.rcParams["font.family"] = old
        return fig

    def _script_figure(self, w):
        import matplotlib.pyplot as plt
        from core.script_gen import generate_plot_script
        settings = w._collect_settings()
        settings["annotations"] = w._collect_annotations_meta()
        meta = w._collect_series_meta()
        used = {c for s in meta["series"] for c in (s["x_col"], s["y_col"]) if c in w.datasets}
        for key in ("z_col", "err_col"):
            if meta.get(key) not in (None, "", "(none)") and meta[key] in w.datasets:
                used.add(meta[key])
        data = {k: w.datasets[k] for k in used}
        script = generate_plot_script(settings, meta, data,
                                      [w._palette_color(i) for i in range(16)], "chart")
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "data"))
            names, n = list(data), max(len(v) for v in data.values())
            with open(os.path.join(d, "data", "data.csv"), "w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(names)
                for i in range(n):
                    writer.writerow([data[c][i] for c in names])
            path = os.path.join(d, "plot.py")
            plt.close("all")
            real_show, plt.show = plt.show, lambda *a, **k: None
            try:
                exec(compile(script, path, "exec"), {"__file__": path, "__name__": "__main__"})
            finally:
                plt.show = real_show
            fig = plt.gcf()
            fig.canvas.draw()
        return fig, script

    @staticmethod
    def _title_box(fig):
        """Title extent as fractions of the figure (x0, x1, y0, y1)."""
        box = fig._suptitle.get_window_extent(fig.canvas.get_renderer())
        w, h = fig.bbox.width, fig.bbox.height
        return box.x0 / w, box.x1 / w, box.y0 / h, box.y1 / h

    def assertSameLayout(self, w, what, tol=2e-3):
        export_fig = self._export_figure(w)
        script_fig, script = self._script_figure(w)
        for got, want in zip(script_fig.get_size_inches(), export_fig.get_size_inches()):
            self.assertAlmostEqual(got, want, places=3, msg=f"{what}: figure size")
        self.assertGreaterEqual(len(script_fig.axes), 1, what)
        for ax_s, ax_e in zip(script_fig.axes[:len(export_fig.axes)], export_fig.axes):
            if ax_s.get_label() == "<colorbar>" or ax_e.get_label() == "<colorbar>":
                continue
            for got, want in zip(ax_s.get_position().bounds, ax_e.get_position().bounds):
                self.assertAlmostEqual(got, want, delta=tol, msg=f"{what}: axes box")
        if export_fig._suptitle.get_text():
            self.assertEqual(script_fig._suptitle.get_text(), export_fig._suptitle.get_text(), what)
            for got, want in zip(self._title_box(script_fig), self._title_box(export_fig)):
                self.assertAlmostEqual(got, want, delta=tol, msg=f"{what}: title box")
        return script

    # ── cases ─────────────────────────────────────────────────────────────────
    def test_default_chart(self):
        self.assertSameLayout(self._window(), "default")

    def test_custom_size_margins_and_title_position(self):
        w = self._window()
        w.fig_width.setValue(12.0)
        w.fig_height.setValue(9.0)
        w._set_margin_fractions(0.2, 0.9, 0.15, 0.8)
        w._set_title_fractions(0.3, 0.92)
        self.assertSameLayout(w, "custom margins")

    def test_title_alignment_and_rotation(self):
        for ha in ("left", "center", "right"):
            w = self._window()
            w._set_title_fractions({"left": 0.1, "center": 0.5, "right": 0.9}[ha], 0.95)
            w.title_ha.setCurrentText(ha)
            w.title_rotation.setValue(8)
            self.assertSameLayout(w, f"title ha={ha}")

    def test_small_figure_is_exact(self):
        w = self._window()
        w.fig_width.setValue(8.5)
        w.fig_height.setValue(6.0)
        self.assertSameLayout(w, "8.5 x 6 cm")

    def test_pixel_units(self):
        w = self._window()
        w.fig_unit.setCurrentText("pixels")
        w.fig_width.setValue(900)
        w.fig_height.setValue(600)
        self.assertSameLayout(w, "pixels")

    def test_empty_title_uses_the_live_charts_placeholder(self):
        w = self._window()
        w.title_input.setText("")
        script = self.assertSameLayout(w, "empty title")
        self.assertIn("Main title", script)

    def test_subplot_grid(self):
        w = self._window(types=["Line", "Scatter", "Bar", "Line"])
        w._set_margin_fractions(0.12, 0.96, 0.1, 0.88)
        self.assertSameLayout(w, "2x2 grid")

    def test_mosaic(self):
        w = self._window(types=["Line", "Scatter", "Bar"])
        w._subplot_mosaic = [["A", "B"], ["C", "C"]]
        self.assertSameLayout(w, "mosaic")

    def test_colorbar_chart(self):
        self.assertSameLayout(self._window(chart="Heatmap", mode="Heatmap & Contour"), "heatmap")

    def test_script_has_no_tight_layout(self):
        script = self.assertSameLayout(self._window(), "no tight_layout")
        self.assertNotIn("tight_layout", script)
        self.assertIn("fig.subplots_adjust(left=", script)


if __name__ == "__main__":
    unittest.main()
