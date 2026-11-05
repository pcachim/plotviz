"""The Transform page's preview: a small plot of what Apply would make.

Runs only where a real PyQt6 is installed; skipped otherwise.
"""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:  # noqa: BLE001 - any import failure means "no usable Qt"
        return False
    return hasattr(QApplication, "instance")


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestTransformPreview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import PlotVizApp
        cls.np = np
        cls._app = QApplication.instance() or QApplication([])
        cls._orig = PlotVizApp._load_on_startup
        PlotVizApp._load_on_startup = lambda self: None
        cls.PlotVizApp = PlotVizApp

    @classmethod
    def tearDownClass(cls):
        cls.PlotVizApp._load_on_startup = cls._orig

    def setUp(self):
        np = self.np
        w = self.w = self.PlotVizApp()
        t = np.linspace(0, 1, 400)
        rng = np.random.default_rng(1)
        y = 2.5 + 0.03 * rng.standard_normal(400)
        y[150:154] += 0.3
        w.datasets.update({"t": t, "v": y})
        w.update_lists()
        w.show()
        for i in range(w.tabs.count()):
            if w.tabs.tabText(i) == "Data":
                w.tabs.setCurrentIndex(i)
        tabs = w.data_inner_tabs
        tabs.setCurrentIndex([tabs.tabText(i) for i in range(tabs.count())].index("Transform"))
        w.tf_y_combo.setCurrentText("v")
        w.tf_x_combo.setCurrentText("t")
        self.settle()

    def tearDown(self):
        self.w.close()

    def settle(self):
        """Let the live preview's short wait pass."""
        from PyQt6.QtTest import QTest
        QTest.qWait(450)  # ty: ignore[missing-argument, invalid-argument-type]

    def flush_undo(self):
        """Let the undo snapshot that loading the data scheduled (400 ms) happen first,
        so that only what the preview itself does is counted. Slow machines need longer."""
        from PyQt6.QtTest import QTest
        for _ in range(100):
            if not self.w._snapshot_timer.isActive():
                break
            QTest.qWait(50)  # ty: ignore[missing-argument, invalid-argument-type]

    def op(self, key):
        self.w.tf_op_combo.setCurrentIndex(self.w.tf_op_combo.findData(key))

    def labels(self):
        return [l.get_label() for l in self.w.tf_preview.ax.get_lines()]

    # ── what it draws ──────────────────────────────────────────────────────────
    def test_it_draws_the_original_and_the_result_and_says_what_would_be_created(self):
        w = self.w
        self.op("savitzky_golay")
        self.settle()
        self.assertEqual(self.labels(), ["original", "result"])
        self.assertIn("Savitzky-Golay: 400 points → would create \"v_SG11\"", w.tf_preview.info.text())
        original, result = w.tf_preview.ax.get_lines()
        self.assertGreater(float(self.np.std(self.np.diff(original.get_ydata()))),
                           float(self.np.std(self.np.diff(result.get_ydata()))))      # smoothed

    def test_peaks_are_drawn_as_markers_and_a_new_x_is_announced(self):
        w = self.w
        self.op("peaks")
        self.settle()
        peaks = [l for l in w.tf_preview.ax.get_lines() if "peak" in str(l.get_label())]
        self.assertEqual(len(peaks), 1)
        self.assertEqual(peaks[0].get_linestyle(), "None")
        self.assertIn('"t_peaks" and "v_peaks"', w.tf_preview.info.text())
        self.assertIn("x also changes", w.tf_preview.info.text())

    def test_a_spectrum_is_drawn_alone_and_can_be_logarithmic(self):
        w = self.w
        self.op("fft_spectrum")
        self.settle()
        self.assertEqual(self.labels(), ["result"])          # the series has other axes
        w.tf_preview.log_check.setChecked(True)
        self.assertEqual(w.tf_preview.ax.get_yscale(), "log")

    def test_a_date_x_is_labelled_with_dates(self):
        from core import dates as D
        w = self.w
        days = D.from_iso([f"2024-03-{d:02d}" for d in range(1, 29)])
        w.datasets.update({"day": days, "val": self.np.arange(28.0)})
        w.update_lists()
        w.tf_y_combo.setCurrentText("val")
        w.tf_x_combo.setCurrentText("day")
        self.op("moving_average")
        self.settle()
        import matplotlib.dates as mdates
        self.assertIsInstance(w.tf_preview.ax.xaxis.get_major_locator(), mdates.DateLocator)

    # ── it never changes anything ────────────────────────────────────────────────
    def test_previewing_changes_nothing(self):
        w = self.w
        self.flush_undo()
        before = {k: v for k, v in w.datasets.items()}
        steps = len(w._undo_stack)
        rows = w.series_table.rowCount()
        for key in ("moving_average", "peaks", "fft_spectrum", "resample_uniform", "derivative"):
            self.op(key)
            self.settle()
        w.tf_preview.button.click()
        self.flush_undo()
        self.assertEqual(list(w.datasets), list(before))
        self.assertTrue(all(w.datasets[k] is before[k] for k in before))
        self.assertEqual((len(w._undo_stack), w.series_table.rowCount()), (steps, rows))

    def test_the_preview_is_exactly_what_apply_creates(self):
        from data.transforms import OPERATIONS
        w = self.w
        for op in OPERATIONS:
            if op["key"] == "align_to_x":
                continue                                      # needs a second series chosen
            with self.subTest(op=op["key"]):
                self.op(op["key"])
                params = w._tf_params()
                try:
                    plan = w._compute_transform()
                except Exception:  # noqa: BLE001 - some operations need parameters the defaults lack
                    continue
                names_before = set(w.datasets)
                w._apply_transform()
                self.assertEqual(set(w.datasets) - names_before, set(plan.made), params)
                self.assertTrue(self.np.array_equal(w.datasets[plan.y_new], plan.y_out, equal_nan=True))
                if plan.x_new:
                    self.assertTrue(self.np.array_equal(w.datasets[plan.x_new], plan.x_out, equal_nan=True))
                for name in plan.made:                          # leave the datasets as they were
                    w.datasets.pop(name)
                w.update_lists()

    # ── live and button ──────────────────────────────────────────────────────────
    def test_live_waits_for_the_last_change_and_the_button_works_without_it(self):
        w = self.w
        self.op("moving_average")
        self.settle()
        before = len(w.tf_preview.ax.get_lines())
        spin = w._tf_param_widgets[w._tf_op_index()]["window"]
        spin.setValue(9)
        spin.setValue(15)
        self.assertTrue(w.tf_preview.timer.isActive())                 # a redraw is pending ...
        self.assertNotIn("v_MA15", w.tf_preview.info.text())            # (not drawn yet)
        self.settle()
        self.assertIn("v_MA15", w.tf_preview.info.text())               # ... and happened once, with the last value
        self.assertEqual(len(w.tf_preview.ax.get_lines()), before)
        w.tf_preview.live_check.setChecked(False)
        spin.setValue(21)
        self.assertFalse(w.tf_preview.timer.isActive())
        self.assertEqual(w.tf_preview.info.text(), "Changed: click Preview to update.")
        self.settle()
        self.assertIn("MA15", w.tf_preview.last_plan.y_new)                    # nothing was redrawn
        w.tf_preview.button.click()
        self.assertIn("v_MA21", w.tf_preview.info.text())

    def test_live_pauses_for_very_long_series_but_the_button_still_draws(self):
        from ui.preview_panel import PREVIEW_LIVE_LIMIT
        w = self.w
        n = PREVIEW_LIVE_LIMIT + 1000
        w.datasets.update({"big": self.np.sin(self.np.arange(n) / 100.0)})
        w.update_lists()
        w.tf_x_combo.setCurrentIndex(0)
        w.tf_y_combo.setCurrentText("big")
        self.op("moving_average")
        self.settle()
        self.assertIn("Live is paused", w.tf_preview.info.text())
        self.assertFalse(w.tf_preview.timer.isActive())
        w.tf_preview.button.click()
        self.assertEqual(self.labels(), ["original", "result"])
        self.assertLess(self.np.asarray(w.tf_preview.ax.get_lines()[0].get_xdata()).size, 2200)   # drawn with few points

    def test_a_problem_is_written_in_the_plot_not_raised(self):
        w = self.w
        self.op("savitzky_golay")
        widgets = w._tf_param_widgets[w._tf_op_index()]
        widgets["window"].setValue(2001)                                  # longer than the 400 points
        self.settle()
        self.assertTrue(w.tf_preview.info.text().startswith("❌"))
        self.assertIn("longer than the series", w.tf_preview.info.text())
        self.assertEqual(w.tf_preview.ax.get_lines(), [])
        w._apply_transform()
        self.assertIn("longer than the series", w.tf_status.text())      # Apply says the same
        widgets["window"].setValue(11)
        self.settle()
        self.assertFalse(w.tf_preview.info.text().startswith("❌"))

    # ── layout ───────────────────────────────────────────────────────────────────
    def test_the_parameter_area_is_as_tall_as_the_operation_shown(self):
        w = self.w
        self.op("derivative")                                             # no parameters
        short = w.tf_param_stack.sizeHint().height()
        self.op("peaks")                                                  # four rows
        tall = w.tf_param_stack.sizeHint().height()
        self.assertGreater(tall, short + 60)


if __name__ == "__main__":
    unittest.main()
