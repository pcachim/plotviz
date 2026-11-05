"""The Seaborn Explorer and the Python Code Runner windows, driven without a screen.

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
class TestSeabornCatplot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def explorer(self):
        import numpy as np
        from ui.seaborn_explorer import SeabornExplorer
        rng = np.random.default_rng(1)
        data = {"day": np.array(["Thu", "Fri", "Sat", "Sun"] * 25),
                "bill": rng.uniform(5, 50, 100)}
        dialog = SeabornExplorer(data, ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"])
        dialog._type_combo.setCurrentText("Catplot")
        dialog._x_combo.setCurrentText("day")
        dialog._y_combo.setCurrentText("bill")
        return dialog

    def test_every_kind_draws_without_an_error(self):
        # Regression: 'box' (the default) failed because matplotlib's boxplot takes no alpha,
        # and 'count' failed because it was given both x and y.
        for kind in ("box", "boxen", "violin", "bar", "point", "count", "strip", "swarm"):
            with self.subTest(kind=kind):
                dialog = self.explorer()
                errors = []
                dialog._show_error = errors.append
                dialog._cat_kind.setCurrentText(kind)
                dialog._draw()
                self.assertEqual(errors, [])
                dialog.hide()

    def test_the_alpha_of_box_plots_is_applied_to_the_boxes(self):
        dialog = self.explorer()
        dialog._cat_kind.setCurrentText("box")
        dialog._cat_alpha.setValue(0.4)
        captured = {}
        original = dialog._swap_figure
        dialog._swap_figure = lambda fig: (captured.update(alphas={p.get_alpha() for ax in fig.axes for p in ax.patches}),
                                           original(fig))[1]
        dialog._draw()
        self.assertEqual(captured["alphas"], {0.4})
        dialog.hide()


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestCodeRunnerError(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def test_the_traceback_shows_only_the_users_lines(self):
        from ui.code_runner import CodeRunnerDialog
        dialog = CodeRunnerDialog({"a": [1, 2, 3]})
        dialog._editor.setPlainText("x = 1\ny = datasets['missing']\n")
        dialog._run()
        text = dialog._error_text.toPlainText()
        self.assertTrue(dialog._error_panel.isVisibleTo(dialog))
        self.assertIn("KeyError: 'missing'", text)
        self.assertIn('File "<code_runner>", line 2', text)
        self.assertNotIn("code_runner.py", text)          # plotviz's own exec frame is left out
        self.assertNotIn("noqa", text)
        dialog.hide()

    def test_a_syntax_error_is_reported_too(self):
        from ui.code_runner import CodeRunnerDialog
        dialog = CodeRunnerDialog({})
        dialog._editor.setPlainText("def broken(:\n    pass\n")
        dialog._run()
        self.assertIn("SyntaxError", dialog._error_text.toPlainText())
        dialog.hide()


if __name__ == "__main__":
    unittest.main()
