"""pytest entry point — ensures the bootstrap (sys.path + PyQt6 stubs) runs
before any test module is imported. unittest users get the same setup because
each test module imports ``_bootstrap`` directly.

It also points the settings of plotviz at a temporary folder for the whole run. The tests
open and save charts, and every file the app opens or saves goes into the *recent files*
of its settings (and changes the last folder used): without this, running the tests
overwrote the real list of recent files of whoever ran them.
"""
import copy
import tempfile
from pathlib import Path

import _bootstrap  # noqa: F401

import config.settings as _settings

_folder = Path(tempfile.mkdtemp(prefix="plotviz-tests-"))
_settings._CFG_DIR = _folder
_settings.CFG_FILE = _folder / "settings.json"
_settings.settings.clear()
_settings.settings.update(copy.deepcopy(_settings.DEFAULTS))
