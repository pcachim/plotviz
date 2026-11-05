"""The licence information that goes with a release: complete, and in step with the dependencies."""
import importlib.util
import re
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = str(_ROOT / "src" / "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _script():
    spec = importlib.util.spec_from_file_location("make_third_party_notices", _ROOT / "util" / "make_third_party_notices.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


class TestNotices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = _script()
        cls.notices = (_ROOT / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8")
        cls.page = (_ROOT / "docs" / "licenses.md").read_text(encoding="utf-8")

    def test_every_dependency_of_a_release_is_in_the_notices_and_in_the_docs(self):
        # If a dependency is added (or one of theirs), regenerate with util/make_third_party_notices.py.
        summary = {_norm(m.group(1)) for m in re.finditer(r"^\| ([^|]+?)(?: \(build tool\))? \|", self.notices, flags=re.M)}
        table = {_norm(m.group(1)) for m in re.finditer(r"^\| ([^|]+?)(?: \(build tool\))? \|", self.page, flags=re.M)}
        for name in self.script.dependency_closure():
            with self.subTest(package=name):
                self.assertIn(_norm(name), summary)
                self.assertIn(_norm(name), table)

    def test_the_direct_dependencies_of_pyproject_are_covered(self):
        from packaging.requirements import Requirement
        for requirement in self.script.direct_dependencies():
            name = _norm(Requirement(requirement).name)
            with self.subTest(package=name):
                self.assertRegex(self.notices.lower().replace("_", "-"), rf"(?m)^## {re.escape(name)} ")

    def test_each_installed_package_carries_the_text_of_its_licence(self):
        rows = [row for row in self.script.collect() if not row["note"]]
        self.assertGreater(len(rows), 20)
        for row in rows:
            with self.subTest(package=row["name"]):
                self.assertTrue(row["files"], "the package ships no licence file")
                self.assertGreater(sum(len(text) for _, text in row["files"]), 200)
                self.assertNotEqual(row["licence"], "see the licence text", "name its licence in LICENCE_NAMES")

    def test_qt_pyqt_and_pyinstaller_are_explained(self):
        for text in (self.notices, self.page):
            self.assertIn("GPL v3", text)
            self.assertIn("Lesser General Public License", text)
            self.assertIn("PyInstaller", text)
            self.assertIn("download.qt.io", text)
        self.assertIn("bootloader exception", self.page.lower())

    def test_the_sample_data_and_the_fonts_are_covered(self):
        self.assertIn("seaborn-data", self.page)
        self.assertIn("DejaVu", self.page)
        self.assertIn("SIL Open Font License", self.notices)         # the STIX fonts of matplotlib

    def test_the_program_ships_the_notices_and_points_to_them(self):
        self.assertIn("THIRD-PARTY-NOTICES.md", (_ROOT / "plotviz.spec").read_text(encoding="utf-8"))
        self.assertIn("THIRD-PARTY-NOTICES.md", (_ROOT / "README.md").read_text(encoding="utf-8"))
        about = (_ROOT / "src" / "plotviz" / "ui" / "data_io.py").read_text(encoding="utf-8")
        self.assertIn("THIRD-PARTY-NOTICES.md", about)
        self.assertIn("Licenses", about)
        self.assertTrue((_ROOT / "SOURCE.md").is_file() and (_ROOT / "LICENSE.md").is_file())

    def test_the_licence_of_the_program_is_the_same_everywhere(self):
        self.assertRegex((_ROOT / "pyproject.toml").read_text(encoding="utf-8"), r'(?m)^license = \{text = "GPL-3.0-or-later"\}')
        self.assertIn("GPL-3.0-or-later", (_ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("GNU General Public License v3.0 or later", self.page)


if __name__ == "__main__":
    unittest.main()
