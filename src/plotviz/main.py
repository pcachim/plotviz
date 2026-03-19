#!/usr/bin/env python3
"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.


main.py — plotviz entry point (dev + PyInstaller bundle).

Run from source:
    cd ~/plotviz && uv run python src/plotviz/main.py
"""

import sys
import os

# ── 1. sys.path ───────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _pkg_dir = sys._MEIPASS                                # type: ignore[attr-defined]
else:
    _pkg_dir = os.path.dirname(os.path.abspath(__file__))

if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

# ── 2. Matplotlib data + cache ────────────────────────────────────────────────
# When launched via double-click macOS provides no shell environment.
# Hard-set every path from sys._MEIPASS — os.environ.setdefault is not enough.
if getattr(sys, 'frozen', False):
    _mpl_data = os.path.join(_pkg_dir, 'matplotlib', 'mpl-data')
    if os.path.isdir(_mpl_data):
        os.environ['MATPLOTLIBDATA'] = _mpl_data

    _mpl_cache = os.path.expanduser(
        '~/Library/Application Support/plotviz/matplotlib'
    )
    os.makedirs(_mpl_cache, exist_ok=True)
    os.environ['MPLCONFIGDIR'] = _mpl_cache
    os.environ['MPLBACKEND'] = 'Qt5Agg'

# ── 3. Import matplotlib and lock data path ───────────────────────────────────
import matplotlib
if getattr(sys, 'frozen', False) and os.path.isdir(_mpl_data):
    matplotlib.get_data_path = lambda: _mpl_data   # type: ignore[method-assign]

matplotlib.use('Qt5Agg')

# ── 4. Reset font manager so bundled fonts are found ─────────────────────────
if getattr(sys, 'frozen', False):
    try:
        import matplotlib.font_manager as _fm
        _fm._load_fontmanager(try_read_cache=False)
    except Exception:
        pass

# ── 5. multiprocessing (required on macOS with spawn start method) ────────────
from multiprocessing import freeze_support
freeze_support()

# ── 6. Application ────────────────────────────────────────────────────────────
from pathlib import Path
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from ui.main_window import ChartStudioApp

# File extensions this app owns
_CHART_EXT    = '.pviz'
_TEMPLATE_EXT = '.pvizt'
_PALETTE_EXT  = '.pvizx'


def _app_icon() -> QIcon:
    """Locate assets/plotviz.icns whether running from source or frozen bundle."""
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)           # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent.parent.parent  # repo root (~/plotviz/)
    icon_path = base / 'assets' / 'plotviz.icns'
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


class PlotVizApp(QApplication):
    """QApplication subclass that handles macOS QFileOpenEvent.

    When the user double-clicks a .pviz or .pvizt file in Finder while the
    app is already running, macOS sends a QFileOpenEvent rather than spawning
    a new process.  We forward it to the main window.
    """

    def __init__(self, argv):
        super().__init__(argv)
        self._window: ChartStudioApp | None = None

    def set_window(self, window: ChartStudioApp) -> None:
        self._window = window

    def event(self, e: QEvent) -> bool:
        if e.type() == QEvent.Type.FileOpen and self._window is not None:
            fp = e.file()                           # type: ignore[attr-defined]
            if fp.endswith(_CHART_EXT):
                self._window._load_project_from_path(fp)
            elif fp.endswith(_TEMPLATE_EXT):
                self._window._load_template_from_path(fp)
            elif fp.endswith(_PALETTE_EXT):
                self._window._import_palette_bundle_from_path(fp)
            return True
        return super().event(e)


def main():
    app = PlotVizApp(sys.argv)
    app.setApplicationName('plotviz')
    app.setApplicationDisplayName('plotviz')
    app.setOrganizationName('plotviz')
    app.setOrganizationDomain('com.pviz.app')
    app.setStyle('Fusion')
    app.setWindowIcon(_app_icon())

    window = ChartStudioApp()
    app.set_window(window)
    window.show()

    # ── Cold-launch: file passed as command-line argument ─────────────────────
    # macOS passes the file path in argv when the app is launched by opening a
    # document from Finder (and the app was not already running).
    for arg in sys.argv[1:]:
        if arg.endswith(_CHART_EXT) and Path(arg).is_file():
            window._load_project_from_path(arg)
            break
        if arg.endswith(_TEMPLATE_EXT) and Path(arg).is_file():
            window._load_template_from_path(arg)
            break
        if arg.endswith(_PALETTE_EXT) and Path(arg).is_file():
            window._import_palette_bundle_from_path(arg)
            break

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
