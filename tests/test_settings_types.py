"""Keep the settings TypedDicts in core/settings_types.py honest.

mypy only catches a mistyped key when the value is later used with a conflicting
type (``settings.get("typo")`` quietly yields ``object``). These tests close the
gap in both directions:

* every literal key core/script_gen.py reads from the settings / series_meta is
  a declared key (so a typo or a stale key fails here);
* the keys the real UI writes (``_collect_settings`` etc.) match the
  declarations, so adding a widget without declaring its key fails here.
"""
import ast
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

import _bootstrap  # noqa: F401
from core.settings_types import (  # noqa: E402
    ChartOpts, DerivedSettings, PlotSettings, SeriesEntry, SeriesMeta, UiSettings,
)

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "src", "plotviz")

SETTINGS_KEYS = set(PlotSettings.__annotations__)
META_KEYS = set(SeriesMeta.__annotations__)
ENTRY_KEYS = set(SeriesEntry.__annotations__)

# Variable names in script_gen.py that hold each kind of dict.
SETTINGS_VARS = {"settings", "sub_settings"}
META_VARS = {"series_meta"}


def _literal_keys(tree, var_names):
    """(key, lineno) for every ``var.get('k')``, ``var['k']`` or
    ``subplot_get(var, 'k', ...)`` on one of *var_names*."""
    found = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("get", "setdefault")
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in var_names
                and node.args and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            found.append((node.args[0].value, node.lineno))
        elif (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
              and node.value.id in var_names and isinstance(node.slice, ast.Constant)
              and isinstance(node.slice.value, str)):
            found.append((node.slice.value, node.lineno))
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id == "subplot_get" and len(node.args) >= 2
              and isinstance(node.args[0], ast.Name) and node.args[0].id in var_names
              and isinstance(node.args[1], ast.Constant)):
            found.append((node.args[1].value, node.lineno))
    return found


class TestDeclaredKeysCoverCoreReads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(_SRC, "core", "script_gen.py")) as fh:
            cls.tree = ast.parse(fh.read())

    def test_settings_keys_read_by_script_gen_are_declared(self):
        unknown = sorted((k, ln) for k, ln in _literal_keys(self.tree, SETTINGS_VARS)
                         if k not in SETTINGS_KEYS)
        self.assertEqual(unknown, [], "undeclared settings keys (typo or missing "
                                      "entry in core/settings_types.py)")

    def test_series_meta_keys_read_by_script_gen_are_declared(self):
        unknown = sorted((k, ln) for k, ln in _literal_keys(self.tree, META_VARS)
                         if k not in META_KEYS)
        self.assertEqual(unknown, [])

    def test_checker_actually_sees_the_keys(self):
        # Guard against the scan silently matching nothing.
        self.assertGreater(len(_literal_keys(self.tree, SETTINGS_VARS)), 50)
        self.assertGreater(len(_literal_keys(self.tree, META_VARS)), 3)

    def test_checker_flags_a_typo(self):
        tree = ast.parse("settings.get('xlabel_sizee', 11)\nsettings['dpi']")
        keys = [k for k, _ in _literal_keys(tree, SETTINGS_VARS)]
        self.assertIn("xlabel_sizee", keys)
        self.assertNotIn("xlabel_sizee", SETTINGS_KEYS)


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:
        return False
    return hasattr(QApplication, "instance")


HAVE_QT = _have_real_qt()


@unittest.skipUnless(HAVE_QT, "real PyQt6 not available")
class TestUiWritesWhatIsDeclared(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if _SRC not in sys.path:
            sys.path.insert(0, _SRC)
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import PlotVizApp
        cls._app = QApplication.instance() or QApplication([])
        cls._orig = PlotVizApp._load_on_startup
        PlotVizApp._load_on_startup = lambda self: None
        cls.PlotVizApp = PlotVizApp
        cls.win = PlotVizApp()
        cls._app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.PlotVizApp._load_on_startup = cls._orig

    def test_collect_settings_keys_match_declarations(self):
        written = set(self.win._collect_settings()) | {"annotations"}
        declared = set(UiSettings.__annotations__) | set(ChartOpts.__annotations__)
        self.assertEqual(sorted(written - declared), [],
                         "UI writes keys missing from core/settings_types.py")
        self.assertEqual(sorted(declared - written), [],
                         "core/settings_types.py declares keys the UI no longer writes")

    def test_chart_option_table_matches_chart_opts(self):
        table_keys = {key for _, key, _, _ in self.win.CHART_OPT_FIELDS}
        self.assertEqual(sorted(table_keys ^ set(ChartOpts.__annotations__)), [])

    def test_series_meta_keys_match_declarations(self):
        written = set(self.win._collect_series_meta())
        declared = set(SeriesMeta.__annotations__) - set(DerivedSettings.__annotations__)
        # subplot_z_cols is optional and only read, never written by the UI.
        self.assertEqual(sorted(written - set(SeriesMeta.__annotations__)), [])
        self.assertEqual(sorted(declared - written - {"subplot_z_cols"}), [])

    def test_series_entry_keys_match_declarations(self):
        w = self.win
        w.series_table.setRowCount(0)
        w._add_series_row()
        entries = w._collect_series_meta()["series"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(sorted(set(entries[0]) ^ ENTRY_KEYS), [])


if __name__ == "__main__":
    unittest.main()
