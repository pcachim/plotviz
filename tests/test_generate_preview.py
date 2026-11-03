"""The Generate page's preview: a small plot of what the button would create.

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
class TestGeneratePreview(unittest.TestCase):
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
        w = self.w = self.PlotVizApp()
        w.show()
        for i in range(w.tabs.count()):
            if w.tabs.tabText(i) == "Data":
                w.tabs.setCurrentIndex(i)
        tabs = w.data_inner_tabs
        tabs.setCurrentIndex([tabs.tabText(i) for i in range(tabs.count())].index("Generate"))
        self.settle()

    def tearDown(self):
        self.w.close()

    def settle(self):
        from PyQt6.QtTest import QTest
        QTest.qWait(450)  # ty: ignore[missing-argument, invalid-argument-type]

    def labels(self):
        return [str(l.get_label()) for l in self.w.gen_preview.ax.get_lines()]

    def test_it_draws_the_function_and_names_what_would_be_created(self):
        w = self.w
        w.gen_expr.setText("x**2")
        self.settle()
        self.assertEqual(self.labels(), ["y"])
        self.assertIn('would create "x" and "y"', w.gen_preview.info.text())
        self.assertIn("200 points", w.gen_preview.info.text())
        w.gen_x_n.setValue(50)
        self.settle()
        self.assertIn("50 points", w.gen_preview.info.text())

    def test_previewing_changes_nothing(self):
        w = self.w
        for expr in ("sin(x)", "x**2", "exp(-x)"):
            w.gen_expr.setText(expr)
            self.settle()
        w.gen_preview.button.click()
        self.assertEqual(w.datasets, {})
        self.assertEqual(w.gen_status.text(), "")

    def test_the_preview_is_exactly_what_generate_creates(self):
        w = self.w
        w.gen_expr.setText("3 * sin(2 * x) + 1")
        w.gen_x_name.setText("t")
        w.gen_y_name.setText("s")
        w.gen_preview.update_preview(forced=True)
        plan = w.gen_preview.last_plan
        w._adv_generate_or_apply()
        self.assertEqual(set(w.datasets), {"t", "s"})
        self.assertTrue(self.np.array_equal(w.datasets["t"], plan.x))
        self.assertTrue(self.np.array_equal(w.datasets["s"], plan.y))

    def test_random_spacing_does_not_flicker_and_matches_apply(self):
        w = self.w
        w.gen_x_spacing.setCurrentText("random")
        w.gen_expr.setText("x")
        w.gen_preview.update_preview(forced=True)
        first = w._compute_generate().x
        self.assertTrue(self.np.array_equal(first, w._compute_generate().x))   # same draw each time
        w._adv_generate_or_apply()
        self.assertTrue(self.np.array_equal(w.datasets["x"], first))
        self.assertFalse(self.np.array_equal(w._compute_generate().x, first))  # a new draw after Apply

    def test_the_names_follow_the_ones_already_taken(self):
        w = self.w
        w.gen_x_name.setText("a")
        w.gen_y_name.setText("a")                       # the same name for both
        plan = w._compute_generate()
        self.assertEqual(plan.made, ["a", "a_1"])
        w.datasets["a"] = self.np.arange(3.0)
        self.assertEqual(w._compute_generate().made, ["a_1", "a_2"])

    def test_a_column_is_drawn_against_the_original(self):
        w = self.w
        w.datasets["v"] = self.np.linspace(1, 5, 40)
        w.update_lists()
        w._adv_mode_col.setChecked(True)
        w.fn_source_combo.setCurrentText("v")
        w.gen_expr.setText("x * 10")
        w.gen_y_name.setText("v10")
        self.settle()
        self.assertEqual(self.labels(), ["v", "v10"])
        self.assertIn('would create "v10"', w.gen_preview.info.text())
        w._adv_generate_or_apply()
        self.assertTrue(self.np.allclose(w.datasets["v10"], w.datasets["v"] * 10))

    def test_logspace_draws_a_log_x_axis(self):
        w = self.w
        w.gen_x_spacing.setCurrentText("logspace")
        w.gen_x_min.setValue(0)
        w.gen_x_max.setValue(3)
        w.gen_expr.setText("x")
        self.settle()
        self.assertEqual(w.gen_preview.ax.get_xscale(), "log")

    def test_problems_are_written_in_the_plot_and_by_the_button(self):
        w = self.w
        for expr, message in (("sin(", "'('"), ("nothing_here(x)", "not defined"), ("", "Type an expression")):
            w.gen_expr.setText(expr)
            self.settle()
            self.assertTrue(w.gen_preview.info.text().startswith("❌"), expr)
            self.assertEqual(w.gen_preview.ax.get_lines(), [])
            w._adv_generate_or_apply()
            self.assertTrue(w.gen_status.text().startswith("❌"), expr)
        w.gen_expr.setText("sin(x)")
        w.gen_x_min.setValue(5)
        w.gen_x_max.setValue(1)
        self.settle()
        self.assertIn("x_min must be less than x_max", w.gen_preview.info.text())
        self.assertEqual(w.datasets, {})

    def test_live_waits_and_can_be_switched_off(self):
        w = self.w
        w.gen_expr.setText("x")
        self.settle()
        w.gen_expr.setText("x + 1")
        w.gen_expr.setText("x + 2")
        self.assertTrue(w.gen_preview.timer.isActive())
        w.gen_preview.live_check.setChecked(False)
        self.assertFalse(w.gen_preview.timer.isActive())
        self.assertEqual(w.gen_preview.info.text(), "Changed: click Preview to update.")
        w.gen_preview.button.click()
        self.assertIn('would create "x" and "y"', w.gen_preview.info.text())

    def test_live_pauses_for_a_very_long_column(self):
        from ui.preview_panel import PREVIEW_LIVE_LIMIT
        w = self.w
        w.datasets["big"] = self.np.arange(PREVIEW_LIVE_LIMIT + 10, dtype=float)
        w.update_lists()
        w._adv_mode_col.setChecked(True)
        w.fn_source_combo.setCurrentText("big")
        w.gen_expr.setText("x * 2")
        self.settle()
        self.assertIn("Live is paused", w.gen_preview.info.text())
        w.gen_preview.button.click()
        self.assertEqual(self.labels(), ["big", "y"])
        self.assertLess(self.np.asarray(w.gen_preview.ax.get_lines()[0].get_xdata()).size, 2200)


if __name__ == "__main__":
    unittest.main()
