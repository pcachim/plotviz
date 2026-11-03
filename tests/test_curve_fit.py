"""Curve fitting (data/scientific.py) and the Curves tab that drives it.

The pure half checks the models on data of very different scales, against known parameters and
against statsmodels; the GUI half (skipped without Qt) the behaviour in the app.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

import _bootstrap  # noqa: F401
from data.scientific import CurveFitter as CF


def noisy(f, x, sigma, seed=0):
    return f(x) + np.random.default_rng(seed).normal(0, sigma, len(x))


class TestFitsAtAnyScale(unittest.TestCase):
    """The starting values come from the data: the old fixed ones failed outside x, y ~ 1."""

    def check(self, model, x, y, truth, rtol=0.05):
        r = CF.fit_ex(x, y, model)
        np.testing.assert_allclose(r["popt"], truth, rtol=rtol, atol=0.02)
        self.assertGreater(r["r2"], 0.99)
        return r

    def test_exponential_over_a_long_x_range(self):
        x = np.linspace(0, 1000, 80)
        self.check("Exponential", x, noisy(lambda x: 50 * np.exp(-x / 200), x, 0.2), [50, -0.005])
        self.check("Exponential", x, noisy(lambda x: np.exp(x / 200), x, 0.5), [1, 0.005])

    def test_exponential_that_decays_or_is_negative(self):
        x = np.linspace(0, 10, 60)
        self.check("Exponential", x, noisy(lambda x: 100 * np.exp(-0.3 * x), x, 0.5), [100, -0.3])
        self.check("Exponential", x, noisy(lambda x: -4 * np.exp(0.4 * x), x, 0.3), [-4, 0.4])

    def test_sigmoid_with_large_amplitude_small_scale_or_decreasing(self):
        x = np.linspace(0, 6, 80)
        self.check("Sigmoid", x, noisy(lambda x: 100 / (1 + np.exp(-(x - 3) / 0.3)), x, 1), [100, 3, 0.3])
        x = np.linspace(0, 100, 80)
        self.check("Sigmoid", x, noisy(lambda x: 5 / (1 + np.exp(-(x - 50) / -5)), x, 0.05), [5, 50, -5])
        x = np.linspace(0, 10, 80)
        self.check("Sigmoid", x, noisy(lambda x: 1000 / (1 + np.exp(-(x - 5) / 0.5)), x, 5), [1000, 5, 0.5])

    def test_power_law_and_logarithmic_keep_their_real_x(self):
        x = np.linspace(1, 100, 80)
        r = self.check("Power Law", x, noisy(lambda x: 3 * x ** 1.5, x, 2), [3, 1.5])
        self.assertEqual(r["x0"], 0.0)
        r = self.check("Logarithmic", x, noisy(lambda x: 2 * np.log(x) + 1, x, 0.1), [2, 1])
        self.assertEqual(r["x0"], 0.0)

    def test_polynomials_and_exponential_far_from_zero_use_a_shifted_x(self):
        years = np.linspace(2000, 2010, 60)
        r = CF.fit_ex(years, noisy(lambda x: 2 * np.exp(0.5 * (x - 2000)), years, 0.5), "Exponential")
        self.assertGreater(r["r2"], 0.999)
        self.assertGreater(r["x0"], 1900)                       # measured from about 2005
        self.assertAlmostEqual(r["popt"][1], 0.5, delta=0.01)   # the rate does not depend on x0
        self.assertIn("₀", r["eq_str"])                    # the equation says x - x0
        # the function takes the real x
        np.testing.assert_allclose(r["func"](years, *r["popt"]), 2 * np.exp(0.5 * (years - 2000)), rtol=0.05)
        days = 19800 + np.arange(60.0)                          # a date column
        truth = {"Linear": lambda t: 0.5 * t + 3, "Quadratic": lambda t: 0.01 * t ** 2 + 3,
                 "Cubic": lambda t: 1e-4 * t ** 3 + 3, "Exponential": lambda t: 2 * np.exp(0.05 * t)}
        for model, f in truth.items():
            y = noisy(lambda d: f(d - 19800), days, 0.3)
            self.assertGreater(CF.fit_ex(days, y, model)["r2"], 0.99, model)

    def test_no_shift_for_ordinary_data(self):
        x = np.linspace(0, 10, 30)
        r = CF.fit_ex(x, 2 * x + 1, "Linear")
        self.assertEqual(r["x0"], 0.0)
        self.assertNotIn("₀", r["eq_str"])


class TestFailuresAreReported(unittest.TestCase):
    def test_domain_of_log_and_power(self):
        x = np.linspace(0, 10, 20)
        for model in ("Logarithmic", "Power Law"):
            with self.assertRaisesRegex(ValueError, "greater than 0"):
                CF.fit_ex(x, x + 1, model)
            self.assertEqual(CF.fit(x, x + 1, model)[0], None)

    def test_too_few_points(self):
        with self.assertRaisesRegex(ValueError, "at least 3 points"):
            CF.fit_ex([1.0, 2.0], [1.0, 2.0], "Quadratic")

    def test_nan_points_are_skipped_and_counted(self):
        x = np.linspace(0, 10, 30)
        y = 2 * x + 1
        y[4] = np.nan
        x[9] = np.inf
        r = CF.fit_ex(x, y, "Linear")
        self.assertEqual((r["n"], r["n_dropped"]), (28, 2))
        np.testing.assert_allclose(r["popt"], [2, 1], atol=1e-8)

    def test_a_fit_that_does_not_converge_is_an_error_not_garbage(self):
        x = np.linspace(0, 10, 30)
        y = np.where(np.arange(30) % 2 == 0, 1e6, -1e6)         # nothing like an exponential
        try:
            r = CF.fit_ex(x, y, "Exponential")
        except ValueError as err:
            self.assertIn("converge", str(err))
        else:                                                   # if it does return, it is finite
            self.assertTrue(np.isfinite(r["r2"]) and np.all(np.isfinite(r["popt"])))


class TestStatisticsAgainstStatsmodels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import statsmodels.api as sm
        rng = np.random.default_rng(2)
        cls.x = np.linspace(0, 10, 40)
        cls.y = 2 * cls.x + 1 + rng.normal(0, 1, 40)
        r = CF.fit_ex(cls.x, cls.y, "Linear")
        cls.r = r
        cls.st = CF.full_stats(cls.x, cls.y, r["popt"], r["pcov"], r["func"], "Linear")
        cls.sm = sm
        cls.ols = sm.OLS(cls.y, sm.add_constant(cls.x)).fit()

    def test_the_summary_numbers(self):
        st, ols = self.st, self.ols
        for key, ref in (("r2", ols.rsquared), ("r2_adj", ols.rsquared_adj), ("f_stat", ols.fvalue),
                         ("aic", ols.aic), ("bic", ols.bic)):
            self.assertAlmostEqual(st[key], ref, places=6, msg=key)

    def test_tiny_p_values_do_not_underflow_to_zero(self):
        self.assertGreater(self.st["f_pvalue"], 0)
        self.assertAlmostEqual(self.st["f_pvalue"] / self.ols.f_pvalue, 1.0, places=6)
        self.assertGreater(self.st["param_pvalue"][0], 0)

    def test_the_parameter_table(self):
        st, ols = self.st, self.ols
        np.testing.assert_allclose(st["param_se"], ols.bse[::-1], rtol=1e-6)
        np.testing.assert_allclose(st["param_ci_lo"], ols.conf_int()[::-1, 0], rtol=1e-6)

    def test_f_test_only_where_it_means_something(self):
        x = np.linspace(0, 10, 50)
        y = noisy(lambda x: 3 * np.exp(0.3 * x), x, 0.5)
        r = CF.fit_ex(x, y, "Exponential")
        st = CF.full_stats(x, y, r["popt"], r["pcov"], r["func"], "Exponential")
        self.assertTrue(np.isnan(st["f_stat"]) and np.isnan(st["f_pvalue"]))

    def test_bands_are_exact_in_probability_even_for_few_points(self):
        sm = self.sm
        x = np.arange(6.0)
        y = 2 * x + np.random.default_rng(4).normal(0, 1, 6)
        r = CF.fit_ex(x, y, "Linear")
        dof = 6 - 2
        pred = sm.OLS(y, sm.add_constant(x)).fit().get_prediction(sm.add_constant(x))
        alpha = 1 - 0.9544997361                                  # the coverage of 2 sigma
        up, lo = CF.confidence_band(x, r["popt"], r["pcov"], r["func"], 2, dof)
        ref = pred.conf_int(alpha=alpha)
        np.testing.assert_allclose(up, ref[:, 1], atol=1e-4)
        np.testing.assert_allclose(lo, ref[:, 0], atol=1e-4)
        pu, pl = CF.prediction_band(x, y, r["popt"], r["pcov"], r["func"], 2)
        ref = pred.conf_int(obs=True, alpha=alpha)
        np.testing.assert_allclose(pu, ref[:, 1], atol=1e-4)
        np.testing.assert_allclose(pl, ref[:, 0], atol=1e-4)

    def test_band_multiplier(self):
        self.assertEqual(CF.band_multiplier(2), 2.0)              # without dof: n sigma
        self.assertGreater(CF.band_multiplier(2, 4), 2.5)         # few points: Student t
        self.assertAlmostEqual(CF.band_multiplier(2, 10_000), 2.0, delta=0.01)


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:  # noqa: BLE001 - any import failure means "no usable Qt"
        return False
    return hasattr(QApplication, "instance")


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestCurvesTab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from ui.main_window import PlotVizApp
        cls._app = QApplication.instance() or QApplication([])
        cls._orig = PlotVizApp._load_on_startup
        PlotVizApp._load_on_startup = lambda self: None
        cls.PlotVizApp = PlotVizApp
        cls.QMessageBox = QMessageBox

    @classmethod
    def tearDownClass(cls):
        cls.PlotVizApp._load_on_startup = cls._orig

    def setUp(self):
        self.messages = []
        for name in ("warning", "critical", "information"):
            self.addCleanup(setattr, self.QMessageBox, name, getattr(self.QMessageBox, name))
            setattr(self.QMessageBox, name, staticmethod(
                lambda *a, _n=name, **k: self.messages.append((_n, a[2] if len(a) > 2 else ""))))

    def window(self, datasets, rows=None):
        w = self.PlotVizApp()
        w.datasets.update(datasets)
        w.update_lists()
        rows = rows or [("x", "y")]
        while w.series_table.rowCount() < len(rows):
            w._add_series_row()
        for r, (xc, yc) in enumerate(rows):
            w.series_table.cellWidget(r, 0).setCurrentText(xc)
            w.series_table.cellWidget(r, 1).setCurrentText(yc)
        return w

    def fit(self, w, model):
        w.fit_combo.setCurrentText(model)
        w.apply_fit()

    def test_a_fit_on_unsorted_x_is_drawn_left_to_right_with_its_bands(self):
        from matplotlib.figure import Figure
        rng = np.random.default_rng(5)
        x = rng.permutation(np.linspace(0, 10, 40))
        w = self.window({"x": x, "y": 2 * x + 1 + rng.normal(0, 0.5, 40)})
        self.fit(w, "Linear")
        w.fit_ci_combo.setCurrentIndex(2)
        axes_list, *_ = w._render_axes(Figure())
        line = next(l for l in axes_list[0].get_lines() if "fit" in l.get_label())
        self.assertTrue(np.all(np.diff(line.get_xdata()) >= 0))
        ribbon = axes_list[0].collections[0].get_paths()[0].vertices[:, 0]
        steps = np.diff(ribbon)
        steps = steps[steps != 0]
        self.assertEqual(int(np.sum(np.diff(np.sign(steps)) != 0)), 1)   # forward along one edge, back along the other

    def test_nan_in_the_data_is_ignored_and_reported_in_the_results(self):
        y = 2 * np.linspace(0, 10, 30) + 1
        y[5] = np.nan
        w = self.window({"x": np.linspace(0, 10, 30), "y": y})
        self.fit(w, "Linear")
        self.assertEqual(self.messages, [])
        text = w.fit_results_text.toPlainText()
        self.assertIn("1 point(s) with a NaN", text)
        self.assertIn("n            = 29", text)

    def test_a_failed_fit_says_why(self):
        x = np.linspace(0, 10, 30)
        w = self.window({"x": x, "y": x + 1})
        self.fit(w, "Logarithmic")
        self.assertEqual(len(self.messages), 1)
        self.assertIn("greater than 0", self.messages[0][1])
        self.assertEqual(w._fits, {})

    def test_exponential_on_dates_and_the_shift_survives_save_and_open(self):
        from core import dates as D
        from core.serialize import encode_datasets, write_project_zip
        x = D.DateArray(19800 + np.arange(40.0))
        y = noisy(lambda d: 2 * np.exp(0.05 * (d - 19800)), np.asarray(x), 0.2, seed=7)
        w = self.window({"x": x, "y": y})
        self.fit(w, "Exponential")
        name = next(iter(w._fits))
        fit = w._fits[name]
        self.assertGreater(fit["r2"], 0.99)
        self.assertGreater(fit["x0"], 19000)
        self.assertIn("x₀", w.fit_results_text.toPlainText())
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "f.pviz")
            write_project_zip(fp, w._collect_settings(), w._collect_series_meta(), encode_datasets(w.datasets))
            w2 = self.PlotVizApp()
            w2._load_project_inner(fp, silent=True)
        again = w2._fits[name]
        self.assertAlmostEqual(again["x0"], fit["x0"])
        np.testing.assert_allclose(again["func"](np.asarray(x), *again["popt"]),
                                   fit["func"](np.asarray(x), *fit["popt"]))

    def band_labels(self, w):
        from matplotlib.figure import Figure
        axes_list, *_ = w._render_axes(Figure())
        return [c.get_label() for a in axes_list for c in a.collections]

    def fit_row(self, w, name):
        return next(r for r in range(w.series_table.rowCount())
                    if w.series_table.cellWidget(r, 1).currentText() == name)

    def test_the_bands_show_whatever_type_the_fit_curve_has(self):
        rng = np.random.default_rng(1)
        x = np.linspace(0, 10, 40)
        for kind in ("Line", "Scatter", "Step", "Area", "Bar", "Stem", "Errorbar", "Fill Between"):
            w = self.window({"x": x, "y": 2 * x + 1 + rng.normal(0, 0.6, 40)})
            self.fit(w, "Linear")
            name = next(iter(w._fits))
            w.curve_select.setCurrentText(name)
            w.fit_ci_combo.setCurrentIndex(2)
            w.fit_pi_combo.setCurrentIndex(2)
            w.series_table.cellWidget(self.fit_row(w, name), 3).setCurrentText(kind)
            labels = self.band_labels(w)
            self.assertIn(f"{name} CI", labels, kind)
            self.assertIn(f"{name} PI", labels, kind)

    def three_fits(self):
        rng = np.random.default_rng(3)
        x = np.linspace(0, 10, 40)
        w = self.window({"x": x, "y": 0.3 * x ** 2 - x + 2 + rng.normal(0, 0.6, 40)})
        for model in ("Linear", "Quadratic", "Cubic"):
            self.fit(w, model)
        return w

    def test_the_default_axis_titles_name_the_data_not_every_fit(self):
        from matplotlib.figure import Figure
        from core.script_gen import generate_plot_script
        w = self.three_fits()
        fig = Figure()
        w._render_axes(fig)
        self.assertEqual(fig.axes[0].get_ylabel(), "Series 1")            # not "Series 1, Series 1 (Linear fit), …"
        self.assertEqual(w.ylabel_input.placeholderText(), "y")
        settings = w._collect_settings()
        used = {"x", "y"} | set(w._fits)
        script = generate_plot_script(settings, w._collect_series_meta(),
                                      {k: w.datasets[k] for k in used}, ["#1f77b4"], "t")
        self.assertIn("set_ylabel('Series 1'", script)                      # the exported chart says the same
        self.assertNotIn("Linear fit", script.split("set_ylabel(")[1].split(")")[0])
        w.series_table.item(0, 2).setText("measured")                       # a typed label still wins
        fig = Figure()
        w._render_axes(fig)
        self.assertEqual(fig.axes[0].get_ylabel(), "measured")
        w.subplot_ylabels[0] = "my axis"
        fig = Figure()
        w._render_axes(fig)
        self.assertEqual(fig.axes[0].get_ylabel(), "my axis")

    def test_each_fit_of_a_series_gets_its_own_colour(self):
        w = self.three_fits()
        colours = [w.curve_styles[name]["color"] for name in w._fits]
        self.assertEqual(len(set(colours)), 3)
        self.assertNotIn(w.curve_styles["Series 1"]["color"], colours)      # nor the series' own

    def test_the_fits_list_shows_every_fit_and_selecting_one_selects_its_curve(self):
        w = self.three_fits()
        t = w.fit_table
        self.assertEqual([t.item(r, 1).text() for r in range(t.rowCount())], ["Linear", "Quadratic", "Cubic"])
        self.assertEqual(w.curve_select.currentText(), "Series 1 (Cubic fit)")         # the last, selected
        self.assertEqual([i.row() for i in t.selectionModel().selectedRows()], [2])
        t.selectRow(0)                                                  # click the first
        self.assertEqual(w.curve_select.currentText(), "Series 1 (Linear fit)")
        self.assertIn("Model:  Linear", w.fit_results_text.toPlainText())
        self.assertTrue(w._fit_controls_widget.isEnabled())
        w.curve_select.setCurrentText("Series 1 (Quadratic fit)")       # and the other way round
        self.assertEqual([i.row() for i in t.selectionModel().selectedRows()], [1])
        self.assertEqual(t.item(0, 3).text(), f'{w._fits["Series 1 (Linear fit)"]["stats"]["r2"]:.4f}')

    def test_the_lowest_aic_of_a_series_is_marked(self):
        w = self.three_fits()                              # the data are quadratic
        t = w.fit_table
        bold = [r for r in range(t.rowCount()) if t.item(r, 5).font().bold()]
        best = min(range(t.rowCount()), key=lambda r: float(t.item(r, 5).text()))
        self.assertEqual(bold, [best])
        self.assertIn(t.item(best, 1).text(), ("Quadratic", "Cubic"))

    def test_hiding_a_fit_removes_it_and_its_bands_from_the_chart_but_keeps_it(self):
        from PyQt6.QtCore import Qt
        from matplotlib.figure import Figure
        w = self.three_fits()
        name = "Series 1 (Quadratic fit)"
        w.curve_select.setCurrentText(name)
        w.fit_ci_combo.setCurrentIndex(2)

        def drawn():
            fig = Figure()
            w._render_axes(fig)
            return ([l.get_label() for l in fig.axes[0].get_lines()],
                    [c.get_label() for c in fig.axes[0].collections])

        self.assertIn(name, drawn()[0])
        self.assertIn(f"{name} CI", drawn()[1])
        w.fit_table.item(1, 0).setCheckState(Qt.CheckState.Unchecked)
        lines, bands = drawn()
        self.assertNotIn(name, lines)
        self.assertEqual(bands, [])
        self.assertIn("Series 1 (Linear fit)", lines)                   # the others stay
        self.assertIn(name, w._fits)                                    # and it is not lost
        self.assertEqual(w._collect_series_meta()["series"][2]["y_col"], name)   # still saved in the chart
        self.assertNotIn(name, [s["y_col"] for s in w._without_hidden_fits(w._collect_series_meta())["series"]])
        # it survives save and open, hidden
        from core.serialize import encode_datasets, write_project_zip
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "f.pviz")
            write_project_zip(fp, w._collect_settings(), w._collect_series_meta(), encode_datasets(w.datasets))
            w2 = self.PlotVizApp()
            w2._load_project_inner(fp, silent=True)
        self.assertFalse(w2._fits[name]["visible"])
        self.assertEqual(w2.fit_table.rowCount(), 3)
        self.assertEqual(w2.fit_table.item(1, 0).checkState(), Qt.CheckState.Unchecked)

    def test_remove_fit_takes_only_the_selected_fit_and_asks_before_removing_several(self):
        w = self.three_fits()
        w.curve_select.setCurrentText("Series 1 (Quadratic fit)")
        w._remove_fit()                                                 # one fit selected: only it goes
        self.assertEqual(list(w._fits), ["Series 1 (Linear fit)", "Series 1 (Cubic fit)"])
        self.assertEqual(w.fit_table.rowCount(), 2)
        answers = []
        self.addCleanup(setattr, self.QMessageBox, "question", self.QMessageBox.question)
        self.QMessageBox.question = staticmethod(lambda *a, **k: answers.append(a[2]) or self.QMessageBox.StandardButton.No)
        w.curve_select.setCurrentText("Series 1")                       # the data curve: all its fits
        w._remove_fit()
        self.assertEqual(len(w._fits), 2)                               # declined
        self.assertIn("Remove all 2 fits", answers[0])
        self.QMessageBox.question = staticmethod(lambda *a, **k: self.QMessageBox.StandardButton.Yes)
        w._remove_fit()
        self.assertEqual((w._fits, w.fit_table.rowCount()), ({}, 0))

    def test_the_results_never_fall_back_to_another_fit(self):
        w = self.three_fits()
        w.curve_select.setCurrentText("Series 1")                       # not a fit
        text = w.fit_results_text.toPlainText()
        self.assertNotIn("Model:", text)
        self.assertIn("Select a fit curve", text)
        self.messages.clear()
        w._export_fit_results()                                         # nothing selected: no silent last fit
        self.assertEqual(self.messages[0][0], "information")
        self.assertIn("Select a fit curve", self.messages[0][1])

    def test_applying_the_same_model_again_says_it_replaced_the_previous_fit(self):
        x = np.linspace(0, 10, 30)
        w = self.window({"x": x, "y": 2 * x + np.random.default_rng(1).normal(0, 0.5, 30)})
        self.fit(w, "Linear")
        self.assertNotIn("replaces", w.fit_results_text.toPlainText())
        self.fit(w, "Linear")
        self.assertIn("replaces the previous fit", w.fit_results_text.toPlainText())
        self.assertEqual(len(w._fits), 1)

    def test_the_fit_of_a_secondary_axis_series_is_drawn_on_that_axis_with_its_bands(self):
        from PyQt6.QtCore import Qt
        from matplotlib.figure import Figure
        rng = np.random.default_rng(3)
        x = np.linspace(0, 10, 40)
        w = self.window({"x": x, "y": 2 * x + 1 + rng.normal(0, 0.8, 40),
                         "big": 1000 * (x + 3) + rng.normal(0, 50, 40)}, [("x", "y"), ("x", "big")])
        w.series_table.item(1, 5).setCheckState(Qt.CheckState.Checked)          # "big" on Y2
        w.curve_select.setCurrentText("Series 2")
        self.fit(w, "Linear")
        name = next(iter(w._fits))
        row = self.fit_row(w, name)
        self.assertEqual(w.series_table.item(row, 5).checkState(), Qt.CheckState.Checked)
        w.curve_select.setCurrentText(name)
        w.fit_ci_combo.setCurrentIndex(2)
        fig = Figure()
        w._render_axes(fig)
        left, right = fig.axes[0], fig.axes[1]           # the primary axes and the twin on the right
        self.assertEqual([l.get_label() for l in left.get_lines()], ["Series 1"])      # not squashed
        self.assertLess(left.get_ylim()[1], 100)
        self.assertIn(name, [l.get_label() for l in right.get_lines()])
        self.assertIn(f"{name} CI", [c.get_label() for c in right.collections])
        # fitting again keeps the fit on the same axis
        w.curve_select.setCurrentText(name)
        self.fit(w, "Linear")
        self.assertEqual(w.series_table.item(self.fit_row(w, name), 5).checkState(), Qt.CheckState.Checked)

    def test_a_fit_without_a_covariance_says_why_it_has_no_bands(self):
        w = self.window({"x": np.array([0.0, 1.0, 2.0]), "y": np.array([1.0, 0.0, 3.0])})
        self.fit(w, "Quadratic")                       # 3 points, 3 parameters: nothing left to estimate from
        self.assertIn("no bands can be drawn", w.fit_results_text.toPlainText())

    def test_renaming_the_fit_curve_keeps_its_bands_and_controls(self):
        rng = np.random.default_rng(1)
        x = np.linspace(0, 10, 40)
        w = self.window({"x": x, "y": 2 * x + 1 + rng.normal(0, 0.6, 40)})
        self.fit(w, "Linear")
        name = next(iter(w._fits))
        w.curve_select.setCurrentText(name)
        w.fit_ci_combo.setCurrentIndex(2)
        w.series_table.item(self.fit_row(w, name), 2).setText("my fit")
        self.assertEqual(self.band_labels(w), ["my fit CI"])
        w.curve_select.setCurrentText("my fit")
        self.assertTrue(w._fit_controls_widget.isEnabled())
        self.assertEqual(w.fit_ci_combo.currentIndex(), 2)
        self.assertIn("Linear", w.fit_results_text.toPlainText())
        w.fit_ci_combo.setCurrentIndex(0)
        self.assertEqual(self.band_labels(w), [])
        w._remove_fit()                                   # also removes the renamed row
        self.assertEqual(w._fits, {})
        self.assertEqual([w.series_table.item(r, 2).text() for r in range(w.series_table.rowCount())],
                         ["Series 1"])

    def test_applying_a_fit_with_a_fit_curve_selected_fits_the_data_not_the_curve(self):
        rng = np.random.default_rng(2)
        x = np.linspace(0, 10, 40)
        w = self.window({"x": x, "y": 0.3 * x ** 2 - x + rng.normal(0, 0.5, 40)})
        self.fit(w, "Linear")
        linear = next(iter(w._fits))
        w.curve_select.setCurrentText(linear)                       # the app selects the fit after a fit
        self.fit(w, "Quadratic")
        self.assertEqual(list(w._fits), [linear, "Series 1 (Quadratic fit)"])   # not "(Linear fit) (Quadratic fit)"
        quad = w._fits["Series 1 (Quadratic fit)"]
        self.assertLess(quad["r2"], 1.0 - 1e-6)                     # it fitted noisy data
        self.assertGreater(quad["stats"]["rmse"], 0.1)
        w.fit_ci_combo.setCurrentIndex(2)
        up, lo = w.datasets["Series 1 (Quadratic fit) CI upper"], w.datasets["Series 1 (Quadratic fit) CI lower"]
        self.assertGreater(float(np.mean(up - lo)), 0.05)           # visible bands

    def test_the_default_band_opacity_is_the_same_everywhere_and_shows_the_prediction_band(self):
        from ui.tab_constants import DEFAULT_FIT_BAND_OPACITY
        w = self.PlotVizApp()
        self.assertEqual(w.fit_ci_alpha_spin.value(), DEFAULT_FIT_BAND_OPACITY)
        self.assertEqual(w._default_settings()["fit_ci_alpha"], DEFAULT_FIT_BAND_OPACITY)
        self.assertGreaterEqual(DEFAULT_FIT_BAND_OPACITY / 2, 0.15)       # the prediction band is half of it
        x = np.linspace(0, 10, 30)
        w = self.window({"x": x, "y": 2 * x + 1 + np.random.default_rng(3).normal(0, 0.5, 30)})
        self.fit(w, "Linear")
        w.curve_select.setCurrentText(next(iter(w._fits)))
        w.fit_pi_combo.setCurrentIndex(2)
        from matplotlib.figure import Figure
        axes_list, *_ = w._render_axes(Figure())
        alpha = axes_list[0].collections[0].get_alpha()
        self.assertAlmostEqual(alpha, DEFAULT_FIT_BAND_OPACITY / 2)

    def test_data_that_lie_exactly_on_the_curve_say_why_there_are_no_bands(self):
        x = np.linspace(0, 10, 30)
        w = self.window({"x": x, "y": 2 * x + 1})
        self.fit(w, "Linear")
        self.assertIn("bands", w.fit_results_text.toPlainText())
        self.assertIn("no width", w.fit_results_text.toPlainText())
        rng = np.random.default_rng(3)
        w = self.window({"x": x, "y": 2 * x + 1 + rng.normal(0, 0.5, 30)})
        self.fit(w, "Linear")
        self.assertNotIn("no width", w.fit_results_text.toPlainText())

    def test_renaming_the_series_keeps_its_fit_attached(self):
        x = np.linspace(0, 10, 30)
        w = self.window({"x": x, "y": 2 * x + 1})
        self.fit(w, "Linear")
        name = next(iter(w._fits))
        w.series_table.item(0, 2).setText("measured")
        self.assertEqual(w._fits[name]["lbl"], "measured")
        w.curve_select.setCurrentText("measured")
        w._remove_fit()
        self.assertEqual(w._fits, {})
        self.assertNotIn(name, w.datasets)


if __name__ == "__main__":
    unittest.main()
