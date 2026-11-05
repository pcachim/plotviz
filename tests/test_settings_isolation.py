"""Running the tests must not touch the user's real plotviz settings (recent files, last folder)."""
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _real_settings_file():
    try:
        from platformdirs import user_config_dir
    except ImportError:
        return Path.home() / ".config" / "plotviz" / "settings.json"
    return Path(user_config_dir("plotviz")) / "settings.json"


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


REAL = _real_settings_file()
BEFORE = _digest(REAL)          # taken when the tests are collected, before any of them has run


class TestSettingsIsolation(unittest.TestCase):
    def test_the_settings_of_the_tests_are_not_the_real_ones(self):
        import config.settings as st
        self.assertNotEqual(Path(st.CFG_FILE).resolve(), REAL.resolve())
        self.assertTrue(str(st.CFG_FILE).startswith(tempfile.gettempdir()) or "plotviz-tests-" in str(st.CFG_FILE))

    def test_opening_and_saving_charts_leaves_the_real_settings_alone(self):
        try:
            from PyQt6.QtWidgets import QApplication
        except Exception:  # noqa: BLE001 - no usable Qt: nothing here to exercise
            self.skipTest("real PyQt6 not available")
        from unittest import mock
        from ui.main_window import PlotVizApp
        import config.settings as st
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)
        original = PlotVizApp._load_on_startup
        PlotVizApp._load_on_startup = lambda self: None
        try:
            w = PlotVizApp()
            path = os.path.join(tempfile.mkdtemp(), "isolation.pviz")
            with mock.patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=(path, "")), \
                    mock.patch("PyQt6.QtWidgets.QMessageBox.information"), \
                    mock.patch.object(PlotVizApp, "_ask_columns_to_save", return_value=False):
                w._save_project(save_as=True)
            w._load_project_inner(path, silent=True)
            w.close()
        finally:
            PlotVizApp._load_on_startup = original
        self.assertIn(path, [str(p) for p in st.get_recent_files()])     # it went to the temporary settings
        self.assertEqual(_digest(REAL), BEFORE)                          # and the real file is as it was


if __name__ == "__main__":
    unittest.main()
