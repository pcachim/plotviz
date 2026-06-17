"""Unit tests for the pure helper functions in ui.python_export."""
import unittest

import _bootstrap  # noqa: F401

pe = _bootstrap.script_gen()


class TestEsc(unittest.TestCase):
    def test_single_quote(self):
        self.assertEqual(pe._esc("it's"), "it\\'s")

    def test_backslash(self):
        self.assertEqual(pe._esc("a\\b"), "a\\\\b")

    def test_backslash_then_quote_order(self):
        # Backslashes must be escaped before quotes, else double-escaping.
        self.assertEqual(pe._esc("\\'"), "\\\\\\'")

    def test_non_string(self):
        self.assertEqual(pe._esc(12), "12")

    def test_emitted_literal_is_valid_python(self):
        for raw in ["plain", "it's a peak", "C:\\path", "quote'and\\slash"]:
            code = "x = '" + pe._esc(raw) + "'"
            ns = {}
            exec(compile(code, "<esc>", "exec"), ns)
            self.assertEqual(ns["x"], raw)


class TestColRef(unittest.TestCase):
    def test_combined_mode(self):
        self.assertEqual(pe._col_ref("a", use_combined=True), "df['a']")

    def test_multi_csv_mode(self):
        ref = pe._col_ref("my col", use_combined=False, datasets={"my col": []})
        self.assertEqual(ref, "_df_my_col['my col']")

    def test_multi_csv_sanitises_dashes(self):
        ref = pe._col_ref("a-b", use_combined=False, datasets={"a-b": []})
        self.assertEqual(ref, "_df_a_b['a-b']")

    def test_uses_global_flag_when_unspecified(self):
        old = pe._USE_COMBINED
        try:
            pe._USE_COMBINED = True
            self.assertEqual(pe._col_ref("a"), "df['a']")
        finally:
            pe._USE_COMBINED = old


class TestProjection(unittest.TestCase):
    def test_3d(self):
        self.assertEqual(pe._projection_for("3D Surface"), "'3d'")

    def test_polar(self):
        self.assertEqual(pe._projection_for("Polar"), "'polar'")

    def test_cartesian(self):
        self.assertEqual(pe._projection_for("Line"), "None")


if __name__ == "__main__":
    unittest.main()
