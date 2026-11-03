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
    except Exception:  # noqa: BLE001 - any import failure means "no usable Qt"
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

    def test_reloaded_subplots_restart_the_palette_in_each_subplot(self):
        # Series are coloured by their position inside their own subplot, and a
        # reload must give them the same colours (not the global row order).
        from core.serialize import read_project_zip, write_project_zip
        w = self._make_window()
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "base.pviz")
            _write_pviz(base, rows=2, cols=2)
            parts = read_project_zip(base)
            meta = parts["series_meta"]
            meta["series"] = [
                {"x_col": "x", "y_col": c, "label": f"Series {i + 1}", "series_type": "Line",
                 "plot_num": n, "y2": False}
                for i, (c, n) in enumerate([("y", 1), ("z", 2), ("y", 3), ("z", 4), ("z", 1), ("y", 3)])]
            parts["settings"]["curve_styles"] = {}
            fp = os.path.join(d, "grid.pviz")
            write_project_zip(fp, parts["settings"], meta, parts["datasets_raw"])
            w._load_project_inner(fp, silent=True)
            colour = lambda n: w.curve_styles[f"Series {n}"]["color"]          # noqa: E731
            first, second = w._palette_color(0), w._palette_color(1)
            self.assertEqual([colour(1), colour(2), colour(3), colour(4)], [first] * 4)
            self.assertEqual([colour(5), colour(6)], [second] * 2)

    def test_every_subplot_of_a_loaded_chart_gets_the_saved_background(self):
        # A .pviz stores one set of canvas colours; all the subplots must use it,
        # not only the first one (the others used to fall back to white).
        from matplotlib.colors import to_hex
        from core.serialize import read_project_zip, write_project_zip
        w = self._make_window()
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "base.pviz")
            _write_pviz(base, rows=2, cols=2)
            parts = read_project_zip(base)
            parts["settings"].update(plot_bg_color="#fff1e5", chart_bg_color="#e5f1ff",
                                     grid_color="#ff0000")
            fp = os.path.join(d, "bg.pviz")
            write_project_zip(fp, parts["settings"], parts["series_meta"], parts["datasets_raw"])
            w._load_project_inner(fp, silent=True)
            axes_list, *_ = w._render_axes(Figure())
            self.assertEqual(len(axes_list), 4)
            self.assertEqual({to_hex(a.get_facecolor()) for a in axes_list}, {"#fff1e5"})
            self.assertEqual({o["plot_bg"] for o in w.subplot_canvas_opts.values()}, {"#fff1e5"})
            self.assertEqual({o["color"] for o in w.subplot_grid_opts.values()}, {"#ff0000"})

    def test_each_subplot_keeps_its_own_canvas_and_grid_when_saved(self):
        from matplotlib.colors import to_hex
        from core.serialize import encode_datasets, write_project_zip
        w = self._make_window()
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "base.pviz")
            _write_pviz(base, rows=2, cols=2)
            w._load_project_inner(base, silent=True)
            colours = ["#ffe0e0", "#e0ffe0", "#e0e0ff", "#fffbe0"]
            for i in range(4):
                co = w._default_canvas_opts()
                co.update(plot_bg=colours[i], border_top=bool(i % 2))
                go = w._default_grid_opts()
                go.update(enabled=bool(i % 2), color=colours[3 - i])
                w.subplot_canvas_opts[i], w.subplot_grid_opts[i] = co, go
            w._load_canvas_grid_opts(0)                  # the widgets show the active subplot
            fp = os.path.join(d, "per.pviz")
            write_project_zip(fp, w._collect_settings(), w._collect_series_meta(),
                              encode_datasets(w.datasets))
            w2 = self._make_window()
            w2._load_project_inner(fp, silent=True)
            self.assertEqual([w2.subplot_canvas_opts[i]["plot_bg"] for i in range(4)], colours)
            self.assertEqual([w2.subplot_canvas_opts[i]["border_top"] for i in range(4)],
                             [False, True, False, True])
            self.assertEqual([w2.subplot_grid_opts[i]["color"] for i in range(4)], colours[::-1])
            axes_list, *_ = w2._render_axes(Figure())
            self.assertEqual([to_hex(a.get_facecolor()) for a in axes_list], colours)

    def test_multi_subplot_layout(self):
        w = self._make_window()
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "p.pviz")
            _write_pviz(fp, rows=2, cols=1)
            w._load_project_inner(fp, silent=True)
            self.assertEqual(len(w.canvas.axes_list), 2)

    def test_sample_charts_menu_opens_a_dialog_in_the_samples_folder(self):
        # Help > Sample Charts used to only reveal the folder in Finder; it now
        # asks for a chart in an Open dialog that starts in that folder.
        from unittest import mock
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        w = self._make_window()
        with tempfile.TemporaryDirectory() as d, \
                mock.patch("config.settings.plots_dir", return_value=d):
            fp = os.path.join(d, "sample.pviz")
            _write_pviz(fp)
            # Stub the "Chart loaded" message box (modal) and the user-settings writes.
            with mock.patch.object(QFileDialog, "getOpenFileName",
                                   return_value=(fp, "")) as dlg, \
                    mock.patch.object(QMessageBox, "information"), \
                    mock.patch("config.settings.add_recent_file"), \
                    mock.patch("config.settings.remember_dir"):
                w._open_sample_chart()
            self.assertEqual(dlg.call_args.args[2], d)         # starts in the samples folder
            self.assertIn("x", w.datasets)                     # ... and the chart was loaded

    def test_sample_datasets_menu_opens_a_dialog_in_the_samples_folder(self):
        from unittest import mock
        from PyQt6.QtWidgets import QFileDialog
        w = self._make_window()
        with tempfile.TemporaryDirectory() as d, \
                mock.patch("config.settings.datasets_dir", return_value=d), \
                mock.patch("ui.data_io._remember_dir") as remember:
            with mock.patch.object(QFileDialog, "getOpenFileNames",
                                   return_value=([], "")) as dlg:
                w._open_sample_dataset()
            self.assertEqual(dlg.call_args.args[2], d)         # starts in the samples folder
            remember.assert_not_called()                       # samples don't change the "last folder"

    def test_sample_charts_dialog_cancel_loads_nothing(self):
        from unittest import mock
        from PyQt6.QtWidgets import QFileDialog
        w = self._make_window()
        with mock.patch.object(QFileDialog, "getOpenFileName", return_value=("", "")):
            w._open_sample_chart()
        self.assertEqual(w.datasets, {})

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
