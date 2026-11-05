"""Capture the app's pages, with numbered zones, for the user guide.

Opens plotviz without a screen, loads a sample chart, and for each page of the left panel
saves a picture whose section headers are numbered (the numbers sit in a margin on the right);
the guide explains each number. Also saves an overview of the whole window.

    uv run python util/make_doc_screenshots.py            # everything
    uv run python util/make_doc_screenshots.py layout plot # only some pages

Files: docs/images/ui/<page>.png and docs/images/ui/zones.json (the title of each numbered zone,
which a test compares with the guide). The user's own settings are never read or written: the
captures use a temporary settings folder, with every collapsible section open.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "plotviz"))

OUT = ROOT / "docs" / "images" / "ui"
SAMPLE = ROOT / "data" / "plots" / "plot_xy-curve_fit.pviz"
MARGIN = 40                       # right margin of the page pictures, where the numbers go
ACCENT = "#d6336c"

# pages that need another sample chart than SAMPLE
PAGE_SAMPLES = {"axes-3d": ROOT / "data" / "plots" / "plot_surface.pviz",
                "plot-options": ROOT / "data" / "plots" / "hist.pviz"}
# on the 3D page the sections of the x and y axes are folded, so that the Z section is in view
FOLDED = {"axes-3d": {"X AXIS", "Y AXIS (LEFT)", "Y AXIS (RIGHT / SECONDARY)"}}

# page key -> (outer tab, inner tab or None, generator page or None)
PAGES = {
    "datasets": ("Data", "Datasets", None),
    "generate-fx": ("Data", "Generate", "y=f(x)"),
    "generate-fxy": ("Data", "Generate", "z=f(x,y)"),
    "generate-fuv": ("Data", "Generate", "(u,v)=f(x,y)"),
    "generate-table": ("Data", "Generate", "📋 Table"),
    "statistics": ("Data", "Statistics", None),
    "transform": ("Data", "Transform", None),
    "layout": ("Layout && Style", None, None),
    "plot": ("Plots", "Plot", None),
    "plot-options": ("Plots", "Plot", None),
    "curves": ("Plots", "Curves", None),
    "axes": ("Plots", "Axes", None),
    "axes-3d": ("Plots", "Axes", None),
    "canvas-grid": ("Plots", "Canvas && Grid", None),
    "legend-notes": ("Plots", "Legend && Notes", None),
}


def isolate_settings():
    """Point the app at an empty temporary settings folder, so the pictures do not depend on
    (or change) the settings of whoever runs this."""
    import config.settings as st
    folder = Path(tempfile.mkdtemp(prefix="plotviz-shots-"))
    st._CFG_DIR = folder
    st.CFG_FILE = folder / "settings.json"
    st.settings.clear()
    st.settings["theme"] = "Light"


def zones_of(w):
    """(title, y) of every numbered zone of the page shown: section labels and collapsible
    headers, top to bottom, with y in the coordinates of the tab widget."""
    from PyQt6.QtWidgets import QGroupBox, QLabel, QToolButton
    from ui.collapsible import CollapsibleSection
    page = w.tabs.currentWidget()
    found = []
    for label in page.findChildren(QLabel):
        if label.property("section") and label.isVisible():
            found.append((label.mapTo(w.tabs, label.rect().center()).y(), label.text().rstrip(":")))
    for box in page.findChildren(QGroupBox):                 # the options of the chart type
        if box.isVisible() and box.title().endswith("Options"):
            found.append((box.mapTo(w.tabs, box.rect().topLeft()).y() + 8, box.title()))
    for section in page.findChildren(CollapsibleSection):
        button = section.findChild(QToolButton)
        if section.isVisible() and button is not None:
            found.append((button.mapTo(w.tabs, button.rect().center()).y(), button.text().replace("&&", "&")))
    return [(title, y) for y, title in sorted(found)]


def table_zones(w):
    """The Table page has no section titles: its numbered zones are the rows of controls."""
    from PyQt6.QtWidgets import QPushButton
    buttons = {b.text(): b for b in w.tabs.currentWidget().findChildren(QPushButton) if b.isVisible()}

    def y(widget):
        return widget.mapTo(w.tabs, widget.rect().center()).y()
    return [("New table", y(buttons["New"])), ("Cells", y(w.data_table)),
            ("Editing buttons", y(buttons["＋R"])), ("Load and CSV", y(buttons["📥 Load"]))]


def content_bottom(w) -> int:
    """The y (in tab-widget coordinates) just under the lowest control of the page shown:
    the page is taller than its controls, and the empty part is cut off."""
    from PyQt6.QtWidgets import QWidget
    page = w.tabs.currentWidget()
    lowest = 0
    for child in page.findChildren(QWidget):
        leaf = not any(isinstance(c, QWidget) and c.isVisible() for c in child.children())
        if child.isVisible() and leaf and child.height() > 2:
            lowest = max(lowest, child.mapTo(w.tabs, child.rect().bottomLeft()).y())
    return lowest + 24


def numbered(pixmap, zones, bottom):
    """The page picture, cropped to *bottom*, with a numbered circle per zone in a margin."""
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
    height = min(pixmap.height(), bottom)
    out = QPixmap(pixmap.width() + MARGIN, height)
    out.fill(QColor("white"))
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.drawPixmap(0, 0, pixmap.copy(0, 0, pixmap.width(), height))
    font = QFont()
    font.setBold(True)
    font.setPixelSize(13)
    painter.setFont(font)
    cx = pixmap.width() + MARGIN // 2
    for number, (_, y) in enumerate(zones, 1):
        painter.setPen(QColor(ACCENT))
        painter.drawLine(QPoint(pixmap.width() - 6, y), QPoint(cx - 11, y))
        painter.setBrush(QColor(ACCENT))
        painter.drawEllipse(QPoint(cx, y), 11, 11)
        painter.setPen(QColor("white"))
        painter.drawText(cx - 11, y - 11, 22, 22, Qt.AlignmentFlag.AlignCenter, str(number))
    painter.end()
    return out


def overview(w):
    """The whole window with five numbered zones (their positions come from the live widgets)."""
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtGui import QColor, QFont, QPainter
    from PyQt6.QtWidgets import QPushButton
    pixmap = w.grab()
    to_window = lambda widget, p: widget.mapTo(w, p)  # noqa: E731
    new_btn = next(b for b in w.findChildren(QPushButton) if "New" in b.text())
    top_bar = to_window(new_btn, new_btn.rect().center()).y()
    toolbar = getattr(w.canvas, "toolbar", None)
    tool_y = to_window(toolbar, toolbar.rect().center()).y() if toolbar else 58
    canvas_left = to_window(w.canvas, QPoint(0, 0)).x()
    points = [
        QPoint(w.width() - 30, w.menuBar().height() // 2),              # 1 menu bar
        QPoint(285, top_bar),                                                              # 2 top bar (between Export and undo)
        QPoint(w.tabs.width() - 40, to_window(w.tabs, QPoint(0, 14)).y()),                 # 3 tabs
        QPoint(w.width() - 30, tool_y),                                  # 4 canvas toolbar
        QPoint(canvas_left + 60, to_window(w.canvas, QPoint(0, 0)).y() + 150),            # 5 chart preview
    ]
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(14)
    painter.setFont(font)
    for number, p in enumerate(points, 1):
        painter.setPen(QColor("white"))
        painter.setBrush(QColor(ACCENT))
        painter.drawEllipse(p, 12, 12)
        painter.drawText(p.x() - 12, p.y() - 12, 24, 24, Qt.AlignmentFlag.AlignCenter, str(number))
    painter.end()
    return pixmap


def prepare_page(w, key):
    """Give the page something to show: the previews drawn, the transform pointed at a series."""
    from PyQt6.QtTest import QTest
    if key == "transform":
        w.tf_x_combo.setCurrentText("t")
        w.tf_y_combo.setCurrentText("linear")
        w.tf_preview.update_preview(forced=True)
    elif key == "generate-fx":
        w.gen_preview.update_preview(forced=True)
    elif key == "generate-fxy":
        w.fxy_preview.update_preview(forced=True)
    elif key == "generate-fuv":
        w.fuv_preview.update_preview(forced=True)
    elif key == "plot-options":
        w.series_table.selectRow(0)
        w.series_table.setCurrentCell(0, 2)
    QTest.qWait(250)


def fit_window(w):
    """Make the window just tall enough for the whole page (a taller one would stretch it)."""
    from PyQt6.QtTest import QTest
    w.resize(1280, 700)
    for _ in range(6):
        QTest.qWait(150)
        missing = content_bottom(w) - w.tabs.height()
        if missing <= 0:
            break
        w.resize(1280, w.height() + missing + 30)


def export_dialog(w, app):
    """The Export Image dialog of a chart with several subplots, numbered like the pages."""
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication, QCheckBox, QComboBox, QDialogButtonBox, QLabel, QSpinBox
    from PyQt6.QtTest import QTest
    w._load_project_inner(str(ROOT / "data" / "plots" / "multiple" / "04_line_bar_scatter_heatmap_2x2.pviz"), silent=True)
    QTest.qWait(500)
    shot = {}

    def grab():
        dialog = QApplication.activeModalWidget()
        assert dialog is not None
        def y(widget):
            return widget.mapTo(dialog, widget.rect().center()).y()
        combos = dialog.findChildren(QComboBox)
        pixels = next(label for label in dialog.findChildren(QLabel) if " px" in label.text())
        zones = [("Format", y(combos[0])), ("Resolution", y(dialog.findChild(QSpinBox))),
                 ("Size in pixels", y(pixels)), ("Each subplot", y(dialog.findChild(QCheckBox))),
                 ("Buttons", y(dialog.findChild(QDialogButtonBox)))]
        shot["zones"] = zones
        shot["pixmap"] = dialog.grab()
        dialog.reject()
    QTimer.singleShot(900, grab)
    wi, hi = w._fig_size_in_inches()
    w._ask_export_options(wi, hi)
    pixmap = shot["pixmap"]
    numbered(pixmap, shot["zones"], pixmap.height()).save(str(OUT / "export.png"))
    print("export", [t for t, _ in shot["zones"]])
    return [t for t, _ in shot["zones"]]


def preferences_dialog(w, app):
    """The Preferences dialog, numbered by its four sections (its folders are shown as on a Mac)."""
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication, QGroupBox, QLineEdit
    shot = {}
    shown = ["~/Library/Application Support/plotviz/settings.json", "~/Library/Application Support/plotviz/",
             "~/Library/Application Support/plotviz/schemes/", "~/Library/Application Support/plotviz/palettes/"]

    def grab():
        dialog = QApplication.activeModalWidget()
        assert dialog is not None
        for edit, text in zip(dialog.findChildren(QLineEdit), shown):
            edit.setText(text)                      # not the temporary folder this run uses
            edit.setCursorPosition(0)
        shot["zones"] = [(box.title(), box.mapTo(dialog, box.rect().topLeft()).y() + 10)
                         for box in dialog.findChildren(QGroupBox)]
        shot["pixmap"] = dialog.grab()
        dialog.reject()
    QTimer.singleShot(700, grab)
    w._open_app_settings_dialog()
    pixmap = shot["pixmap"]
    numbered(pixmap, shot["zones"], pixmap.height()).save(str(OUT / "preferences.png"))
    print("preferences", [t for t, _ in shot["zones"]])
    return [t for t, _ in shot["zones"]]


def home_picture(w):
    """The whole window with the gallery of charts, for the home page of the documentation."""
    from PyQt6.QtTest import QTest
    from ui.collapsible import CollapsibleSection
    w._load_project_inner(str(ROOT / "data" / "plots" / "multiple" / "09_gallery_2x3.pviz"), silent=True)
    for section in w.findChildren(CollapsibleSection):
        section._toggle.setChecked(True)
    w.resize(1280, 820)
    w.tabs.setCurrentIndex(2)                                   # Plots
    w.plots_inner_tabs.setCurrentIndex(0)                       # Plot: the series table
    QTest.qWait(700)
    w.grab().save(str(OUT / "home.png"))
    print("home")


def main(only: list[str]) -> int:
    unknown = [k for k in only if k not in PAGES and k not in ("overview", "export", "preferences", "home")]
    if unknown:
        print("unknown page(s):", ", ".join(unknown), "| known:", ", ".join(PAGES))
        return 2
    isolate_settings()
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication
    from ui.collapsible import CollapsibleSection
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    from ui.main_window import PlotVizApp
    PlotVizApp._load_on_startup = lambda self: None
    w = PlotVizApp()
    w.resize(1280, 820)
    w.show()
    w._load_project_inner(str(SAMPLE), silent=True)
    QTest.qWait(600)
    for section in w.findChildren(CollapsibleSection):
        section._toggle.setChecked(True)
    OUT.mkdir(parents=True, exist_ok=True)
    zones_file = OUT / "zones.json"
    zones = json.loads(zones_file.read_text(encoding="utf-8")) if zones_file.exists() else {}

    def tab_names(tabs):
        return [tabs.tabText(i) for i in range(tabs.count())]

    loaded = SAMPLE
    for key, (outer, inner, generator) in PAGES.items():
        if only and key not in only:
            continue
        wanted = PAGE_SAMPLES.get(key, SAMPLE)
        if wanted != loaded:
            w._load_project_inner(str(wanted), silent=True)
            QTest.qWait(500)
            loaded = wanted
        w.tabs.setCurrentIndex(tab_names(w.tabs).index(outer))
        if inner:
            tabs = w.data_inner_tabs if outer == "Data" else w.plots_inner_tabs
            tabs.setCurrentIndex(tab_names(tabs).index(inner))
        if generator:
            w.gen_inner_tabs.setCurrentIndex(tab_names(w.gen_inner_tabs).index(generator))
        prepare_page(w, key)
        for section in w.findChildren(CollapsibleSection):
            section._toggle.setChecked(section._toggle.text().replace("&&", "&") not in FOLDED.get(key, set()))
        fit_window(w)
        found = table_zones(w) if key == "generate-table" else zones_of(w)
        numbered(w.tabs.grab(), found, content_bottom(w)).save(str(OUT / f"{key}.png"))
        zones[key] = [title for title, _ in found]
        print(f"{key:<16} {len(found)} zone(s): {', '.join(zones[key])}")
    if not only or "export" in only:
        zones["export"] = export_dialog(w, app)
    if not only or "home" in only:
        home_picture(w)
    if not only or "preferences" in only:
        zones["preferences"] = preferences_dialog(w, app)
    if not only or "overview" in only:
        w.resize(1280, 820)
        w.tabs.setCurrentIndex(0)
        w.data_inner_tabs.setCurrentIndex(0)
        QTest.qWait(400)
        overview(w).save(str(OUT / "overview.png"))
        print("overview")
    zones_file.write_text(json.dumps(zones, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    w.close()
    return 0


if __name__ == "__main__":
    sys.exit(main([k for k in sys.argv[1:]]))
