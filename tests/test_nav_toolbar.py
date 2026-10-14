"""The chart toolbar must not touch the mouse cursor while drawing.

matplotlib's Agg canvas wraps each draw in ``toolbar._wait_cursor_for_draw_cm()``,
which calls QWidget.setCursor(WaitCursor). On macOS 27 / Qt 6.11 that call crashed
the app when a chart was loaded (see ui/nav_toolbar.py), so SafeNavigationToolbar
turns it off.

Runs only where a real PyQt6 is installed; skipped otherwise.
"""
import os
import sys
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
    except Exception:  # noqa: BLE001 - any import failure means "no usable Qt"
        return False
    return hasattr(QApplication, "instance")


HAVE_QT = _have_real_qt()


@unittest.skipUnless(HAVE_QT, "real PyQt6 not available")
class TestNoBusyCursorWhileDrawing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def _draw_with(self, toolbar_cls):
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
        canvas = FigureCanvasQTAgg(Figure())
        canvas.figure.add_subplot(111).plot([0, 1], [0, 1])
        toolbar_cls(canvas, None)          # registers itself as canvas.toolbar
        with mock.patch.object(canvas, "set_cursor") as set_cursor:
            canvas.draw()
        return set_cursor

    def test_plain_matplotlib_toolbar_does_set_the_cursor(self):
        # Guards the test itself: this is the behaviour being switched off.
        from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
        self.assertTrue(self._draw_with(NavigationToolbar2QT).called)

    def test_safe_toolbar_never_sets_the_cursor(self):
        from ui.nav_toolbar import SafeNavigationToolbar
        self.assertFalse(self._draw_with(SafeNavigationToolbar).called)

    def test_every_chart_canvas_in_the_app_uses_the_safe_toolbar(self):
        import ast
        for name in ("main_window.py", "code_runner.py", "seaborn_explorer.py"):
            with open(os.path.join(_SRC, "ui", name)) as fh:
                src = fh.read()
            instantiated = [n.func.id for n in ast.walk(ast.parse(src))
                            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                            and "Toolbar" in n.func.id]
            self.assertNotIn("NavigationToolbar2QT", instantiated, name)


if __name__ == "__main__":
    unittest.main()
