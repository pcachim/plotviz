"""The result pictures of the worked examples of the guide (docs/examples.md).

Each example is done here the way the page tells the reader to do it: the sample dataset is
loaded, the operation is applied (with the code the Transform page uses), the series and the
fits are set up in the real window, and the chart is written through the export path.

    uv run python util/make_doc_examples.py

Files: docs/images/examples/<name>.png
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "plotviz"))

OUT = ROOT / "docs" / "images" / "examples"
DATA = ROOT / "data" / "datasets"
DPI = 90


def read_csv(name: str) -> dict:
    import pandas as pd
    from core.dates import parse_series
    frame = pd.read_csv(DATA / name)
    out = {}
    for column in frame.columns:
        dates = None if pd.api.types.is_numeric_dtype(frame[column]) else parse_series(frame[column])
        out[column] = dates if dates is not None else frame[column].to_numpy()
    return out


def window(datasets: dict, rows: list[tuple], app):
    """A window with the datasets loaded and one series row per (x, y, type, label)."""
    from ui.main_window import PlotVizApp
    w = PlotVizApp()
    w.datasets.update(datasets)
    w.update_lists()
    while w.series_table.rowCount() < len(rows):
        w._add_series_row()
    for r, (xc, yc, kind, label) in enumerate(rows):
        w.series_table.cellWidget(r, 0).setCurrentText(xc)
        w.series_table.cellWidget(r, 1).setCurrentText(yc)
        w.series_table.cellWidget(r, 3).setCurrentText(kind)
        w.series_table.item(r, 2).setText(label)
    app.processEvents()
    return w


def save(w, name: str):
    import matplotlib
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    OUT.mkdir(parents=True, exist_ok=True)
    matplotlib.rcParams["text.usetex"] = False
    wi, hi = w._fig_size_in_inches()
    old = matplotlib.rcParams.get("font.family")
    matplotlib.rcParams["font.family"] = w.title_font.currentText()
    try:
        fig = w._build_export_figure(wi, hi, DPI)
        FigureCanvasAgg(fig).draw()
        path = OUT / f"{name}.png"
        fig.savefig(path, dpi=DPI, facecolor=fig.get_facecolor())
    finally:
        matplotlib.rcParams["font.family"] = old
    print(f"{name:<14} {(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)}  {path.stat().st_size // 1024} KB")


def pulse(app):
    """Example 1: Find peaks on the pulse_signal sample, 5 x noise."""
    from data.transforms import apply_operation
    data = read_csv("pulse_signal.csv")
    px, py = apply_operation("peaks", data["time_s"], data["voltage"], min_height_noise=5.0)
    assert len(py) == 2, len(py)
    data.update({"time_s_peaks": px, "voltage_peaks": py})
    w = window(data, [("time_s", "voltage", "Line", "voltage"),
                      ("time_s_peaks", "voltage_peaks", "Scatter", "peaks")], app)
    w.title_input.setText("Two pulses in a noisy signal")
    w.xlabel_input.setText("time (s)")
    w.ylabel_input.setText("voltage (V)")
    save(w, "pulse")
    return px, py


def fits(app):
    """Example 2: a straight line and a parabola on the quadratic column of fit_test."""
    data = read_csv("fit_test.csv")
    w = window(data, [("x", "quadratic", "Scatter", "quadratic")], app)
    w.title_input.setText("Which model fits?")
    for model in ("Linear", "Quadratic"):
        w.fit_combo.setCurrentText(model)
        w.apply_fit()
    w.fit_ci_combo.setCurrentIndex(2)
    app.processEvents()
    save(w, "fits")
    table = w.fit_table
    rows = [[table.item(r, c).text() if table.item(r, c) else "" for c in range(table.columnCount())]
            for r in range(table.rowCount())]
    w.resize(500, 900)
    w.show()
    w.tabs.setCurrentIndex(2)
    w.plots_inner_tabs.setCurrentIndex(1)
    app.processEvents()
    table.grab().save(str(OUT / "fits-table.png"))
    print("fits-table", rows)
    return rows


def daily(app):
    """Example 3: a daily series with dates, and its 7-day moving average."""
    from data.transforms import apply_operation
    data = read_csv("dates_daily.csv")
    _, smooth = apply_operation("moving_average", data["date"], data["temperature"], window=7)
    data["temperature_MA7"] = smooth
    w = window(data, [("date", "temperature", "Line", "daily"),
                      ("date", "temperature_MA7", "Line", "7-day average")], app)
    w.title_input.setText("Daily temperature")
    w.ylabel_input.setText("temperature (°C)")
    save(w, "daily")


def main() -> int:
    import config.settings as st
    folder = Path(tempfile.mkdtemp(prefix="plotviz-examples-"))
    st._CFG_DIR, st.CFG_FILE = folder, folder / "settings.json"
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    from ui.main_window import PlotVizApp
    PlotVizApp._load_on_startup = lambda self: None
    print("peaks at", [round(float(v), 3) for v in pulse(app)[0]])
    fits(app)
    daily(app)
    return 0


if __name__ == "__main__":
    sys.exit(main())
