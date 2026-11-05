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
from data.digitize import (  # noqa: E402
    AxisCalibration, Calibration, CalibrationError, PointCalibration, trace_by_color,
)


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


class TestPointCalibration(unittest.TestCase):
    def rotated(self, angle, scale=(30.0, 20.0), shift=(100.0, 200.0)):
        """Pixel positions of data points when the chart is turned by *angle* (radians) and y grows downwards."""
        c, s = np.cos(angle), np.sin(angle)

        def pixels(x, y):
            px, py = scale[0] * x, -scale[1] * y
            return shift[0] + c * px - s * py, shift[1] + s * px + c * py
        return pixels

    def test_three_points_recover_a_rotated_chart(self):
        pixels = self.rotated(np.radians(12))
        refs = [(0, 0), (10, 0), (0, 5)]
        cal = PointCalibration([pixels(*r) for r in refs], refs)
        px, py = pixels(4.0, 3.0)
        x, y = cal.to_data(px, py)
        self.assertAlmostEqual(float(x), 4.0, places=6)
        self.assertAlmostEqual(float(y), 3.0, places=6)
        bx, by = cal.to_pixel(4.0, 3.0)
        self.assertAlmostEqual(float(bx), float(px), places=6)

    def test_four_points_recover_a_perspective_view(self):
        def view(x, y):                                   # a projective map, as a photograph at an angle gives
            w = 1 + 0.002 * x + 0.001 * y
            return (120 + 28 * x + 3 * y) / w, (260 - 18 * y + 2 * x) / w
        refs = [(0, 0), (10, 0), (10, 8), (0, 8)]
        cal = PointCalibration([view(*r) for r in refs], refs)
        for x0, y0 in [(3.0, 2.0), (7.5, 6.0), (1.0, 7.0)]:
            x, y = cal.to_data(*view(x0, y0))
            self.assertAlmostEqual(float(x), x0, places=6)
            self.assertAlmostEqual(float(y), y0, places=6)

    def test_arrays_and_log_axes(self):
        refs = [(1, 0), (1000, 0), (1, 50)]
        pixels = [(0, 300), (300, 300), (0, 100)]
        cal = PointCalibration(pixels, refs, log_x=True)
        x, y = cal.to_data(np.array([100, 200]), np.array([300, 200]))
        np.testing.assert_allclose(x, [10, 100], rtol=1e-9)
        np.testing.assert_allclose(y, [0, 25], atol=1e-9)

    def test_points_on_one_line_or_a_wrong_number_are_refused(self):
        with self.assertRaises(CalibrationError):
            PointCalibration([(0, 0), (10, 10), (20, 20)], [(0, 0), (1, 1), (2, 2)])
        with self.assertRaises(CalibrationError):
            PointCalibration([(0, 0), (10, 0)], [(0, 0), (1, 0)])
        with self.assertRaises(CalibrationError):
            PointCalibration([(0, 0), (10, 0), (0, 10)], [(0, 0), (-1, 0), (0, 1)], log_x=True)
        with self.assertRaises(CalibrationError):
            PointCalibration([(0, 0), (10, 0), (20, 0), (30, 5)], [(0, 0), (1, 0), (2, 0), (3, 1)])


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

    def test_adding_to_the_chart_emits_two_columns_named_after_the_curve(self):
        self.calibrate()
        self.d.add_point(200, 150)
        self.d.rename_curve("signal")
        seen = []
        self.d.columns_ready.connect(seen.append)
        self.d.add_to_chart()
        self.assertEqual(list(seen[0]), ["signal_x", "signal_y"])
        np.testing.assert_allclose(seen[0]["signal_y"], [50.0])

    def test_adding_without_a_calibration_or_without_points_is_refused(self):
        seen = []
        self.d.columns_ready.connect(seen.append)
        self.d.add_point(200, 150)
        with mock.patch("ui.digitizer.QMessageBox.information") as info:
            self.d.add_to_chart()                       # not calibrated
        self.assertIn("X point 1", info.call_args[0][2])
        self.calibrate()
        self.d.clear_points()
        with mock.patch("ui.digitizer.QMessageBox.information") as info:
            self.d.add_to_chart()                       # no points
        self.assertIn("Click on the curve", info.call_args[0][2])
        self.assertEqual(seen, [])

    def test_several_curves_keep_their_own_points_and_all_are_added(self):
        self.calibrate()
        self.d.add_point(200, 150)
        self.d.add_curve("second")
        self.assertEqual(self.d._points, [])             # a new curve starts empty
        self.d.add_point(100, 100)
        self.d.add_point(300, 100)
        self.d.set_active_curve(0)
        self.assertEqual(self.d._points, [(200, 150)])
        self.assertEqual(self.d.curve_names(), ["curve1", "second"])
        seen = []
        self.d.columns_ready.connect(seen.append)
        self.d.add_to_chart()
        self.assertEqual(list(seen[0]), ["curve1_x", "curve1_y", "second_x", "second_y"])
        self.assertEqual(len(seen[0]["second_x"]), 2)
        self.assertEqual(len(seen[0]["curve1_x"]), 1)

    def test_each_curve_has_its_own_x_values_and_marker_colour(self):
        self.calibrate()
        self.d.add_point(100, 100)
        self.d.add_curve()
        self.d.add_point(300, 100)
        self.assertNotEqual(self.d._curves[0]["marker"], self.d._curves[1]["marker"])
        names_x = {name: x for name, x, _ in self.d.curves_data()}
        self.assertNotEqual(float(names_x["curve1"][0]), float(names_x["curve2"][0]))

    def test_a_curve_remembers_its_colour_and_tolerance(self):
        self.d.pick_color_at(200, 150)
        self.d.tolerance.setValue(33)
        self.d.add_curve()
        self.assertIsNone(self.d._color)
        self.assertEqual(self.d.tolerance.value(), 60)
        self.d.set_active_curve(0)
        self.assertEqual(self.d._color, (220, 30, 30))
        self.assertEqual(self.d.tolerance.value(), 33)

    def test_trace_adds_to_the_active_curve_only(self):
        self.calibrate()
        self.d.add_curve()
        self.d.pick_color_at(200, 150)
        self.assertGreater(self.d.trace_curve(), 0)
        self.assertEqual(self.d._curves[0]["points"], [])
        self.assertGreater(len(self.d._curves[1]["points"]), 0)

    def test_names_are_unique_and_a_blank_name_is_ignored(self):
        self.d.add_curve()
        self.d.rename_curve("curve1")
        self.assertEqual(self.d.curve_names(), ["curve1", "curve1_2"])
        self.d.rename_curve("   ")
        self.assertEqual(self.d.curve_names()[1], "curve1_2")

    def test_deleting_a_curve_removes_its_points_and_the_last_one_is_only_emptied(self):
        self.d.add_point(100, 100)
        self.d.add_curve()
        self.d.add_point(200, 100)
        before = len(self.d.scene.items())
        self.d.delete_curve()
        self.assertEqual(self.d.curve_names(), ["curve1"])
        self.assertEqual(len(self.d.scene.items()), before - 1)
        self.d.delete_curve()
        self.assertEqual(self.d.curve_names(), ["curve1"])
        self.assertEqual(self.d._points, [])

    def test_the_combo_lists_the_curves_with_their_number_of_points(self):
        self.d.add_point(100, 100)
        self.d.add_curve()
        texts = [self.d.curve_combo.itemText(i) for i in range(self.d.curve_combo.count())]
        self.assertEqual(texts, ["curve1  (1)", "curve2  (0)"])
        self.d.curve_combo.setCurrentIndex(0)
        self.assertEqual(self.d._active, 0)

    def test_a_new_image_starts_with_one_empty_curve(self):
        from PyQt6.QtGui import QImage
        self.d.add_curve()
        self.d.add_point(100, 100)
        self.d.set_image(QImage(100, 100, QImage.Format.Format_RGB32), "other")
        self.assertEqual(self.d.curve_names(), ["curve1"])
        self.assertEqual(self.d._points, [])

    def reference_mode(self, n_points=3):
        """Reference points for a picture whose axes are rotated: pixel = (100 + 20x + 5y, 250 - 2x - 15y)."""
        d = self.d
        d.cal_mode.setCurrentIndex(1)
        refs = [(0, 0), (10, 0), (0, 10), (10, 10)][:n_points]
        for i, (x, y) in enumerate(refs, start=1):
            d.set_calibration_point(f"p{i}", 100 + 20 * x + 5 * y, 250 - 2 * x - 15 * y)
            d.cal_values[f"p{i}x"].setText(str(x))
            d.cal_values[f"p{i}y"].setText(str(y))

    def test_three_reference_points_read_a_rotated_picture(self):
        self.reference_mode(3)
        self.assertIsNotNone(self.d.calibration())
        self.d.add_point(100 + 20 * 4 + 5 * 6, 250 - 2 * 4 - 15 * 6)
        x, y = self.d.points_data()
        np.testing.assert_allclose([x[0], y[0]], [4, 6], atol=1e-9)

    def test_a_fourth_reference_point_is_used_when_it_is_complete(self):
        self.reference_mode(4)
        self.assertEqual(len(self.d.calibration().pixels), 4)

    def test_a_half_set_fourth_point_is_reported_not_ignored(self):
        self.reference_mode(3)
        self.d.cal_values["p4x"].setText("10")
        self.assertIsNone(self.d.calibration())
        self.assertIn("point 4", self.d._calibration_or_reason()[1])

    def test_the_status_says_which_reference_point_is_missing(self):
        self.d.cal_mode.setCurrentIndex(1)
        self.assertIn("Set point 1", self.d._calibration_or_reason()[1])
        self.d.set_calibration_point("p1", 10, 10)
        self.assertIn("Type the x and y of point 1", self.d._calibration_or_reason()[1])

    def test_each_mode_keeps_its_own_markers_and_the_other_ones_are_hidden(self):
        self.calibrate()
        self.d.cal_mode.setCurrentIndex(1)
        self.assertFalse(self.d._cal_items["x1"].isVisible())
        self.d.cal_mode.setCurrentIndex(0)
        self.assertTrue(self.d._cal_items["x1"].isVisible())
        self.assertIsNotNone(self.d.calibration())

    def test_a_reference_calibration_limits_the_trace_to_the_points(self):
        self.reference_mode(3)
        self.d.pick_color_at(200, 150)
        self.d.step.setValue(20)
        self.assertGreater(self.d.trace_curve(), 0)

    def test_the_magnifier_follows_the_pointer_and_hides_for_the_pan_tool(self):
        self.d._on_move(200.0, 150.0)
        self.assertTrue(self.d.magnifier.isVisible())
        self.assertFalse(self.d.magnifier.pixmap().isNull())
        self.d._on_move(-5.0, 10.0)                              # outside the picture
        self.assertFalse(self.d.magnifier.isVisible())
        self.d._on_move(200.0, 150.0)
        self.d.tool_combo.setCurrentIndex(1)
        self.d._on_move(210.0, 150.0)
        self.assertFalse(self.d.magnifier.isVisible())

    def test_the_magnifier_works_at_the_edge_of_the_picture(self):
        self.d._on_move(0.5, 0.5)
        self.assertTrue(self.d.magnifier.isVisible())
        self.d._on_move(399.5, 299.5)
        self.assertTrue(self.d.magnifier.isVisible())

    def test_a_marked_point_is_taken_and_carried_by_the_pointer(self):
        self.d.add_point(100, 100)
        self.d.add_point(300, 200)
        self.assertTrue(self.d._grab_at(102, 101))
        self.d._on_drag(150, 160)
        self.d._on_drag_end()
        self.assertEqual(self.d._points[0], (150, 160))
        self.assertEqual(self.d._points[1], (300, 200))
        self.assertFalse(self.d._grab_at(10, 10))             # nothing there

    def test_a_point_cannot_be_dragged_out_of_the_picture(self):
        self.d.add_point(100, 100)
        self.d._grab_at(100, 100)
        self.d._on_drag(-50, 900)
        self.d._on_drag_end()
        x, y = self.d._points[0]
        self.assertTrue(0 <= x < 400 and 0 <= y < 300)

    def test_a_reference_marker_can_be_dragged_and_the_values_follow(self):
        self.calibrate()
        self.d.add_point(200, 150)
        before = self.d.points_data()[0][0]
        self.assertTrue(self.d._grab_at(350, 150))            # x2
        self.d._on_drag(250, 150)
        self.d._on_drag_end()
        self.assertEqual(self.d._cal_points["x2"], (250, 150))
        self.assertGreater(self.d.points_data()[0][0], before)

    def test_nothing_is_taken_while_a_calibration_click_is_awaited(self):
        self.d.add_point(100, 100)
        self.d._await("x1")
        self.assertFalse(self.d._grab_at(100, 100))

    def test_move_point_helper_and_the_table_follow(self):
        self.calibrate()
        self.d.add_point(100, 100)
        self.d.move_point(0, 200, 150)
        self.assertEqual(self.d.table.item(0, 0).text(), "5")

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
