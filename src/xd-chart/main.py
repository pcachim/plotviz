"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.
"""
#!/usr/bin/env python3
"""
main.py — xd-chart entry point (dev + PyInstaller bundle).

Run from source:
    cd ~/xd-chart && uv run python src/xd-chart/main.py
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
        '~/Library/Application Support/xd-chart/matplotlib'
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
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from ui.main_window import ChartStudioApp


def _app_icon() -> QIcon:
    """Locate assets/xd-chart.icns whether running from source or frozen bundle."""
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)           # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent.parent.parent  # repo root (~/xd-chart/)
    icon_path = base / 'assets' / 'xd-chart.icns'
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('xd-chart')
    app.setApplicationDisplayName('xd-chart')
    app.setOrganizationName('xd-chart')
    app.setOrganizationDomain('com.xdchart.app')
    app.setStyle('Fusion')
    app.setWindowIcon(_app_icon())
    window = ChartStudioApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
