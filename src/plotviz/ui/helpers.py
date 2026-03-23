"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.

ui/helpers.py — small UI utilities shared across ui modules.
Kept in a separate file to avoid circular imports.
File-dialog directory management now delegates to config.settings so the
last-used directory persists across sessions.
"""
import config.settings as _s

# ── Recent-colour persistence ─────────────────────────────────────────────────
_MAX_RECENT = 8          # one row of 8, matching the Basic/Custom grid columns
_RECENT_KEY = 'recent_colors'

# Cell dimensions matching the QColorDialog Basic/Custom grids exactly
_CELL_W = 28
_CELL_H = 24


def _load_recent_colors():
    """Return list of hex strings (newest first)."""
    return list(_s.get(_RECENT_KEY, []))


def _save_recent_color(hex_color: str):
    """Prepend hex_color to the persisted recent list, dedup, cap at _MAX_RECENT."""
    recent = _load_recent_colors()
    hex_color = hex_color.lower()
    recent = [c for c in recent if c != hex_color]
    recent.insert(0, hex_color)
    _s.set(_RECENT_KEY, recent[:_MAX_RECENT])


# ── Directory helpers ─────────────────────────────────────────────────────────

def _get_dir() -> str:
    """Return the directory for the next open/save dialog."""
    return _s.get_last_dir()


def _remember_dir(filepath: str) -> None:
    """Call after a successful open/save to persist the directory."""
    _s.remember_dir(filepath)


# Legacy alias kept for any call sites that still use the old name
def _default_dir() -> str:
    return _get_dir()


# ── Recent-colour swatch widget ───────────────────────────────────────────────

def _make_recent_widget(dialog, cell_w=_CELL_W, cell_h=_CELL_H):
    """
    Single row of 8 colour swatches, pixel-perfect match of QColorDialog's
    Basic/Custom grids:
      - cell stride: 28 × 24 px
      - coloured square: 20 × 16 px (fill), bordered by 1 px #b8b8b8
      - 3 px gap on each side (background #efefef)
    Clicking a swatch sets that colour on *dialog*.
    """
    from PyQt6.QtWidgets import QWidget
    from PyQt6.QtGui import QColor, QPainter, QBrush, QPen
    from PyQt6.QtCore import Qt, QRect

    # Exact values measured from a rendered QColorDialog grid
    GAP       = 3            # px gap around each square
    BORDER    = 1            # px border around coloured fill
    FILL_W    = cell_w - 2 * GAP - 2 * BORDER   # 20 px
    FILL_H    = cell_h - 2 * GAP - 2 * BORDER   # 16 px
    BORDER_C  = QColor(0xb8, 0xb8, 0xb8)         # #b8b8b8 — Qt's cell border
    EMPTY_C   = QColor(0xff, 0xff, 0xff)         # white for empty slots

    total_w = cell_w * _MAX_RECENT
    total_h = cell_h

    class RecentWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.setFixedSize(total_w, total_h)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            # Inherit parent background instead of painting our own
            self.setAutoFillBackground(True)
            self._colors  = []
            self._hovered = -1
            self.setMouseTracking(True)
            self.refresh()

        def refresh(self):
            self._colors = [QColor(h) for h in _load_recent_colors()]
            self.update()

        def _idx(self, x):
            i = x // cell_w
            return i if 0 <= i < _MAX_RECENT else -1

        def paintEvent(self, _):
            p = QPainter(self)

            # Use the dialog's Window palette colour for the gap areas —
            # matches the form background on any OS/theme
            from PyQt6.QtGui import QPalette
            bg = self.palette().color(QPalette.ColorRole.Window)

            # Fill entire widget with the form background
            p.fillRect(0, 0, total_w, total_h, bg)

            for i in range(_MAX_RECENT):
                ox = i * cell_w          # left edge of this cell slot
                oy = 0

                fill = self._colors[i] if i < len(self._colors) else EMPTY_C

                # Hover: lighten the fill slightly
                if i == self._hovered and i < len(self._colors):
                    r = min(255, fill.red()   + 30)
                    g = min(255, fill.green() + 30)
                    b = min(255, fill.blue()  + 30)
                    fill = QColor(r, g, b)

                # Draw border rect (1 px #b8b8b8)
                bx = ox + GAP
                by = oy + GAP
                bw = FILL_W + 2 * BORDER
                bh = FILL_H + 2 * BORDER
                p.fillRect(bx, by, bw, bh, BORDER_C)

                # Draw coloured fill
                p.fillRect(bx + BORDER, by + BORDER, FILL_W, FILL_H, fill)

        def mouseMoveEvent(self, event):
            idx = self._idx(event.position().toPoint().x())
            if idx != self._hovered:
                self._hovered = idx
                self.update()

        def leaveEvent(self, _):
            self._hovered = -1
            self.update()

        def mousePressEvent(self, event):
            if event.button() == Qt.MouseButton.LeftButton:
                idx = self._idx(event.position().toPoint().x())
                if 0 <= idx < len(self._colors):
                    dialog.setCurrentColor(self._colors[idx])

    return RecentWidget()


# ── Main colour dialog ────────────────────────────────────────────────────────

def _show_color_dialog(initial=None, parent=None, palette_colors=None):
    """Open QColorDialog with:
    - current palette pre-loaded into the custom colour slots
    - a 'Recent colors' swatch row inserted above the 'Custom colors' section

    Uses DontUseNativeDialog so the custom-colour grid is always visible.
    Returns a QColor — invalid if the user cancelled.
    """
    from PyQt6.QtGui import QColor
    from PyQt6.QtWidgets import QColorDialog, QLabel, QSizePolicy

    if palette_colors:
        for i, hex_col in enumerate(palette_colors[:16]):
            QColorDialog.setCustomColor(i, QColor(hex_col))

    dlg = QColorDialog(initial if initial else QColor('#000000'), parent)
    dlg.setWindowTitle('Choose Colour')
    dlg.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)

    # ── Locate the left VBox (contains Basic/Custom sections) ─────────────────
    # Layout tree: QVBoxLayout → [QHBoxLayout → [left QVBoxLayout, right QVBoxLayout],
    #                              QDialogButtonBox]
    try:
        top_vbox = dlg.layout()                           # QVBoxLayout
        left_vbox = (top_vbox.itemAt(0).layout()          # QHBoxLayout
                              .itemAt(0).layout())         # left QVBoxLayout

        # Find index of the "&Custom colors" label (index 5 in Qt 6.x)
        custom_idx = None
        for i in range(left_vbox.count()):
            item = left_vbox.itemAt(i)
            w = item.widget() if item else None
            if w and isinstance(w, QLabel) and 'Custom' in (w.text() or ''):
                custom_idx = i
                break

        if custom_idx is not None:
            lbl = QLabel('Recent colors')
            lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

            recent_widget = _make_recent_widget(dlg)

            left_vbox.insertWidget(custom_idx, recent_widget)
            left_vbox.insertWidget(custom_idx, lbl)
    except Exception:
        pass   # If layout introspection fails, just show the dialog normally

    if dlg.exec():
        color = dlg.currentColor()
        if color.isValid():
            _save_recent_color(color.name())
        return color
    return QColor()
