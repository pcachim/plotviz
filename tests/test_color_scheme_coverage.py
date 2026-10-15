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
        self.assertEqual(schemes["Nature / print"]["color_palette"], "Nature")
        self.assertEqual(schemes["Scientific (minimal)"]["color_palette"], "Colorblind")
        for s in schemes.values():                       # every palette must exist
            self.assertIn(s["color_palette"], COLOR_PALETTES)
        light = [schemes[n] for n in ("Default (white)", "Nature / print", "Scientific (minimal)")]
        self.assertEqual(len({tuple(sorted(s.items())) for s in light}), 3)


if __name__ == "__main__":
    unittest.main()
