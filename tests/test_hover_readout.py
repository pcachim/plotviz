"""Passing the pointer over a chart writes the nearest data point to the status bar."""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import numpy as np  # noqa: E402

import _bootstrap  # noqa: F401,E402


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
        return hasattr(QApplication, "instance") and not getattr(QApplication, "_is_stub", False)
    except Exception:  # noqa: BLE001
        return False


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestHoverReadout(unittest.TestCase):
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

    def setUp(self):
        w = self.w = self.PlotVizApp()
        w.show()
        w.datasets.update({"x": np.array([1.0, 2.0, 3.0, 4.0]), "y": np.array([10.0, 20.0, 15.0, 30.0])})
        w.update_lists()
        w._add_series_row()
        w.series_table.cellWidget(0, 0).setCurrentText("x")
        w.series_table.cellWidget(0, 1).setCurrentText("y")
        w.canvas.draw()
        self.canvas = w.canvas
        self.ax = w.canvas.axes_list[0]

    def tearDown(self):
        self.w.close()

    def move_to(self, x, y, dx=0, dy=0):
        from matplotlib.backend_bases import MouseEvent
        px, py = self.ax.transData.transform((x, y))
        self.canvas._hover_last = 0.0                 # no throttling in the test
        self.canvas.on_mouse_move(MouseEvent("motion_notify_event", self.canvas, px + dx, py + dy))

    def message(self):
        return self.w.statusBar().currentMessage()

    def test_the_nearest_point_is_the_data_point_not_the_cursor(self):
        from matplotlib.backend_bases import MouseEvent
        px, py = self.ax.transData.transform((2.0, 20.0))
        found = self.canvas.nearest_point(self.ax, MouseEvent("motion_notify_event", self.canvas, px + 4, py - 3))
        self.assertIsNotNone(found)
        self.assertEqual((found[1], found[2]), (2.0, 20.0))

    def test_the_status_bar_shows_the_series_and_the_values(self):
        self.move_to(3.0, 15.0, dx=3)
        text = self.message()
        self.assertIn("x = 3", text)
        self.assertIn("y = 15", text)
        self.assertTrue(text.startswith(self.ax.get_lines()[0].get_label()))

    def test_far_from_every_point_nothing_is_shown_and_an_old_readout_is_cleared(self):
        self.move_to(2.0, 20.0)
        self.assertIn("y = 20", self.message())
        self.move_to(2.5, 5.0)                          # between points, well below the line
        self.assertEqual(self.message(), "")

    def test_leaving_the_axes_clears_the_readout(self):
        self.move_to(4.0, 30.0)
        self.assertIn("y = 30", self.message())
        from matplotlib.backend_bases import MouseEvent
        self.canvas.on_mouse_move(MouseEvent("motion_notify_event", self.canvas, 1, 1))
        self.assertEqual(self.message(), "")

    def test_a_message_that_is_not_the_readout_is_left_alone(self):
        self.w.statusBar().showMessage("Saved")
        self.move_to(2.5, 5.0)                          # not near a point, no readout was shown
        self.assertEqual(self.message(), "Saved")

    def test_dragging_an_annotation_does_not_write_the_readout(self):
        self.canvas._place_text_annotation(self.ax, 0, 2.0, 20.0, label="note")
        self.canvas._drag_ann = self.canvas.annotations[-1]
        self.canvas._drag_part = "both"
        self.move_to(2.0, 20.0)
        self.assertEqual(self.message(), "")


if __name__ == "__main__":
    unittest.main()
