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
class PreviewCase(unittest.TestCase):
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


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestGeneratePreview(PreviewCase):
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


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestGridPreviews(PreviewCase):
    """z = f(x, y) and (u, v) = f(x, y): the same behaviour, on their own pages."""

    def page(self, title):
        tabs = self.w.gen_inner_tabs
        tabs.setCurrentIndex([tabs.tabText(i) for i in range(tabs.count())].index(title))
        self.settle()

    def test_z_is_drawn_as_a_grid_and_named(self):
        w = self.w
        self.page("z=f(x,y)")
        w.fxy_meshgrid.setChecked(True)
        w.fxy_x_n.setValue(30)
        w.fxy_y_n.setValue(20)
        self.settle()
        self.assertIn("600 points (30 × 20 grid)", w.fxy_preview.info.text())
        self.assertIn('would create "x", "y", "z"', w.fxy_preview.info.text())
        self.assertGreaterEqual(len(w.fxy_preview.ax.collections), 2)    # filled contours and their lines
        self.assertEqual(w.fxy_preview.ax.get_xlabel(), "x")

    def test_without_meshgrid_the_points_are_scattered(self):
        w = self.w
        self.page("z=f(x,y)")
        self.assertTrue(w.fxy_meshgrid.isChecked())                       # on by default
        w.fxy_meshgrid.setChecked(False)
        self.settle()
        self.assertIn("50 points", w.fxy_preview.info.text())
        self.assertNotIn(" grid)", w.fxy_preview.info.text())
        self.assertIn("Without Meshgrid", w.fxy_preview.info.text())

    def test_the_vectors_are_drawn_as_arrows(self):
        w = self.w
        self.page("(u,v)=f(x,y)")
        w.fuv_meshgrid.setChecked(True)
        self.settle()
        self.assertIn('"u", "v"', w.fuv_preview.info.text())
        self.assertIn("|(u, v)| from", w.fuv_preview.info.text())
        self.assertEqual(len(w.fuv_preview.ax.collections), 1)           # the quiver

    def test_previews_change_nothing_and_match_the_buttons(self):
        w = self.w
        for page, preview, plan_of, button, outs in (
                ("z=f(x,y)", w.fxy_preview, w._compute_fxy, w._generate_fxy, ["z"]),
                ("(u,v)=f(x,y)", w.fuv_preview, w._compute_fuv, w._generate_fuv, ["u", "v"])):
            with self.subTest(page=page):
                self.page(page)
                w.datasets.clear()
                preview.button.click()
                self.assertEqual(w.datasets, {})
                for flag in (False, True):
                    getattr(w, "fxy_meshgrid" if outs == ["z"] else "fuv_meshgrid").setChecked(flag)
                    plan = plan_of()
                    button()
                    for name in plan.made:
                        self.assertIn(name, w.datasets)
                    for _, name, values in plan.outputs:
                        self.assertTrue(self.np.array_equal(w.datasets[name], values, equal_nan=True))
                    if plan.x_new:
                        self.assertTrue(self.np.array_equal(w.datasets[plan.x_new], plan.x))
                    w.datasets.clear()

    def test_each_axis_has_its_own_input_choice(self):
        w = self.w
        w.fxy_x_mode_col.setChecked(True)
        w.fxy_y_mode_col.setChecked(True)
        w.fxy_y_mode_range.setChecked(True)               # y back to a range: x must stay a column
        self.assertTrue(w.fxy_x_mode_col.isChecked())
        self.assertFalse(w.fxy_x_mode_range.isChecked())
        w.fuv_x_mode_col.setChecked(True)
        w.fuv_y_mode_col.setChecked(True)
        self.assertTrue(w.fuv_x_mode_col.isChecked())

    def test_columns_are_used_as_they_are(self):
        w = self.w
        w.datasets.update({"a": self.np.arange(5.0), "b": self.np.arange(5.0) * 2})
        w.update_lists()
        self.page("z=f(x,y)")
        w.fxy_x_mode_col.setChecked(True)
        w.fxy_y_mode_col.setChecked(True)
        w.fxy_x_combo.setCurrentText("a")
        w.fxy_y_combo.setCurrentText("b")
        w.fxy_expr.setText("x + y")
        w.fxy_meshgrid.setChecked(False)
        plan = w._compute_fxy()
        self.assertEqual((plan.x_name, plan.y_name, plan.x_new, plan.y_new), ("a", "b", None, None))
        self.assertEqual(plan.made, ["z"])
        self.assertEqual(list(plan.outputs[0][2]), [0, 3, 6, 9, 12])

    def test_random_axes_are_not_the_same_draw(self):
        w = self.w
        self.page("z=f(x,y)")
        w.fxy_meshgrid.setChecked(False)
        w.fxy_x_spacing.setCurrentText("random")
        w.fxy_y_spacing.setCurrentText("random")
        plan = w._compute_fxy()
        self.assertFalse(self.np.array_equal(plan.x, plan.y))
        self.assertTrue(self.np.array_equal(plan.x, w._compute_fxy().x))

    def test_problems_are_written_in_the_plot(self):
        w = self.w
        self.page("z=f(x,y)")
        w.fxy_expr.setText("")
        self.settle()
        self.assertIn("Expression is empty", w.fxy_preview.info.text())
        w.fxy_expr.setText("x + nothing")
        w.fxy_x_min.setValue(9)
        w.fxy_x_max.setValue(1)
        self.settle()
        self.assertIn("x: x_min must be less than x_max", w.fxy_preview.info.text())
        w._generate_fxy()
        self.assertTrue(w.fxy_status.text().startswith("\u274c"))
        self.page("(u,v)=f(x,y)")
        w.fuv_v_expr.setText("")
        self.settle()
        self.assertIn("v expression is empty", w.fuv_preview.info.text())


if __name__ == "__main__":
    unittest.main()
