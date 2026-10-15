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
        scheme = dict(self.PlotVizApp._BUILTIN_COLOR_SCHEMES["Dark (charcoal)"])
        w._apply_color_scheme_dict(scheme)
        saved = w._collect_settings()
        w2 = self._window(chart="Line", mode="Standard")
        w2._cs_combo.setCurrentText("Dark (slate)")           # a stale selection
        w2._applying_settings = True
        try:
            w2._apply_settings(saved)
        finally:
            w2._applying_settings = False
        self.assertEqual(w2._cs_combo.currentText(), "Dark (charcoal)")
        # colours that match no scheme read '(custom)'
        saved["chart_bg_color"] = "#123456"
        w2._applying_settings = True
        try:
            w2._apply_settings(saved)
        finally:
            w2._applying_settings = False
        self.assertEqual(w2._cs_combo.currentText(), "(custom)")


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


    def test_palette_and_scheme_combos_show_their_colours(self):
        w = self._window(chart="Line", mode="Standard")
        for combo in (w.palette_combo, w._cs_combo):
            self.assertGreater(combo.count(), 3)
            missing = [combo.itemText(i) for i in range(combo.count())
                       if combo.itemIcon(i).isNull() and combo.itemText(i) != "(custom)"]
            self.assertEqual(missing, [])
        # a palette added later gets its strip too
        from ui.tab_constants import add_custom_palette
        add_custom_palette("mine", ["#112233"] * 16)
        w.palette_combo.addItem("mine")
        w._refresh_palette_swatches()
        self.assertFalse(w.palette_combo.itemIcon(w.palette_combo.findText("mine")).isNull())


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
