"""Save/load round-trip of .pviz project files through the real GUI.

Loads a project, saves it again with the app's own ``_save_project`` and checks
that nothing the user cares about is lost: the series table, the datasets and
the settings. A second load+save must reproduce the first save exactly
(idempotence), which catches keys that are written but not read back (or the
reverse).

Runs only where a real PyQt6 is installed; skipped otherwise.
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

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
    return hasattr(QApplication, "instance")


HAVE_QT = _have_real_qt()

if HAVE_QT:
    import numpy as np
    from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
    from core.serialize import encode_datasets, read_project_zip, write_project_zip

    _app = QApplication.instance() or QApplication([])

    def _write_pviz(path):
        settings = {
            "_app": "plotviz", "_version": "1.2", "_file_type": "project",
            "chart_type": "Line", "subplot_rows": 2, "subplot_cols": 1,
            "title_show": True, "title_text": "round trip", "title_font": "DejaVu Sans",
            "title_size": 14, "title_color": "#000", "title_x": 0.5, "title_y": 0.98,
            "title_pos_format": "fractions", "title_ha": "center", "title_rotation": 0,
            "fig_unit": "cm", "fig_width": 20.0, "fig_height": 15.0, "dpi": 150,
            "chart_bg_color": "#fff", "plot_bg_color": "#fff", "chart_fg_color": "#000",
            "grid_on": True, "subplot_chart_types": {"0": "Line", "1": "Bar"},
        }
        series = [
            {"x_col": "x", "y_col": "y", "label": "sine", "series_type": "Line",
             "plot_num": 1, "y2": False},
            {"x_col": "x", "y_col": "z", "label": "cosine", "series_type": "Bar",
             "plot_num": 2, "y2": False},
        ]
        meta = {"series": series, "z_col": "(none)", "err_col": "(none)",
                "subplot_chart_types": {"0": "Line", "1": "Bar"}}
        x = np.linspace(0, 10, 12)
        datasets = {"x": list(x), "y": list(np.sin(x)), "z": list(np.cos(x))}
        write_project_zip(path, settings, meta, encode_datasets(datasets))


@unittest.skipUnless(HAVE_QT, "real PyQt6 not available")
class TestProjectRoundTrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ui.main_window import PlotVizApp
        cls.PlotVizApp = PlotVizApp
        cls._orig = PlotVizApp._load_on_startup
        PlotVizApp._load_on_startup = lambda self: None

    @classmethod
    def tearDownClass(cls):
        cls.PlotVizApp._load_on_startup = cls._orig

    def _save(self, win, path):
        """Run the app's own _save_project, with dialogs and user config stubbed."""
        def _fail(*a, **k):
            raise AssertionError("save reported an error: %r" % (a,))
        with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(path, "")), \
             mock.patch.object(QMessageBox, "information"), \
             mock.patch.object(QMessageBox, "critical", side_effect=_fail), \
             mock.patch("config.settings.add_recent_file"):
            win._save_project()
        self.assertTrue(os.path.exists(path))

    def _open(self, path):
        w = self.PlotVizApp()
        _app.processEvents()
        w._load_project_inner(path, silent=True)
        return w

    def test_save_preserves_series_datasets_and_settings(self):
        with tempfile.TemporaryDirectory() as d:
            src, out = os.path.join(d, "a.pviz"), os.path.join(d, "b.pviz")
            _write_pviz(src)
            self._save(self._open(src), out)

            a, b = read_project_zip(src), read_project_zip(out)
            for key in ("chart_type", "title_text", "fig_width", "fig_height",
                        "subplot_rows", "subplot_cols"):
                self.assertEqual(b["settings"][key], a["settings"][key], key)
            keep = ("x_col", "y_col", "label", "series_type", "plot_num")
            self.assertEqual(
                [{k: s[k] for k in keep} for s in b["series_meta"]["series"]],
                [{k: s[k] for k in keep} for s in a["series_meta"]["series"]])
            self.assertEqual(b["datasets_raw"], a["datasets_raw"])

    def test_save_reaches_a_fixed_point(self):
        # The first reload may materialise defaults (e.g. curve_styles gain
        # ``color_locked: False``), so compare save #2 with save #3: from then on
        # load+save must be a no-op.
        with tempfile.TemporaryDirectory() as d:
            paths = [os.path.join(d, n) for n in ("a.pviz", "b.pviz", "c.pviz", "d.pviz")]
            _write_pviz(paths[0])
            for before, after in zip(paths, paths[1:]):
                self._save(self._open(before), after)

            c, e = read_project_zip(paths[2]), read_project_zip(paths[3])
            self.assertEqual(e["settings"], c["settings"])
            self.assertEqual(e["series_meta"], c["series_meta"])
            self.assertEqual(e["datasets_raw"], c["datasets_raw"])

if __name__ == "__main__":
    unittest.main()
