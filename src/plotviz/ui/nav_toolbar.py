"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/nav_toolbar.py  –  plotviz
The matplotlib navigation toolbar used by every chart canvas in the app.
"""
from contextlib import contextmanager

try:
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
except ImportError:
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT


class SafeNavigationToolbar(NavigationToolbar2QT):
    """NavigationToolbar2QT that never switches to the "busy" cursor while drawing.

    By default matplotlib's Agg canvas wraps every draw in
    ``toolbar._wait_cursor_for_draw_cm()``, which calls ``QWidget.setCursor`` with
    Qt.WaitCursor and then restores the previous cursor. On macOS 27 with
    Qt 6.11 that call crashed the app (EXC_BREAKPOINT in
    QImage::toCGImage -> CGImageCreate) as soon as a file was opened and the
    chart was redrawn. The busy cursor is purely cosmetic, so it is disabled.
    """

    @contextmanager
    def _wait_cursor_for_draw_cm(self):
        yield
