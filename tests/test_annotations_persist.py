"""Annotations are changes to the chart: they enable Save, and they come back from the file.

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
class TestAnnotationsPersist(unittest.TestCase):
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

    def window(self):
        np = self.np
        w = self.PlotVizApp()
        w.show()
        x = np.linspace(0, 10, 50)
        w.datasets.update({"x": x, "y": 0.3 * x ** 2 - x + 2 + np.random.default_rng(1).normal(0, 0.3, 50)})
        w.update_lists()
        w._add_series_row()
        w.series_table.cellWidget(0, 0).setCurrentText("x")
        w.series_table.cellWidget(0, 1).setCurrentText("y")
        w.update_preview()
        return w

    def save(self, w, path):
        from unittest import mock
        with mock.patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=(path, "")), \
                mock.patch("PyQt6.QtWidgets.QMessageBox.information"), \
                mock.patch.object(type(w), "_ask_columns_to_save", return_value=False):
            w._save_project(save_as=True)

    def saved_clean(self, w, path):
        """Save, so that the chart has a file and nothing is waiting to be saved."""
        self.save(w, path)
        self.assertFalse(w._is_dirty)
        self.assertFalse(w._btn_save.isEnabled())

    def test_adding_an_annotation_makes_the_chart_dirty_and_enables_save(self):
        import tempfile
        w = self.window()
        self.saved_clean(w, os.path.join(tempfile.mkdtemp(), "c.pviz"))
        w.canvas._place_text_annotation(w.canvas.axes_list[0], 0, 5.0, 10.0, label="note")
        self.assertTrue(w._is_dirty)
        self.assertTrue(w._btn_save.isEnabled())
        w.close()

    def test_moving_and_deleting_one_do_too(self):
        import tempfile
        w = self.window()
        w.canvas._place_text_annotation(w.canvas.axes_list[0], 0, 5.0, 10.0, label="note")
        self.saved_clean(w, os.path.join(tempfile.mkdtemp(), "c.pviz"))
        ann = w.canvas.annotations[0]
        w.canvas._drag_ann = ann                                   # a drag ends with the release
        w.canvas.on_release(None)
        self.assertTrue(w._is_dirty)
        self.save(w, os.path.join(tempfile.mkdtemp(), "d.pviz"))
        self.assertFalse(w._is_dirty)
        w.canvas.remove_annotation_at(0)
        self.assertTrue(w._is_dirty)
        w.close()

    def test_a_fit_label_makes_the_chart_dirty(self):
        import tempfile
        w = self.window()
        w.fit_combo.setCurrentText("Quadratic")
        w.apply_fit()
        self.saved_clean(w, os.path.join(tempfile.mkdtemp(), "c.pviz"))
        w._add_fit_label(list(w._fits)[0])
        self.assertTrue(w._is_dirty)
        self.assertTrue(w._btn_save.isEnabled())
        w.close()

    def test_opening_a_file_with_annotations_is_not_a_change(self):
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "c.pviz")
        w = self.window()
        w.canvas._place_text_annotation(w.canvas.axes_list[0], 0, 5.0, 10.0, label="note")
        self.save(w, path)
        other = self.PlotVizApp()
        other.show()
        other._load_project_inner(path, silent=True)
        self.assertEqual([a["label"] for a in other.canvas.annotations], ["note"])
        self.assertFalse(other._is_dirty)
        w.close()
        other.close()

    def test_annotations_and_fit_labels_come_back_from_the_file(self):
        import tempfile
        from data.fit_text import FitTextOptions
        path = os.path.join(tempfile.mkdtemp(), "c.pviz")
        w = self.window()
        w.fit_combo.setCurrentText("Quadratic")
        w.apply_fit()
        key = list(w._fits)[0]
        label = w._add_fit_label(key, FitTextOptions(parameters=True))
        w.canvas._place_text_annotation(w.canvas.axes_list[0], 0, 5.0, 10.0, label="my note")
        before = [(a["type"], a["label"], round(a["x"], 6), round(a["y"], 6), a.get("source_fit"))
                  for a in w.canvas.annotations]
        self.save(w, path)
        other = self.PlotVizApp()
        other.show()
        other._load_project_inner(path, silent=True)
        after = [(a["type"], a["label"], round(a["x"], 6), round(a["y"], 6), a.get("source_fit"))
                 for a in other.canvas.annotations]
        self.assertEqual(after, before)
        self.assertEqual(len(before), 2)
        texts = [t.get_text() for t in other.canvas.axes_list[0].texts]
        self.assertIn(label["label"], texts)                        # and drawn again
        self.assertIn("my note", texts)
        w.close()
        other.close()


if __name__ == "__main__":
    unittest.main()
