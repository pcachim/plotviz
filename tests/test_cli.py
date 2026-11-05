"""The command line: plotviz render draws saved charts to files without opening the program."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

ROOT = Path(__file__).resolve().parent.parent
_SRC = ROOT / "src" / "plotviz"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import _bootstrap  # noqa: F401,E402

BAR = ROOT / "data" / "plots" / "bar.pviz"
TWO_PANELS = ROOT / "data" / "plots" / "radar-new-2.pviz"


_MPL_CACHE = tempfile.mkdtemp(prefix="plotviz-mpl-")     # one font cache for all the runs, built once


def run(*args, home=None):
    """Run `plotviz render …` as a program, with a home folder of its own (it must not touch yours)."""
    env = dict(os.environ, HOME=str(home or tempfile.mkdtemp()), QT_QPA_PLATFORM="offscreen", MPLCONFIGDIR=_MPL_CACHE,
               XDG_CONFIG_HOME=str((home or Path(tempfile.mkdtemp())) / ".config"))
    return subprocess.run([sys.executable, str(_SRC / "main.py"), "render", *map(str, args)],
                          capture_output=True, text=True, env=env, timeout=120)


class TestParser(unittest.TestCase):
    def setUp(self):
        from cli import build_parser
        self.parse = build_parser().parse_args

    def test_the_defaults(self):
        a = self.parse(["a.pviz"])
        self.assertEqual((a.dpi, a.unit, a.format, a.output, a.reload), (300, "cm", None, None, False))

    def test_output_and_outdir_exclude_each_other(self):
        with self.assertRaises(SystemExit):
            self.parse(["a.pviz", "-o", "x.png", "--outdir", "d"])

    def test_format_comes_from_the_option_then_the_extension_then_png(self):
        from cli import _format_of
        self.assertEqual(_format_of(self.parse(["a.pviz", "-o", "x.PDF"])), "pdf")
        self.assertEqual(_format_of(self.parse(["a.pviz", "-o", "x.jpg"])), "jpeg")
        self.assertEqual(_format_of(self.parse(["a.pviz", "-o", "x.tif"])), "tiff")
        self.assertEqual(_format_of(self.parse(["a.pviz", "-o", "x.png", "-f", "svg"])), "svg")
        self.assertEqual(_format_of(self.parse(["a.pviz"])), "png")
        with self.assertRaises(ValueError):
            _format_of(self.parse(["a.pviz", "-o", "x.bmp"]))

    def test_the_file_is_named_after_the_chart(self):
        from cli import _output_path
        a = self.parse(["dir/chart.pviz", "--outdir", "figs", "-f", "jpeg"])
        self.assertEqual(_output_path("dir/chart.pviz", a, "jpeg"), str(Path("figs") / "chart.jpg"))
        a = self.parse(["dir/chart.pviz"])
        self.assertEqual(_output_path("dir/chart.pviz", a, "png"), str(Path("dir/chart.pviz").resolve().parent / "chart.png"))


class TestProgram(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_a_chart_becomes_a_png_of_the_requested_size(self):
        out = self.tmp / "bar.png"
        r = run(BAR, "-o", out, "--dpi", "100", "--width", "10", "--height", "5", "--unit", "cm", home=self.tmp / "h")
        self.assertEqual(r.returncode, 0, r.stderr)
        from PIL import Image
        with Image.open(out) as image:
            self.assertEqual(image.format, "PNG")
            width, height = image.size                               # 10 cm x 5 cm at 100 dpi (394 x 197, give or take a pixel)
            self.assertLessEqual(abs(width - 394), 1)
            self.assertLessEqual(abs(height - 197), 1)
        self.assertIn("->", r.stdout)

    def test_the_other_formats(self):
        for ext, magic in (("pdf", b"%PDF"), ("svg", b"<?xml"), ("eps", b"%!PS")):
            out = self.tmp / f"bar.{ext}"
            r = run(BAR, "-o", out, home=self.tmp / "h")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.read_bytes().startswith(magic), ext)

    def test_several_charts_go_to_a_folder_and_quiet_prints_nothing(self):
        r = run(BAR, TWO_PANELS, "--outdir", self.tmp / "figs", "-f", "png", "--dpi", "50", "-q", home=self.tmp / "h")
        self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)
        self.assertEqual(sorted(p.name for p in (self.tmp / "figs").iterdir()), ["bar.png", "radar-new-2.png"])

    def test_each_subplot_also_gets_its_own_file(self):
        r = run(TWO_PANELS, "-o", self.tmp / "p.png", "--each-subplot", "--dpi", "50", home=self.tmp / "h")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.tmp / "p_1.png").exists() and (self.tmp / "p_2.png").exists())

    def test_it_does_not_write_to_the_settings_of_the_program(self):
        home = self.tmp / "home"
        r = run(BAR, "-o", self.tmp / "b.png", "--dpi", "50", home=home)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([p for p in home.rglob("settings.json")], [])

    def test_a_missing_or_wrong_file_is_an_error_and_the_others_are_still_drawn(self):
        notchart = self.tmp / "text.pviz"
        notchart.write_text("this is not a zip")
        r = run(self.tmp / "none.pviz", notchart, BAR, "--outdir", self.tmp / "o", "--dpi", "50", home=self.tmp / "h")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no such file", r.stderr)
        self.assertIn("not a plotviz chart", r.stderr)
        self.assertTrue((self.tmp / "o" / "bar.png").exists())

    def test_wrong_use_exits_with_2(self):
        self.assertEqual(run(BAR, TWO_PANELS, "-o", self.tmp / "x.png").returncode, 2)
        self.assertEqual(run(BAR, "-o", self.tmp / "x.bmp").returncode, 2)
        self.assertEqual(run(BAR, "--template", self.tmp / "nope.pvizt").returncode, 2)
        self.assertEqual(run(BAR, "--dpi", "0").returncode, 2)


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
        return hasattr(QApplication, "instance") and not getattr(QApplication, "_is_stub", False)
    except Exception:  # noqa: BLE001
        return False


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestReload(unittest.TestCase):
    """--reload draws the chart with the data files as they are now."""

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

    def make_chart(self, tmp):
        from unittest import mock
        from PyQt6.QtWidgets import QDialog
        csv = tmp / "d.csv"
        csv.write_text("t,v\n1,1\n2,2\n3,3\n")
        w = self.PlotVizApp()
        try:
            with mock.patch("ui.data_io.QFileDialog.getOpenFileNames", return_value=([str(csv)], "")), \
                    mock.patch("ui.dialogs.DataImportDialog.exec", return_value=QDialog.DialogCode.Accepted):
                w._load_data_files("Load", str(tmp), remember_dir=False)
            w.series_table.cellWidget(0, 0).setCurrentText("t")
            w.series_table.cellWidget(0, 1).setCurrentText("v")
            chart = tmp / "c.pviz"
            w._current_filepath = str(chart)
            w._save_project()
        finally:
            w._is_dirty = False
            w.close()
        return chart, csv

    def test_reload_draws_the_new_data_and_without_it_the_saved_data(self):
        tmp = Path(tempfile.mkdtemp())
        chart, csv = self.make_chart(tmp)
        before = tmp / "before.png"
        self.assertEqual(run(chart, "-o", before, "--dpi", "60", home=tmp / "h").returncode, 0)
        csv.write_text("t,v\n1,9\n2,1\n3,9\n")
        plain, fresh = tmp / "plain.png", tmp / "fresh.png"
        self.assertEqual(run(chart, "-o", plain, "--dpi", "60", home=tmp / "h").returncode, 0)
        self.assertEqual(run(chart, "-o", fresh, "--dpi", "60", "--reload", home=tmp / "h").returncode, 0)
        self.assertEqual(before.read_bytes(), plain.read_bytes())          # still the saved values
        self.assertNotEqual(before.read_bytes(), fresh.read_bytes())       # the new ones

    def test_a_data_file_that_is_gone_stops_the_chart_instead_of_drawing_old_data(self):
        tmp = Path(tempfile.mkdtemp())
        chart, csv = self.make_chart(tmp)
        csv.unlink()
        out = tmp / "x.png"
        r = run(chart, "-o", out, "--reload", home=tmp / "h")
        self.assertEqual(r.returncode, 1)
        self.assertIn("could not be read again", r.stderr)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
