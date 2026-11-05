"""Closing the window with unsaved changes asks first."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import _bootstrap  # noqa: F401,E402


_REAL: dict = {}


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
        return hasattr(QApplication, "instance") and not getattr(QApplication, "_is_stub", False)
    except Exception:  # noqa: BLE001
        return False


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestClosePrompt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import PlotVizApp
        cls._app = QApplication.instance() or QApplication([])
        cls._orig = PlotVizApp._load_on_startup
        _REAL.setdefault('confirm', PlotVizApp._confirm_close)
        PlotVizApp._load_on_startup = lambda self: None
        cls.PlotVizApp = PlotVizApp

    @classmethod
    def tearDownClass(cls):
        cls.PlotVizApp._load_on_startup = cls._orig

    def setUp(self):
        from ui.main_window import PlotVizApp
        self._patched = PlotVizApp._confirm_close
        PlotVizApp._confirm_close = _REAL['confirm']        # the real question (the test run patches it away)
        self.w = self.PlotVizApp()
        self.w.show()

    def tearDown(self):
        from ui.main_window import PlotVizApp
        self.w._is_dirty = False
        self.w.close()
        PlotVizApp._confirm_close = self._patched

    def click(self, label):
        """Answer the question by clicking the button with this text."""
        def answer(box):
            [b for b in box.buttons() if b.text() == label][0].click()
        return mock.patch("ui.main_window.QMessageBox.exec", answer)

    def test_a_chart_without_changes_closes_without_asking(self):
        self.w._is_dirty = False
        with mock.patch("ui.main_window.QMessageBox.exec") as ask:
            self.assertTrue(self.w._confirm_close())
        ask.assert_not_called()

    def test_cancel_keeps_the_window_open(self):
        self.w._is_dirty = True
        with self.click('Cancel'):
            self.assertFalse(self.w._confirm_close())
        from PyQt6.QtGui import QCloseEvent
        event = QCloseEvent()
        with self.click('Cancel'):
            self.w.closeEvent(event)
        self.assertFalse(event.isAccepted())

    def test_dont_save_closes_and_discards_the_changes(self):
        self.w._is_dirty = True
        with self.click("Don't save"):
            self.assertTrue(self.w._confirm_close())

    def test_save_writes_the_file_then_closes(self):
        path = str(Path(tempfile.mkdtemp()) / "c.pviz")
        self.w._current_filepath = path
        self.w._is_dirty = True
        with self.click('Save'), mock.patch.object(self.w, "_ask_columns_to_save", return_value=False):
            self.assertTrue(self.w._confirm_close())
        self.assertTrue(os.path.exists(path))
        self.assertFalse(self.w._is_dirty)

    def test_a_save_that_does_not_happen_keeps_the_window_open(self):
        self.w._is_dirty = True
        self.w._current_filepath = None
        with self.click('Save'), mock.patch("ui.serialization.QFileDialog.getSaveFileName", return_value=("", "")):
            self.assertFalse(self.w._confirm_close())


if __name__ == "__main__":
    unittest.main()
