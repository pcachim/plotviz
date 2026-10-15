"""A colour scheme reaches every chart type, in the live chart and in the script.

Elements that used to be hard-coded black (3D panes and ticks, tricontour lines,
boxplot lines, stem baseline) must follow the scheme's foreground colour, and the
generated script must paint them the same way.

Runs only where a real PyQt6 is installed; skipped otherwise.
"""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(os.path.dirname(_HERE), "src", "plotviz"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from matplotlib.colors import to_hex  # noqa: E402

import test_script_layout as tsl  # noqa: E402

FG, BG, GRID = "#cdd6f4", "#181825", "#45475a"      # 'Dark (charcoal)'


@unittest.skipUnless(tsl.HAVE_QT, "real PyQt6 not available")
class TestColorSchemeCoverage(unittest.TestCase):
    setUpClass = classmethod(tsl.TestScriptLayoutMatchesExport.setUpClass.__func__)
    tearDownClass = classmethod(tsl.TestScriptLayoutMatchesExport.tearDownClass.__func__)
    _window = tsl.TestScriptLayoutMatchesExport._window
    _export_figure = tsl.TestScriptLayoutMatchesExport._export_figure
    _script_figure = tsl.TestScriptLayoutMatchesExport._script_figure

    def _themed(self, chart, mode):
        w = self._window(chart=chart, mode=mode)
        w._apply_color_scheme_dict(dict(self.PlotVizApp._BUILTIN_COLOR_SCHEMES["Dark (charcoal)"]))
        self._app.processEvents()
        return w

    def _both(self, chart, mode):
        w = self._themed(chart, mode)
        return self._export_figure(w).axes[0], self._script_figure(w)[0].axes[0]

    def test_3d_surface_follows_the_scheme(self):
        for ax in self._both("3D Surface", "3D"):
            self.assertEqual(to_hex(ax.get_facecolor()), "#1e1e2e")     # the page colour
            for name in "xyz":
                axis = getattr(ax, f"{name}axis")
                self.assertEqual(to_hex(axis.pane.get_facecolor()), BG)
                self.assertEqual(to_hex(axis.line.get_color()), FG)
                self.assertEqual(to_hex(axis._axinfo["grid"]["color"]), GRID)
                ticks = [t.get_color() for t in axis.get_ticklabels() if t.get_text()]
                self.assertTrue(ticks)
                self.assertTrue(all(to_hex(c) == FG for c in ticks), ticks)

    def test_3d_z_label_is_on_the_axis_not_the_colorbar(self):
        w = self._window(chart="3D Surface", mode="3D")
        for fig in (self._export_figure(w), self._script_figure(w)[0]):
            ax = [a for a in fig.axes if a.name == "3d"][0]
            cbar = [a for a in fig.axes if a.get_label() == "<colorbar>"][0]
            self.assertEqual(ax.get_zlabel(), "s")             # the series label
            self.assertEqual(cbar.get_ylabel(), "")

    def test_tricontour_lines_follow_the_foreground(self):
        w = self._themed("Tricontour", "Heatmap / Contour")
        w.tri_triplot.setChecked(True)
        for fig in (self._export_figure(w), self._script_figure(w)[0]):
            ax = fig.axes[0]
            lines = [c for c in ax.collections if c.get_linewidth()[0] > 0 and c.get_alpha() == 0.5]
            self.assertTrue(lines)
            self.assertTrue(all(to_hex(c.get_edgecolor()[0]) == FG for c in lines))

    def test_boxplot_lines_follow_the_foreground(self):
        for ax in self._both("Boxplot", "Statistical"):
            for ln in ax.lines:
                if ln.get_marker() == "o":                    # outliers: the marker edge
                    self.assertEqual(to_hex(ln.get_markeredgecolor()), FG)
                else:                                         # whiskers, caps, medians
                    self.assertEqual(to_hex(ln.get_color()), FG)

    def test_stem_baseline_follows_the_foreground(self):
        for ax in self._both("Stem", "Standard"):
            base = [ln for ln in ax.lines if len(set(ln.get_ydata())) == 1
                    and len(ln.get_xdata()) == 2]
            self.assertTrue(base)
            self.assertEqual(to_hex(base[0].get_color()), FG)

    def test_default_black_contour_lines_follow_the_foreground(self):
        w = self._themed("Contour", "Heatmap / Contour")
        w.heat_contour_lines.setChecked(True)
        for fig in (self._export_figure(w), self._script_figure(w)[0]):
            ax = fig.axes[0]
            edges = [to_hex(c.get_edgecolor()[0]) for c in ax.collections
                     if len(c.get_edgecolor()) and c.get_linewidth()[0] > 0]
            self.assertIn(FG, edges)

    def test_zlabel_colour_is_part_of_a_scheme(self):
        w = self._window(chart="3D Surface", mode="3D")
        self.assertIn("zlabel_color", w._COLOR_SCHEME_KEYS)
        w._apply_color_scheme_dict(dict(self.PlotVizApp._BUILTIN_COLOR_SCHEMES["Dark (charcoal)"]))
        self.assertEqual(w.zlabel_color, "#a6adc8")        # follows the y-label colour


    def test_choosing_a_scheme_applies_it_but_loading_a_file_does_not(self):
        w = self._window(chart="Line", mode="Standard")
        idx = w._cs_combo.findText("Dark (charcoal)")
        w._cs_combo.setCurrentIndex(idx)                       # by code: nothing applied
        self.assertNotEqual(w.chart_bg_color, "#1e1e2e")
        w._cs_combo.activated.emit(idx)                        # the user picks it
        self.assertEqual(w.chart_bg_color, "#1e1e2e")

    def test_combo_follows_the_scheme_of_the_loaded_chart(self):
        w = self._window(chart="Line", mode="Standard")      # a plain white chart
        w._activate_scheme("Dark (charcoal)")
        saved = w._collect_settings()
        self.assertEqual(saved["color_scheme_name"], "Dark (charcoal)")
        w2 = self._window(chart="Line", mode="Standard")
        w2._select_scheme("Dark (slate)")                    # a stale selection
        w2._applying_settings = True
        try:
            w2._apply_settings(saved)
        finally:
            w2._applying_settings = False
        self.assertEqual(w2._active_scheme, "Dark (charcoal)")
        # a chart whose colours differ from its built-in scheme becomes an editable copy
        saved["chart_bg_color"] = "#123456"
        w2._applying_settings = True
        try:
            w2._apply_settings(saved)
        finally:
            w2._applying_settings = False
        self.assertEqual(w2._active_scheme, "Dark (charcoal) – edited")
        self.assertIn("Dark (charcoal) – edited", w2._scheme_unsaved)
        self.assertEqual(w2._cs_combo.currentText(), "Dark (charcoal) – edited *")
        self.assertEqual(w2._COLOR_SCHEME_REGISTRY["Dark (charcoal)"]["chart_bg_color"], "#1e1e2e")

    def test_a_chart_file_brings_its_own_scheme_back(self):
        w = self._window(chart="Line", mode="Standard")
        w._register_scheme("Mine", {**w._COLOR_SCHEME_REGISTRY["Ivory"],
                                    "chart_bg_color": "#abcdef"}, unsaved=True)
        w._activate_scheme("Mine")
        saved = w._collect_settings()
        w2 = self._window(chart="Line", mode="Standard")
        self.assertNotIn("Mine", w2._COLOR_SCHEME_REGISTRY)
        w2._applying_settings = True
        try:
            w2._apply_settings(saved)
        finally:
            w2._applying_settings = False
        self.assertEqual(w2._active_scheme, "Mine")
        self.assertIn("Mine", w2._scheme_unsaved)            # exists only in this session
        self.assertEqual(w2._COLOR_SCHEME_REGISTRY["Mine"]["chart_bg_color"], "#abcdef")

    def test_editing_a_builtin_makes_an_editable_copy(self):
        w = self._window(chart="Line", mode="Standard")
        w._activate_scheme("Ivory")
        w.chart_bg_color = "#102030"                         # an edit made anywhere in the UI
        w._sync_active_scheme()
        self.assertEqual(w._active_scheme, "Ivory – edited")
        self.assertEqual(w._COLOR_SCHEME_REGISTRY["Ivory"]["chart_bg_color"], "#fffff8")
        self.assertEqual(w._COLOR_SCHEME_REGISTRY["Ivory – edited"]["chart_bg_color"], "#102030")
        w.chart_fg_color = "#445566"                         # further edits go to the copy
        w._sync_active_scheme()
        self.assertEqual(w._active_scheme, "Ivory – edited")
        self.assertEqual(w._COLOR_SCHEME_REGISTRY["Ivory – edited"]["chart_fg_color"], "#445566")
        # switching away keeps it; coming back restores it
        w._activate_scheme("Dark (slate)")
        self.assertIn("Ivory – edited", w._COLOR_SCHEME_REGISTRY)
        w._activate_scheme("Ivory – edited")
        self.assertEqual(w.chart_bg_color, "#102030")

    def test_a_copy_edited_back_to_its_origin_is_dropped(self):
        w = self._window(chart="Line", mode="Standard")
        w._activate_scheme("Ivory")
        w.chart_bg_color = "#102030"
        w._sync_active_scheme()
        w.chart_bg_color = w._BUILTIN_COLOR_SCHEMES["Ivory"]["chart_bg_color"]
        w._sync_active_scheme()
        self.assertEqual(w._active_scheme, "Ivory")
        self.assertNotIn("Ivory – edited", w._COLOR_SCHEME_REGISTRY)

    def test_edits_go_into_a_scheme_of_your_own(self):
        w = self._window(chart="Line", mode="Standard")
        w._register_scheme("Mine", w._COLOR_SCHEME_REGISTRY["Ivory"], unsaved=False)
        w._activate_scheme("Mine")
        w.chart_bg_color = "#102030"
        w._sync_active_scheme()
        self.assertEqual(w._active_scheme, "Mine")           # no copy: it is edited in place
        self.assertEqual(w._COLOR_SCHEME_REGISTRY["Mine"]["chart_bg_color"], "#102030")
        self.assertIn("Mine", w._scheme_unsaved)             # no longer matches its file

    def test_a_scheme_for_one_subplot_leaves_the_active_scheme_alone(self):
        w = self._window(chart="Line", mode="Standard")
        w.subplot_rows, w.subplot_cols = 1, 2
        w._cs_target.setEnabled(True)
        w._cs_target.setCurrentIndex(1)                      # Active subplot only
        w._activate_scheme("Dark (charcoal)")
        self.assertEqual(w._active_scheme, "Default (white)")
        self.assertEqual(w._cs_combo.currentData(), "Default (white)")
        w._sync_active_scheme()                              # per-subplot values are not tracked
        self.assertEqual(w._active_scheme, "Default (white)")

    def test_a_built_in_name_cannot_be_replaced_by_a_loaded_scheme(self):
        w = self._window(chart="Line", mode="Standard")
        name = w._register_scheme("Ivory", {"chart_bg_color": "#010203"}, unsaved=False)
        self.assertEqual(name, "Ivory (file)")
        self.assertEqual(w._COLOR_SCHEME_REGISTRY["Ivory"]["chart_bg_color"], "#fffff8")


    def test_palettes_follow_the_same_rules_as_schemes(self):
        from ui.tab_constants import COLOR_PALETTES, _CUSTOM_PALETTES
        w = self._window(chart="Line", mode="Standard")
        self.addCleanup(_CUSTOM_PALETTES.pop, "mine", None)
        self.addCleanup(_CUSTOM_PALETTES.pop, "Bold (file)", None)
        name = w._register_palette("mine", ["#112233"] * 3, unsaved=True)
        self.assertEqual(len(_CUSTOM_PALETTES[name]), 16)          # padded to 16 colours
        w._rebuild_palette_combo()
        i = w.palette_combo.findData("mine")
        self.assertEqual(w.palette_combo.itemText(i), "mine *")    # exists only in this session
        # picking it applies it, by the data and not by the label
        w.palette_combo.setCurrentIndex(i)
        self.assertEqual(w._color_palette, "mine")
        self.assertEqual(w._active_palette_colors()[0], "#112233")
        # a built-in is never replaced
        self.assertEqual(w._register_palette("Bold", ["#000000"] * 16, unsaved=False), "Bold (file)")
        self.assertEqual(COLOR_PALETTES["Bold"][0] == "#000000", False)
        # only the active palette travels with a chart, and only when it is yours
        self.assertIn("mine", w._active_palette_json())
        w._color_palette = "Bold"
        self.assertEqual(w._active_palette_json(), "{}")
        # a chart file brings its palette back as a session palette
        w._load_custom_palettes_json('{"mine": ["#445566"]}')
        self.assertIn("mine", w._palette_unsaved)
        self.assertEqual(_CUSTOM_PALETTES["mine"][0], "#445566")

    def test_a_scheme_file_carries_its_palette_colours(self):
        from ui.tab_constants import _CUSTOM_PALETTES
        w = self._window(chart="Line", mode="Standard")
        self.addCleanup(_CUSTOM_PALETTES.pop, "travelling", None)
        w._adopt_palette_from_scheme_file(
            {"_palette": {"name": "travelling", "colors": ["#0a0b0c"] * 16}})
        self.assertEqual(_CUSTOM_PALETTES["travelling"][0], "#0a0b0c")
        self.assertIn("travelling", w._palette_unsaved)

    def test_reset_palette_releases_manual_colours_and_says_so(self):
        w = self._window(chart="Line", mode="Standard")
        lbl = next(iter(w.curve_styles))
        w.curve_styles[lbl]["color"] = "#ff0000"
        w.curve_styles[lbl]["color_locked"] = True
        w._reset_all_color_locks()
        self.assertFalse(w.curve_styles[lbl].get("color_locked"))
        self.assertNotEqual(w.curve_styles[lbl]["color"], "#ff0000")
        self.assertIn("1 manually", w.statusBar().currentMessage())

    def _library(self):
        """Point the preferences folder at an empty temporary one."""
        import tempfile
        from pathlib import Path
        import config.settings as cfg
        tmp = tempfile.TemporaryDirectory()
        saved = (cfg._CFG_DIR, cfg.CFG_FILE, dict(cfg.settings))
        cfg._CFG_DIR, cfg.CFG_FILE = Path(tmp.name), Path(tmp.name) / "settings.json"
        def restore():
            cfg._CFG_DIR, cfg.CFG_FILE = saved[0], saved[1]
            cfg.settings.clear()
            cfg.settings.update(saved[2])
            tmp.cleanup()
        self.addCleanup(restore)
        return cfg

    def test_start_up_loads_every_scheme_and_palette_in_the_folders(self):
        import json
        import zipfile
        from ui.tab_constants import _CUSTOM_PALETTES
        cfg = self._library()
        self.addCleanup(_CUSTOM_PALETTES.pop, "shelf", None)
        w = self._window(chart="Line", mode="Standard")
        w._write_scheme_file(str(cfg.schemes_dir() / "Mine.pvizc"), "Mine",
                             {**w._COLOR_SCHEME_REGISTRY["Ivory"], "chart_bg_color": "#abcdef"})
        (cfg.schemes_dir() / "broken.pvizc").write_bytes(b"not a zip")
        with zipfile.ZipFile(cfg.palettes_dir() / "shelf.pvizp", "w") as zf:
            zf.writestr("palette.json", json.dumps({"shelf": ["#010203"] * 16}))
        (cfg.palettes_dir() / "broken.pvizp").write_bytes(b"not a zip")
        w._load_palette_library()
        w._load_library_schemes()                                 # a bad file is skipped
        self.assertEqual(w._COLOR_SCHEME_REGISTRY["Mine"]["chart_bg_color"], "#abcdef")
        self.assertNotIn("Mine", w._scheme_unsaved)                # in the folder: no *
        self.assertGreaterEqual(w._cs_combo.findData("Mine"), 0)
        self.assertEqual(_CUSTOM_PALETTES["shelf"][0], "#010203")
        self.assertNotIn("shelf", w._palette_unsaved)
        self.assertEqual(w.palette_combo.itemText(w.palette_combo.findData("shelf")), "shelf")

    def test_palettes_kept_in_the_preferences_move_to_the_folder(self):
        from ui.tab_constants import _CUSTOM_PALETTES
        cfg = self._library()
        self.addCleanup(_CUSTOM_PALETTES.pop, "Old one", None)
        cfg.settings["custom_palettes"] = {"Old one": ["#0a0a0a"] * 16}
        w = self._window(chart="Line", mode="Standard")
        w._load_palette_library()
        self.assertTrue((cfg.palettes_dir() / "Old one.pvizp").is_file())
        self.assertEqual(cfg.settings["custom_palettes"], {})
        self.assertNotIn("Old one", w._palette_unsaved)           # it is in the folder now

    def test_a_star_means_not_in_the_folder(self):
        import os
        cfg = self._library()
        self.assertTrue(cfg.in_folder(str(cfg.schemes_dir() / "x.pvizc"), cfg.schemes_dir()))
        self.assertFalse(cfg.in_folder(os.path.join(os.path.dirname(cfg.schemes_dir()), "x.pvizc"),
                                       cfg.schemes_dir()))
        w = self._window(chart="Line", mode="Standard")
        self.assertTrue(w._scheme_in_library(str(cfg.schemes_dir() / "x.pvizc")))
        self.assertFalse(w._scheme_in_library(str(cfg.palettes_dir() / "x.pvizc")))

    def test_a_scheme_file_round_trips_with_its_palette(self):
        from ui.tab_constants import _CUSTOM_PALETTES
        cfg = self._library()
        self.addCleanup(_CUSTOM_PALETTES.pop, "carried", None)
        w = self._window(chart="Line", mode="Standard")
        w._register_palette("carried", ["#0a0b0c"] * 16, unsaved=True)
        scheme = {**w._COLOR_SCHEME_REGISTRY["Ivory"], "color_palette": "carried"}
        fp = str(cfg.schemes_dir() / "round.pvizc")
        w._write_scheme_file(fp, "round", scheme)
        _CUSTOM_PALETTES.pop("carried")                            # a machine without it
        name, got = w._read_scheme_file(fp)
        self.assertEqual((name, got["color_palette"]), ("round", "carried"))
        self.assertEqual(_CUSTOM_PALETTES["carried"][0], "#0a0b0c")

    def test_the_light_schemes_are_distinct(self):
        from ui.tab_constants import COLOR_PALETTES
        schemes = self.PlotVizApp._BUILTIN_COLOR_SCHEMES
        for s in schemes.values():                       # every palette must exist
            self.assertIn(s["color_palette"], COLOR_PALETTES)
        light = [s for s in schemes.values() if s["chart_bg_color"] > "#cccccc"]
        self.assertEqual(len(light), 9)
        self.assertEqual(len({tuple(sorted(s.items())) for s in light}), 9)
        # no two light schemes share both a plot background and a palette
        self.assertEqual(len({(s["plot_bg_color"], s["color_palette"]) for s in light}), 9)


    def test_colormap_combos_show_their_gradients(self):
        w = self._window(chart="Line", mode="Standard")
        for name in ("cmap_combo", "tri_cmap_combo", "hist2d_cmap_combo", "hexbin_cmap_combo",
                     "quiver_cmap_combo", "barbs_cmap_combo", "stream_cmap_combo",
                     "scatter_cmap_combo"):
            combo = getattr(w, name)
            self.assertGreater(combo.count(), 10)
            self.assertTrue(all(not combo.itemIcon(i).isNull() for i in range(combo.count())), name)


    def test_palette_and_scheme_combos_show_their_colours(self):
        w = self._window(chart="Line", mode="Standard")
        for combo in (w.palette_combo, w._cs_combo):
            self.assertGreater(combo.count(), 3)
            missing = [combo.itemText(i) for i in range(combo.count())
                       if combo.itemIcon(i).isNull() and combo.itemText(i) != "(custom)"]
            self.assertEqual(missing, [])
        # a palette added later gets its strip too
        w._register_palette("mine", ["#112233"] * 16, unsaved=True)
        w._rebuild_palette_combo()
        w._refresh_palette_swatches()
        self.assertFalse(w.palette_combo.itemIcon(w.palette_combo.findData("mine")).isNull())


    # ── Apply to: all subplots / the active subplot only ─────────────────────
    def _multi(self):
        w = self._window(types=["Line", "Bar", "Line", "Bar"])
        w.update_preview()
        return w

    def test_apply_to_is_only_offered_with_several_subplots(self):
        w = self._window(chart="Line", mode="Standard")
        self.assertFalse(w._cs_target.isEnabled())
        self.assertTrue(self._multi()._cs_target.isEnabled())

    def test_a_scheme_can_be_applied_to_the_active_subplot_only(self):
        w = self._multi()
        before_fig = w.chart_bg_color
        w.global_sp_active.setCurrentIndex(1)
        w._cs_combo.setCurrentText("Dark (charcoal)")
        w._cs_target.setCurrentIndex(1)                       # Active subplot only
        w._cs_combo.activated.emit(w._cs_combo.currentIndex())
        w.update_preview()                                    # must not undo it
        opts = w.subplot_canvas_opts
        self.assertEqual(opts[1]["plot_bg"], "#181825")
        self.assertEqual(opts[1]["fg"], "#cdd6f4")
        self.assertFalse(opts[1]["border_top"])
        self.assertEqual(w.subplot_grid_opts[1]["color"], "#45475a")
        self.assertEqual(w.subplot_title_color[1], "#cdd6f4")
        for other in (0, 2, 3):                               # the rest is untouched
            self.assertEqual(to_hex(opts[other]["plot_bg"]), "#ffffff", other)
            self.assertTrue(opts[other]["border_top"], other)
        self.assertEqual(to_hex(w.chart_bg_color), to_hex(before_fig))   # figure background too
        facecolors = [to_hex(a.get_facecolor()) for a in w.canvas.figure.axes]
        self.assertEqual(facecolors.count("#181825"), 1)

    def test_loading_a_scheme_file_respects_apply_to(self):
        import json
        import tempfile
        import zipfile
        from unittest import mock
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        w = self._multi()
        scheme = dict(self.PlotVizApp._BUILTIN_COLOR_SCHEMES["Dark (charcoal)"])
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "dark.pvizc")
            with zipfile.ZipFile(fp, "w") as zf:
                zf.writestr("settings.json", json.dumps({"_scheme_name": "mine", **scheme}))
            w.global_sp_active.setCurrentIndex(2)
            w._cs_target.setCurrentIndex(1)
            asked = []
            with mock.patch.object(QFileDialog, "getOpenFileName", return_value=(fp, "")), \
                    mock.patch.object(QMessageBox, "question",
                                      side_effect=lambda *a, **k: (asked.append(a[2]),
                                                                   QMessageBox.StandardButton.Yes)[1]):
                w._load_color_scheme()
        self.assertIn("subplot 3", asked[0])                  # the question says where
        opts = w.subplot_canvas_opts
        self.assertEqual(opts[2]["plot_bg"], "#181825")
        for other in (0, 1, 3):
            self.assertEqual(to_hex(opts[other]["plot_bg"]), "#ffffff", other)

    def test_all_subplots_is_still_the_default(self):
        w = self._multi()
        w._cs_combo.setCurrentText("Dark (charcoal)")
        w._cs_combo.activated.emit(w._cs_combo.currentIndex())
        self.assertTrue(all(o["plot_bg"] == "#181825" for o in w.subplot_canvas_opts.values()))


if __name__ == "__main__":
    unittest.main()
