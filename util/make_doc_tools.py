"""Pictures for the pages of the Seaborn Explorer and the Python Code Runner.

Opens the two windows without a screen, with sample data (the `tips` and `penguins` datasets of
data/datasets/seaborn) and saves:

* docs/images/tools/seaborn-explorer.png  the whole window, with numbered zones
* docs/images/tools/seaborn-<type>.png    what the Explorer draws for each of its eight chart types
* docs/images/tools/code-runner.png       the whole window, with numbered zones
* docs/images/tools/code-runner-example.png  a chart made from a loaded dataset
* docs/images/tools/code-runner-error.png the editor with the error panel
* docs/images/tools/zones.json            the title of each numbered zone (a test compares them
                                          with the guide)

    uv run python util/make_doc_tools.py            # everything
    uv run python util/make_doc_tools.py seaborn    # only the Explorer ("runner" for the other)
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

OUT = ROOT / "docs" / "images" / "tools"
SNS_DATA = ROOT / "data" / "datasets" / "seaborn"
ACCENT = "#d6336c"
DPI = 90
PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]

SEABORN_TYPES = ["KDE", "Regression", "Strip", "Swarm", "Heatmap", "Pairplot", "Joint", "Catplot"]
ZONES = {
    "seaborn-explorer": ["Chart type", "Color theme", "Data columns", "Chart options", "Canvas toolbar",
                         "Preview", "Bottom bar"],
    "code-runner": ["Editor toolbar", "Editor", "Status line", "Run Code", "Canvas toolbar", "Preview",
                    "Export bar"],
    "code-runner-error": ["Runtime Error"],
}

EXAMPLE_CODE = '''\
# The loaded columns are in the dict `datasets`
bill = datasets["total_bill"]
tip = datasets["tip"]

fig, ax = plt.subplots(figsize=(7, 5))
ax.scatter(bill, tip, s=14, alpha=0.7)
slope, intercept = np.polyfit(bill, tip, 1)
ax.plot(bill, slope * bill + intercept, color="C1")
ax.set_xlabel("total bill ($)")
ax.set_ylabel("tip ($)")
ax.set_title(f"tip = {slope:.2f} x bill + {intercept:.2f}")
plt.show()
'''
ERROR_CODE = '''\
fig, ax = plt.subplots()
ax.plot(datasets["total_bil"], datasets["tip"])
plt.show()
'''


def load_dataset(name: str) -> dict:
    """A seaborn sample file as a dict of arrays, without the rows that have a missing value."""
    import pandas as pd
    frame = pd.read_csv(SNS_DATA / f"{name}.csv").dropna()
    return {col: frame[col].to_numpy() for col in frame.columns}


def markers(pixmap, points):
    """Numbered circles painted on a picture, at the given (x, y) points."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QFont, QPainter
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(14)
    painter.setFont(font)
    for number, point in enumerate(points, 1):
        painter.setPen(QColor("white"))
        painter.setBrush(QColor(ACCENT))
        painter.drawEllipse(point, 12, 12)
        painter.drawText(point.x() - 12, point.y() - 12, 24, 24, Qt.AlignmentFlag.AlignCenter, str(number))
    painter.end()
    return pixmap


def centre(widget, window, dx=0, dy=0):
    from PyQt6.QtCore import QPoint
    return widget.mapTo(window, widget.rect().center()) + QPoint(dx, dy)


def seaborn_pictures(app):
    from PyQt6.QtCore import QPoint
    from PyQt6.QtWidgets import QGroupBox
    from ui.seaborn_explorer import SeabornExplorer

    def explorer(data):
        dialog = SeabornExplorer(data, PALETTE)
        dialog.show()
        app.processEvents()
        return dialog

    tips, penguins = load_dataset("tips"), load_dataset("penguins")
    OUT.mkdir(parents=True, exist_ok=True)

    def choose(dialog, kind, x=None, y=None, hue=None):
        dialog._type_combo.setCurrentText(kind)
        for combo, name in ((dialog._x_combo, x), (dialog._y_combo, y), (dialog._hue_combo, hue)):
            if name:
                combo.setCurrentText(name)
        dialog._draw()
        app.processEvents()

    # whole window
    dialog = explorer(tips)
    choose(dialog, "Regression", "total_bill", "tip")
    boxes = {box.title(): box for box in dialog.findChildren(QGroupBox) if box.isVisible()}
    options = next(box for title, box in boxes.items() if title.endswith("options"))
    picture = dialog.grab()
    bar = dialog._btn_to_runner
    gap = QPoint((bar.mapTo(dialog, bar.rect().topRight()).x() + dialog._btn_close.mapTo(dialog, QPoint(0, 0)).x()) // 2,
                 centre(bar, dialog).y())
    points = [boxes[title].mapTo(dialog, QPoint(boxes[title].width() - 20, 8))
              for title in ("Chart type", "Color theme", "Data columns")]
    points.append(options.mapTo(dialog, QPoint(options.width() - 20, 8)))
    points.append(centre(dialog._toolbar, dialog, dialog._toolbar.width() // 2 - 24))
    points.append(centre(dialog._canvas, dialog, dialog._canvas.width() // 2 - 30, -dialog._canvas.height() // 2 + 34))
    points.append(gap)
    markers(picture, points).save(str(OUT / "seaborn-explorer.png"))
    print("seaborn-explorer")
    dialog.close()

    # one picture per chart type
    cases = {
        "KDE": (tips, {"y": "total_bill"}),
        "Regression": (tips, {"x": "total_bill", "y": "tip"}),
        "Strip": (tips, {"x": "day", "y": "total_bill"}),
        "Swarm": (tips, {"x": "day", "y": "tip"}),
        "Heatmap": (penguins, {}),
        "Pairplot": (penguins, {"hue": "species"}),
        "Joint": (penguins, {"x": "bill_length_mm", "y": "flipper_length_mm"}),
        "Catplot": (tips, {"x": "day", "y": "total_bill"}),
    }
    for kind, (data, columns) in cases.items():
        dialog = explorer(data)
        dialog._type_combo.setCurrentText(kind)
        if kind in ("Heatmap", "Pairplot"):
            dialog._col_list.selectAll()
        if kind == "Heatmap":
            dialog._heat_annot.setChecked(True)
        if kind == "Catplot":
            dialog._cat_kind.setCurrentText("box")
        choose(dialog, kind, columns.get("x"), columns.get("y"), columns.get("hue"))
        path = OUT / f"seaborn-{kind.lower()}.png"
        dialog._canvas_fig.savefig(path, dpi=DPI, facecolor="white")
        print(f"{kind:<10} {(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)}  {path.stat().st_size // 1024} KB")
        dialog.close()


def runner_pictures(app):
    from PyQt6.QtCore import QPoint, QRect
    from ui.code_runner import CodeRunnerDialog

    OUT.mkdir(parents=True, exist_ok=True)
    tips = load_dataset("tips")
    dialog = CodeRunnerDialog(tips)
    dialog.show()
    app.processEvents()
    dialog._run()                                   # the built-in sample
    app.processEvents()

    # whole window
    picture = dialog.grab()
    editor_x = dialog._editor.mapTo(dialog, QPoint(dialog._editor.width() - 24, 24))
    bar = dialog._btn_open
    points = [
        bar.mapTo(dialog, QPoint(-30, bar.height() // 2)),
        editor_x,
        dialog._lbl_pos.mapTo(dialog, QPoint(dialog._lbl_pos.width() + 90, dialog._lbl_pos.height() // 2)),
        centre(dialog._btn_run, dialog, dialog._btn_run.width() // 2 - 24),
        centre(dialog._nav, dialog, dialog._nav.width() // 2 - 24),
        centre(dialog._canvas, dialog, dialog._canvas.width() // 2 - 30, -dialog._canvas.height() // 2 + 34),
        centre(dialog._btn_export, dialog, 90),
    ]
    markers(picture, points).save(str(OUT / "code-runner.png"))
    print("code-runner")

    # a chart made from a loaded dataset
    dialog._editor.setPlainText(EXAMPLE_CODE)
    dialog._run()
    app.processEvents()
    dialog.grab().save(str(OUT / "code-runner-example.png"))
    print("code-runner-example")

    # the error panel (only the editor side of the window)
    dialog._editor.setPlainText(ERROR_CODE)
    dialog._run()
    app.processEvents()
    left = dialog._editor.parentWidget()
    assert left is not None
    side = dialog.grab(QRect(0, 0, left.mapTo(dialog, QPoint(left.width(), 0)).x() + 6, dialog.height()))
    header = dialog._error_panel.mapTo(dialog, QPoint(dialog._error_panel.width() - 120, 14))
    markers(side, [header]).save(str(OUT / "code-runner-error.png"))
    print("code-runner-error")
    dialog.close()


def main(only: list[str]) -> int:
    unknown = [k for k in only if k not in ("seaborn", "runner")]
    if unknown:
        print("unknown:", ", ".join(unknown), "| known: seaborn, runner")
        return 2
    import config.settings as st
    folder = Path(tempfile.mkdtemp(prefix="plotviz-tools-"))
    st._CFG_DIR, st.CFG_FILE = folder, folder / "settings.json"
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    if not only or "seaborn" in only:
        seaborn_pictures(app)
    if not only or "runner" in only:
        runner_pictures(app)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "zones.json").write_text(json.dumps(ZONES, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
