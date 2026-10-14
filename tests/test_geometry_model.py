"""Margins and title position are stored as fractions of the figure.

The spinboxes only display ``fraction x figure size``. These tests pin the
invariants the old physical-unit model kept breaking: changing the figure size,
unit or preset never moves the layout, editing one value changes only that
fraction, and the exact fractions survive save/load. Older project files (physical
or pre-2.5.8 fractional values) still load to the same layout.

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
DEFAULT_MARGINS = (0.10, 0.95, 0.10, 0.95)
DEFAULT_TITLE = (0.5, 0.97)


@unittest.skipUnless(HAVE_QT, "real PyQt6 not available")
class TestFractionModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import PlotVizApp
        cls._app = QApplication.instance() or QApplication([])
        cls._orig = PlotVizApp._load_on_startup
        PlotVizApp._load_on_startup = lambda self: None
        cls.PlotVizApp = PlotVizApp

    @classmethod
    def tearDownClass(cls):
        cls.PlotVizApp._load_on_startup = cls._orig

    def _win(self):
        w = self.PlotVizApp()
        self._app.processEvents()
        return w

    def assertLayout(self, w, margins=DEFAULT_MARGINS, title=DEFAULT_TITLE):
        for got, want in zip(w._margins_as_fractions(), margins):
            self.assertAlmostEqual(got, want, places=9)
        for got, want in zip(w._title_pos_as_fractions(), title):
            self.assertAlmostEqual(got, want, places=9)

    # ── the layout never moves when the figure changes ────────────────────────
    def test_defaults(self):
        w = self._win()
        self.assertLayout(w)
        self.assertAlmostEqual(w.fig_right.value(), 19.0, places=1)    # 0.95 x 20 cm

    def test_size_edits_keep_the_fractions(self):
        # Regression: widening the figure used to leave the right margin stuck.
        w = self._win()
        for width in (30.0, 13.0, 17.3, 20.0):
            w.fig_width.setValue(width)
            self.assertLayout(w)
            self.assertAlmostEqual(w.fig_right.value(), 0.95 * width, delta=0.051)
            self.assertAlmostEqual(w.title_x.value(), 0.5 * width, delta=0.051)
        for height in (22.0, 8.0, 15.0):
            w.fig_height.setValue(height)
            self.assertLayout(w)
            self.assertAlmostEqual(w.fig_top.value(), 0.95 * height, delta=0.051)

    def test_many_size_changes_do_not_drift(self):
        w = self._win()
        for i in range(40):
            w.fig_width.setValue(10.0 + (i * 7) % 23 + 0.1 * (i % 7))
            w.fig_height.setValue(6.0 + (i * 5) % 17 + 0.1 * (i % 3))
        w.fig_width.setValue(20.0)
        w.fig_height.setValue(15.0)
        self.assertLayout(w)

    def test_unit_round_trip_keeps_the_fractions(self):
        w = self._win()
        for unit in ("inches", "pixels", "cm", "pixels", "inches", "cm"):
            w.fig_unit.setCurrentText(unit)
            self.assertLayout(w)
        self.assertAlmostEqual(w.fig_width.value(), 20.0, places=1)

    def test_preset_change_keeps_the_fractions(self):
        w = self._win()
        for i in range(w.fig_preset_combo.count()):
            w.fig_preset_combo.setCurrentIndex(i)
            self.assertLayout(w)

    # ── editing ───────────────────────────────────────────────────────────────
    def test_editing_one_margin_changes_only_that_fraction(self):
        w = self._win()
        w.fig_width.setValue(17.3)                 # a size where 0.95 x W is not round
        w.fig_left.setValue(3.0)
        l, r, b, t = w._margins_as_fractions()
        self.assertAlmostEqual(l, 3.0 / 17.3, places=9)
        self.assertAlmostEqual(r, 0.95, places=9)  # untouched, not re-quantised
        self.assertAlmostEqual(b, 0.10, places=9)
        self.assertAlmostEqual(t, 0.95, places=9)

    def test_editing_the_title_position(self):
        w = self._win()
        w.title_x.setValue(5.0)
        w.title_y.setValue(12.0)
        tx, ty = w._title_pos_as_fractions()
        self.assertAlmostEqual(tx, 0.25, places=9)
        self.assertAlmostEqual(ty, 0.80, places=9)
        w.fig_width.setValue(40.0)                 # and it follows a size change
        self.assertAlmostEqual(w._title_pos_as_fractions()[0], 0.25, places=9)

    def test_degenerate_margins_never_reach_matplotlib(self):
        w = self._win()
        w.fig_left.setValue(18.0)
        w.fig_right.setValue(2.0)                  # right < left
        w.fig_bottom.setValue(14.0)
        w.fig_top.setValue(1.0)
        l, r, b, t = w._margins_as_fractions()
        self.assertLess(l, r)
        self.assertLess(b, t)
        w.canvas.figure.subplots_adjust(left=l, right=r, bottom=b, top=t)   # must not raise

    def test_export_axes_use_the_margin_fractions(self):
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        w = self._win()
        w.fig_width.setValue(25.0)
        w.fig_height.setValue(11.0)
        w._set_margin_fractions(0.2, 0.9, 0.15, 0.85)
        w.update_preview()
        fig = w._build_export_figure(*w._fig_size_in_inches(), 100)
        FigureCanvasAgg(fig)
        x0, y0, width, height = fig.axes[0].get_position().bounds
        self.assertAlmostEqual(x0, 0.2, places=6)
        self.assertAlmostEqual(x0 + width, 0.9, places=6)
        self.assertAlmostEqual(y0, 0.15, places=6)
        self.assertAlmostEqual(y0 + height, 0.85, places=6)

    # ── files ─────────────────────────────────────────────────────────────────
    def _apply(self, w, settings):
        w._applying_settings = True
        try:
            w._apply_settings(settings)
        finally:
            w._applying_settings = False

    def test_exact_fractions_survive_save_and_load(self):
        w = self._win()
        w._set_margin_fractions(0.1234, 0.9876, 0.0567, 0.9012)
        w._set_title_fractions(0.3333, 0.8765)
        saved = w._collect_settings()
        self.assertEqual(saved["margin_fractions"], [0.1234, 0.9876, 0.0567, 0.9012])
        self.assertEqual(saved["title_pos_fractions"], [0.3333, 0.8765])
        w2 = self._win()
        self._apply(w2, saved)
        self.assertLayout(w2, (0.1234, 0.9876, 0.0567, 0.9012), (0.3333, 0.8765))

    def test_legacy_fields_still_written_for_older_readers(self):
        w = self._win()
        saved = w._collect_settings()
        self.assertEqual(saved["margin_format"], "physical")
        self.assertEqual(saved["title_pos_format"], "physical")
        self.assertAlmostEqual(saved["fig_right"], 19.0, places=4)
        self.assertAlmostEqual(saved["title_x"], 10.0, places=4)

    def test_old_physical_files_load_to_the_same_layout(self):
        w = self._win()
        s = w._collect_settings()
        for key in ("margin_fractions", "title_pos_fractions"):
            s.pop(key)
        s.update(fig_unit="cm", fig_width=30.0, fig_height=10.0,
                 fig_left=3.0, fig_right=27.0, fig_bottom=2.0, fig_top=9.0,
                 margin_format="physical", title_x=15.0, title_y=9.0,
                 title_pos_format="physical")
        w2 = self._win()
        self._apply(w2, s)
        self.assertLayout(w2, (0.1, 0.9, 0.2, 0.9), (0.5, 0.9))

    def test_pre_2_5_8_files_with_fractions_load_unchanged(self):
        w = self._win()
        s = w._collect_settings()
        for key in ("margin_fractions", "title_pos_fractions", "margin_format",
                    "title_pos_format"):
            s.pop(key)
        s.update(fig_left=0.12, fig_right=0.88, fig_bottom=0.11, fig_top=0.93,
                 title_x=0.4, title_y=0.95)
        w2 = self._win()
        self._apply(w2, s)
        self.assertLayout(w2, (0.12, 0.88, 0.11, 0.93), (0.4, 0.95))

    def test_project_file_round_trip_through_a_real_pviz(self):
        from core.serialize import read_project_zip
        w = self._win()
        w.fig_width.setValue(23.7)
        w._set_margin_fractions(0.111, 0.933, 0.077, 0.911)
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "p.pviz")
            from unittest import mock
            from PyQt6.QtWidgets import QFileDialog, QMessageBox
            with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(fp, "")), \
                    mock.patch.object(QMessageBox, "information"), \
                    mock.patch("config.settings.add_recent_file"):
                w._save_project()
            self.assertEqual(read_project_zip(fp)["settings"]["margin_fractions"],
                             [0.111, 0.933, 0.077, 0.911])
            w2 = self._win()
            w2._load_project_inner(fp, silent=True)
        self.assertLayout(w2, (0.111, 0.933, 0.077, 0.911))
        self.assertAlmostEqual(w2.fig_width.value(), 23.7, places=1)


if __name__ == "__main__":
    unittest.main()
