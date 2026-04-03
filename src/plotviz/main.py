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
from ui.main_window import PlotVizApp

# File extensions this app owns
_CHART_EXT    = '.pviz'
_TEMPLATE_EXT = '.pvizt'
_PALETTE_EXT  = '.pvizp'
_SCHEME_EXT   = '.pvizc'
_PYTHON_EXT   = '.pvizx'   # Python bundle (zip of plot.py + data CSVs)


def _app_icon() -> QIcon:
    """Locate the app icon whether running from source or a frozen bundle.

    On Windows we prefer the .ico file; on macOS we use .icns.
    Falls back gracefully if neither is found.
    """
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)           # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent.parent.parent  # repo root

    assets = base / 'assets'

    # Prefer .ico on Windows, .icns on macOS/Linux
    candidates = (
        [assets / 'plotviz.ico', assets / 'plotviz.icns']
        if sys.platform == 'win32'
        else [assets / 'plotviz.icns', assets / 'plotviz.ico']
    )
    for p in candidates:
        if p.exists():
            return QIcon(str(p))
    return QIcon()


def _set_win_appusermodel_id() -> None:
    """Tell Windows to use 'plotviz' as the AppUserModelID.

    This ensures the taskbar groups all plotviz windows together and
    shows the correct icon instead of a generic Python/PyInstaller icon.
    Must be called before the first window is shown.
    """
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('com.pviz.app.plotviz')
    except Exception:
        pass


class PlotVizQApplication(QApplication):
    """QApplication subclass that handles macOS QFileOpenEvent.

    When the user double-clicks a .pviz or .pvizt file in Finder while the
    app is already running, macOS sends a QFileOpenEvent rather than spawning
    a new process.  We forward it to the main window.
    """

    def __init__(self, argv):
        super().__init__(argv)
        self._window: PlotVizApp | None = None

    def set_window(self, window: PlotVizApp) -> None:
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
            elif fp.endswith(_SCHEME_EXT):
                self._window._load_color_scheme_from_path(fp)
            elif fp.endswith(_PYTHON_EXT):
                self._window._open_pvizx_in_code_runner(fp)
            return True
        return super().event(e)


def main():
    _set_win_appusermodel_id()   # must be before QApplication on Windows

    # ── Logging ───────────────────────────────────────────────────────────────
    import logging
    from pathlib import Path
    try:
        from platformdirs import user_config_dir
        _log_dir = Path(user_config_dir('plotviz'))
    except ImportError:
        _log_dir = Path.home() / '.config' / 'plotviz'
    _log_dir.mkdir(parents=True, exist_ok=True)
    _log_file = _log_dir / 'plotviz.log'
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s  %(levelname)-8s  %(name)s  %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            # 'w' truncates on each restart — fresh log every run
            logging.FileHandler(_log_file, mode='w', encoding='utf-8'),
            logging.StreamHandler(),          # also echoes to console/terminal
        ],
        force=True,
    )
    log = logging.getLogger('plotviz')
    log.info('plotviz starting — log: %s', _log_file)
    # ─────────────────────────────────────────────────────────────────────────

    app = PlotVizQApplication(sys.argv)
    app.setApplicationName('plotviz')
    app.setApplicationDisplayName('plotviz')
    app.setOrganizationName('plotviz')
    app.setOrganizationDomain('com.pviz.app')
    app.setStyle('Fusion')
    icon = _app_icon()
    app.setWindowIcon(icon)

    window = PlotVizApp()
    window.setWindowIcon(icon)   # drives the taskbar button on Windows
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
        if arg.endswith(_SCHEME_EXT) and Path(arg).is_file():
            window._load_color_scheme_from_path(arg)
            break
        if arg.endswith(_PYTHON_EXT) and Path(arg).is_file():
            window._open_pvizx_in_code_runner(arg)
            break

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
