"""The question asked when saving: which dataset columns to put in the file.

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
class TestSaveColumnsDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import PlotVizApp
        cls._app = QApplication.instance() or QApplication([])
        cls._orig = PlotVizApp._load_on_startup
        PlotVizApp._load_on_startup = lambda self: None
        cls.PlotVizApp = PlotVizApp
        cls.original_style = cls._app.style().objectName()

    @classmethod
    def tearDownClass(cls):
        cls.PlotVizApp._load_on_startup = cls._orig
        cls._app.setStyle(cls.original_style)

    def setUp(self):
        self.w = self.PlotVizApp()

    def left_to_right(self, style):
        self._app.setStyle(style)
        dlg, used, all_, cancel = self.w._make_save_columns_dialog()
        dlg.show()
        self._app.processEvents()
        x = {b: b.mapTo(dlg, b.rect().topLeft()).x() for b in (used, all_, cancel)}
        dlg.close()
        return [b.text() for b in sorted(x, key=lambda b: x[b])]

    def test_all_columns_is_on_the_right_on_every_platform_layout(self):
        for style in ("macOS", "Windows", "Fusion"):
            with self.subTest(style=style):
                self.assertEqual(self.left_to_right(style), ["Cancel", "Used series only", "All columns"])

    def test_all_columns_is_the_default_and_escape_cancels(self):
        dlg, used, all_, cancel = self.w._make_save_columns_dialog()
        self.assertIs(dlg.defaultButton(), all_)
        self.assertIs(dlg.escapeButton(), cancel)
        dlg.close()

    def answer(self, act):
        """Run the question, doing *act(dialog, buttons)* once it is open; return its result."""
        from PyQt6.QtCore import QTimer
        real = self.w._make_save_columns_dialog
        holder = {}

        def make():
            holder["parts"] = real()
            return holder["parts"]

        self.w._make_save_columns_dialog = make
        QTimer.singleShot(50, lambda: act(*holder["parts"]))
        return self.w._ask_columns_to_save()

    def test_the_answers(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.assertIs(self.answer(lambda d, u, a, c: u.click()), True)           # used series only
        self.assertIs(self.answer(lambda d, u, a, c: a.click()), False)          # all columns
        self.assertIs(self.answer(lambda d, u, a, c: c.click()), None)           # cancel
        self.assertIs(self.answer(lambda d, u, a, c: QTest.keyClick(d, Qt.Key.Key_Escape)), None)  # ty: ignore[no-matching-overload]
        # Enter, the default: all columns
        self.assertIs(self.answer(lambda d, u, a, c: QTest.keyClick(d, Qt.Key.Key_Return)), False)  # ty: ignore[no-matching-overload]


if __name__ == "__main__":
    unittest.main()
