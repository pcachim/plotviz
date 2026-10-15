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
        self.assertEqual(self._inner(), ["Plot", "Curves", "Axes", "Annotations"])

    def test_canvas_borders_and_grid_live_with_the_axes(self):
        w = self.w
        for widget in (w.border_top, w.border_left, w.grid_check, w.grid_linestyle,
                       w.minor_grid_check, w.view3d_elev_spin):
            self.assertTrue(self._in_tab(widget, "Axes"), widget)

    def test_clicking_the_plot_area_goes_to_the_axes_tab(self):
        # The canvas jumps to the tab by index: it must still be the Axes tab.
        from ui.canvas import CanvasPlotter
        self.assertEqual(self._inner()[CanvasPlotter._INNER_AXES], "Axes")
        self.assertEqual(self._inner()[CanvasPlotter._INNER_LAYOUT], "Axes")
        self.assertEqual(self._inner()[CanvasPlotter._INNER_SERIES], "Curves")
        self.assertEqual(self._inner()[CanvasPlotter._INNER_ANNOTATIONS], "Annotations")

    def test_the_subplot_selector_is_always_shown(self):
        w = self.w
        self.assertFalse(w._global_sp_container.isHidden())
        self.assertFalse(w.global_sp_active.isEnabled())      # one subplot: nothing to pick
        w.sp_cols.setValue(2)                                  # a 1 x 2 grid
        self.assertFalse(w._global_sp_container.isHidden())
        self.assertTrue(w.global_sp_active.isEnabled())
        self.assertEqual(w.global_sp_active.count(), 2)


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


    # ── top bar: New / Open / Save ... Undo / Redo ───────────────────────────
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


if __name__ == "__main__":
    unittest.main()
