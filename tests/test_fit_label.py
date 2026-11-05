"""The label of a fit on the chart: the text (pure) and the annotation (real window).

The window tests run only where a real PyQt6 is installed; skipped otherwise.
"""
import os
import re
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import numpy as np  # noqa: E402

import _bootstrap  # noqa: F401,E402
from data.fit_text import FitTextOptions, equation_latex, fit_annotation_text, format_value_error, parameter_label  # noqa: E402
from data.scientific import CurveFitter  # noqa: E402


def make_fit(model, x, y, label="series", tag=""):
    result = CurveFitter.fit_ex(x, y, model)
    stats = CurveFitter.full_stats(x, y, result["popt"], result["pcov"], result["func"], model)
    return dict(model=model, lbl=label, tag=tag, eq_str=result["eq_str"], r2=result["r2"], stats=stats,
                x0=result["x0"], popt=result["popt"])


def data_for(model):
    rng = np.random.default_rng(3)
    x = np.linspace(0.5, 10, 80)
    clean = {
        "Linear": 2 * x + 1, "Quadratic": 0.3 * x ** 2 - x + 2, "Cubic": 0.02 * x ** 3 - 0.3 * x ** 2 + x,
        "Exponential": 2 * np.exp(0.2 * x), "Exponential + offset": 3 * np.exp(-0.4 * x) + 1,
        "Power Law": 1.5 * x ** 1.3, "Logarithmic": 2 * np.log(x) + 1,
        "Sigmoid": 5 / (1 + np.exp(-(x - 5) / 1.2)),
        "Gaussian": 4 * np.exp(-(x - 5) ** 2 / (2 * 1.1 ** 2)) + 0.5,
        "Sinusoid": 2 * np.sin(2 * np.pi * 0.35 * x + 0.4) + 1,
        "Polynomial deg 4": 0.01 * x ** 4 - 0.2 * x ** 3 + x ** 2 - x,
        "Custom: a*x**2 + b*exp(-x/c)": 0.5 * x ** 2 + 3 * np.exp(-x / 2),
    }[model]
    return x, clean + rng.normal(0, 0.02 * (np.ptp(clean) or 1), x.size)


MODELS = ["Linear", "Quadratic", "Cubic", "Exponential", "Exponential + offset", "Power Law", "Logarithmic",
          "Sigmoid", "Gaussian", "Sinusoid", "Polynomial deg 4", "Custom: a*x**2 + b*exp(-x/c)"]


class TestFormatting(unittest.TestCase):
    def test_the_error_has_two_digits_and_the_value_the_same_decimals(self):
        self.assertEqual(format_value_error(0.2134, 0.0087), "0.2134 ± 0.0087")
        self.assertEqual(format_value_error(5.4, 0.2), "5.40 ± 0.20")
        self.assertEqual(format_value_error(1234.5, 12.3), "1234 ± 12")
        self.assertEqual(format_value_error(123456.0, 3000.0), "123500 ± 3000")

    def test_a_missing_error_or_extreme_numbers_fall_back_to_significant_digits(self):
        self.assertEqual(format_value_error(3.14159265, None), "3.142")
        self.assertEqual(format_value_error(3.14159265, float("nan")), "3.142")
        self.assertEqual(format_value_error(3.0, 0.0), "3")
        self.assertEqual(format_value_error(1e-6, 1e-8), "1e-06 ± 1e-08")

    def test_parameter_names_lose_their_explanation(self):
        self.assertEqual(parameter_label("b (rate)"), "b")
        self.assertEqual(parameter_label("σ (width)"), "σ")
        self.assertEqual(parameter_label("c2"), "c2")


def latex(fit, symbolic=False):
    """equation_latex, which is None for LOWESS, for the models that have an equation."""
    text = equation_latex(fit, symbolic=symbolic)
    assert text is not None
    return text


class TestText(unittest.TestCase):
    ALL = FitTextOptions(name=True, equation=True, parameters=True, r2=True, rmse=True, aic=True, n=True, latex=False)

    def test_every_model_gives_a_title_the_parameters_and_the_numbers(self):
        for model in MODELS:
            with self.subTest(model=model):
                x, y = data_for(model)
                fit = make_fit(model, x, y)
                text = fit_annotation_text(fit, self.ALL)
                lines = text.split("\n")
                self.assertTrue(lines[0].endswith("fit: series"), lines[0])
                self.assertTrue(lines[1].startswith("y = "), lines[1])
                n_params = len(fit["popt"])
                shown = [ln for ln in lines if re.match(r"^[\w.μσφ]+ = [−\d.e+-]+ ± [\d.e+-]+$", ln)]
                self.assertEqual(len(shown), n_params, text)
                for line, value in zip(shown, fit["popt"]):
                    printed = float(line.split("=")[1].split("±")[0].strip().replace("−", "-"))
                    self.assertAlmostEqual(printed, float(value), delta=max(abs(float(value)) * 2e-3, 0.06))
                for label in ("R² = ", "RMSE = ", "AIC = ", "n = 80"):
                    self.assertIn(label, text)

    def test_with_parameters_the_equation_is_written_with_their_names(self):
        x, y = data_for("Quadratic")
        text = fit_annotation_text(make_fit("Quadratic", x, y), FitTextOptions(parameters=True, latex=False))
        self.assertIn("y = a·x² + b·x + c", text)
        plain = fit_annotation_text(make_fit("Quadratic", x, y), FitTextOptions(parameters=False, latex=False))
        self.assertRegex(plain, r"y = [\d.]+·x²")
        self.assertNotIn("a = ", plain)

    def test_the_parameter_lines_are_typeset_too_and_matplotlib_reads_them(self):
        from matplotlib.mathtext import MathTextParser
        for model in MODELS:
            with self.subTest(model=model):
                x, y = data_for(model)
                lines = fit_annotation_text(make_fit(model, x, y), FitTextOptions(parameters=True)).split("\n")
                params = [ln for ln in lines if ln.startswith("$") and "\\pm" in ln]
                self.assertEqual(len(params), len(make_fit(model, x, y)["popt"]))
                for line in params:
                    MathTextParser("path").parse(line)
        x, y = data_for("Gaussian")
        lines = fit_annotation_text(make_fit("Gaussian", x, y), FitTextOptions(parameters=True)).split("\n")
        self.assertTrue(any(ln.startswith(r"$\mu = ") for ln in lines))
        self.assertTrue(any(ln.startswith(r"$\sigma = ") for ln in lines))

    def test_the_equation_is_written_in_latex_between_dollar_signs(self):
        x, y = data_for("Quadratic")
        fit = make_fit("Quadratic", x, y)
        numeric, symbolic = latex(fit), latex(fit, symbolic=True)
        self.assertRegex(numeric, r"^\$y = [\d.]+\\,x\^\{2\} [-+] [\d.]+\\,x [-+] [\d.]+\$$")
        self.assertEqual(symbolic, r"$y = a\,x^{2} + b\,x + c$")
        self.assertIn("-", numeric)                               # a negative coefficient is a minus sign, not "+ -"
        self.assertNotIn("+ -", numeric)

    def test_every_model_has_a_latex_equation_that_matplotlib_can_typeset(self):
        from matplotlib.mathtext import MathTextParser
        parser = MathTextParser("path")
        for model in MODELS:
            with self.subTest(model=model):
                x, y = data_for(model)
                fit = make_fit(model, x, y)
                for symbolic in (False, True):
                    text = latex(fit, symbolic=symbolic)
                    self.assertTrue(text and text.startswith("$y = ") and text.endswith("$"), text)
                    parser.parse(text)                              # raises if matplotlib cannot read it
                numeric = latex(fit)
                first = f"{abs(float(fit['popt'][0])):.4g}".split("e")[0]
                self.assertIn(first, numeric)

    def test_models_written_in_latex_have_the_expected_shape(self):
        for model, wanted in (("Exponential", r"e^{"), ("Logarithmic", r"\ln"), ("Sigmoid", r"\frac{"),
                              ("Gaussian", r"\left(x - "), ("Sinusoid", r"\sin"), ("Power Law", "x^{")):
            with self.subTest(model=model):
                x, y = data_for(model)
                self.assertIn(wanted, latex(make_fit(model, x, y)))
        x, y = data_for("Gaussian")
        self.assertIn(r"\mu", latex(make_fit("Gaussian", x, y), symbolic=True))
        x, y = data_for("Polynomial deg 4")
        self.assertIn("c_{4}", latex(make_fit("Polynomial deg 4", x, y), symbolic=True))

    def test_lowess_has_no_latex_equation(self):
        self.assertIsNone(equation_latex({"model": "LOWESS span 0.3", "stats": {}}))

    def test_the_default_is_the_title_the_equation_and_r2(self):
        x, y = data_for("Linear")
        lines = fit_annotation_text(make_fit("Linear", x, y)).split("\n")
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[1].startswith("$y = ") and lines[1].endswith("$"))
        self.assertTrue(lines[2].startswith("R² = "))

    def test_a_far_away_x_is_shifted_and_the_label_says_by_how_much(self):
        rng = np.random.default_rng(5)
        years = np.linspace(1990, 2020, 40)
        y = 2.5 * np.exp(0.03 * (years - 2005)) + rng.normal(0, 0.05, 40)
        text = fit_annotation_text(make_fit("Exponential", years, y), FitTextOptions(parameters=True, latex=False))
        self.assertIn("(x−x₀)", text)
        self.assertRegex(text, r"x₀ = 2005")
        typeset = fit_annotation_text(make_fit("Exponential", years, y), FitTextOptions(parameters=True))
        self.assertIn(r"\left(x - x_{0}\right)", typeset)
        self.assertIn("$x_{0} = 2005$", typeset)

    def test_lowess_has_no_equation_and_no_parameters(self):
        x = np.linspace(0, 10, 60)
        y = np.sin(x) + np.random.default_rng(2).normal(0, 0.1, 60)
        fit = make_fit("LOWESS span 0.3", x, y)
        fit["stats"] = {}
        text = fit_annotation_text(fit, FitTextOptions(parameters=True))
        self.assertIn("LOWESS fit:", text)
        self.assertIn("no equation", text)
        self.assertNotIn("±", text)

    def test_the_tag_of_a_weighted_or_ranged_fit_is_in_the_title(self):
        x, y = data_for("Linear")
        fit = make_fit("Linear", x, y, label="pulse", tag=", x 2–8, robust")
        self.assertEqual(fit_annotation_text(fit, FitTextOptions(equation=False, r2=False)),
                         "Linear fit: pulse, x 2–8, robust")


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:  # noqa: BLE001 - any import failure means "no usable Qt"
        return False
    return hasattr(QApplication, "instance")


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestLabelOnTheChart(unittest.TestCase):
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
        x = np.linspace(0, 10, 60)
        y = 0.3 * x ** 2 - x + 2 + np.random.default_rng(1).normal(0, 0.3, 60)
        w = self.w = self.PlotVizApp()
        w.show()
        w.datasets.update({"x": x, "y": y})
        w.update_lists()
        w._add_series_row()
        w.series_table.cellWidget(0, 0).setCurrentText("x")
        w.series_table.cellWidget(0, 1).setCurrentText("y")
        for model in ("Linear", "Quadratic"):
            w.fit_combo.setCurrentText(model)
            w.apply_fit()
        self.keys = list(w._fits)

    def tearDown(self):
        self.w.close()

    def exported(self):
        """The chart as exported: (the annotation boxes by their text, the axes box), in pixels."""
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        wi, hi = self.w._fig_size_in_inches()
        fig = self.w._build_export_figure(wi, hi, 100)
        FigureCanvasAgg(fig).draw()
        renderer = fig.canvas.get_renderer()
        ax = fig._pviz_axes[0]
        boxes = {t.get_text(): t.get_bbox_patch().get_window_extent(renderer) for t in ax.texts if t.get_bbox_patch()}
        return boxes, ax.get_window_extent(renderer)

    def test_the_label_is_a_text_annotation_at_the_top_left_of_the_exported_plot_area(self):
        ann = self.w._add_fit_label(self.keys[1])
        self.assertEqual((ann["type"], ann["source_fit"]), ("text", self.keys[1]))
        self.assertIn("Quadratic fit:", ann["label"])
        boxes, area = self.exported()
        box = boxes[ann["label"]]
        self.assertGreaterEqual(box.x0, area.x0)
        self.assertLessEqual(box.y1, area.y1)
        point = 10 * 100 / 72                                     # the default 10 pt text, in pixels at 100 dpi
        self.assertAlmostEqual(area.y1 - box.y1, 0.8 * point, delta=0.35 * point)     # a little under the top edge
        self.assertAlmostEqual(box.x0 - area.x0, 0.8 * point, delta=0.35 * point)     # and in from the left one

    def test_the_place_does_not_depend_on_the_size_of_the_window(self):
        results = []
        for size in ((700, 500), (1500, 1000)):
            self.w.resize(*size)
            self._app.processEvents()
            for ann in list(self.w.canvas.annotations):
                self.w.canvas.annotations.remove(ann)
            self.w.canvas.clear_annotations()
            ann = self.w._add_fit_label(self.keys[1])
            boxes, area = self.exported()
            results.append((round(boxes[ann["label"]].x0 - area.x0), round(area.y1 - boxes[ann["label"]].y1)))
        self.assertLessEqual(abs(results[0][0] - results[1][0]), 1)
        self.assertLessEqual(abs(results[0][1] - results[1][1]), 1)

    def test_a_second_label_goes_under_the_first_without_touching_it(self):
        first = self.w._add_fit_label(self.keys[0])
        second = self.w._add_fit_label(self.keys[1])
        boxes, _ = self.exported()
        upper, lower = boxes[first["label"]], boxes[second["label"]]
        self.assertLess(lower.y1, upper.y0)                       # a clear gap, not overlapping
        self.assertGreater(upper.y0 - lower.y1, 3)

    def test_it_is_one_undo_step(self):
        self.w._snapshot_timer.stop()
        self.w._snapshot()                                      # the state with the fits, before the label
        before = len(self.w.canvas.annotations)
        self.w._add_fit_label(self.keys[1])
        self.assertTrue(self.w._snapshot_timer.isActive())      # the label asked for its own step
        self.w._snapshot_timer.stop()
        self.w._snapshot()
        self.assertEqual(len(self.w.canvas.annotations), before + 1)
        self.w._undo()
        self.assertEqual(len(self.w.canvas.annotations), before)

    def test_it_is_saved_with_the_chart_and_drawn_in_the_export(self):
        ann = self.w._add_fit_label(self.keys[1], FitTextOptions(parameters=True))
        meta = [a for a in self.w._collect_annotations_meta() if a.get("source_fit")]
        self.assertEqual([m["source_fit"] for m in meta], [self.keys[1]])
        self.assertEqual(meta[0]["label"], ann["label"])
        wi, hi = self.w._fig_size_in_inches()
        fig = self.w._build_export_figure(wi, hi, 80)
        texts = [t.get_text() for ax in fig.axes for t in ax.texts]
        self.assertIn(ann["label"], texts)

    def test_it_is_in_the_exported_python_script(self):
        from core.script_gen import generate_plot_script
        self.w._add_fit_label(self.keys[1], FitTextOptions(parameters=True))
        settings = self.w._collect_settings()
        settings["annotations"] = self.w._collect_annotations_meta()
        meta = self.w._collect_series_meta()
        used = {c for s in meta["series"] for c in (s["x_col"], s["y_col"]) if c in self.w.datasets}
        script = generate_plot_script(settings, meta, {c: self.w.datasets[c] for c in used},
                                      [self.w._palette_color(i) for i in range(16)], "chart")
        self.assertIn("Quadratic fit", script)
        self.assertIn("x^{2}", script)                          # the typeset equation travels with the script

    def test_the_results_file_is_plain_text_without_latex(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        out = Path(tempfile.mkdtemp()) / "r.txt"
        self.w.fit_export_all_check.setChecked(True)
        with mock.patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=(str(out), "")):
            self.w._export_fit_results()
        text = out.read_text(encoding="utf-8")
        self.assertIn("Equation:", text)
        self.assertNotIn("$", text)
        self.assertNotIn("LaTeX", text)
        self.assertNotIn("\\", text)

    def test_the_label_can_be_picked_by_its_text_and_moved_like_any_annotation(self):
        ann = self.w._add_fit_label(self.keys[1], FitTextOptions(parameters=True, aic=True))   # eight lines
        canvas = self.w.canvas
        canvas.draw()
        ax = canvas.axes_list[0]
        box = canvas._annotation_box(ann)
        self.assertIsNotNone(box)
        # a point near the top of the text block, far from the anchor at its bottom left
        top_left = ax.transData.inverted().transform((box.x0 + 8, box.y1 - 8))
        far = float(np.hypot(*(np.array(top_left) - np.array([ann["x"], ann["y"]]))))
        self.assertGreater(far, 0.05 * (ax.get_ylim()[1] - ax.get_ylim()[0]))       # beyond the old 5 % reach
        self.assertIs(canvas._find_annotation_at(ax, *top_left), ann)
        # and one on the plot, away from the label, still finds nothing
        self.assertIsNone(canvas._find_annotation_at(ax, *ax.transData.inverted().transform((box.x1 + 150, box.y0 - 150))))
        # dragging works from there: the press records the offset from the anchor, the move shifts it
        canvas._drag_ann = ann
        canvas._drag_offx, canvas._drag_offy = top_left[0] - ann["x"], top_left[1] - ann["y"]
        before = (ann["x"], ann["y"])
        moved = ax.transData.inverted().transform((box.x0 + 8 + 60, box.y1 - 8 - 40))
        canvas._drag_part = "both"
        canvas._drag_ann = ann
        from matplotlib.backend_bases import MouseButton, MouseEvent
        px, py = ax.transData.transform(moved)
        canvas.on_mouse_move(MouseEvent("motion_notify_event", canvas, px, py, button=MouseButton.LEFT))
        self.assertNotEqual((ann["x"], ann["y"]), before)

    def test_picking_a_short_annotation_by_its_anchor_still_works(self):
        canvas = self.w.canvas
        canvas.draw()
        ax = canvas.axes_list[0]
        canvas._place_text_annotation(ax, 0, 5.0, 10.0, label="peak")
        ann = canvas.annotations[-1]
        self.assertIs(canvas._find_annotation_at(ax, 5.0, 10.0), ann)

    def test_the_dialog_chooses_what_the_label_shows(self):
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication, QCheckBox

        def answer():
            dialog = QApplication.activeModalWidget()
            boxes = {b.text(): b for b in dialog.findChildren(QCheckBox)}
            boxes["Parameters, with their errors"].setChecked(True)
            boxes["AIC"].setChecked(True)
            dialog.accept()
        self.w.curve_select.setCurrentText(self.keys[1])
        QTimer.singleShot(200, answer)
        self.w._add_fit_label_dialog()
        label = self.w.canvas.annotations[-1]["label"]
        self.assertIn("a = ", label)
        self.assertIn("AIC = ", label)
        self.assertEqual(len([a for a in self.w.canvas.annotations if a.get("source_fit")]), 1)

    def answer_with(self, accept=True):
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication

        def answer():
            dialog = QApplication.activeModalWidget()
            dialog.accept() if accept else dialog.reject()
        QTimer.singleShot(200, answer)

    def test_without_all_fits_only_the_selected_fit_is_labelled(self):
        self.w.curve_select.setCurrentText(self.keys[0])
        self.assertFalse(self.w.fit_export_all_check.isChecked())
        self.answer_with()
        self.w._add_fit_label_dialog()
        self.assertEqual([a["source_fit"] for a in self.w.canvas.annotations if a.get("source_fit")], [self.keys[0]])

    def test_all_fits_labels_every_fit(self):
        self.w.curve_select.setCurrentText(self.keys[0])
        self.w.fit_export_all_check.setChecked(True)
        self.answer_with()
        self.w._add_fit_label_dialog()
        labels = [a["source_fit"] for a in self.w.canvas.annotations if a.get("source_fit")]
        self.assertEqual(sorted(labels), sorted(self.keys))

    def test_with_no_fit_selected_and_all_fits_off_it_asks_for_one_and_adds_nothing(self):
        from unittest import mock
        self.w.curve_select.setCurrentIndex(0)                    # the data series, not a fit
        self.assertNotIn(self.w._selected_curve_key(), self.w._fits)
        with mock.patch("ui.fitting.QMessageBox.information") as info:
            self.w._add_fit_label_dialog()
        info.assert_called_once()
        self.assertIn("Select a fit curve first", info.call_args[0][2])
        self.assertEqual([a for a in self.w.canvas.annotations if a.get("source_fit")], [])

    def test_cancelling_the_dialog_adds_nothing(self):
        self.w.curve_select.setCurrentText(self.keys[1])
        self.answer_with(accept=False)
        self.w._add_fit_label_dialog()
        self.assertEqual([a for a in self.w.canvas.annotations if a.get("source_fit")], [])

    def test_export_writes_only_the_selected_fit_unless_all_fits_is_ticked(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        out = Path(tempfile.mkdtemp()) / "r.txt"
        for every, expected in ((False, 1), (True, 2)):
            with self.subTest(all_fits=every):
                self.w.curve_select.setCurrentText(self.keys[1])
                self.w.fit_export_all_check.setChecked(every)
                with mock.patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=(str(out), "")):
                    self.w._export_fit_results()
                self.assertEqual(out.read_text(encoding="utf-8").count("Equation:"), expected)

    def test_a_label_on_the_second_subplot_goes_in_that_subplot(self):
        self.w.sp_rows.setValue(1)
        self.w.sp_cols.setValue(2)
        self.w.update_preview()
        row = next(r for r in range(self.w.series_table.rowCount())
                   if self.w.series_table.item(r, 2).text() == self.keys[1])
        self.w.series_table.cellWidget(row, 4).setValue(2)
        self.w.update_preview()
        ann = self.w._add_fit_label(self.keys[1])
        self.assertEqual(ann["axes_index"], 1)


if __name__ == "__main__":
    unittest.main()
