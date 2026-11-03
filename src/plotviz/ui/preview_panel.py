"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/preview_panel.py  –  plotviz
PreviewPanel: the small "what would Apply create?" plot of the Transform and Generate pages.
A Preview button, a Live checkbox (redraw shortly after the last change), a log-y checkbox,
a mini matplotlib canvas and a line of text. What is drawn comes from two callbacks, so the
page's Apply and its preview can share the same calculation.
"""
from typing import Any, Callable

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:                                   # matplotlib < 3.5
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

PREVIEW_LIVE_LIMIT = 50_000       # above this many points the preview waits for the button
PREVIEW_DELAY_MS = 300            # live preview: wait this long after the last change


class PreviewPanel(QWidget):
    """compute() returns a plan or raises (its message is shown in the plot);
    draw(ax, plan, fg) draws the plan and returns the text for the line under the plot;
    size() is the number of points involved (Live pauses above PREVIEW_LIVE_LIMIT)."""

    def __init__(self, compute: Callable[[], Any], draw: Callable[[Any, Any, str], str],
                 size: Callable[[], int], what: str = 'the result', parent=None):
        super().__init__(parent)
        self._compute, self._draw, self._size = compute, draw, size
        self.last_plan: Any = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.button = QPushButton('👁  Preview')
        self.button.setToolTip(f'Draw {what}, without creating anything')
        self.button.clicked.connect(lambda: self.update_preview(forced=True))
        row.addWidget(self.button)
        self.live_check = QCheckBox('Live')
        self.live_check.setChecked(True)
        self.live_check.setToolTip(f'Redraw as you change anything it depends on '
                                   f'(paused above {PREVIEW_LIVE_LIMIT:,} points: use the button)')
        row.addWidget(self.live_check)
        self.log_check = QCheckBox('log y')
        self.log_check.setToolTip('Logarithmic y axis for the preview')
        row.addWidget(self.log_check)
        row.addStretch()
        layout.addLayout(row)
        self.canvas = FigureCanvas(Figure(figsize=(3.6, 2.2)))
        self.canvas.setMinimumHeight(170)
        self.ax = self.canvas.figure.add_subplot(111)
        layout.addWidget(self.canvas)
        self.info = QLabel('')
        self.info.setWordWrap(True)
        self.info.setStyleSheet('color:#555;font-size:11px;')
        layout.addWidget(self.info)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(PREVIEW_DELAY_MS)
        self.timer.timeout.connect(lambda: self.update_preview(forced=False))
        self.live_check.toggled.connect(self.schedule)
        self.log_check.toggled.connect(self.redraw)

    # ── when to draw ─────────────────────────────────────────────────────────────
    def schedule(self, *_):
        """A live preview a moment after the last change (not for very long series)."""
        if not self.live_check.isChecked():
            self.timer.stop()
            if self.last_plan is not None or self.info.text():
                self.info.setText('Changed: click Preview to update.')
            return
        n = self._size()
        if n > PREVIEW_LIVE_LIMIT:
            self.timer.stop()
            self.info.setText(f'Live is paused for {n:,} points: click Preview.')
            return
        self.timer.start()

    def update_preview(self, forced):
        """Compute the plan and draw it; problems are written in the plot, not raised."""
        self.timer.stop()
        if not forced and not (self.live_check.isChecked() and self.canvas.isVisible()):
            return                                       # no drawing for a page nobody is looking at
        try:
            plan = self._compute()
        except Exception as e:  # noqa: BLE001 - any failure of the calculation is shown to the user
            self.last_plan = None
            self.hint(str(e), error=True)
            return
        self.last_plan = plan
        self.redraw()

    def redraw(self, *_):
        if self.last_plan is None:
            return
        self.ax.clear()
        fg = self._style_axes()
        try:
            self.info.setText(self._draw(self.ax, self.last_plan, fg))
        except Exception as e:  # noqa: BLE001 - e.g. a result that cannot be drawn (text, wrong shape)
            self.last_plan = None
            self.hint(f'Cannot draw it: {e}', error=True)
            return
        self.canvas.draw_idle()

    # ── drawing ──────────────────────────────────────────────────────────────────
    def _style_axes(self):
        """The mini plot follows the window's colours."""
        pal = self.palette()
        bg, fg = pal.window().color().name(), pal.windowText().color().name()
        fig, ax = self.canvas.figure, self.ax
        fig.patch.set_facecolor(bg)
        ax.set_facecolor(bg)
        ax.tick_params(colors=fg, labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor(fg)
        fig.subplots_adjust(left=0.15, right=0.97, top=0.95, bottom=0.17)
        return fg

    def hint(self, message, error=False):
        ax = self.ax
        ax.clear()
        fg = self._style_axes()
        ax.set_xticks([])
        ax.set_yticks([])
        ax.text(0.5, 0.5, message, transform=ax.transAxes, ha='center', va='center', wrap=True,
                fontsize=8, color='#c0392b' if error else fg)
        self.info.setText('❌  ' + message if error else '')
        self.canvas.draw_idle()
