"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/collapsible.py  –  plotviz
CollapsibleSection: a titled block of controls that folds away under a clickable header.
Whether each section is open is remembered across sessions in settings.json.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel

import config.settings as settings

_SETTINGS_KEY = 'section_open'


class CollapsibleSection(QWidget):
    """Header (arrow, title, one-line summary while closed) above a body of controls.

    Add controls to `body_layout`. `key` names the section in settings.json;
    `expanded` is the state used until the user has toggled it once.
    `summary` is an optional callable returning the text shown while closed.
    """

    def __init__(self, title, key, expanded=True, summary=None, parent=None):
        super().__init__(parent)
        self._key = key
        self._summary = summary
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)

        head = QHBoxLayout()
        head.setSpacing(4)
        self._toggle = QToolButton()
        self._toggle.setText(title.upper().replace('&', '&&'))   # &&: a literal & in Qt button text
        self._toggle.setCheckable(True)
        self._toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle.setStyleSheet(
            'QToolButton { border: none; font-weight: bold; color: #888; font-size: 10px; }')
        self._toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        head.addWidget(self._toggle)
        self._summary_lbl = QLabel()
        self._summary_lbl.setStyleSheet('color:#999; font-size:10px;')
        head.addWidget(self._summary_lbl, 1)
        outer.addLayout(head)

        self._body = QWidget()
        self.body_layout = QVBoxLayout(self._body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(4)
        outer.addWidget(self._body)

        stored = settings.get(_SETTINGS_KEY, {}) or {}
        self._toggle.setChecked(bool(stored.get(key, expanded)))
        self._set_open(self._toggle.isChecked(), save=False)
        self._toggle.toggled.connect(self._set_open)   # after the initial state: not a user choice

    def is_open(self):
        return self._toggle.isChecked()

    def refresh_summary(self):
        """Re-read the summary text; shown only while the section is closed."""
        text = ''
        if self._summary is not None and not self.is_open():
            try:
                text = self._summary()
            except Exception:
                text = ''
        self._summary_lbl.setText(text)

    def _set_open(self, is_open, save=True):
        self._toggle.setArrowType(
            Qt.ArrowType.DownArrow if is_open else Qt.ArrowType.RightArrow)
        self._body.setVisible(is_open)
        self.refresh_summary()
        if save:
            stored = dict(settings.get(_SETTINGS_KEY, {}) or {})
            stored[self._key] = is_open
            settings.set(_SETTINGS_KEY, stored)
