"""Undo / redo: what a step holds, when one is recorded, and what the interface does after it.

Runs only where a real PyQt6 is installed; skipped otherwise.  The 400 ms wait before a step is
recorded is not waited for: the test checks that the change armed the timer (so the real app
records it) and then takes the snapshot itself.
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
class TestUndoRedo(unittest.TestCase):
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
        np = self.np
        w = self.w = self.PlotVizApp()
        x = np.linspace(0, 10, 30)
        w.datasets.update({"x": x, "y": 2 * x + np.sin(x), "z": x ** 2})
        w.update_lists()
        w._add_series_row()
        w.series_table.cellWidget(0, 0).setCurrentText("x")
        w.series_table.cellWidget(0, 1).setCurrentText("y")
        w.update_preview()
        self.step()

    # ── helpers ──────────────────────────────────────────────────────────────
    def step(self, armed=None):
        """Record the undo step the change asked for (the app does it 400 ms later)."""
        w = self.w
        timer = getattr(w, "_snapshot_timer", None)
        if armed is not None:
            self.assertTrue(timer is not None and timer.isActive(), f"{armed}: no undo step was asked for")
        if timer is not None:
            timer.stop()
        w._snapshot()

    def set_title(self, text):
        self.w.title_input.setText(text)
        self.w.title_input.editingFinished.emit()

    def undo(self):
        self.w._undo()

    # ── data operations are steps, and an unrelated undo no longer eats them ──────
    def test_a_generated_dataset_is_an_undo_step_and_survives_an_unrelated_undo(self):
        w = self.w
        w.gen_expr.setText("x**2")
        w._generate_fx()
        self.step("generate")
        self.assertEqual(w._undo_stack[-1].label, "Generate y = f(x)")
        self.assertIn("y_1", w.datasets)
        self.set_title("Hello")
        self.step("title")
        self.undo()                                           # undoes the title only
        self.assertEqual(w.title_input.text(), "")
        self.assertIn("y_1", w.datasets)                      # used to disappear here
        self.undo()                                           # now the dataset
        self.assertNotIn("y_1", w.datasets)
        self.assertEqual(sorted(w.datasets), ["x", "y", "z"])
        w._redo()
        self.assertIn("y_1", w.datasets)
        w._redo()
        self.assertEqual(w.title_input.text(), "Hello")

    def test_transform_remove_and_load_are_steps(self):
        w = self.w
        w.tf_y_combo.setCurrentText("y")
        w.tf_op_combo.setCurrentIndex(w.tf_op_combo.findData("moving_average"))
        w._apply_transform()
        self.step("transform")
        self.assertEqual(w._undo_stack[-1].label, "Transform")
        created = set(w.datasets) - {"x", "y", "z"}
        self.assertTrue(created)
        self.undo()
        self.assertEqual(set(w.datasets), {"x", "y", "z"})
        w._redo()
        self.assertTrue(created <= set(w.datasets))
        w.dataset_list.findItems("z", __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.MatchFlag.MatchExactly)[0].setSelected(True)
        w._remove_selected_datasets()
        self.step("remove")
        self.assertNotIn("z", w.datasets)
        self.undo()
        self.assertIn("z", w.datasets)

    def test_a_change_that_only_touches_the_data_is_still_a_step(self):
        w = self.w
        n = len(w._undo_stack)
        w._snapshot()
        self.assertEqual(len(w._undo_stack), n)               # nothing changed: no step
        w.datasets["z"] = self.np.zeros(30)                   # only an array replaced
        w._snapshot()
        self.assertEqual(len(w._undo_stack), n + 1)
        self.undo()
        self.assertGreater(float(w.datasets["z"].max()), 0)

    # ── what a step holds ────────────────────────────────────────────────────
    def test_curve_styles_are_copied_so_that_a_style_change_can_be_undone(self):
        w = self.w
        old = w.curve_styles["Series 1"]["color"]
        w.curve_styles["Series 1"].update(color="#ff0000", color_locked=True, linewidth=4.0)
        w.update_preview()
        self.step("style")
        self.assertEqual(w.curve_styles["Series 1"]["color"], "#ff0000")
        self.undo()
        self.assertEqual(w.curve_styles["Series 1"]["color"], old)
        self.assertNotEqual(w.curve_styles["Series 1"].get("linewidth"), 4.0)
        w._redo()
        self.assertEqual((w.curve_styles["Series 1"]["color"], w.curve_styles["Series 1"]["linewidth"]),
                         ("#ff0000", 4.0))

    def test_annotations_are_part_of_the_history(self):
        w = self.w
        ax = w.canvas.axes_list[0]
        w.canvas._place_text_annotation(ax, 0, 5.0, 0.5, label="note")
        self.step("add an annotation")
        self.assertEqual(w._undo_stack[-1].label, "Annotation")
        self.assertEqual(len(w.canvas.annotations), 1)
        ann = w.canvas.annotations[0]
        ann["x"], ann["y"] = 7.0, 1.0                          # what dragging does
        w.canvas._notify()
        self.step("move it")
        w.canvas.remove_annotation_at(0)
        self.step("delete it")
        self.assertEqual(len(w.canvas.annotations), 0)
        self.undo()                                            # the delete
        self.assertEqual([(a["x"], a["y"]) for a in w.canvas.annotations], [(7.0, 1.0)])
        self.assertIn("artist", w.canvas.annotations[0])       # and it is drawn again
        self.undo()                                            # the move
        self.assertEqual((w.canvas.annotations[0]["x"], w.canvas.annotations[0]["y"]), (5.0, 0.5))
        self.undo()                                            # the add
        self.assertEqual(w.canvas.annotations, [])
        w._redo()
        w._redo()
        w._redo()
        self.assertEqual(w.canvas.annotations, [])

    def test_the_fits_and_their_state_come_back(self):
        from PyQt6.QtCore import Qt
        w = self.w
        w.fit_combo.setCurrentText("Linear")
        w.apply_fit()
        self.step("fit")
        self.assertEqual(w._undo_stack[-1].label, "Apply fit")
        name = next(iter(w._fits))
        w.fit_ci_combo.setCurrentIndex(2)
        self.step("limits")
        w.fit_table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
        self.step("hide")
        self.assertFalse(w._fits[name]["visible"])
        self.undo()
        self.assertTrue(w._fits[name]["visible"])
        self.assertEqual(w.fit_table.item(0, 0).checkState(), Qt.CheckState.Checked)
        self.undo()
        self.assertEqual(w._fits[name]["ci_idx"], 0)
        self.assertNotIn(f"{name} CI upper", w.datasets)
        self.undo()
        self.assertEqual((w._fits, w.fit_table.rowCount()), ({}, 0))
        self.assertNotIn(name, w.datasets)
        w._redo()
        self.assertIn(name, w._fits)
        self.assertEqual(w.fit_table.rowCount(), 1)

    # ── what the interface does afterwards ──────────────────────────────────────
    def test_undo_keeps_you_on_the_same_subplot_and_syncs_the_plot_mode(self):
        w = self.w
        w.sp_cols.setValue(2)
        self.step()
        w.sp_active.setCurrentIndex(1)
        w.sp_title_input.setText("second")
        w.sp_title_input.editingFinished.emit()
        self.step("subplot title")
        self.undo()
        self.assertEqual(w.sp_active.currentIndex(), 1)       # used to jump back to the first
        self.assertEqual(w.sp_title_input.text(), "")
        w.sp_active.setCurrentIndex(0)
        w.plot_mode_combo.setCurrentText(w.plot_mode_combo.itemText(1))
        self.step("plot mode")
        self.assertNotEqual(w.plot_mode_combo.currentText(), "Standard")
        self.undo()
        self.assertEqual(w.plot_mode_combo.currentText(), "Standard")   # the selector follows the data
        self.assertEqual(w.subplot_plot_modes[0], "Standard")

    def test_the_selected_curve_and_datasets_stay_selected(self):
        from PyQt6.QtCore import Qt
        w = self.w
        w.dataset_list.findItems("z", Qt.MatchFlag.MatchExactly)[0].setSelected(True)
        w.curve_select.setCurrentText("Series 1")
        self.set_title("t")
        self.step("title")
        self.undo()
        self.assertEqual(w.curve_select.currentText(), "Series 1")
        self.assertEqual([i.text() for i in w.dataset_list.selectedItems()], ["z"])

    # ── memory ────────────────────────────────────────────────────────────────
    def test_steps_share_the_arrays_instead_of_copying_the_data(self):
        w = self.w
        self.set_title("a")
        self.step("a")
        self.set_title("b")
        self.step("b")
        first, second = w._undo_stack[-2], w._undo_stack[-1]
        self.assertTrue(all(first.datasets[k] is second.datasets[k] for k in first.datasets))
        self.assertTrue(all(second.datasets[k] is w.datasets[k] for k in second.datasets))

    def test_the_history_is_limited_and_a_new_change_ends_the_redo_chain(self):
        w = self.w
        for i in range(w._MAX_UNDO + 8):
            self.set_title(f"t{i}")
            self.step()
        self.assertEqual(len(w._undo_stack), w._MAX_UNDO)
        self.undo()
        self.assertTrue(w._redo_stack)
        self.set_title("new branch")
        self.step()
        self.assertEqual(w._redo_stack, [])

    # ── naming ───────────────────────────────────────────────────────────────────
    def test_the_buttons_say_what_they_will_undo_and_redo(self):
        w = self.w
        w.canvas._place_text_annotation(w.canvas.axes_list[0], 0, 5.0, 0.5, label="n")
        self.step()
        self.assertEqual(w._btn_undo.toolTip(), "Undo: Annotation")
        self.undo()
        self.assertEqual(w._btn_redo.toolTip(), "Redo: Annotation")
        self.assertEqual(w.statusBar().currentMessage(), "Undid: Annotation")


if __name__ == "__main__":
    unittest.main()
