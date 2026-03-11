"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.

config/settings.py  –  plotviz
Persistent user preferences stored in the platform config directory:
  macOS   ~/Library/Application Support/plotviz/settings.json
  Linux   ~/.config/plotviz/settings.json
  Windows %APPDATA%\\plotviz\\settings.json

All reads and writes go through get() / set() / save().
The module-level `settings` dict is the live in-memory state.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

try:
    from platformdirs import user_config_dir
    _CFG_DIR = Path(user_config_dir('plotviz'))
except ImportError:
    # Fallback if platformdirs is not installed yet (first run before pip)
    _CFG_DIR = Path.home() / '.config' / 'plotviz'

CFG_FILE = _CFG_DIR / 'settings.json'

# Maximum number of recent files to track
MAX_RECENT = 12

DEFAULTS: dict = {
    # UI appearance
    'theme':            'System',   # 'System' | 'Light' | 'Dark'

    # Active colour palette name
    'color_palette':    'Matplotlib',

    # Last directory used in any open / save dialog
    'last_dir':         str(Path.home() / 'Documents')
                        if (Path.home() / 'Documents').is_dir()
                        else str(Path.home()),

    # Recently opened .pviz files  (newest first)
    'recent_files':     [],

    # Window geometry  [x, y, width, height]
    'window_geometry':  [100, 100, 1400, 900],

    # Whether the window was maximised on last close
    'window_maximised': False,

    # Default export format shown in the Export row
    'export_format':    'PNG',

    # Default export DPI
    'export_dpi':       300,

    # Whether to show the navigator toolbar below the canvas
    'show_toolbar':     True,

    # Active subplot-sharing defaults (user can still change per chart)
    'default_sharex':   False,
    'default_sharey':   False,

    # Figure size preset remembered across sessions
    'fig_preset':       'Custom',

    # Custom palettes the user has created (name → list-of-hex)
    'custom_palettes':  {},
}


def _ensure_dir() -> None:
    _CFG_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    """Read settings.json, merge with DEFAULTS, return the result."""
    _ensure_dir()
    if CFG_FILE.exists():
        try:
            stored = json.loads(CFG_FILE.read_text(encoding='utf-8'))
            return {**DEFAULTS, **stored}
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULTS.copy()


def save(data: dict) -> None:
    """Atomically write *data* to settings.json (temp-file + rename)."""
    _ensure_dir()
    try:
        fd, tmp_path = tempfile.mkstemp(dir=_CFG_DIR, suffix='.tmp', text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        Path(tmp_path).replace(CFG_FILE)
    except OSError:
        pass  # Never crash the app over a settings write failure


# ── Live in-memory state ──────────────────────────────────────────────────────
settings: dict = load()


_MISSING = object()


def get(key: str, default=_MISSING):
    """Return the current value for *key*, falling back to DEFAULTS then *default*."""
    if key in settings:
        return settings[key]
    if key in DEFAULTS:
        return DEFAULTS[key]
    return None if default is _MISSING else default


def set(key: str, value) -> None:
    """Update *key* in the live settings dict and flush to disk."""
    settings[key] = value
    save(settings)


# ── Helpers used by the rest of the application ───────────────────────────────

def get_last_dir() -> str:
    """Return the directory to open the next file dialog in."""
    d = get('last_dir')
    if d and os.path.isdir(d):
        return d
    # Fallback chain
    docs = str(Path.home() / 'Documents')
    if os.path.isdir(docs):
        return docs
    return str(Path.home())


def remember_dir(filepath: str) -> None:
    """Call after any successful open/save to persist the directory."""
    if filepath:
        set('last_dir', os.path.dirname(os.path.abspath(filepath)))


def add_recent_file(filepath: str) -> None:
    """Prepend *filepath* to the recent-files list, capping at MAX_RECENT."""
    if not filepath:
        return
    fp = os.path.abspath(filepath)
    recent: list = list(get('recent_files'))
    # Remove stale entry (if already present) then prepend
    recent = [r for r in recent if r != fp]
    recent.insert(0, fp)
    set('recent_files', recent[:MAX_RECENT])


def get_recent_files() -> list[str]:
    """Return recent files that still exist on disk."""
    return [r for r in get('recent_files') if os.path.isfile(r)]


def prune_recent_files() -> None:
    """Remove entries that no longer exist from the recent-files list."""
    set('recent_files', get_recent_files())
