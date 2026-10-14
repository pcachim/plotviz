"""Generator + smoke tests for ui.python_export.generate_plot_script.

These tests build a complete standalone script from a settings/series_meta
dict and (a) assert that decoration features are emitted, and (b) actually
run the generated plot.py in a subprocess with the Agg backend to prove it
executes and produces a non-empty image. This is the regression net for the
fidelity work: if the generator emits broken Python, these tests fail.
"""
import os
import subprocess
import sys
import tempfile
import unittest

import _bootstrap  # noqa: F401

pe = _bootstrap.script_gen()

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "src", "plotviz")


def _write_csv(path, columns):
    n = max((len(v) for v in columns.values()), default=0)
    names = list(columns)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(",".join(names) + "\n")
        for i in range(n):
            fh.write(",".join(str(columns[c][i]) if i < len(columns[c]) else ""
                              for c in names) + "\n")


def _run_script(script, datasets, workdir):
    """Write plot.py + data/data.csv, run it headless, return the PNG path."""
    os.makedirs(os.path.join(workdir, "data"), exist_ok=True)
    _write_csv(os.path.join(workdir, "data", "data.csv"), datasets)
    out_png = os.path.join(workdir, "out.png")
    script = script.replace("plt.show()", f"plt.savefig({out_png!r}, dpi=70)")
    with open(os.path.join(workdir, "plot.py"), "w", encoding="utf-8") as fh:
        fh.write(script)
    env = dict(os.environ, MPLBACKEND="Agg")
    res = subprocess.run([sys.executable, "plot.py"], cwd=workdir, env=env,
                         capture_output=True, text=True)
    return out_png, res


def _single_line():
    datasets = {"x": [0, 1, 2, 3, 4], "y": [0, 1, 4, 9, 16]}
    settings = {
        "chart_type": "Line", "subplot_rows": 1, "subplot_cols": 1,
        "title_text": "T", "title_show": True, "title_font": "DejaVu Sans",
        "title_size": 14, "title_color": "#000", "title_x": 0.5, "title_y": 0.98,
        "title_pos_format": "fractions", "title_ha": "center", "title_rotation": 0,
        "chart_bg_color": "#fff", "plot_bg_color": "#fafafa", "chart_fg_color": "#000",
        "fig_unit": "cm", "fig_width": 18, "fig_height": 12,
        "xlabel_font": "DejaVu Sans", "xlabel_size": 11, "xlabel_color": "#003",
        "ylabel_font": "DejaVu Sans", "ylabel_size": 11, "ylabel_color": "#300",
        "grid_on": True, "grid_color": "#ccc", "grid_linestyle": "-",
        "grid_linewidth": 0.6, "grid_alpha": 0.5,
        "border_top": False, "border_right": False,
        "border_bottom": True, "border_left": True,
    }
    meta = {"series": [{"x_col": "x", "y_col": "y", "label": "sq",
                        "series_type": "Line", "plot_num": 1}]}
    return settings, meta, datasets


def _grid_mixed():
    settings, meta, datasets = _single_line()
    settings.update({"subplot_rows": 2, "subplot_cols": 1,
                     "subplot_chart_types": {"0": "Line", "1": "Bar"},
                     "subplot_title_show": {"0": True, "1": True},
                     "sp_titles": {"0": "top", "1": "bottom"}})
    datasets["z"] = [4, 3, 2, 1, 0]
    meta = {"series": [
        {"x_col": "x", "y_col": "y", "label": "sq", "series_type": "Line", "plot_num": 1},
        {"x_col": "x", "y_col": "z", "label": "dn", "series_type": "Bar", "plot_num": 2}],
        "subplot_chart_types": {"0": "Line", "1": "Bar"}}
    return settings, meta, datasets


PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c"] + ["#333"] * 13


class TestGeneratorEmission(unittest.TestCase):
    def test_decoration_features_present(self):
        settings, meta, datasets = _single_line()
        settings["subplot_yscales"] = {"0": "log"}
        settings["subplot_xlims"] = {"0": [0, 4]}
        settings["minor_grid_on"] = True
        settings["minor_grid_color"] = "#eee"
        settings["minor_grid_linestyle"] = ":"
        settings["minor_grid_linewidth"] = 0.4
        settings["minor_grid_alpha"] = 0.5
        script = pe.generate_plot_script(settings, meta, datasets, PALETTE, "c")
        self.assertIn("set_yscale('log')", script)
        self.assertIn("set_xlim(0", script)
        self.assertIn("color='#003'", script)            # styled x label
        self.assertIn("grid(True, which='major'", script)
        self.assertIn("grid(True, which='minor'", script)
        self.assertIn("rcParams['font.family'] = 'DejaVu Sans'", script)
        self.assertIn("spines['top'].set_visible(False)", script)
        self.assertIn("set_facecolor('#fafafa')", script)  # plot_bg on axes

    def test_default_labels_match_the_live_chart(self):
        # Single axes: X is the X column, Y is the series label ("sq", not the
        # column "y") - except grid-type charts, which use the Y column name.
        settings, meta, datasets = _single_line()
        script = pe.generate_plot_script(settings, meta, datasets, PALETTE, "c")
        self.assertIn("set_xlabel('x'", script)
        self.assertIn("set_ylabel('sq'", script)
        settings, meta, datasets = _one_series("Heatmap", label="sq")
        script = pe.generate_plot_script(settings, meta, datasets, PALETTE, "c")
        self.assertIn("set_ylabel('y'", script)

    def test_output_is_valid_python(self):
        for build in (_single_line, _grid_mixed):
            settings, meta, datasets = build()
            script = pe.generate_plot_script(settings, meta, datasets, PALETTE, "c")
            compile(script, "<gen>", "exec")  # raises SyntaxError on bad output


def _one_series(series_type, label="s", **styles):
    """Single-subplot project whose only series is of *series_type*.

    *styles* become the series' per-series ``opts`` (curve_styles[label]['opts']).
    """
    settings, meta, datasets = _single_line()
    settings["chart_type"] = series_type
    if styles:
        settings["curve_styles"] = {label: {"opts": styles}}
    meta = {"series": [{"x_col": "x", "y_col": "y", "label": label,
                        "series_type": series_type, "plot_num": 1}]}
    return settings, meta, datasets


def _gen(settings, meta, datasets):
    return pe.generate_plot_script(settings, meta, datasets, PALETTE, "c")


class TestMatchesLiveChart(unittest.TestCase):
    """The script must resolve per-series options the way the live chart does."""

    def test_scatter_alpha_default_matches_preview(self):
        # The live scatter alpha default is 0.7 (the Series-tab spinbox).
        script = _gen(*_one_series("Scatter"))
        self.assertIn("alpha=0.7", script)

    def test_scatter_alpha_uses_series_option(self):
        script = _gen(*_one_series("Scatter", sc_alpha=0.3))
        self.assertIn("alpha=0.3", script)
        self.assertNotIn("alpha=0.7", script)

    def test_area_alpha_default_matches_preview(self):
        script = _gen(*_one_series("Area"))
        self.assertIn("alpha=0.4", script)

    def test_area_alpha_uses_series_option(self):
        script = _gen(*_one_series("Area", area_alpha=0.9))
        self.assertIn("alpha=0.9", script)

    def test_bubble_alpha_keeps_its_own_default(self):
        # Bubble has its own alpha (default 0.6), distinct from scatter's 0.7.
        script = _gen(*_one_series("Bubble"))
        self.assertIn("alpha=0.6", script)
        script = _gen(*_one_series("Bubble", bubble_alpha=0.25))
        self.assertIn("alpha=0.25", script)

    def test_histogram_edge_colour_default_is_white(self):
        script = _gen(*_one_series("Histogram"))
        self.assertIn("edgecolor='white'", script)

    def test_histogram_edge_colour_uses_series_option(self):
        script = _gen(*_one_series("Histogram", hist_edgecolor="red"))
        self.assertIn("edgecolor='red'", script)
        self.assertNotIn("edgecolor='white'", script)

    def test_histogram_edge_colour_auto_is_the_series_colour(self):
        script = _gen(*_one_series("Histogram", hist_edgecolor="auto"))
        self.assertIn("edgecolor='#1f77b4'", script)   # palette[0]

    def test_histogram_edge_colour_none_means_no_edge(self):
        settings, meta, datasets = _one_series("Histogram", hist_edgecolor="none")
        script = _gen(settings, meta, datasets)
        self.assertIn("edgecolor=None", script)
        with tempfile.TemporaryDirectory() as d:
            out, res = _run_script(script, datasets, d)
            self.assertEqual(res.returncode, 0, res.stderr)


def _cat_data():
    return {"cat": ["a", "b", "c", "d"], "v": [1.0, -2.0, 3.0, 2.5],
            "u": [2.0, 1.0, -1.0, 0.5], "x": [1, 2, 3, 4], "y": [2.0, 1.0, 3.0, 2.0],
            "z": [0.1, 0.2, 0.1, 0.3]}


def _project(series, datasets, types=None, rows=1, cols=1, **settings_extra):
    """Settings/meta for *series* (list of dicts) in a rows x cols layout."""
    settings, meta, _ = _single_line()
    settings.update({"subplot_rows": rows, "subplot_cols": cols, **settings_extra})
    if types:
        settings["subplot_chart_types"] = {str(k): v for k, v in types.items()}
        settings["chart_type"] = types[0]
    meta = {"series": series}
    if types:
        meta["subplot_chart_types"] = {str(k): v for k, v in types.items()}
    return settings, meta, datasets


def _ser(x, y, label, kind, plot_num=1, y2=False):
    return {"x_col": x, "y_col": y, "label": label, "series_type": kind,
            "plot_num": plot_num, "y2": y2}


class TestExportMatchesPreview(unittest.TestCase):
    """Behaviours the exported script must share with the live chart."""

    def _run_ok(self, settings, meta, datasets):
        script = _gen(settings, meta, datasets)
        with tempfile.TemporaryDirectory() as d:
            out, res = _run_script(script, datasets, d)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(os.path.getsize(out) > 0)
        return script

    def test_categorical_axis_is_not_reset_to_linear(self):
        # set_xscale('linear') on a string axis turns its labels into numbers.
        settings, meta, ds = _project([_ser("cat", "v", "a", "Line")], _cat_data(),
                                      {0: "Line"})
        script = self._run_ok(settings, meta, ds)
        self.assertNotIn("set_xscale('linear')", script)
        self.assertNotIn("set_yscale('linear')", script)
        self.assertIn("plt.setp(ax.get_xticklabels(), rotation=45, ha='right')", script)

    def test_log_scale_is_still_emitted(self):
        settings, meta, ds = _single_line()
        settings["subplot_xscales"] = {"0": "log"}
        self.assertIn("set_xscale('log')", _gen(settings, meta, ds))

    def test_legend_follows_the_live_rules(self):
        s, m, d = _project([_ser("x", "y", "a", "Heatmap")], _cat_data(), {0: "Heatmap"})
        self.assertNotIn(".legend(", _gen(s, m, d))          # no legend for heatmaps
        s, m, d = _project([_ser("x", "y", "a", "Line")], _cat_data(), {0: "Line"},
                           subplot_legends={"0": False})
        self.assertNotIn(".legend(", _gen(s, m, d))          # "Show legend" off
        s, m, d = _project([_ser("x", "y", "a", "Line")], _cat_data(), {0: "Line"})
        self.assertIn(".legend(", _gen(s, m, d))

    def test_per_subplot_chart_options_override_global_ones(self):
        # Without the override every subplot used the active subplot's options.
        settings, meta, ds = _project(
            [_ser("x", "y", "a", "Histogram", 1), _ser("x", "z", "b", "Histogram", 2)],
            _cat_data(), {0: "Histogram", 1: "Histogram"}, rows=2, hist_bins=20)
        meta["subplot_chart_opts"] = {"0": {"hist_bins": 5}, "1": {"hist_bins": 15}}
        script = self._run_ok(settings, meta, ds)
        self.assertIn("bins=5,", script)
        self.assertIn("bins=15,", script)
        self.assertNotIn("bins=20,", script)

    def test_multiple_bar_series_are_grouped(self):
        two = [_ser("x", "y", "a", "Bar"), _ser("x", "z", "b", "Bar")]
        settings, meta, ds = _project(two, _cat_data(), {0: "Bar"})
        script = self._run_ok(settings, meta, ds)
        self.assertIn("width=0.4", script)                  # 0.8 split between 2 series
        self.assertIn("+ -0.2", script)                     # offsets +-0.2
        self.assertIn("+ 0.2", script)

    def test_grouped_categorical_bars_share_one_category_axis(self):
        two = [_ser("cat", "v", "a", "Bar"), _ser("cat", "u", "b", "Bar")]
        settings, meta, ds = _project(two, _cat_data(), {0: "Bar"})
        script = self._run_ok(settings, meta, ds)
        self.assertIn("_bar_cats", script)
        self.assertIn("set_xticklabels(_bar_cats, rotation=45", script)

    def test_waterfall_connectors(self):
        s, m, d = _project([_ser("cat", "v", "a", "Waterfall")], _cat_data(), {0: "Waterfall"})
        with_conn = self._run_ok(s, m, d)
        self.assertIn("linestyle='--'", with_conn)
        s["waterfall_connector"] = False
        self.assertNotIn("linestyle='--'", _gen(s, m, d))

    def test_errorbar_uses_the_error_column(self):
        s, m, d = _project([_ser("x", "y", "a", "Errorbar")], _cat_data(), {0: "Errorbar"})
        m["err_col"] = "z"
        script = self._run_ok(s, m, d)
        self.assertIn("yerr=df['z']", script)

    def test_boxplot_and_violin_options(self):
        s, m, d = _project([_ser("x", "y", "a", "Boxplot"), _ser("x", "z", "b", "Boxplot")],
                           _cat_data(), {0: "Boxplot"}, box_vert=False, box_alpha=0.4)
        script = self._run_ok(s, m, d)
        self.assertIn("vert=False", script)
        self.assertIn("set_alpha(0.4)", script)
        self.assertIn("set_yticklabels(['a', 'b'])", script)
        s, m, d = _project([_ser("x", "y", "a", "Violin")], _cat_data(), {0: "Violin"},
                           violin_show_extrema=True)
        self.assertIn("showextrema=True", self._run_ok(s, m, d))

    def test_colorbar_carries_the_series_label(self):
        s, m, d = _project([_ser("x", "y", "sq", "Heatmap")], _cat_data(), {0: "Heatmap"})
        m["z_col"] = "z"
        script = self._run_ok(s, m, d)
        self.assertIn("_cb.set_label('sq'", script)

    def test_radar_spokes_come_from_the_x_column(self):
        s, m, d = _project([_ser("cat", "v", "a", "Radar"), _ser("cat", "u", "b", "Radar")],
                           _cat_data(), {0: "Radar"}, radar_gridlevels=3)
        script = self._run_ok(s, m, d)
        self.assertIn("_rad_n = len(df['v'])", script)
        self.assertIn("np.linspace(0, _rad_max, 3 + 1)", script)

    def test_secondary_axis_in_multi_subplot_layouts(self):
        series = [_ser("x", "y", "a", "Line", 1), _ser("x", "z", "b", "Line", 2),
                  _ser("x", "v", "c", "Line", 1, y2=True)]
        s, m, d = _project(series, _cat_data(), {0: "Line", 1: "Line"}, rows=2)
        script = self._run_ok(s, m, d)
        self.assertIn("twinx()", script)
        self.assertIn("_h1 + _h2", script)                  # combined legend

    def test_single_axes_chart_drops_y2_series(self):
        # The live single-axes chart draws only the primary series.
        series = [_ser("x", "y", "a", "Line"), _ser("x", "z", "b", "Line", y2=True)]
        s, m, d = _project(series, _cat_data(), {0: "Line"})
        script = _gen(s, m, d)
        self.assertIn("label='a'", script)
        self.assertNotIn("label='b'", script)


class TestSmokeRun(unittest.TestCase):
    def test_single_line_runs(self):
        settings, meta, datasets = _single_line()
        script = pe.generate_plot_script(settings, meta, datasets, PALETTE, "c")
        with tempfile.TemporaryDirectory() as d:
            out, res = _run_script(script, datasets, d)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(os.path.getsize(out) > 0)

    def test_grid_mixed_runs(self):
        settings, meta, datasets = _grid_mixed()
        script = pe.generate_plot_script(settings, meta, datasets, PALETTE, "c")
        with tempfile.TemporaryDirectory() as d:
            out, res = _run_script(script, datasets, d)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(os.path.getsize(out) > 0)


if __name__ == "__main__":
    unittest.main()
