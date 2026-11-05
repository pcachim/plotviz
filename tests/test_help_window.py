"""The in-app documentation window (docs/ rendered in a QTextBrowser).

The pure checks run anywhere; the window tests need a real PyQt6 and are skipped otherwise.
"""
import os
import re
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_ROOT = Path(__file__).resolve().parent.parent
_SRC = str(_ROOT / "src" / "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

DOCS = _ROOT / "docs"


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:  # noqa: BLE001 - any import failure means "no usable Qt"
        return False
    return hasattr(QApplication, "instance")


def _headings(page):
    """The anchors mkdocs makes for the headings of a page."""
    from ui.help_window import slugify
    text = (DOCS / page).read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return {slugify(m.group(1)) for m in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, flags=re.M)}


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestDocsContent(unittest.TestCase):
    def test_the_index_is_the_navigation_of_mkdocs(self):
        from ui.help_window import NAV
        in_index = [page for _, pages in NAV for _, page in pages]
        config = (_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        nav = config[config.index("\nnav:"):config.index("\nextra:")]
        in_mkdocs = re.findall(r":\s*(\S+\.md)\s*$", nav, flags=re.M)
        self.assertEqual(in_index, in_mkdocs)

    def test_every_page_exists_and_every_page_is_in_the_index(self):
        from ui.help_window import NAV
        in_index = {page for _, pages in NAV for _, page in pages}
        on_disk = {p.name for p in DOCS.glob("*.md")} - {"README.md"}
        self.assertEqual(in_index, on_disk)

    def test_every_link_between_pages_leads_somewhere(self):
        bad = []
        for page in sorted(p.name for p in DOCS.glob("*.md")):
            for target in re.findall(r"\]\(([^)\s]+\.md(?:#[^)\s]*)?)\)", (DOCS / page).read_text(encoding="utf-8")):
                name, _, anchor = target.partition("#")
                if not (DOCS / name).is_file() or (anchor and anchor not in _headings(name)):
                    bad.append(f"{page} -> {target}")
        self.assertEqual(bad, [])


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestChartFigures(unittest.TestCase):
    """Each chart type has a section in chart-types.md with its figure."""

    def _types(self):
        from ui.tab_builders import PLOT_MODE_GROUPS
        return [t for types in PLOT_MODE_GROUPS.values() for t in types]

    def test_every_image_in_the_docs_exists(self):
        missing = []
        for md in sorted(DOCS.glob("*.md")):
            for target in re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", md.read_text(encoding="utf-8")):
                if not target.startswith("http") and not (DOCS / target).is_file():
                    missing.append(f"{md.name}: {target}")
        self.assertEqual(missing, [])

    def test_every_chart_type_has_a_section_and_a_figure(self):
        text = (DOCS / "chart-types.md").read_text(encoding="utf-8")
        for chart_type in self._types():
            with self.subTest(chart_type=chart_type):
                self.assertRegex(text, rf"(?m)^### {re.escape(chart_type)}\n\n!\[[^\]]*\]\(images/charts/[\w-]+\.png\)")

    def test_the_image_script_covers_every_chart_type(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("make_doc_images", _ROOT / "util_files" / "make_doc_images.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(sorted(module.CHART_SAMPLES), sorted(self._types()))
        for sample in module.CHART_SAMPLES.values():
            self.assertTrue((_ROOT / "data" / "plots" / sample).is_file(), sample)
        for chart_type in self._types():
            self.assertTrue((DOCS / "images" / "charts" / f"{module.slug(chart_type)}.png").is_file(), chart_type)

    def test_the_count_in_the_text_is_the_number_of_types(self):
        n = len(self._types())
        for name in ("chart-types.md", "index.md"):
            self.assertIn(f"{n} chart types", (DOCS / name).read_text(encoding="utf-8"), name)


class TestTransformFigures(unittest.TestCase):
    """The figures of the Transform page: the script, the files and the page agree."""

    def test_every_figure_of_the_script_is_in_the_page(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("make_doc_transforms", _ROOT / "util_files" / "make_doc_transforms.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        text = (DOCS / "transform.md").read_text(encoding="utf-8")
        for name in module.GROUPS:
            with self.subTest(figure=name):
                self.assertTrue((DOCS / "images" / "transform" / f"{name}.png").is_file())
                self.assertIn(f"(images/transform/{name}.png)", text)

    def test_the_script_runs_with_the_parameters_of_the_current_operations(self):
        # Rendering the figures calls apply_operation with every operation they show, so a
        # renamed operation or parameter makes this fail (into a temporary folder).
        import importlib.util
        import tempfile
        spec = importlib.util.spec_from_file_location("make_doc_transforms", _ROOT / "util_files" / "make_doc_transforms.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            module.OUT = Path(folder)
            self.assertEqual(module.main([]), 0)
            self.assertEqual(sorted(p.stem for p in Path(folder).glob("*.png")), sorted(module.GROUPS))


class TestInterfaceFigures(unittest.TestCase):
    """The numbered screenshots of the pages: every zone of a picture is explained, in order."""

    ZONES = DOCS / "images" / "ui" / "zones.json"

    @staticmethod
    def _norm(text):
        return re.sub(r"\s+", " ", text.strip().rstrip(":")).lower()

    def _explained(self, key):
        """The bold titles of the numbered list that follows the picture images/ui/<key>.png."""
        for md in DOCS.glob("*.md"):
            text = md.read_text(encoding="utf-8")
            marker = f"(images/ui/{key}.png)"
            if marker in text:
                rest = text.split(marker, 1)[1]
                titles = []
                for line in rest.split("\n")[1:]:
                    m = re.match(r"(\d+)\. \*\*(.+?)\*\* — ", line)
                    if m:
                        titles.append((int(m.group(1)), self._norm(m.group(2))))
                    elif titles and line.strip() == "":
                        break
                    elif titles:
                        break
                return titles
        return None

    def test_every_picture_is_in_the_guide_and_every_zone_is_explained(self):
        import json
        zones = json.loads(self.ZONES.read_text(encoding="utf-8"))
        for key, titles in zones.items():
            with self.subTest(page=key):
                self.assertTrue((DOCS / "images" / "ui" / f"{key}.png").is_file())
                explained = self._explained(key)
                self.assertIsNotNone(explained, f"images/ui/{key}.png is not used in the guide")
                if titles:
                    self.assertEqual([t for _, t in explained], [self._norm(t) for t in titles])
                    self.assertEqual([n for n, _ in explained], list(range(1, len(titles) + 1)))

    def test_the_overview_has_its_five_zones(self):
        self.assertTrue((DOCS / "images" / "ui" / "overview.png").is_file())
        self.assertEqual(len(self._explained("overview") or []), 5)

    def test_the_screenshot_script_knows_every_page(self):
        import importlib.util
        import json
        spec = importlib.util.spec_from_file_location("make_doc_screenshots", _ROOT / "util_files" / "make_doc_screenshots.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        zones = json.loads(self.ZONES.read_text(encoding="utf-8"))
        self.assertEqual(sorted(module.PAGES), sorted(zones))


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestMarkdownPreparation(unittest.TestCase):
    def test_slugify_matches_mkdocs(self):
        from ui.help_window import slugify
        self.assertEqual(slugify("Date and time columns"), "date-and-time-columns")
        self.assertEqual(slugify("Canvas (matplotlib toolbar)"), "canvas-matplotlib-toolbar")
        self.assertEqual(slugify("Z column and error column"), "z-column-and-error-column")

    def test_admonitions_become_quotes(self):
        from ui.help_window import prepare_markdown
        out = prepare_markdown('!!! note "Requirements"\n    Needs seaborn.\n\n    More.\n\nAfter.')
        self.assertEqual(out.split("\n"), ["> **Requirements**", "> Needs seaborn.", ">", "> More.", "", "After."])
        self.assertEqual(prepare_markdown("!!! note\n    Text").split("\n"), ["> **Note**", "> Text"])

    def test_icons_and_wrappers_go(self):
        from ui.help_window import prepare_markdown
        out = prepare_markdown('<div class="grid cards" markdown>\n\n- :material-rocket-launch: **[Start](a.md)**\n\n</div>')
        self.assertNotIn("material", out)
        self.assertNotIn("div", out)
        self.assertIn("- **[Start](a.md)**", out)


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestHelpWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        from ui.help_window import HelpWindow
        self.h = HelpWindow(folder=DOCS)

    def tearDown(self):
        self.h.close()

    def test_every_page_renders_with_its_title(self):
        from ui.help_window import NAV
        for _, pages in NAV:
            for _, page in pages:
                with self.subTest(page=page):
                    self.h.open_page(page)
                    self.assertGreater(len(self.h.browser.toPlainText()), 200, page)
                    self.assertNotIn(":material", self.h.browser.toPlainText())
                    self.assertNotIn("!!!", self.h.browser.toPlainText())

    def test_the_figures_are_shown_and_not_wider_than_the_page(self):
        self.h.open_page("chart-types.md")
        doc = self.h.browser.document()
        widths, block = [], doc.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fmt = it.fragment().charFormat()
                if fmt.isImageFormat():
                    widths.append(fmt.toImageFormat().width())
                it += 1
            block = block.next()
        self.assertEqual(len(widths), 26)
        self.assertLessEqual(max(widths), 760)

    def test_a_link_to_a_heading_scrolls_to_it(self):
        from PyQt6.QtCore import QUrl
        self.h.show()
        self.h.open_page("index.md")
        self.h._link_clicked(QUrl("datasets.md#date-and-time-columns"))
        self.assertEqual(self.h.selected_page(), "datasets.md")
        self.assertGreater(self.h.browser.verticalScrollBar().value(), 0)
        self.assertEqual(self.h.index.currentItem().text(0), "Datasets and Import")

    def test_back_and_forward(self):
        self.h.open_page("datasets.md")
        self.h.open_page("axes.md")
        self.assertTrue(self.h.back_btn.isEnabled())
        self.assertFalse(self.h.fwd_btn.isEnabled())
        self.h.back()
        self.assertEqual(self.h.selected_page(), "datasets.md")
        self.assertTrue(self.h.fwd_btn.isEnabled())
        self.h.forward()
        self.assertEqual(self.h.selected_page(), "axes.md")
        self.h.back()
        self.h.open_page("plot.md")                     # a new page drops what was ahead
        self.assertFalse(self.h.fwd_btn.isEnabled())

    def test_web_links_open_the_browser_not_a_page(self):
        from unittest import mock
        from PyQt6.QtCore import QUrl
        with mock.patch("ui.help_window.QDesktopServices.openUrl") as opened:
            self.h._link_clicked(QUrl("https://github.com/pcachim/plotviz"))
        opened.assert_called_once()
        self.assertEqual(self.h.selected_page(), "index.md")

    def test_search_keeps_only_the_pages_that_contain_the_text(self):
        self.h.search.setText("Savitzky")
        shown = {p for p, item in self.h._items.items() if not item.isHidden()}
        self.assertIn("transform.md", shown)
        self.assertNotIn("palettes.md", shown)
        self.assertIn("page(s) contain", self.h.status.text())
        self.h.search.setText("")
        self.assertTrue(all(not item.isHidden() for item in self.h._items.values()))

    def test_opening_a_page_while_searching_goes_to_the_first_match(self):
        self.h.search.setText("Savitzky")
        self.h.open_page("transform.md")
        self.assertIn("Savitzky", self.h.browser.textCursor().selectedText())


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestHelpMenu(unittest.TestCase):
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

    def test_documentation_opens_the_window_and_online_has_its_own_entry(self):
        w = self.PlotVizApp()
        titles = [a.text() for a in w._help_menu.actions()]
        self.assertIn("Documentation", titles)
        self.assertIn("Documentation Online", titles)
        w._open_documentation()
        self.assertTrue(w._help_window.isVisible())
        first = w._help_window
        w._open_documentation()
        self.assertIs(w._help_window, first)            # one window, shown again
        first.close()
        w.close()

    def test_without_the_docs_on_disk_the_browser_is_used(self):
        from unittest import mock
        w = self.PlotVizApp()
        with mock.patch("ui.help_window.docs_dir", return_value=None), \
                mock.patch.object(self.PlotVizApp, "_open_documentation_online") as online:
            w._open_documentation()
        online.assert_called_once()
        self.assertIsNone(getattr(w, "_help_window", None))
        w.close()


if __name__ == "__main__":
    unittest.main()
