"""Shared test bootstrap.

Puts ``src/plotviz`` on sys.path and stubs the PyQt6 modules that the pure
generator code imports at module scope, so the generator can be imported and
tested without a Qt installation (and without a display).

Import this module FIRST in every test module and load the pure module via the
file-path loader (this bypasses ``ui/__init__.py``, which imports the full Qt
main window)::

    import _bootstrap  # noqa: F401
    pe = _bootstrap.python_export()
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src", "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _stub_pyqt6() -> None:
    """Insert minimal PyQt6 stubs so pure modules import without Qt.

    No-op when a real PyQt6 is installed — so the GUI smoke tests can use the
    real toolkit in the same test process (CI), while the pure tests still run
    without Qt locally.
    """
    if "PyQt6.QtWidgets" in sys.modules:
        return
    import importlib.util
    if importlib.util.find_spec("PyQt6") is not None:
        return  # real PyQt6 available — don't shadow it

    class _Dummy:  # stands in for QFileDialog / QMessageBox (never instantiated in tests)
        pass

    pyqt6 = types.ModuleType("PyQt6")
    qtw = types.ModuleType("PyQt6.QtWidgets")
    qtw.QFileDialog = _Dummy
    qtw.QMessageBox = _Dummy
    pyqt6.QtWidgets = qtw
    sys.modules["PyQt6"] = pyqt6
    sys.modules["PyQt6.QtWidgets"] = qtw


_stub_pyqt6()


def load_module(relpath: str, modname: str):
    """Load a source file under ``src/plotviz`` directly as *modname*.

    Bypasses package ``__init__`` files so a single pure module can be imported
    without dragging in Qt-heavy siblings.
    """
    if modname in sys.modules:
        return sys.modules[modname]
    path = os.path.join(_SRC, relpath)
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


def script_gen():
    """Return the pure core.script_gen module.

    It is Qt-free, so it imports as a normal package without the file-path
    trick — but we still go through the loader for a stable handle.
    """
    return load_module("core/script_gen.py", "core.script_gen")


def python_export():
    """Return the Qt-adapter ui.python_export module (loaded standalone)."""
    return load_module("ui/python_export.py", "plotviz_test_python_export")
