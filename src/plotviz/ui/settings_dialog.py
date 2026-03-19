"""
Copyright (c) 2026 Paulo Cachim
ui/settings_dialog.py  –  plotviz
AppSettingsDialog: app-level settings (paths, defaults, UI options).
"""
class AppSettingsDialog:
    """App-level settings dialog: paths, defaults, UI options.
    Instantiated via AppSettingsDialog.run(parent)."""

    @staticmethod
    def run(parent):
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                     QDialogButtonBox, QPushButton, QGroupBox,
                                     QFormLayout, QLineEdit, QCheckBox, QSpinBox,
                                     QFrame)
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        import config.settings as _cfg
        from config._version import __version__

        dlg = QDialog(self)
        dlg.setWindowTitle('Settings')
        dlg.setMinimumWidth(520)
        lay = QVBoxLayout(dlg); lay.setSpacing(12)

        # ── Config paths ─────────────────────────────────────────────────────
        grp_paths = QGroupBox('Configuration files')
        paths_form = QFormLayout(grp_paths); paths_form.setSpacing(6)

        def _path_row(label, path_str):
            row = QHBoxLayout(); row.setSpacing(4)
            le = QLineEdit(path_str); le.setReadOnly(True)
            le.setToolTip(path_str)
            btn = QPushButton('📂'); btn.setFixedWidth(32)
            btn.setToolTip('Open containing folder')
            import os as _os
            folder = _os.path.dirname(path_str)
            btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(folder)))
            row.addWidget(le, 1); row.addWidget(btn)
            paths_form.addRow(label, row)

        _path_row('Settings file:', str(_cfg.CFG_FILE))
        _path_row('Config folder:', str(_cfg.CFG_FILE.parent))

        lay.addWidget(grp_paths)

        # ── UI defaults ──────────────────────────────────────────────────────
        grp_ui = QGroupBox('Defaults')
        ui_form = QFormLayout(grp_ui); ui_form.setSpacing(6)

        chk_toolbar = QCheckBox()
        chk_toolbar.setChecked(_cfg.get('show_toolbar', True))
        chk_toolbar.setToolTip('Show the navigation toolbar below the chart canvas')
        ui_form.addRow('Show navigation toolbar:', chk_toolbar)

        max_recent_spin = QSpinBox(); max_recent_spin.setRange(1, 30)
        max_recent_spin.setValue(_cfg.MAX_RECENT)
        max_recent_spin.setFixedWidth(60)
        ui_form.addRow('Max recent files:', max_recent_spin)

        lay.addWidget(grp_ui)

        # ── Maintenance ──────────────────────────────────────────────────────
        grp_maint = QGroupBox('Maintenance')
        maint_lay = QVBoxLayout(grp_maint); maint_lay.setSpacing(6)

        recent_row = QHBoxLayout()
        lbl_recent = QLabel(f'{len(_cfg.get_recent_files())} recent file(s) stored')
        btn_clear_recent = QPushButton('Clear recent files')
        def _clear_recent():
            _cfg.set('recent_files', [])
            lbl_recent.setText('0 recent file(s) stored')
            if hasattr(self, '_rebuild_recent_files_ui'):
                self._rebuild_recent_files_ui()
        btn_clear_recent.clicked.connect(_clear_recent)
        recent_row.addWidget(lbl_recent); recent_row.addStretch(); recent_row.addWidget(btn_clear_recent)
        maint_lay.addLayout(recent_row)

        btn_reset_settings = QPushButton('Reset all settings to defaults…')
        btn_reset_settings.setToolTip('Resets settings.json to factory defaults (does not affect chart data)')
        def _reset_settings():
            from PyQt6.QtWidgets import QMessageBox
            if QMessageBox.question(dlg, 'Reset settings',
                'Reset all app settings to defaults?\nThis cannot be undone.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                _cfg.save(_cfg.DEFAULTS.copy())
                _cfg.settings.update(_cfg.DEFAULTS.copy())
                QMessageBox.information(dlg, 'Done', 'Settings reset. Some changes take effect on next launch.')
        btn_reset_settings.clicked.connect(_reset_settings)
        maint_lay.addWidget(btn_reset_settings)

        lay.addWidget(grp_maint)

        # ── Buttons ──────────────────────────────────────────────────────────
        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(dlg.accept)
        bbox.rejected.connect(dlg.reject)
        lay.addWidget(bbox)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        # Apply changes
        _cfg.set('show_toolbar', chk_toolbar.isChecked())
        if hasattr(self, 'canvas') and hasattr(self.canvas, 'toolbar'):
            tb = self.canvas.toolbar
            if tb:
                tb.setVisible(chk_toolbar.isChecked())
        _cfg.MAX_RECENT = max_recent_spin.value()

