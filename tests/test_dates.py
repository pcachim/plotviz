"""Date/time columns: core/dates.py (pure), saving, script export, and the GUI paths.

The GUI half runs only where a real PyQt6 is installed; skipped otherwise.
"""
import copy
import os
import tempfile
import unittest
from typing import Any, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np
import pandas as pd

import _bootstrap  # noqa: F401
from core import dates as D
from core.serialize import decode_datasets, encode_datasets


class TestDateArray(unittest.TestCase):
    def test_days_since_1970(self):
        a = D.from_datetime64(np.array(['1970-01-02', '2024-03-01T12:00'], dtype='datetime64[ns]'))
        np.testing.assert_allclose(a, [1.0, 19783.5])

    def test_tag_survives_slicing_and_copy_but_not_arithmetic(self):
        a = D.from_iso(['2024-03-01', '2024-03-02', '2024-03-03'])
        self.assertTrue(D.is_date(a[:2]))
        self.assertTrue(D.is_date(copy.deepcopy(a)))
        self.assertTrue(D.is_date(a.copy()))
        self.assertFalse(D.is_date(a * 2))
        self.assertFalse(D.is_date(np.diff(a)))
        self.assertFalse(D.is_date(a.min()))
        self.assertFalse(D.is_date(np.asarray(a, dtype=float)))

    def test_iso_round_trip_picks_the_coarsest_exact_unit(self):
        self.assertEqual(D.to_iso(D.from_iso(['2024-03-01', '2024-03-05'])), ['2024-03-01', '2024-03-05'])
        self.assertEqual(D.to_iso(D.from_iso(['2024-03-01T10:30:00', '2024-03-01'])),
                         ['2024-03-01T10:30:00', '2024-03-01T00:00:00'])
        ms = D.from_iso(['2024-03-01T10:30:00.250'])
        self.assertEqual(D.to_iso(ms), ['2024-03-01T10:30:00.250'])
        np.testing.assert_allclose(D.from_iso(D.to_iso(ms)), ms)

    def test_nan_is_nat(self):
        a = D.DateArray([19783.0, np.nan])
        self.assertEqual(D.to_iso(a)[1], 'NaT')
        self.assertTrue(np.isnan(D.from_iso(D.to_iso(a))[1]))
        self.assertEqual(D.format_date(np.nan), '')

    def test_format_date(self):
        self.assertEqual(D.format_date(19783.5), '2024-03-01 12:00:00')
        self.assertEqual(D.format_date(19783.0), '2024-03-01')

    def test_parse_date_text(self):
        self.assertEqual(D.parse_date('2024-03-01'), 19783.0)
        self.assertEqual(D.parse_date('1 Mar 2024 12:00'), 19783.5)
        self.assertEqual(D.parse_date('04/03/2024', dayfirst=True), D.parse_date('2024-03-04'))
        with self.assertRaises(ValueError):
            D.parse_date('not a date')


class TestParseSeries(unittest.TestCase):
    def parse(self, values, **kw):
        return D.parse_series(pd.Series(values), **kw)

    def test_iso_dates_and_times(self):
        np.testing.assert_allclose(self.parse(['2024-03-01', '2024-03-05']), [19783, 19787])
        np.testing.assert_allclose(self.parse(['2024-03-01 10:00', '2024-03-01 12:30']),
                                   [19783 + 10 / 24, 19783 + 12.5 / 24])

    def test_mixed_formats_and_gaps(self):
        a = self.parse(['2024-03-01', '2024-03-02 12:00', None])
        np.testing.assert_allclose(a[:2], [19783, 19784.5])
        self.assertTrue(np.isnan(a[2]))

    def test_day_first_changes_the_reading(self):
        np.testing.assert_allclose(self.parse(['03/04/2024', '04/04/2024']),
                                   self.parse(['2024-03-04', '2024-04-04']))
        np.testing.assert_allclose(self.parse(['03/04/2024', '04/04/2024'], dayfirst=True),
                                   self.parse(['2024-04-03', '2024-04-04']))

    def test_real_datetime_columns_and_time_zones(self):
        s = pd.Series(pd.to_datetime(['2024-03-01', '2024-03-02']))
        parsed = D.parse_series(s)
        assert parsed is not None
        np.testing.assert_allclose(parsed, [19783, 19784])
        tz = pd.Series(pd.to_datetime(['2024-03-01 12:00']).tz_localize('Europe/Lisbon'))
        parsed_tz = D.parse_series(tz)
        assert parsed_tz is not None
        np.testing.assert_allclose(parsed_tz, [19783.5])

    def test_things_that_are_not_dates(self):
        for values in (['1,5', '3,5'], ['May', 'June'], ['10-20', '10-21'], ['a1', 'b2'],
                       ['1.2.3', '4.5.6'], [1.5, 2.5], ['2024-03-01', 'oops']):
            with self.subTest(values=values):
                self.assertIsNone(self.parse(values))


class TestSaving(unittest.TestCase):
    def test_pviz_encoding_round_trip(self):
        ds = {'t': D.from_iso(['2024-03-01', '2024-03-02T06:00:00']), 'y': np.array([1.0, 2.0]),
              'c': np.array(['a', 'b'], dtype=object)}
        enc = encode_datasets(ds)
        self.assertEqual(enc['t']['dtype'], 'date')
        self.assertEqual(enc['t']['values'], ['2024-03-01T00:00:00', '2024-03-02T06:00:00'])
        back = decode_datasets(enc)
        self.assertTrue(D.is_date(back['t']))
        np.testing.assert_allclose(back['t'], ds['t'])
        self.assertFalse(D.is_date(back['y']))
        self.assertEqual(back['c'].dtype, object)


class TestScriptExport(unittest.TestCase):
    def _script(self, datasets):
        from core.script_gen import generate_plot_script
        settings = {"chart_type": "Line", "subplot_rows": 1, "subplot_cols": 1,
                    "title_text": "t", "fig_unit": "cm", "fig_width": 20.0, "fig_height": 15.0,
                    "dpi": 100, "subplot_x_formatter": {"0": "%Y-%m"}}
        series = [{"x_col": "t", "y_col": "y", "label": "s", "series_type": "Line",
                   "plot_num": 1, "y2": False}]
        meta = {"series": series, "z_col": "(none)", "err_col": "(none)"}
        return generate_plot_script(cast(Any, settings), cast(Any, meta), datasets, ['#1f77b4'], "t")

    def test_script_reads_date_columns_back_as_dates(self):
        script = self._script({'t': D.from_iso(['2024-03-01', '2024-03-02']), 'y': np.array([1.0, 2.0])})
        self.assertIn("df['t'] = pd.to_datetime(df['t'])", script)
        self.assertNotIn("df['y'] = pd.to_datetime", script)
        compile(script, '<script>', 'exec')

    def test_script_without_dates_is_unchanged(self):
        script = self._script({'t': np.array([1.0, 2.0]), 'y': np.array([1.0, 2.0])})
        self.assertNotIn("to_datetime", script)

    def test_date_format_becomes_a_date_formatter(self):
        script = self._script({'t': D.from_iso(['2024-03-01', '2024-03-02']), 'y': np.array([1.0, 2.0])})
        self.assertIn("_mdates.DateFormatter('%Y-%m')", script)
        self.assertIn("import matplotlib.dates as _mdates", script)


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:  # noqa: BLE001 - any import failure means "no usable Qt"
        return False
    return hasattr(QApplication, "instance")


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestDatesInTheApp(unittest.TestCase):
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
        self.w = self.PlotVizApp()
        self._app.processEvents()

    def _csv_dialog(self, text, **kw):
        from ui.dialogs import DataImportDialog
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        self.addCleanup(os.remove, path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return DataImportDialog(path)

    def test_import_detects_date_columns(self):
        d = self._csv_dialog("when,value\n2024-03-01,1\n2024-03-02,2\n")
        data = d.get_selected_data()
        self.assertTrue(D.is_date(data["when"]))
        np.testing.assert_allclose(data["when"], [19783, 19784])
        self.assertFalse(D.is_date(data["value"]))
        d._dates_combo.setCurrentIndex(1)                        # dates: off
        self.assertEqual(d.get_selected_data()["when"].dtype, object)

    def test_import_day_first(self):
        d = self._csv_dialog("when,v\n03/04/2024,1\n04/04/2024,2\n")
        month_first = list(d.get_selected_data()["when"])
        d._dayfirst_check.setChecked(True)
        self.assertNotEqual(list(d.get_selected_data()["when"]), month_first)

    def _plot_dates(self, w, fmt=None):
        w.datasets.clear()
        w.datasets["t"] = D.from_iso(pd.date_range("2024-01-01", periods=30).strftime("%Y-%m-%d"))
        w.datasets["y"] = np.arange(30.0)
        w.update_lists()
        if w.series_table.rowCount() == 0:
            w._add_series_row()
        w.series_table.cellWidget(0, 0).setCurrentText("t")
        w.series_table.cellWidget(0, 1).setCurrentText("y")
        if fmt:
            w.x_formatter.setCurrentText(fmt)
        from matplotlib.figure import Figure
        fig = Figure(figsize=(6, 4))
        axes_list, *_ = w._render_axes(fig)
        return axes_list[0], fig

    def test_a_date_x_makes_a_date_axis(self):
        import matplotlib.dates as mdates
        ax, fig = self._plot_dates(self.w)
        fig.canvas.draw()
        self.assertIsInstance(ax.xaxis.get_major_locator(), mdates.DateLocator)
        labels = [t.get_text() for t in ax.get_xticklabels() if t.get_text()]
        self.assertTrue(any("2024" in s or "Jan" in s or "Feb" in s for s in labels), labels)

    def test_axes_tab_date_format_is_applied(self):
        ax, fig = self._plot_dates(self.w, "%d/%m/%Y")
        fig.canvas.draw()
        labels = [t.get_text() for t in ax.get_xticklabels() if t.get_text()]
        self.assertTrue(labels and all(len(s) == 10 and s[2] == "/" for s in labels), labels)

    def test_a_plain_numeric_x_stays_numeric(self):
        import matplotlib.dates as mdates
        w = self.w
        w.datasets.clear()
        w.datasets["t"], w.datasets["y"] = np.arange(10.0), np.arange(10.0)
        w.update_lists()
        if w.series_table.rowCount() == 0:
            w._add_series_row()
        w.series_table.cellWidget(0, 0).setCurrentText("t")
        w.series_table.cellWidget(0, 1).setCurrentText("y")
        from matplotlib.figure import Figure
        axes_list, *_ = w._render_axes(Figure())
        self.assertNotIsInstance(axes_list[0].xaxis.get_major_locator(), mdates.DateLocator)

    def test_a_saved_chart_with_dates_loads_with_dates_and_a_date_axis(self):
        from core.serialize import read_project_zip, write_project_zip
        from test_gui_smoke import _write_pviz
        w = self.w
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "base.pviz")
            _write_pviz(base)
            parts = read_project_zip(base)
            fp = os.path.join(d, "dates.pviz")
            ds = {"x": D.from_iso(pd.date_range("2024-01-01", periods=30).strftime("%Y-%m-%d")),
                  "y": np.arange(30.0), "z": np.arange(30.0)}
            write_project_zip(fp, parts["settings"], parts["series_meta"], encode_datasets(ds))
            w._load_project_inner(fp, silent=True)
            self.assertTrue(D.is_date(w.datasets["x"]))
            self.assertFalse(D.is_date(w.datasets["y"]))
            from matplotlib.figure import Figure
            import matplotlib.dates as mdates
            axes_list, *_ = w._render_axes(Figure())
            self.assertIsInstance(axes_list[0].xaxis.get_major_locator(), mdates.DateLocator)

    def test_transform_keeps_the_date_tag_and_crops_by_date(self):
        w = self.w
        self._plot_dates(w)
        w.tf_y_combo.setCurrentText("y")
        w.tf_x_combo.setCurrentText("t")
        w.tf_op_combo.setCurrentIndex(w.tf_op_combo.findData("crop_x"))
        widgets = w._tf_param_widgets[w._tf_op_index()]
        widgets["xmin"].setText("2024-01-10")
        widgets["xmax"].setText("2024-01-12")
        w.tf_out_name.setText("")
        w._apply_transform()
        self.assertEqual(list(w.datasets["y_crop"]), [9.0, 10.0, 11.0])
        self.assertTrue(D.is_date(w.datasets["t_crop"]))
        self.assertEqual(D.to_iso(w.datasets["t_crop"])[0], "2024-01-10")

    def test_fft_of_a_date_x_gives_plain_frequencies(self):
        w = self.w
        self._plot_dates(w)
        w.tf_y_combo.setCurrentText("y")
        w.tf_x_combo.setCurrentText("t")
        w.tf_op_combo.setCurrentIndex(w.tf_op_combo.findData("fft_spectrum"))
        w.tf_out_name.setText("")
        w._apply_transform()
        self.assertFalse(D.is_date(w.datasets["t_fft"]))

    def test_statistics_show_dates_as_dates(self):
        w = self.w
        self._plot_dates(w)
        tabs = w.data_inner_tabs
        tabs.setCurrentIndex([tabs.tabText(i) for i in range(tabs.count())].index("Statistics"))
        t = w.stats_table
        series = [t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]
        stats = [t.verticalHeaderItem(r).text() for r in range(t.rowCount())]
        self.assertEqual(t.item(stats.index("min"), series.index("t")).text(), "2024-01-01")
        self.assertEqual(t.item(stats.index("max"), series.index("t")).text(), "2024-01-30")
        self.assertEqual(t.item(stats.index("max"), series.index("y")).text(), "29")


if __name__ == "__main__":
    unittest.main()
