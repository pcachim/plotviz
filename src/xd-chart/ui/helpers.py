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


def _get_dir() -> str:
    """Return the directory for the next open/save dialog."""
    return _s.get_last_dir()


def _remember_dir(filepath: str) -> None:
    """Call after a successful open/save to persist the directory."""
    _s.remember_dir(filepath)


# Legacy alias kept for any call sites that still use the old name
def _default_dir() -> str:
    return _get_dir()


def _show_color_dialog(initial=None, parent=None, palette_colors=None):
    """Open QColorDialog with current palette pre-loaded into the custom colour slots.

    Uses DontUseNativeDialog so the custom-colour grid is always visible (the
    macOS native picker ignores setCustomColor entirely).
    Returns a QColor — invalid if the user cancelled.
    """
    from PyQt6.QtGui import QColor
    from PyQt6.QtWidgets import QColorDialog

    if palette_colors:
        for i, hex_col in enumerate(palette_colors[:16]):
            QColorDialog.setCustomColor(i, QColor(hex_col))

    dlg = QColorDialog(initial if initial else QColor('#000000'), parent)
    dlg.setWindowTitle('Choose Colour')
    dlg.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
    if dlg.exec():
        return dlg.currentColor()
    return QColor()
