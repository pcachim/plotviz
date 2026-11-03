"""Where things live in the tabs: per-subplot controls and the shared subplot selector.

Runs only where a real PyQt6 is installed; skipped otherwise.
"""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "src", "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:  # noqa: BLE001 - any import failure means "no usable Qt"
        return False
    return hasattr(QApplication, "instance")


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestTabLayout(unittest.TestCase):
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

    def _inner(self):
        t = self.w.plots_inner_tabs
        return [t.tabText(i) for i in range(t.count())]

    def _in_tab(self, widget, tab_name):
        t = self.w.plots_inner_tabs
        page = t.widget(self._inner().index(tab_name))
        return widget is page or page.isAncestorOf(widget)

    def test_inner_tab_order_follows_the_workflow(self):
        self.assertEqual(self._inner(), ["Plot", "Curves", "Axes", "Canvas && Grid", "Legend && Notes"])

    def test_canvas_borders_and_grid_have_their_own_tab(self):
        w = self.w
        for widget in (w.border_top, w.border_left, w.grid_check, w.grid_linestyle,
                       w.minor_grid_check):
            self.assertTrue(self._in_tab(widget, "Canvas && Grid"), widget)

    def test_the_3d_viewpoint_sits_with_the_z_axis(self):
        w = self.w
        for widget in (w.view3d_elev_spin, w.view3d_azim_spin):
            self.assertTrue(self._in_tab(widget, "Axes"), widget)

    def test_clicking_the_plot_area_goes_to_the_canvas_and_grid_tab(self):
        # The canvas jumps to the tab by index: it must still be the right tab.
        from ui.canvas import CanvasPlotter
        self.assertEqual(self._inner()[CanvasPlotter._INNER_AXES], "Axes")
        self.assertEqual(self._inner()[CanvasPlotter._INNER_LAYOUT], "Canvas && Grid")
        self.assertEqual(self._inner()[CanvasPlotter._INNER_SERIES], "Curves")
        self.assertEqual(self._inner()[CanvasPlotter._INNER_ANNOTATIONS], "Legend && Notes")

    def test_the_subplot_selector_is_always_shown(self):
        w = self.w
        self.assertFalse(w._global_sp_container.isHidden())
        self.assertFalse(w.global_sp_active.isEnabled())      # one subplot: nothing to pick
        w.sp_cols.setValue(2)                                  # a 1 x 2 grid
        self.assertFalse(w._global_sp_container.isHidden())
        self.assertTrue(w.global_sp_active.isEnabled())
        self.assertEqual(w.global_sp_active.count(), 2)


    def test_the_plots_tabs_fit_the_panel_without_scroll_arrows(self):
        w = self.w
        w.show()
        self._app.processEvents()
        w.tabs.setCurrentIndex([w.tabs.tabText(i) for i in range(w.tabs.count())].index("Plots"))
        self._app.processEvents()
        bar = w.plots_inner_tabs.tabBar()
        needed = sum(bar.tabRect(i).width() for i in range(bar.count()))
        self.assertLessEqual(needed, w.plots_inner_tabs.width())

    def test_the_subplot_title_is_in_the_axes_tab_and_only_with_several_subplots(self):
        w = self.w
        for widget in (w.sp_title_input, w.title_show_check, w.sp_title_font, w.sp_title_size,
                       w.sp_title_pad, w.sp_title_rotation, w.sp_title_ha):
            self.assertTrue(self._in_tab(widget, "Axes"), widget)
            self.assertFalse(self._in_tab(widget, "Legend && Notes"), widget)
        self.assertTrue(w._axes_title_section.isHidden())             # one subplot: figure title only
        w.sp_cols.setValue(2)
        self.assertFalse(w._axes_title_section.isHidden())
        w.sp_active.setCurrentIndex(1)                                # a title per subplot
        w.sp_title_input.setText("second")
        w.sp_title_input.editingFinished.emit()
        w.sp_active.setCurrentIndex(0)
        self.assertEqual(w.sp_title_input.text(), "")
        w.sp_active.setCurrentIndex(1)
        self.assertEqual(w.sp_title_input.text(), "second")
        self.assertEqual(w.sp_titles[1], "second")

    def test_a_new_subplot_takes_the_look_of_the_active_one_but_not_its_content(self):
        w = self.w
        w.subplot_xtick_sizes[0] = 14
        w.subplot_legend_frameon[0] = False
        w.subplot_title_font[0] = "serif"
        w.subplot_xaxis_pos[0] = "top"
        w.subplot_xlabel_rotation[0] = 30
        w.subplot_xlabels[0] = "time"                  # content: must not be copied
        w.subplot_xlims[0] = (0.0, 5.0)
        w.subplot_yscales[0] = "log"
        w.subplot_xtick_step[0] = 2.0
        w.sp_titles[0] = "first"
        w.sp_cols.setValue(2)
        self.assertEqual(w.subplot_xtick_sizes[1], 14)
        self.assertFalse(w.subplot_legend_frameon[1])
        self.assertEqual(w.subplot_title_font[1], "serif")
        self.assertEqual(w.subplot_xaxis_pos[1], "top")
        self.assertEqual(w.subplot_xlabel_rotation[1], 30)
        self.assertEqual(w.subplot_xlabels[1], "")
        self.assertIsNone(w.subplot_xlims[1])
        self.assertEqual(w.subplot_yscales[1], "linear")
        self.assertEqual(w.subplot_xtick_step[1], 0.0)
        self.assertEqual(w.sp_titles[1], "")

    def _in_outer(self, widget, name):
        t = self.w.tabs
        names = [t.tabText(i) for i in range(t.count())]
        page = t.widget(names.index(name))
        return page.isAncestorOf(widget)

    def test_whole_figure_settings_share_the_layout_and_style_tab(self):
        w = self.w
        self.assertEqual([w.tabs.tabText(i) for i in range(w.tabs.count())],
                         ["Data", "Layout && Style", "Plots"])
        for widget in (w.fig_width, w.fig_left, w.title_input, w.sp_hspace,
                       w._subplot_grid_panel, w._cs_combo, w.palette_combo, w.chart_bg_color_swatch):
            self.assertTrue(self._in_outer(widget, "Layout && Style"), widget)

    def test_the_data_tab_has_datasets_and_generators(self):
        w = self.w
        self.assertTrue(self._in_outer(w.dataset_list, "Data"))
        self.assertTrue(self._in_outer(w.gen_x_min, "Data"))      # the generators
        self.assertFalse(self._in_outer(w.palette_combo, "Data"))

    def _data_page(self, name):
        t = self.w.data_inner_tabs
        return [t.tabText(i) for i in range(t.count())].index(name)

    def test_baseline_options_appear_with_the_method_and_use_the_value(self):
        w = self.w
        w.datasets.clear()
        w.datasets["t"] = [float(i) for i in range(10)]
        w.datasets["v"] = [5.0, 5, 5, 5, 9, 5, 5, 5, 5, 5]
        w.update_lists()
        w.data_inner_tabs.setCurrentIndex(self._data_page("Transform"))
        w.tf_y_combo.setCurrentText("v")
        w.tf_x_combo.setCurrentText("t")
        w.tf_op_combo.setCurrentIndex(w.tf_op_combo.findData("subtract_baseline"))
        p = w._tf_param_widgets[w._tf_op_index()]
        self.assertTrue(p["value"].isHidden() and p["x_from"].isHidden() and p["x_to"].isHidden())
        p["method"].setCurrentText("value")
        self.assertFalse(p["value"].isHidden())
        self.assertTrue(p["x_from"].isHidden())
        p["method"].setCurrentText("median of range")
        self.assertTrue(p["value"].isHidden())
        self.assertFalse(p["x_from"].isHidden() or p["x_to"].isHidden())
        p["method"].setCurrentText("value")
        p["value"].setValue(4.5)
        w.tf_out_name.setText("")
        w._apply_transform()
        self.assertEqual(list(w.datasets["v_bl"])[:2], [0.5, 0.5])
        p["method"].setCurrentText("mean of range")                    # a stretch, typed as numbers
        p["x_from"].setText("0")
        p["x_to"].setText("3")
        w._apply_transform()
        self.assertEqual(list(w.datasets["v_bl_1"])[:5], [0.0, 0.0, 0.0, 0.0, 4.0])

    def test_the_data_tab_has_a_transform_page_that_creates_series(self):
        w = self.w
        t = w.data_inner_tabs
        self.assertEqual([t.tabText(i) for i in range(t.count())],
                         ["Datasets", "Generate", "Statistics", "Transform"])
        w.datasets.clear()
        w.datasets["t"] = list(range(10))
        w.datasets["v"] = [float(i * i) for i in range(10)]
        w.update_lists()
        w.tf_y_combo.setCurrentText("v")
        w.tf_x_combo.setCurrentText("t")
        self.assertLess(w.tf_x_combo.y(), w.tf_y_combo.y())            # x is asked before y
        w.tf_op_combo.setCurrentIndex(w.tf_op_combo.findData("every_n"))
        w._tf_param_widgets[w._tf_op_index()]["step"].setValue(3)
        w._apply_transform()
        self.assertEqual(list(w.datasets["v_every3"]), [0.0, 9.0, 36.0, 81.0])
        self.assertEqual(list(w.datasets["t_every3"]), [0, 3, 6, 9])
        self.assertEqual(len(w.datasets["v"]), 10)           # original untouched
        self.assertEqual(w.tf_op_combo.itemText(0), "Smoothing")     # group headers, not selectable
        self.assertIsNone(w.tf_op_combo.itemData(0))
        w.datasets["p"] = [0.0, 3.0, 0.0, 1.0, 0.0, 5.0, 0.0]
        w.update_lists()
        w.tf_x_combo.setCurrentIndex(0)                              # no x: peaks makes its own
        w.tf_y_combo.setCurrentText("p")
        w.tf_op_combo.setCurrentIndex(w.tf_op_combo.findData("peaks"))
        w.tf_out_name.setText("")
        w._apply_transform()
        self.assertEqual(list(w.datasets["p_x_peaks"]), [1.0, 3.0, 5.0])
        self.assertEqual(list(w.datasets["p_peaks"]), [3.0, 1.0, 5.0])
        # Statistics page: summary of the selected series, or all of them
        w.data_inner_tabs.setCurrentIndex(self._data_page("Statistics"))
        t = w.stats_table                                    # series in columns, statistics in rows
        self.assertEqual(t.columnCount(), len(w.datasets))
        series = [t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]
        self.assertEqual(series, sorted(w.datasets))
        stats = [t.verticalHeaderItem(r).text() for r in range(t.rowCount())]
        self.assertEqual(t.item(stats.index("max"), series.index("v")).text(), "81")
        self.assertEqual(w.corr_table.rowCount(), len(w.datasets))
        w.data_inner_tabs.setCurrentIndex(self._data_page("Transform"))
        # "series" parameter: align onto another series' x, which is reused, not duplicated
        w.datasets["grid"] = [0.0, 4.5, 9.0]
        w.update_lists()
        w.tf_y_combo.setCurrentText("v")
        w.tf_x_combo.setCurrentText("t")
        w.tf_op_combo.setCurrentIndex(w.tf_op_combo.findData("align_to_x"))
        w._tf_param_widgets[w._tf_op_index()]["target_x"].setCurrentText("grid")
        w.tf_out_name.setText("")
        w._apply_transform()
        self.assertEqual(list(w.datasets["v_al"]), [0.0, 20.5, 81.0])
        self.assertNotIn("t_al", w.datasets)
        self.assertIn("v_every3", [w.y_list.item(i).text() for i in range(w.y_list.count())])


    # ── top bar: New / Open / Save ... Undo / Redo ───────────────────────────
    def test_new_series_never_repeat_a_label_after_a_row_is_deleted(self):
        w = self.w
        w.datasets.clear()
        w.datasets["x"] = [0.0, 1.0]
        w.datasets["y"] = [0.0, 1.0]
        w.update_lists()
        w.series_table.setRowCount(0)
        for _ in range(5):
            w._add_series_row()
        label = lambda r: w.series_table.item(r, 2).text()                    # noqa: E731
        self.assertEqual([label(r) for r in range(5)], [f"Series {n}" for n in range(1, 6)])
        w.series_table.removeRow(1)                                           # delete "Series 2"
        w._add_series_row()
        w._add_series_row()
        labels = [label(r) for r in range(w.series_table.rowCount())]
        self.assertEqual(len(labels), len(set(labels)), labels)

    def test_the_top_bar_has_open_and_save(self):
        w = self.w
        for btn in (w._btn_open, w._btn_save, w._btn_export, w._btn_undo, w._btn_redo):
            self.assertFalse(btn.isHidden())
        self.assertIn("Ctrl+O", w._btn_open.toolTip())
        self.assertIn("Ctrl+S", w._btn_save.toolTip())

    def test_save_is_live_only_when_there_is_something_to_save(self):
        w = self.w
        w._current_filepath = None
        w._is_dirty = False
        w._update_window_title()
        self.assertTrue(w._btn_save.isEnabled())          # no file yet: Save asks where
        w._current_filepath = "/tmp/some/chart.pviz"
        w._is_dirty = False
        w._update_window_title()
        self.assertFalse(w._btn_save.isEnabled())         # saved and unchanged
        w._is_dirty = True
        self.assertTrue(w._btn_save.isEnabled())          # an edit makes it live again
        w._is_dirty = False
        self.assertFalse(w._btn_save.isEnabled())

    def test_the_buttons_call_open_and_save(self):
        from unittest import mock
        w = self.w
        with mock.patch.object(type(w), "_load_project") as load, \
                mock.patch.object(type(w), "_save_project") as save, \
                mock.patch.object(type(w), "export_chart") as export:
            w._btn_open.click()
            w._btn_save.click()
            w._btn_export.click()
        load.assert_called_once()
        save.assert_called_once()
        export.assert_called_once()


    # ── export dialog: Save… or Copy to clipboard ────────────────────────────
    def _press(self, text, fmt=None):
        """Run the export-options dialog, 'clicking' the button called *text*."""
        from unittest import mock
        from PyQt6.QtWidgets import QDialog, QPushButton, QComboBox
        seen = {}

        def fake_exec(dlg):
            if fmt:
                dlg.findChild(QComboBox).setCurrentText(fmt)
            btn = next(b for b in dlg.findChildren(QPushButton) if b.text() == text)
            copy_btn = next(b for b in dlg.findChildren(QPushButton)
                            if b.text() == "Copy to clipboard")
            seen["copy_enabled"] = copy_btn.isEnabled()
            seen["tooltip"] = copy_btn.toolTip()
            if btn.isEnabled():
                btn.click()
                return QDialog.DialogCode.Accepted
            return QDialog.DialogCode.Rejected
        with mock.patch.object(QDialog, "exec", new=fake_exec):
            return self.w._ask_export_options(8.0, 6.0, "png"), seen

    def test_the_export_dialog_can_copy_instead_of_save(self):
        (fmt, dpi, action, _each), _ = self._press("Copy to clipboard")
        self.assertEqual((fmt, action), ("png", "copy"))
        (fmt, dpi, action, _each), seen = self._press("Save…")
        self.assertEqual(action, "save")
        self.assertIn("PNG", seen["tooltip"])                  # says what it copies
        self.assertIn(f"{dpi} dpi", seen["tooltip"])           # names the resolution
        self.assertIn(f"{round(8 * dpi)} × {round(6 * dpi)} px", seen["tooltip"])

    def test_copy_is_not_offered_for_vector_formats(self):
        result, seen = self._press("Copy to clipboard", fmt="SVG")
        self.assertFalse(seen["copy_enabled"])
        self.assertIsNone(result)                               # nothing could be clicked

    def test_copying_from_the_export_dialog_fills_the_clipboard(self):
        from unittest import mock
        from PyQt6.QtWidgets import QApplication, QFileDialog
        QApplication.clipboard().clear()
        with mock.patch.object(type(self.w), "_ask_export_options",
                               return_value=("png", 96, "copy", False)), \
                mock.patch.object(QFileDialog, "getSaveFileName") as save_dialog:
            self.w.export_chart()
        save_dialog.assert_not_called()                         # no file was asked for
        clip = QApplication.clipboard().image()
        self.assertFalse(clip.isNull())
        wi, hi = self.w._fig_size_in_inches()
        self.assertAlmostEqual(clip.width(), wi * 96, delta=1)
        self.assertAlmostEqual(clip.height(), hi * 96, delta=1)


    # ── export dialog: estimated file size ───────────────────────────────────
    def test_the_size_estimate_matches_what_export_writes(self):
        w = self.w
        for fmt in ("png", "jpeg"):
            real = len(w._render_export_bytes(fmt, 150))
            self.assertAlmostEqual(w._estimate_export_bytes(fmt, 150), real, delta=real * 0.05, msg=fmt)
        wi, hi = w._fig_size_in_inches()
        real = len(w._render_export_bytes("tiff", 100))
        self.assertAlmostEqual(w._estimate_export_bytes("tiff", 100), real, delta=real * 0.01)
        svg = w._estimate_export_bytes("svg", 96)
        self.assertEqual(svg, w._estimate_export_bytes("svg", 600))     # dpi does not matter
        self.assertGreater(svg, 0)

    def test_the_estimate_grows_with_the_resolution(self):
        w = self.w
        sizes = [w._estimate_export_bytes("png", d) for d in (96, 300, 1200)]
        self.assertEqual(sizes, sorted(sizes))
        self.assertGreater(sizes[2], sizes[1] * 4)          # 1200 dpi is scaled, not capped

    def test_megabytes_are_shown_readably(self):
        f = self.PlotVizApp._format_megabytes
        self.assertEqual(f(3_000), "<0.01 MB")
        self.assertEqual(f(69_000), "0.07 MB")
        self.assertEqual(f(4_181_760), "4.2 MB")

    def test_the_dialog_shows_the_estimated_size_beside_the_pixels(self):
        from unittest import mock
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QDialog, QLabel
        seen = {}

        def fake_exec(dlg):
            label = next(lbl for lbl in dlg.findChildren(QLabel) if " px" in lbl.text())
            seen["before"] = label.text()
            QTest.qWait(450)  # ty: ignore[missing-argument, invalid-argument-type]                                  # past the 200 ms debounce
            seen["after"] = label.text()
            return QDialog.DialogCode.Rejected
        with mock.patch.object(QDialog, "exec", new=fake_exec):
            self.w._ask_export_options(8.0, 6.0, "png")
        self.assertIn("… MB", seen["before"])                 # measuring
        self.assertRegex(seen["after"], r"\d+ × \d+ px  ·  ≈ (<0\.01|\d+\.?\d*) MB")


if __name__ == "__main__":
    unittest.main()
