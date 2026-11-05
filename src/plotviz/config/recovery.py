"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.

config/recovery.py  –  plotviz
Where the automatic copy of the open chart is kept, and which copies were left behind by a
plotviz that did not close properly.  The folder is `recovery/` in the settings folder; each
running plotviz has its own pair of files, `chart-<pid>.pviz` and `chart-<pid>.json`.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import config.settings as _settings

INTERVAL_S = 90                      # how often the copy is made (only when the chart changed)
STALE_AFTER_S = 4 * INTERVAL_S       # a copy not refreshed for this long belongs to a plotviz that is gone


def recovery_dir() -> Path:
    path = _settings._CFG_DIR / 'recovery'
    path.mkdir(parents=True, exist_ok=True)
    return path


def chart_path(pid: int | None = None) -> Path:
    return recovery_dir() / f'chart-{os.getpid() if pid is None else pid}.pviz'


def meta_path(pid: int | None = None) -> Path:
    return chart_path(pid).with_suffix('.json')


def write_meta(original: str, pid: int | None = None) -> None:
    """Note whose copy this is, when it was made and that its plotviz is alive."""
    data = {'pid': os.getpid() if pid is None else pid, 'original': original or '', 'saved_at': time.time(),
            'heartbeat': time.time()}
    meta_path(pid).write_text(json.dumps(data), encoding='utf-8')


def touch() -> None:
    """The plotviz that owns the copy is still running."""
    path = meta_path()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        data['heartbeat'] = time.time()
        path.write_text(json.dumps(data), encoding='utf-8')
    except (OSError, ValueError):
        logging.getLogger('plotviz').debug('ignored exception', exc_info=True)


def remove(pid: int | None = None) -> None:
    for path in (chart_path(pid), meta_path(pid)):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            logging.getLogger('plotviz').debug('ignored exception', exc_info=True)


def has_copy() -> bool:
    return chart_path().exists()


def _process_exists(pid: int) -> bool:
    if os.name == 'nt':
        import ctypes
        kernel = getattr(ctypes, 'windll').kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
        if handle:
            kernel.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def orphans() -> list[dict]:
    """The copies of plotviz sessions that are over, newest first: dicts with the keys
    pid, original, saved_at and file.  A copy whose plotviz still runs (another window) is not one."""
    found = []
    now = time.time()
    for meta in recovery_dir().glob('chart-*.json'):
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
            pid = int(data['pid'])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        file = meta.with_suffix('.pviz')
        if not file.exists():
            meta.unlink(missing_ok=True)
            continue
        alive = pid == os.getpid() or (_process_exists(pid) and now - float(data.get('heartbeat', 0)) < STALE_AFTER_S)
        if alive:
            continue
        found.append({'pid': pid, 'original': data.get('original', ''), 'saved_at': float(data.get('saved_at', 0)),
                      'file': str(file)})
    return sorted(found, key=lambda d: d['saved_at'], reverse=True)
