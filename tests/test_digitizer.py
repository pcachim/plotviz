"""Digitize Image: the arithmetic of the calibration and the window that uses it."""
import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import numpy as np  # noqa: E402

import _bootstrap  # noqa: F401,E402
from data.digitize import AxisCalibration, Calibration, CalibrationError, trace_by_color  # noqa: E402


class TestCalibration(unittest.TestCase):
    def test_a_linear_axis_maps_pixels_to_values_and_back(self):
        axis = AxisCalibration(p1=50, v1=0, p2=350, v2=10)
        self.assertAlmostEqual(float(axis.value(200)), 5.0)
        self.assertAlmostEqual(float(axis.value(350)), 10.0)
        np.testing.assert_allclose(axis.value([50, 125]), [0, 2.5])
        self.assertAlmostEqual(float(axis.pixel(7.5)), 275.0)

    def test_a_y_axis_has_pixels_that_grow_downwards(self):
        axis = AxisCalibration(p1=250, v1=0, p2=50, v2=100)
        self.assertAlmostEqual(float(axis.value(150)), 50.0)
        self.assertAlmostEqual(float(axis.value(300)), -25.0)

    def test_a_log_axis_is_linear_in_the_exponent(self):
        axis = AxisCalibration(p1=0, v1=1, p2=300, v2=1000, log=True)
        self.assertAlmostEqual(float(axis.value(100)), 10.0)
        self.assertAlmostEqual(float(axis.value(200)), 100.0)
        self.assertAlmostEqual(float(axis.pixel(100.0)), 200.0)

    def test_bad_reference_points_are_refused(self):
        with self.assertRaises(CalibrationError):
            AxisCalibration(p1=10, v1=0, p2=10, v2=5)             # same position
        with self.assertRaises(CalibrationError):
            AxisCalibration(p1=0, v1=3, p2=10, v2=3)              # same value
        with self.assertRaises(CalibrationError):
            AxisCalibration(p1=0, v1=0, p2=10, v2=5, log=True)    # log of zero

    def test_both_axes_together(self):
        cal = Calibration(AxisCalibration(0, 0, 100, 1), AxisCalibration(100, 0, 0, 10))
        x, y = cal.to_data(50, 50)
        self.assertAlmostEqual(float(x), 0.5)
        self.assertAlmostEqual(float(y), 5.0)
        px, py = cal.to_pixel(0.5, 5.0)
        self.assertAlmostEqual(float(px), 50.0)
        self.assertAlmostEqual(float(py), 50.0)


class TestTrace(unittest.TestCase):
    def picture(self):
        rgb = np.full((100, 200, 3), 255, dtype=np.uint8)
        for x in range(20, 180):                       # a red diagonal, 3 pixels thick
            y = 10 + (x - 20) // 2
            rgb[y - 1:y + 2, x] = (220, 30, 30)
        rgb[:8, :] = (220, 30, 30)                     # a red band at the top (a title, say)
        return rgb

    def test_it_follows_the_colour_one_point_per_step(self):
        px, py = trace_by_color(self.picture(), (220, 30, 30), tolerance=30, step=10, region=(0, 8, 200, 100))
        self.assertEqual(len(px), 16)
        np.testing.assert_allclose(py, 10 + (px - 0.5 - 20) // 2 + 0.5, atol=1.0)

    def test_the_region_keeps_other_things_of_the_same_colour_out(self):
        rgb = self.picture()
        _, py_all = trace_by_color(rgb, (220, 30, 30), 30, 10)
        _, py_region = trace_by_color(rgb, (220, 30, 30), 30, 10, region=(0, 8, 200, 100))
        self.assertLess(py_all.min(), 5)               # the band is found without a region
        self.assertGreater(py_region.min(), 8)

    def test_a_colour_that_is_not_there_gives_nothing(self):
        px, py = trace_by_color(self.picture(), (0, 0, 255), 30, 1)
        self.assertEqual((len(px), len(py)), (0, 0))


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
        return hasattr(QApplication, "instance") and not getattr(QApplication, "_is_stub", False)
    except Exception:  # noqa: BLE001
        return False


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        from PyQt6.QtGui import QColor, QImage, QPainter, QPen
        from ui.digitizer import DigitizerDialog
        image = QImage(400, 300, QImage.Format.Format_RGB32)
        image.fill(QColor("white"))
        painter = QPainter(image)
        painter.setPen(QPen(QColor(220, 30, 30), 3))
        painter.drawLine(50, 250, 350, 50)             # y = 100 - ... : from (0, 0) to (10, 100) in data
        painter.end()
        self.d = DigitizerDialog()
        self.d.show()
        self.d.set_image(image, "test")

    def tearDown(self):
        self.d.close()

    def calibrate(self, log_y=False):
        d = self.d
        d.set_calibration_point("x1", 50, 150)
        d.set_calibration_point("x2", 350, 150)
        d.set_calibration_point("y1", 20, 250)
        d.set_calibration_point("y2", 20, 50)
        for key, value in zip(("x1", "x2", "y1", "y2"), ("0", "10", "0", "100")):
            d.cal_values[key].setText(value)

    def test_nothing_is_calibrated_at_first_and_the_reason_is_said(self):
        self.assertIsNone(self.d.calibration())
        self.assertIn("X point 1", self.d._calibration_or_reason()[1])

    def test_clicked_points_become_values(self):
        self.calibrate()
        self.d.add_point(200, 150)                      # half way on both axes
        x, y = self.d.points_data()
        np.testing.assert_allclose(x, [5.0])
        np.testing.assert_allclose(y, [50.0])
        self.assertEqual(self.d.table.item(0, 0).text(), "5")

    def test_a_decimal_comma_is_accepted(self):
        self.calibrate()
        self.d.cal_values["x2"].setText("10,5")
        self.d.add_point(350, 150)
        np.testing.assert_allclose(self.d.points_data()[0], [10.5])

    def test_changing_the_calibration_moves_every_value(self):
        self.calibrate()
        self.d.add_point(200, 150)
        self.d.cal_values["y2"].setText("200")
        np.testing.assert_allclose(self.d.points_data()[1], [100.0])

    def test_points_are_sorted_by_x_unless_that_is_turned_off(self):
        self.calibrate()
        for px in (300, 100, 200):
            self.d.add_point(px, 150)
        np.testing.assert_allclose(self.d.points_data()[0], [1.667, 5.0, 8.333], atol=0.01)
        self.d.sort_check.setChecked(False)
        np.testing.assert_allclose(self.d.points_data()[0], [8.333, 1.667, 5.0], atol=0.01)

    def test_a_point_is_removed_by_right_clicking_near_it(self):
        self.d.add_point(100, 100)
        self.d.add_point(300, 200)
        self.d.remove_nearest(102, 101)
        self.assertEqual(self.d._points, [(300, 200)])
        self.d.remove_nearest(10, 10)                    # nothing near
        self.assertEqual(len(self.d._points), 1)

    def test_selected_rows_are_removed_from_the_right_points(self):
        self.calibrate()
        for px in (300, 100, 200):
            self.d.add_point(px, 150)
        self.d.table.selectRow(0)                        # the smallest x is the second point added
        self.d.remove_selected()
        self.assertEqual(self.d._points, [(300, 150), (200, 150)])

    def test_tracing_the_colour_follows_the_line_between_the_x_references(self):
        self.calibrate()
        self.d.pick_color_at(200, 150)                   # the line passes here
        self.assertEqual(self.d._color, (220, 30, 30))
        added = self.d.trace_curve()
        self.assertGreater(added, 20)
        x, y = self.d.points_data()
        np.testing.assert_allclose(y, 10 * x, atol=2.0)  # the line is y = 10 x

    def test_adding_to_the_chart_emits_the_two_columns(self):
        self.calibrate()
        self.d.add_point(200, 150)
        self.d.name_x.setText("t")
        self.d.name_y.setText("v")
        seen = []
        self.d.columns_ready.connect(seen.append)
        self.d.add_to_chart()
        self.assertEqual(list(seen[0]), ["t", "v"])
        np.testing.assert_allclose(seen[0]["v"], [50.0])

    def test_adding_without_a_calibration_or_with_one_name_is_refused(self):
        self.d.add_point(200, 150)
        seen = []
        self.d.columns_ready.connect(seen.append)
        with mock.patch("ui.digitizer.QMessageBox.information") as info:
            self.d.add_to_chart()
        info.assert_called_once()
        self.calibrate()
        self.d.name_y.setText(self.d.name_x.text())
        with mock.patch("ui.digitizer.QMessageBox.warning") as warn:
            self.d.add_to_chart()
        warn.assert_called_once()
        self.assertEqual(seen, [])

    def test_a_new_image_starts_over(self):
        from PyQt6.QtGui import QImage
        self.calibrate()
        self.d.add_point(200, 150)
        self.d.set_image(QImage(100, 100, QImage.Format.Format_RGB32), "other")
        self.assertEqual(self.d._points, [])
        self.assertIsNone(self.d.calibration())

    def test_an_unreadable_file_is_reported(self):
        with mock.patch("ui.digitizer.QMessageBox.warning") as warn:
            self.assertFalse(self.d.open_image("/no/such/image.png"))
        warn.assert_called_once()


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestInTheApp(unittest.TestCase):
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
        self.w = self.PlotVizApp()
        self.w.show()

    def tearDown(self):
        self.w.close()

    def test_the_tools_menu_has_the_entry(self):
        tools = [m for m in self.w.menuBar().actions() if m.text() == "Tools"][0].menu()
        self.assertIn("Digitize Image…", [a.text() for a in tools.actions()])

    def test_the_points_arrive_as_datasets_and_names_in_use_get_a_number(self):
        self.w.datasets["t"] = np.arange(3.0)
        self.w._open_digitizer()
        self.w._digitizer.columns_ready.emit({"t": np.array([1.0, 2.0]), "v": np.array([3.0, 4.0])})
        self.assertEqual(set(self.w.datasets), {"t", "t_1", "v"})
        np.testing.assert_allclose(self.w.datasets["t_1"], [1, 2])
        self.assertTrue(self.w._is_dirty)

    def test_the_window_is_created_once(self):
        self.w._open_digitizer()
        first = self.w._digitizer
        self.w._open_digitizer()
        self.assertIs(self.w._digitizer, first)


if __name__ == "__main__":
    unittest.main()
