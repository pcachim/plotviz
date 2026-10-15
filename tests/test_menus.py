"""The menu bar: unique shortcuts, discoverable undo/redo, no hijacked Ctrl+C.

Runs only where a real PyQt6 is installed; skipped otherwise.
"""
import collections
import os
import sys
import unittest

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


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestMenus(unittest.TestCase):
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
        self.win = self.PlotVizApp()
        self._app.processEvents()

    def _actions(self):
        return [a for m in self.win.menuBar().actions() for a in m.menu().actions()
                if not a.isSeparator()]

    def _action(self, text):
        return next(a for a in self._actions() if a.text() == text)

    def test_no_shortcut_is_used_twice(self):
        keys = collections.Counter(s.toString() for a in self._actions() for s in a.shortcuts())
        self.assertEqual([k for k, n in keys.items() if n > 1], [])

    def test_copy_image_does_not_take_over_ctrl_c(self):
        keys = [s.toString() for s in self._action("Copy Image to Clipboard").shortcuts()]
        self.assertNotIn("Ctrl+C", keys)
        self.assertFalse(any(s.toString() == "Ctrl+C" for a in self._actions() for s in a.shortcuts()))

    def test_undo_and_redo_are_in_the_edit_menu(self):
        edit = next(m.menu() for m in self.win.menuBar().actions() if m.text() == "Edit")
        names = [a.text() for a in edit.actions() if not a.isSeparator()]
        self.assertEqual(names[:2], ["Undo", "Redo"])
        undo, redo = self._action("Undo"), self._action("Redo")
        self.assertEqual(undo.shortcut().toString(), "Ctrl+Z")
        self.assertIn("Ctrl+Y", [s.toString() for s in redo.shortcuts()])
        self.assertIn("Ctrl+Shift+Z", [s.toString() for s in redo.shortcuts()])

    def test_undo_and_redo_follow_the_history(self):
        # Fake history entries: put the real (empty) stacks back afterwards, or the
        # debounced snapshot timer would later trip over them inside a Qt slot
        # (an unhandled exception there aborts the whole test run).
        w = self.win
        timer = getattr(w, "_snapshot_timer", None)
        if timer is not None:
            timer.stop()
        saved = (w._undo_stack, w._redo_stack)
        try:
            w._undo_stack, w._redo_stack = [{}], []
            w._update_undo_buttons()
            self.assertFalse(self._action("Undo").isEnabled())
            self.assertFalse(self._action("Redo").isEnabled())
            w._undo_stack, w._redo_stack = [{}, {}], [{}]
            w._update_undo_buttons()
            self.assertTrue(self._action("Undo").isEnabled())
            self.assertTrue(self._action("Redo").isEnabled())
        finally:
            w._undo_stack, w._redo_stack = saved
            w._update_undo_buttons()

    def test_open_recent_lists_the_recent_charts(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.pviz"), os.path.join(d, "b.pviz")
            for fp in (a, b):
                open(fp, "w").close()
            with mock.patch("config.settings.get_recent_files", return_value=[a, b]):
                self.win._rebuild_recent_files_ui()
            self.assertEqual([x.text() for x in self.win._recent_menu.actions()],
                             ["a.pviz", "b.pviz"])
            with mock.patch.object(self.win, "_load_project_from_path") as load:
                self.win._recent_menu.actions()[1].trigger()
            load.assert_called_once_with(b)

    def test_open_recent_says_so_when_empty(self):
        from unittest import mock
        with mock.patch("config.settings.get_recent_files", return_value=[]):
            self.win._rebuild_recent_files_ui()
        acts = self.win._recent_menu.actions()
        self.assertEqual([x.text() for x in acts], ["No recent charts"])
        self.assertFalse(acts[0].isEnabled())

    def test_every_entry_has_a_status_tip(self):
        missing = [a.text() for a in self._actions()
                   if a.menu() is None and not a.statusTip()
                   and a.text() not in ("About plotviz", "Preferences…")]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
