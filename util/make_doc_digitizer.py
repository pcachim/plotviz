"""The picture of the Digitize Image page: docs/images/tools/digitizer.png.

Draws a chart like the ones of a paper (a damped oscillation, as an image), opens it in the
Digitize Image window without a screen, sets the reference points, follows the red curve and
saves the whole window.

    uv run python util/make_doc_digitizer.py
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "plotviz"))

OUT = ROOT / "docs" / "images" / "tools" / "digitizer.png"


def main() -> int:
    import matplotlib.pyplot as plt
    import numpy as np
    from PyQt6.QtWidgets import QApplication

    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    x = np.linspace(0, 10, 200)
    ax.plot(x, 10 * np.exp(-x / 4) * np.cos(x) + 12, color="#d62728", lw=2.2)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 25)
    ax.grid(alpha=0.3)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("signal")
    picture = Path(tempfile.mkdtemp()) / "figure-from-a-paper.png"
    fig.savefig(picture)
    height = fig.get_size_inches()[1] * 100

    def pixel(xv, yv):
        px, py = ax.transData.transform((xv, yv))
        return px, height - py

    app = QApplication.instance() or QApplication([])
    from ui.digitizer import DigitizerDialog
    dialog = DigitizerDialog()
    dialog.resize(1180, 720)
    dialog.show()
    dialog.open_image(str(picture))
    for key, point in (("x1", (0, 0)), ("x2", (10, 0)), ("y1", (0, 0)), ("y2", (0, 25))):
        dialog.set_calibration_point(key, *pixel(*point))
    for key, value in zip(("x1", "x2", "y1", "y2"), ("0", "10", "0", "25")):
        dialog.cal_values[key].setText(value)
    dialog.pick_color_at(*pixel(3, 10 * np.exp(-3 / 4) * np.cos(3) + 12))
    dialog.step.setValue(14)
    dialog.trace_curve()
    dialog._on_move(*pixel(5.0, 10 * np.exp(-5 / 4) * np.cos(5) + 12))      # the magnifier shows near the curve
    app.processEvents()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    dialog.grab().save(str(OUT))
    dialog.close()
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
