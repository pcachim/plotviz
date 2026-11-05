"""Write THIRD-PARTY-NOTICES.md and the table of docs/licenses.md.

The notices list every package that goes into a plotviz release (the runtime dependencies of
pyproject.toml and, recursively, theirs) with its version, its licence and the text of the
licence file(s) that the package itself ships, as the BSD, MIT and Apache licences require
when a program is distributed in binary form. The table in docs/licenses.md is rewritten
between its two marker lines.

    uv run python util/make_third_party_notices.py

Run it after changing the dependencies, and check the result in `git diff`.
"""
import importlib.metadata as md
import re
import sys
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parent.parent
NOTICES = ROOT / "THIRD-PARTY-NOTICES.md"
DOCS_PAGE = ROOT / "docs" / "licenses.md"
START, END = "<!-- licenses:start (written by util/make_third_party_notices.py) -->", "<!-- licenses:end -->"

# The licence of each package, as it should be written. "BSD" is replaced by the 2- or 3-clause
# name after reading the text of the licence. Anything missing here falls back to the metadata.
LICENCE_NAMES = {
    "contourpy": "BSD", "cycler": "BSD", "et-xmlfile": "MIT", "fonttools": "MIT", "kiwisolver": "BSD",
    "matplotlib": "Matplotlib licence (PSF-based)",
    "numpy": "BSD (with components under 0BSD, MIT, Zlib and CC0-1.0)", "openpyxl": "MIT",
    "packaging": "Apache-2.0 OR BSD-2-Clause", "pandas": "BSD", "patsy": "BSD", "pillow": "MIT-CMU (HPND)",
    "platformdirs": "MIT", "pyparsing": "MIT", "pyqt6": "GPL-3.0-only (or a commercial licence from Riverbank)",
    "pyqt6-qt6": "LGPL-3.0 (the Qt libraries)", "pyqt6-sip": "BSD", "python-dateutil": "Apache-2.0 OR BSD-3-Clause",
    "scipy": "BSD", "seaborn": "BSD", "six": "MIT", "statsmodels": "BSD", "pyinstaller": "GPL-2.0-or-later, with a bootloader exception (run-time hooks: Apache-2.0)",
}
# Packages that only some platforms need, so they may not be installed where this runs.
NOT_ALWAYS_INSTALLED = {
    "tzdata": ("Apache-2.0", "https://github.com/python/tzdata",
               "Windows builds only. The licence text is in the package and at the address above."),
}
# Licence files outside the .dist-info folder that belong to a package (fonts bundled with matplotlib).
EXTRA_FILES = {"matplotlib": ["matplotlib/mpl-data/fonts/ttf/LICENSE_DEJAVU", "matplotlib/mpl-data/fonts/ttf/LICENSE_STIX"]}
BUILD_TOOLS = {"pyinstaller"}      # not imported by the program: its bootloader is inside every binary


def direct_dependencies() -> list[str]:
    """The `dependencies` of pyproject.toml, as written there (read as text: tomllib needs Python 3.11)."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"(?ms)^dependencies\s*=\s*\[(.*?)^\]", text)
    assert block, "no dependencies list in pyproject.toml"
    return re.findall(r'"([^"]+)"', block.group(1))


def dependency_closure() -> list[str]:
    """Canonical names of the runtime dependencies of plotviz and of theirs (every platform)."""
    dists = {canonicalize_name(d.metadata["Name"]): d for d in md.distributions()}
    seen: list[str] = []

    def walk(name: str) -> None:
        key = canonicalize_name(name)
        if key in seen:
            return
        seen.append(key)
        dist = dists.get(key)
        for requirement in (dist.requires or []) if dist else []:
            parsed = Requirement(requirement)
            if parsed.marker and "extra" in str(parsed.marker):
                continue                                    # an optional extra
            walk(parsed.name)
    for requirement in direct_dependencies():
        walk(Requirement(requirement).name)
    return sorted(seen)


def licence_files(dist: md.Distribution, key: str) -> list[tuple[str, str]]:
    """(file name, text) of the licence files that the package ships next to its metadata."""
    found = []
    for entry in dist.files or []:
        parts = entry.parts
        top_level = len(parts) == 2 or (len(parts) == 3 and parts[1] == "licenses")      # not those of bundled sub-parts
        if parts[0].endswith(".dist-info") and top_level and re.match(r"(?i)(licen[sc]e|copying|notice)", entry.name):
            found.append((entry.name, Path(str(dist.locate_file(entry))).read_text(encoding="utf-8", errors="replace")))
    for extra in EXTRA_FILES.get(key, []):
        path = Path(str(dist.locate_file(extra)))
        if path.is_file():
            found.append((path.name, path.read_text(encoding="utf-8", errors="replace")))
    return found


def bsd_name(texts: list[str]) -> str:
    joined = " ".join(texts).lower()
    return "BSD-3-Clause" if "neither the name" in joined or "may be used to endorse" in joined else "BSD-2-Clause"


def homepage(dist: md.Distribution) -> str:
    meta = dist.metadata
    for key in ("Home-page",):
        if meta.get(key):
            return meta[key]
    for entry in meta.get_all("Project-URL") or []:
        label, _, url = entry.partition(",")
        if label.strip().lower() in ("homepage", "home", "source", "repository", "source code", "documentation"):
            return url.strip()
    return ""


def collect() -> list[dict]:
    dists = {canonicalize_name(d.metadata["Name"]): d for d in md.distributions()}
    rows = []
    for key in dependency_closure() + sorted(BUILD_TOOLS):
        dist = dists.get(key)
        if dist is None:
            note = NOT_ALWAYS_INSTALLED.get(key)
            if note:
                rows.append(dict(name=key, version="", licence=note[0], url=note[1], note=note[2], files=[], build=False))
            continue
        files = licence_files(dist, key)
        licence = LICENCE_NAMES.get(key) or dist.metadata.get("License-Expression") or "see the licence text"
        if licence == "BSD":
            licence = bsd_name([text for _, text in files])
        rows.append(dict(name=dist.metadata["Name"], version=dist.version, licence=licence, url=homepage(dist),
                         note="", files=files, build=key in BUILD_TOOLS))
    return sorted(rows, key=lambda r: (r["build"], r["name"].lower()))


def notices_text(rows: list[dict]) -> str:
    out = [
        "# Third-party notices",
        "",
        "plotviz is free software under the GNU General Public License v3.0 or later (`LICENSE.md`); its source code",
        "is at the address in `SOURCE.md`. A plotviz release also contains the packages below, each under its own",
        "licence, whose terms ask for this notice and for the text of the licence to travel with the program.",
        "The same information, with a short explanation of the Qt and PyInstaller licences, is in the documentation",
        "(Help > Documentation > Licenses).",
        "",
        "## Summary",
        "",
        "| Package | Version | Licence | Project |",
        "|---------|---------|---------|---------|",
    ]
    for row in rows:
        name = row["name"] + (" (build tool)" if row["build"] else "")
        out.append(f"| {name} | {row['version'] or '—'} | {row['licence']} | {row['url'] or '—'} |")
    out += [
        "",
        "## Qt",
        "",
        "plotviz uses Qt 6 through PyQt6. PyQt6 is licensed under the GPL v3 (plotviz is distributed under the same",
        "licence). The Qt libraries (package `PyQt6-Qt6`) are licensed under the GNU Lesser General Public License v3",
        "and are shipped as separate library files inside the application, so they can be replaced by another build of",
        "the same Qt version. Their source code is available from https://download.qt.io/ and the sources of PyQt6 from",
        "https://www.riverbankcomputing.com/software/pyqt/.",
        "",
        "## PyInstaller",
        "",
        "The macOS and Windows programs are made with PyInstaller, which is licensed under the GPL v2 or later. Its",
        "bootloader exception gives unlimited permission to embed the compiled bootloader and related files in a",
        "program and distribute it under any licence; the run-time hooks are under the Apache License 2.0. The text is",
        "in its licence file below.",
        "",
        "## Fonts",
        "",
        "matplotlib brings the DejaVu fonts (and the STIX fonts), whose licences are included under matplotlib.",
        "",
        "## Sample data",
        "",
        "The files of `data/datasets/seaborn` come from the seaborn-data collection (https://github.com/mwaskom/seaborn-data),",
        "which gathers public datasets, each with its own origin and terms of use. See that repository before reusing",
        "them outside plotviz.",
        "",
    ]
    for row in rows:
        out += ["---", "", f"## {row['name']} {row['version']}".rstrip(), "", f"Licence: {row['licence']}"]
        if row["url"]:
            out.append(f"Project: {row['url']}")
        if row["note"]:
            out.append(row["note"])
        for filename, text in row["files"]:
            out += ["", f"### {filename}", "", "~~~~text", text.strip("\n"), "~~~~"]
        if not row["files"] and not row["note"]:
            out += ["", "(the package ships no licence file)"]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def docs_table(rows: list[dict]) -> str:
    lines = ["| Package | Licence |", "|---------|---------|"]
    for row in rows:
        name = row["name"] + (" (build tool)" if row["build"] else "")
        lines.append(f"| {name} | {row['licence']} |")
    return "\n".join(lines)


def main() -> int:
    rows = collect()
    NOTICES.write_text(notices_text(rows), encoding="utf-8")
    print(f"{NOTICES.relative_to(ROOT)}: {len(rows)} packages, {NOTICES.stat().st_size // 1024} KB")
    if DOCS_PAGE.exists():
        page = DOCS_PAGE.read_text(encoding="utf-8")
        if START in page and END in page:
            head, rest = page.split(START, 1)
            _, tail = rest.split(END, 1)
            DOCS_PAGE.write_text(f"{head}{START}\n\n{docs_table(rows)}\n\n{END}{tail}", encoding="utf-8")
            print(f"{DOCS_PAGE.relative_to(ROOT)}: table updated")
        else:
            print(f"{DOCS_PAGE.relative_to(ROOT)}: no markers, table not written")
    for row in rows:
        if not row["files"] and not row["note"]:
            print("  no licence file:", row["name"], file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
