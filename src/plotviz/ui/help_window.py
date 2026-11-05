"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/help_window.py  –  plotviz
HelpWindow: the documentation (the Markdown files of docs/) in a window of the app, with a
page index, links between pages, a search that filters the pages and a back/forward history.
Works offline and follows the light/dark palette. When the documentation is not on disk
(a pip install does not carry it) the Help menu opens the online version instead.
"""
import re
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFontDatabase, QImage, QTextCharFormat, QTextCursor, QTextFormat
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSplitter, QTextBrowser,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

ONLINE_URL = 'https://pcachim.github.io/plotviz/'

# The page index: the same order as `nav` in mkdocs.yml (a test keeps them in step).
NAV: list[tuple[str, list[tuple[str, str]]]] = [
    ('', [('Home', 'index.md'), ('Getting Started', 'getting-started.md')]),
    ('Data', [
        ('Datasets and Import', 'datasets.md'),
        ('Generate', 'generate.md'),
        ('Statistics', 'statistics.md'),
        ('Transform', 'transform.md'),
    ]),
    ('Layout & Style', [
        ('Figure', 'layout-style.md'),
        ('Subplots', 'subplots.md'),
        ('Color Schemes', 'color-schemes.md'),
        ('Color Palettes', 'palettes.md'),
    ]),
    ('Plots', [
        ('Plot', 'plot.md'),
        ('Chart Types', 'chart-types.md'),
        ('Curves and Fitting', 'curves.md'),
        ('Axes', 'axes.md'),
        ('Canvas & Grid', 'canvas-grid.md'),
        ('Legend & Notes', 'legend-notes.md'),
    ]),
    ('Tools', [
        ('Seaborn Explorer', 'seaborn-explorer.md'),
        ('Python Code Runner', 'code-runner.md'),
        ('Python Export Bundle', 'python-export.md'),
    ]),
    ('Reference', [
        ('File Formats', 'file-formats.md'),
        ('Menus', 'menus.md'),
        ('Keyboard Shortcuts', 'shortcuts.md'),
    ]),
]


def docs_dir() -> Path | None:
    """The folder with the Markdown pages: inside the bundle, or docs/ of a source checkout."""
    if getattr(sys, 'frozen', False):
        base = Path(getattr(sys, '_MEIPASS')) / 'docs'
    else:
        base = Path(__file__).resolve().parents[3] / 'docs'
    return base if (base / 'index.md').is_file() else None


def slugify(text: str) -> str:
    """The anchor mkdocs gives a heading, so that links such as data.md#removing-datasets work."""
    text = re.sub(r'[^\w\s-]', '', text.lower()).strip()
    return re.sub(r'[\s-]+', '-', text)


_ADMONITION = re.compile(r'^!!!\s+\w+(?:\s+"([^"]*)")?\s*$')
_ICON = re.compile(r':(?:material|fontawesome|octicons)-[\w-]+:\s*')


def prepare_markdown(text: str) -> str:
    """mkdocs-only syntax rewritten as plain Markdown: admonitions become quotes, icons and
    the wrapper of the home page's cards go away."""
    out: list[str] = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _ADMONITION.match(line)
        if m:
            out.append(f'> **{m.group(1) or "Note"}**')
            i += 1
            while i < len(lines):
                body = lines[i].startswith('    ')
                follows = i + 1 < len(lines) and lines[i + 1].startswith('    ')
                if not (body or (not lines[i].strip() and follows)):
                    break
                out.append('> ' + lines[i][4:] if body else '>')
                i += 1
            continue
        if line.strip().startswith('<div') or line.strip() == '</div>':
            i += 1
            continue
        out.append(_ICON.sub('', line))
        i += 1
    return '\n'.join(out)


class HelpWindow(QDialog):
    def __init__(self, parent=None, folder: Path | None = None):
        super().__init__(parent)
        self.setWindowTitle('plotviz documentation')
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.resize(1050, 720)
        self._folder = folder or docs_dir()
        self._text: dict[str, str] = {}          # page file -> its Markdown
        self._history: list[tuple[str, str]] = []
        self._pos = -1
        self._page = ''

        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.back_btn = QPushButton('◀')
        self.fwd_btn = QPushButton('▶')
        for btn, tip, slot in ((self.back_btn, 'Back', self.back), (self.fwd_btn, 'Forward', self.forward)):
            btn.setToolTip(tip)
            btn.setFixedWidth(34)
            btn.clicked.connect(slot)
            bar.addWidget(btn)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search the documentation')
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter_pages)
        self.search.returnPressed.connect(self.find_next)
        bar.addWidget(self.search, 1)
        online = QPushButton('Online version')
        online.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(ONLINE_URL)))
        bar.addWidget(online)
        layout.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.index = QTreeWidget()
        self.index.setHeaderHidden(True)
        self.index.setMinimumWidth(170)
        self.index.itemClicked.connect(self._index_clicked)
        split.addWidget(self.index)
        self.browser = QTextBrowser()
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(self._link_clicked)
        self.browser.document().setDocumentMargin(14)
        split.addWidget(self.browser)
        split.setSizes([210, 840])
        layout.addWidget(split, 1)
        self.status = QLabel('')
        self.status.setStyleSheet('color:#888;font-size:11px;')
        layout.addWidget(self.status)

        self._build_index()
        self.open_page('index.md')

    # ── pages ───────────────────────────────────────────────────────────────────
    def _read(self, page: str) -> str:
        if page not in self._text:
            try:
                self._text[page] = (self._folder / page).read_text(encoding='utf-8') if self._folder else ''
            except OSError:
                self._text[page] = ''
        return self._text[page]

    def _build_index(self):
        self._items: dict[str, QTreeWidgetItem] = {}
        for section, pages in NAV:
            parent = QTreeWidgetItem(self.index, [section]) if section else None
            for title, page in pages:
                item = QTreeWidgetItem(parent or self.index, [title])
                item.setData(0, Qt.ItemDataRole.UserRole, page)
                self._items[page] = item
        self.index.expandAll()

    def _index_clicked(self, item, _column):
        page = item.data(0, Qt.ItemDataRole.UserRole)
        if page:
            self.open_page(page)

    def open_page(self, page: str, anchor: str = '', remember: bool = True):
        """Show *page* (a file of docs/), scrolled to the heading *anchor* when given."""
        if page != self._page:
            if self._folder:
                self.browser.setSearchPaths([str(self._folder)])      # images/… are relative to docs/
            self.browser.setMarkdown(prepare_markdown(self._read(page)) or f'*{page} is not available.*')
            self._page = page
            self._style_code()
            self._size_images()
            item = self._items.get(page)
            if item:
                self.index.setCurrentItem(item)
        if anchor:
            self._scroll_to(anchor)
        else:
            self.browser.verticalScrollBar().setValue(0)
        if remember:
            del self._history[self._pos + 1:]
            self._history.append((page, anchor))
            self._pos = len(self._history) - 1
        self._update_nav_buttons()
        query = self.search.text().strip()
        if query and not anchor:
            self.browser.find(query)

    def _style_code(self):
        """Code (inline and fenced) in the system's monospace font, fenced blocks on a tinted band."""
        doc = self.browser.document()
        assert doc is not None
        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()
        tint = self.palette().alternateBase().color()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        block = doc.begin()
        while block.isValid():
            fenced = block.blockFormat().hasProperty(QTextFormat.Property.BlockCodeFence)
            if fenced:
                fmt = block.blockFormat()
                fmt.setBackground(tint)
                QTextCursor(block).setBlockFormat(fmt)
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid() and (fenced or frag.charFormat().fontFixedPitch()):
                    mono_fmt = QTextCharFormat()
                    mono_fmt.setFontFamilies([mono])
                    sel = QTextCursor(doc)
                    sel.setPosition(frag.position())
                    sel.setPosition(frag.position() + frag.length(), QTextCursor.MoveMode.KeepAnchor)
                    sel.mergeCharFormat(mono_fmt)
                it += 1
            block = block.next()
        cursor.endEditBlock()

    def _size_images(self, max_width: int = 760):
        """Figures are shown at most *max_width* px wide (they are saved larger, for the site)."""
        doc = self.browser.document()
        if doc is None or not self._folder:
            return
        block = doc.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                fmt = frag.charFormat()
                if frag.isValid() and fmt.isImageFormat():
                    image = fmt.toImageFormat()
                    picture = QImage(str(self._folder / image.name()))
                    if not picture.isNull() and picture.width() > max_width:
                        image.setWidth(max_width)
                        image.setHeight(round(picture.height() * max_width / picture.width()))
                        sel = QTextCursor(doc)
                        sel.setPosition(frag.position())
                        sel.setPosition(frag.position() + frag.length(), QTextCursor.MoveMode.KeepAnchor)
                        sel.setCharFormat(image)
                it += 1
            block = block.next()

    def _scroll_to(self, anchor: str):
        doc = self.browser.document()
        assert doc is not None
        block = doc.begin()
        while block.isValid():
            if block.blockFormat().headingLevel() and slugify(block.text()) == anchor:
                cursor = QTextCursor(block)
                self.browser.setTextCursor(cursor)
                bar = self.browser.verticalScrollBar()
                layout = doc.documentLayout()
                if bar and layout:
                    bar.setValue(int(layout.blockBoundingRect(block).top()))
                return
            block = block.next()

    def _link_clicked(self, url: QUrl):
        target = url.toString()
        if target.startswith(('http://', 'https://', 'mailto:')):
            QDesktopServices.openUrl(url)
            return
        page, _, anchor = target.partition('#')
        page = Path(page).name if page else self._page
        if page in self._items or (self._folder and (self._folder / page).is_file()):
            self.open_page(page, anchor)

    # ── history ─────────────────────────────────────────────────────────────────
    def back(self):
        if self._pos > 0:
            self._pos -= 1
            self.open_page(*self._history[self._pos], remember=False)

    def forward(self):
        if self._pos < len(self._history) - 1:
            self._pos += 1
            self.open_page(*self._history[self._pos], remember=False)

    def _update_nav_buttons(self):
        self.back_btn.setEnabled(self._pos > 0)
        self.fwd_btn.setEnabled(self._pos < len(self._history) - 1)

    # ── search ──────────────────────────────────────────────────────────────────
    def _filter_pages(self, query: str):
        """Only the pages that contain the text stay in the index; the shown page is searched."""
        query = query.strip().lower()
        found = 0
        for page, item in self._items.items():
            visible = not query or query in self._read(page).lower()
            item.setHidden(not visible)
            found += visible
        for i in range(self.index.topLevelItemCount()):    # a section with no page left goes too
            top = self.index.topLevelItem(i)
            assert top is not None
            if top.childCount():
                top.setHidden(all(top.child(j).isHidden() for j in range(top.childCount())))
        self.status.setText(f'{found} page(s) contain "{query}"' if query else '')
        doc = self.browser.document()
        if query and doc:
            cursor = QTextCursor(doc)
            self.browser.setTextCursor(cursor)
            self.browser.find(query)

    def find_next(self):
        query = self.search.text().strip()
        if query and not self.browser.find(query):          # wrap around
            self.browser.moveCursor(QTextCursor.MoveOperation.Start)
            self.browser.find(query)

    def selected_page(self) -> str:
        return self._page

