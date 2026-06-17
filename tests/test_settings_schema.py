"""Tests for the typed per-subplot settings model in core.settings_schema."""
import unittest

import _bootstrap  # noqa: F401

ss = _bootstrap.load_module("core/settings_schema.py", "core.settings_schema")
SubplotStyle = ss.SubplotStyle
subplot_get = ss.subplot_get


class TestSubplotGet(unittest.TestCase):
    def test_str_key(self):
        s = {"d": {"0": 5}}
        self.assertEqual(subplot_get(s, "d", 0, -1), 5)

    def test_int_key(self):
        s = {"d": {1: 9}}
        self.assertEqual(subplot_get(s, "d", 1, -1), 9)

    def test_default_when_missing(self):
        self.assertEqual(subplot_get({}, "d", 0, "fallback"), "fallback")

    def test_default_when_dict_none(self):
        self.assertEqual(subplot_get({"d": None}, "d", 0, 7), 7)


class TestSubplotStyleDefaults(unittest.TestCase):
    def test_empty_settings_gives_documented_defaults(self):
        st = SubplotStyle.from_settings({}, 0)
        self.assertEqual(st.xlabel_size, 11)
        self.assertEqual(st.ylabel_rotation, 90)
        self.assertEqual(st.title_pad, 6)
        self.assertEqual(st.xscale, "linear")
        self.assertIsNone(st.xlim)
        self.assertFalse(st.equal_aspect)
        self.assertEqual(st.fg, "#000000")
        self.assertEqual(st.plot_bg, "#ffffff")
        self.assertEqual(st.xtick_size, 9)
        self.assertFalse(st.grid_on)
        self.assertTrue(st.border_top)

    def test_frozen(self):
        st = SubplotStyle.from_settings({}, 0)
        with self.assertRaises(Exception):
            st.fg = "#fff"  # frozen dataclass


class TestSubplotStyleResolution(unittest.TestCase):
    def test_global_label_fields(self):
        s = {"xlabel_size": 14, "xlabel_color": "#abc", "xlabel_font": "Serif"}
        st = SubplotStyle.from_settings(s, 0)
        self.assertEqual((st.xlabel_size, st.xlabel_color, st.xlabel_font),
                         (14, "#abc", "Serif"))

    def test_per_subplot_override(self):
        s = {"subplot_xscales": {"1": "log"}, "subplot_xlims": {"1": [0, 5]}}
        st = SubplotStyle.from_settings(s, 1)
        self.assertEqual(st.xscale, "log")
        self.assertEqual(st.xlim, [0, 5])
        # other subplot keeps default
        self.assertEqual(SubplotStyle.from_settings(s, 0).xscale, "linear")

    def test_tick_size_fallback_chain(self):
        # per-subplot wins
        self.assertEqual(
            SubplotStyle.from_settings({"subplot_xtick_sizes": {"0": 7},
                                        "xtick_size": 20}, 0).xtick_size, 7)
        # falls back to global xtick_size
        self.assertEqual(
            SubplotStyle.from_settings({"xtick_size": 20}, 0).xtick_size, 20)
        # falls back to hard default
        self.assertEqual(SubplotStyle.from_settings({}, 0).xtick_size, 9)

    def test_grid_global(self):
        st = SubplotStyle.from_settings({"grid_on": True, "grid_color": "#ccc"}, 0)
        self.assertTrue(st.grid_on)
        self.assertEqual(st.grid_color, "#ccc")


if __name__ == "__main__":
    unittest.main()
