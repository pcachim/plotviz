"""Export: each subplot as its own file, next to the whole figure.

Runs only where a real PyQt6 is installed; skipped otherwise.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_script_layout as tsl  # noqa: E402


def _png_size(path):
    import matplotlib.image as mpimg
    h, w = mpimg.imread(path).shape[:2]
    return w, h


@unittest.skipUnless(tsl.HAVE_QT, "real PyQt6 not available")
class TestExportSubplots(unittest.TestCase):
    setUpClass = classmethod(tsl.TestScriptLayoutMatchesExport.setUpClass.__func__)
    tearDownClass = classmethod(tsl.TestScriptLayoutMatchesExport.tearDownClass.__func__)
    _window = tsl.TestScriptLayoutMatchesExport._window

    def _save(self, w, fmt, dpi=100):
        wi, hi = w._fig_size_in_inches()
        d = tempfile.mkdtemp()
        paths = w._subplot_file_names(os.path.join(d, "c"), fmt, w._n_export_subplots())
        with w._export_rc():
            fig = w._build_export_figure(wi, hi, dpi)
            w._save_subplot_files(fig, paths, wi, hi, dpi, fmt)
        return paths, (wi, hi)

    def test_each_subplot_keeps_its_proportions_and_fills_the_long_side(self):
        w = self._window(types=["Line", "Scatter", "Bar"])
        w._subplot_mosaic = [["A", "B"], ["C", "C"]]          # C is twice as wide as A
        paths, (wi, hi) = self._save(w, "png")
        sizes = [_png_size(p) for p in paths]
        self.assertEqual(len(sizes), 3)
        for (pw, ph) in sizes:
            self.assertAlmostEqual(max(pw, ph), max(wi, hi) * 100, delta=3)
        ratio = [pw / ph for pw, ph in sizes]
        self.assertGreater(ratio[2], ratio[0] * 1.4)            # the wide panel stays wide

    def test_vector_files_keep_the_natural_size(self):
        w = self._window(types=["Line", "Scatter", "Bar", "Line"])
        paths, _ = self._save(w, "svg")
        for p in paths:
            self.assertGreater(os.path.getsize(p), 500)
            with open(p, encoding="utf-8") as fh:
                head = fh.read(600)
            self.assertIn("<svg", head)

    def test_a_colorbar_belongs_to_its_subplot(self):
        w = self._window(chart="Heatmap", mode="Heatmap & Contour")
        wi, hi = w._fig_size_in_inches()
        with w._export_rc():
            fig = w._build_export_figure(wi, hi, 100)
            (group, box), = w._subplot_export_boxes(fig)
        self.assertEqual(len(group), 2)                         # the axes and its colorbar
        self.assertGreater(box.width, 0)

    def test_the_figure_title_and_other_subplots_are_left_out_of_a_subplot_file(self):
        from unittest import mock
        w = self._window(types=["Line", "Bar", "Line", "Bar"])
        w.title_input.setText("Shared title")
        w.title_check.setChecked(True)
        wi, hi = w._fig_size_in_inches()
        seen = []
        with w._export_rc():
            fig = w._build_export_figure(wi, hi, 100)
            self.assertTrue(fig._suptitle.get_visible())

            def fake_savefig(path, **kw):
                seen.append((fig._suptitle.get_visible(),
                             sum(a.get_visible() for a in fig.axes)))
            with mock.patch.object(fig, "savefig", side_effect=fake_savefig):
                w._save_subplot_files(fig, ["a.png", "b.png", "c.png", "d.png"],
                                      wi, hi, 100, "png")
            self.assertTrue(fig._suptitle.get_visible())               # restored
            self.assertTrue(all(a.get_visible() for a in fig.axes))
        self.assertEqual(len(seen), 4)
        for title_visible, axes_visible in seen:
            self.assertFalse(title_visible)
            self.assertEqual(axes_visible, 1)                          # only its own subplot

    def test_the_dialog_offers_it_only_with_several_subplots(self):
        from unittest import mock
        from PyQt6.QtWidgets import QCheckBox, QDialog
        seen = {}

        def fake_exec(dlg):
            box = next(c for c in dlg.findChildren(QCheckBox) if "subplot" in c.text())
            seen["enabled"] = box.isEnabled()
            return QDialog.DialogCode.Rejected
        w = self._window()
        with mock.patch.object(QDialog, "exec", new=fake_exec):
            w._ask_export_options(8.0, 6.0, "png")
        self.assertFalse(seen["enabled"])
        w = self._window(types=["Line", "Bar"])
        with mock.patch.object(QDialog, "exec", new=fake_exec):
            w._ask_export_options(8.0, 6.0, "png")
        self.assertTrue(seen["enabled"])

    def test_a_mosaic_counts_its_cells_not_the_grid(self):
        w = self._window(types=["Line", "Scatter", "Bar"])
        w._subplot_mosaic = [["A", "B"], ["C", "C"]]
        self.assertEqual(w._n_export_subplots(), 3)
        self.assertEqual(w._subplot_file_names("/x/c", "png", 3),
                         ["/x/c_1.png", "/x/c_2.png", "/x/c_3.png"])


if __name__ == "__main__":
    unittest.main()
