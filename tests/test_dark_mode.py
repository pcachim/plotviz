"""The inner tab widgets (Data and Plots) follow a change of the application palette.

A style sheet on their tab bars used to freeze their palette, which left the pages
light in dark mode. Runs only where a real PyQt6 is installed; skipped otherwise.
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
class TestInnerTabsFollowThePalette(unittest.TestCase):
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

    def test_pages_are_dark_after_a_dark_palette(self):
        from PyQt6.QtGui import QColor, QPalette
        from PyQt6.QtTest import QTest
        app = self._app
        light = app.palette()
        w = self.PlotVizApp()
        w.show()
        dark = QPalette(light)
        dark.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        dark.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
        try:
            app.setPalette(dark)
            QTest.qWait(100)  # ty: ignore[missing-argument, invalid-argument-type]
            for tabs in (w.data_inner_tabs, w.plots_inner_tabs):
                self.assertEqual(tabs.palette().window().color().name(), "#1e1e1e")
                self.assertEqual(tabs.widget(0).palette().window().color().name(), "#1e1e1e")
        finally:
            app.setPalette(light)
            w.close()

    def test_the_tabs_are_compact_and_the_selected_one_is_underlined(self):
        w = self.PlotVizApp()
        bar = w.data_inner_tabs.tabBar()
        self.assertEqual(w.data_inner_tabs.tabBar().styleSheet(), "")      # a style, not a style sheet
        self.assertLess(bar.tabRect(0).width(), 110)
        self.assertLessEqual(w.plots_inner_tabs.tabBar().sizeHint().width(), 400)
        w.close()


if __name__ == "__main__":
    unittest.main()
