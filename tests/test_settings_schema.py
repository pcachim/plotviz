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


class TestSubplotCanvasAndGrid(unittest.TestCase):
    """Canvas colours, borders and grid belong to each subplot; old files only have global keys."""

    SETTINGS = {
        "plot_bg_color": "#111111", "border_top": True, "grid_on": False, "grid_color": "#222222",
        "subplot_canvas_opts": {"1": {"plot_bg": "#fff1e5", "fg": "#333333", "border_top": False}},
        "subplot_grid_opts": {"1": {"enabled": True, "color": "#ff0000", "ls": ":", "lw": 2.0,
                                    "alpha": 0.5, "minor_enabled": True, "minor_color": "#00ff00"}},
    }

    def test_a_subplot_uses_its_own_options(self):
        st = SubplotStyle.from_settings(self.SETTINGS, 1)
        self.assertEqual((st.plot_bg, st.fg, st.border_top), ("#fff1e5", "#333333", False))
        self.assertEqual((st.grid_on, st.grid_color, st.grid_linestyle, st.grid_linewidth, st.grid_alpha),
                         (True, "#ff0000", ":", 2.0, 0.5))
        self.assertEqual((st.minor_grid_on, st.minor_grid_color), (True, "#00ff00"))

    def test_a_subplot_without_options_and_old_files_use_the_global_keys(self):
        for idx in (0, 2):
            st = SubplotStyle.from_settings(self.SETTINGS, idx)
            self.assertEqual((st.plot_bg, st.border_top, st.grid_on, st.grid_color),
                             ("#111111", True, False, "#222222"))

    def test_options_with_missing_keys_fall_back_per_key(self):
        st = SubplotStyle.from_settings(self.SETTINGS, 1)
        self.assertTrue(st.border_bottom)                 # not in the subplot's options


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
