"""Reload data files, and the automatic copy of the chart with its restore after a crash."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import numpy as np  # noqa: E402

import _bootstrap  # noqa: F401,E402
from data.importing import ImportOptions, column_data, read_table  # noqa: E402


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
        return hasattr(QApplication, "instance") and not getattr(QApplication, "_is_stub", False)
    except Exception:  # noqa: BLE001
        return False


class TestImporting(unittest.TestCase):
    def test_options_survive_a_round_trip_and_unknown_names_are_ignored(self):
        opts = ImportOptions(sep=";", decimal=",", header=2, dayfirst=True)
        self.assertEqual(ImportOptions.from_dict(opts.to_dict()), opts)
        self.assertEqual(ImportOptions.from_dict({"sep": "|", "from_a_future_version": 1}).sep, "|")
        self.assertEqual(ImportOptions.from_dict(None), ImportOptions())

    def test_a_file_with_decimal_commas_is_read_with_the_saved_options(self):
        path = Path(tempfile.mkdtemp()) / "d.csv"
        path.write_text("t;v\n1;0,5\n2;1,5\n", encoding="utf-8")
        opts = ImportOptions(sep=";", decimal=",")
        columns = column_data(read_table(str(path), opts), opts)
        np.testing.assert_allclose(columns["v"], [0.5, 1.5])


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class WindowCase(unittest.TestCase):
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
        self.tmp = Path(tempfile.mkdtemp())
        self.w = self.PlotVizApp()
        self.w.show()

    def tearDown(self):
        self.w.close()


class TestReload(WindowCase):
    def write(self, text, name="data.csv"):
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def import_file(self, path):
        from PyQt6.QtWidgets import QDialog
        with mock.patch("ui.data_io.QFileDialog.getOpenFileNames", return_value=([path], "")), \
                mock.patch("ui.dialogs.DataImportDialog.exec", return_value=QDialog.DialogCode.Accepted):
            self.w._load_data_files("Load", str(self.tmp), remember_dir=False)

    def test_an_imported_column_remembers_its_file_column_and_options(self):
        path = self.write("t,v\n1,10\n2,20\n")
        self.import_file(path)
        self.assertEqual(set(self.w.datasets), {"t", "v"})
        src = self.w.dataset_sources["v"]
        self.assertEqual((src["path"], src["column"]), (os.path.abspath(path), "v"))
        self.assertEqual(src["options"]["sep"], ",")

    def test_reloading_reads_the_new_values_and_keeps_the_series(self):
        path = self.write("t,v\n1,10\n2,20\n")
        self.import_file(path)
        self.w.series_table.cellWidget(0, 0).setCurrentText("t")
        self.w.series_table.cellWidget(0, 1).setCurrentText("v")
        self.write("t,v\n1,10\n2,20\n3,35\n")
        self.w._is_dirty = False
        self.assertEqual(self.w._reload_datasets(), 2)
        np.testing.assert_allclose(self.w.datasets["v"], [10, 20, 35])
        self.assertEqual(self.w.series_table.cellWidget(0, 1).currentText(), "v")
        self.assertTrue(self.w._is_dirty)

    def test_a_renamed_column_is_found_by_its_name_in_the_file(self):
        path = self.write("t,v\n1,10\n")
        from PyQt6.QtWidgets import QDialog
        with mock.patch("ui.data_io.QFileDialog.getOpenFileNames", return_value=([path], "")), \
                mock.patch("ui.dialogs.DataImportDialog.exec", return_value=QDialog.DialogCode.Accepted), \
                mock.patch("ui.dialogs.DataImportDialog.get_selected_origin", return_value={"time": "t", "value": "v"}), \
                mock.patch("ui.dialogs.DataImportDialog.get_selected_data",
                           return_value={"time": np.array([1.0]), "value": np.array([10.0])}):
            self.w._load_data_files("Load", str(self.tmp), remember_dir=False)
        self.write("t,v\n1,11\n")
        self.w._reload_datasets()
        np.testing.assert_allclose(self.w.datasets["value"], [11])

    def test_a_column_that_left_the_file_keeps_its_values_and_is_reported(self):
        path = self.write("t,v\n1,10\n")
        self.import_file(path)
        self.write("t,w\n1,5\n")
        with mock.patch("ui.data_io.QMessageBox.warning") as warn:
            self.assertEqual(self.w._reload_datasets(), 1)           # t only
        self.assertIn('"v"', warn.call_args[0][2])
        np.testing.assert_allclose(self.w.datasets["v"], [10])

    def test_datasets_without_a_file_are_left_alone(self):
        self.w.datasets["g"] = np.arange(3.0)
        self.w.update_lists()
        with mock.patch("ui.data_io.QMessageBox.information") as info:
            self.assertEqual(self.w._reload_datasets(), 0)
        info.assert_called_once()
        self.assertEqual(self.w._reload_datasets(quiet=True), 0)

    def test_a_deleted_file_is_reported_not_raised(self):
        path = self.write("t,v\n1,10\n")
        self.import_file(path)
        os.remove(path)
        with mock.patch("ui.data_io.QMessageBox.warning") as warn:
            self.assertEqual(self.w._reload_datasets(), 0)
        warn.assert_called_once()

    def test_the_sources_are_saved_with_the_chart_and_come_back(self):
        path = self.write("t,v\n1,10\n2,20\n")
        self.import_file(path)
        self.w.series_table.cellWidget(0, 0).setCurrentText("t")
        self.w.series_table.cellWidget(0, 1).setCurrentText("v")
        chart = str(self.tmp / "c.pviz")
        self.w._current_filepath = chart
        self.w._save_project()
        self.w._load_project_inner(chart, silent=True)
        self.assertEqual(self.w.dataset_sources["v"]["path"], os.path.abspath(path))
        self.write("t,v\n1,1\n2,2\n")
        self.assertEqual(self.w._reload_datasets(), 2)
        np.testing.assert_allclose(self.w.datasets["v"], [1, 2])

    def test_a_new_chart_forgets_the_sources(self):
        self.import_file(self.write("t,v\n1,10\n"))
        self.w._is_dirty = False
        with mock.patch("ui.data_io.QMessageBox.question",
                        return_value=__import__("PyQt6.QtWidgets", fromlist=["QMessageBox"]).QMessageBox.StandardButton.Yes):
            self.w._reset_app()
        self.assertEqual(self.w.dataset_sources, {})

    def test_a_file_changed_while_away_is_offered_once(self):
        from PyQt6.QtWidgets import QMessageBox
        path = self.write("t,v\n1,10\n")
        self.import_file(path)
        self.write("t,v\n1,99\n")
        later = time.time() + 5
        os.utime(path, (later, later))
        with mock.patch("ui.data_io.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes) as ask:
            self.w._check_data_files_changed()
            self.w._check_data_files_changed()
        self.assertEqual(ask.call_count, 1)
        np.testing.assert_allclose(self.w.datasets["v"], [99])

    def test_answering_no_does_not_ask_again_until_the_file_changes_again(self):
        from PyQt6.QtWidgets import QMessageBox
        path = self.write("t,v\n1,10\n")
        self.import_file(path)
        later = time.time() + 5
        os.utime(path, (later, later))
        with mock.patch("ui.data_io.QMessageBox.question", return_value=QMessageBox.StandardButton.No) as ask:
            self.w._check_data_files_changed()
            self.w._check_data_files_changed()
        self.assertEqual(ask.call_count, 1)
        np.testing.assert_allclose(self.w.datasets["v"], [10])

    def test_the_menu_and_the_button_exist(self):
        titles = [a.text() for a in self.w.menuBar().actions()[0].menu().actions()]
        self.assertIn("Reload Data Files", titles)
        from PyQt6.QtWidgets import QPushButton
        self.assertTrue([b for b in self.w.findChildren(QPushButton) if "Reload" in b.text()])


def dead_pid():
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


class TestRecovery(WindowCase):
    def setUp(self):
        super().setUp()
        import config.recovery as recovery
        self.recovery = recovery
        self.recovery.remove()
        for f in self.recovery.recovery_dir().glob("chart-*"):
            f.unlink()
        self.w.datasets.update({"x": np.arange(5.0), "y": np.arange(5.0) ** 2})
        self.w.update_lists()
        self.w.series_table.cellWidget(0, 0).setCurrentText("x") if self.w.series_table.rowCount() else None

    def tearDown(self):
        super().tearDown()
        for f in self.recovery.recovery_dir().glob("chart-*"):
            f.unlink()

    def as_other_session(self, pid):
        """Hand this session's copy to a session with number *pid* (as if that one had crashed)."""
        for suffix in (".pviz", ".json"):
            self.recovery.chart_path().with_suffix(suffix).rename(self.recovery.chart_path(pid).with_suffix(suffix))
        import json
        meta = self.recovery.meta_path(pid)
        data = json.loads(meta.read_text())
        data["pid"] = pid
        meta.write_text(json.dumps(data))

    def test_a_changed_chart_is_copied_and_a_saved_one_is_not(self):
        self.w._is_dirty = False
        self.w._recovery_tick()
        self.assertFalse(self.recovery.has_copy())
        self.w._is_dirty = True
        self.w._recovery_tick()
        self.assertTrue(self.recovery.has_copy())
        self.w._is_dirty = False
        self.w._recovery_tick()
        self.assertFalse(self.recovery.has_copy())

    def test_an_unchanged_chart_is_not_written_again(self):
        self.w._is_dirty = True
        self.w._recovery_tick()
        stamp = self.recovery.chart_path().stat().st_mtime_ns
        time.sleep(0.02)
        self.w._recovery_tick()
        self.assertEqual(self.recovery.chart_path().stat().st_mtime_ns, stamp)
        self.w._is_dirty = True                                   # a new change
        self.w._recovery_tick()
        self.assertGreater(self.recovery.chart_path().stat().st_mtime_ns, stamp)

    def test_saving_or_closing_removes_the_copy(self):
        self.w._is_dirty = True
        self.w._recovery_tick()
        self.w._current_filepath = str(self.tmp / "c.pviz")
        with mock.patch.object(self.w, "_ask_columns_to_save", return_value=False):
            self.w._save_project()
        self.assertFalse(self.recovery.has_copy())
        self.w._is_dirty = True
        self.w._recovery_tick()
        self.assertTrue(self.recovery.has_copy())
        self.w.close()
        self.assertFalse(self.recovery.has_copy())

    def test_the_copy_of_a_session_that_ended_is_an_orphan_but_a_running_one_is_not(self):
        self.w._is_dirty = True
        self.w._recovery_tick()
        self.assertEqual(self.recovery.orphans(), [])             # this very session
        self.as_other_session(dead_pid())
        self.assertEqual(len(self.recovery.orphans()), 1)

    def test_another_running_plotviz_is_left_alone_unless_its_heartbeat_is_old(self):
        import json
        self.w._is_dirty = True
        self.w._recovery_tick()
        self.as_other_session(os.getppid())                        # a process that exists and is not this one
        self.assertEqual(self.recovery.orphans(), [])
        meta = self.recovery.meta_path(os.getppid())
        data = json.loads(meta.read_text())
        data["heartbeat"] = time.time() - 10 * self.recovery.INTERVAL_S
        meta.write_text(json.dumps(data))
        self.assertEqual(len(self.recovery.orphans()), 1)

    def test_restoring_brings_back_the_chart_and_removes_the_copies(self):
        self.w._is_dirty = True
        self.w._recovery_tick()
        self.as_other_session(dead_pid())
        other = self.PlotVizApp()
        try:
            with mock.patch("ui.recovery.QMessageBox.exec", lambda box: box.buttons()[0].click()):
                other._offer_recovery()
            self.assertEqual(set(other.datasets), {"x", "y"})
            self.assertTrue(other._is_dirty)
            self.assertEqual(self.recovery.orphans(), [])
            self.assertEqual(list(self.recovery.recovery_dir().glob("chart-*")), [])
        finally:
            other.close()

    def test_discarding_removes_the_copies_without_loading(self):
        self.w._is_dirty = True
        self.w._recovery_tick()
        self.as_other_session(dead_pid())
        other = self.PlotVizApp()
        try:
            with mock.patch("ui.recovery.QMessageBox.exec", lambda box: box.buttons()[1].click()):
                other._offer_recovery()
            self.assertEqual(other.datasets, {})
            self.assertEqual(list(self.recovery.recovery_dir().glob("chart-*")), [])
        finally:
            other.close()

    def test_nothing_is_asked_when_there_is_nothing_to_recover(self):
        with mock.patch("ui.recovery.QMessageBox.exec") as ask:
            self.w._offer_recovery()
        ask.assert_not_called()


if __name__ == "__main__":
    unittest.main()
