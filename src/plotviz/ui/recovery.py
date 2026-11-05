"""
Copyright (c) 2026 Paulo Cachim
ui/recovery.py  –  plotviz

RecoveryMixin: an automatic copy of the chart while it has unsaved changes, and the offer to
restore it when plotviz did not close properly (a crash, a power cut, the process killed).
The copy is never the user's file: it lives in the settings folder and is removed when the
chart is saved or the program is closed normally.
"""
import logging
import os
import time

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

import config.recovery as recovery
from core.serialize import encode_datasets, write_project_zip
from ui.mixin_base import MixinBase


class RecoveryMixin(MixinBase):
    def _start_recovery_timer(self):
        self._autosaved_epoch = -1
        self._recovery_timer = QTimer(self)
        self._recovery_timer.setInterval(recovery.INTERVAL_S * 1000)
        self._recovery_timer.timeout.connect(self._recovery_tick)
        self._recovery_timer.start()

    def _recovery_tick(self):
        """Every interval: copy the chart if it changed since the last copy; drop the copy once it is saved."""
        if getattr(self, '_applying_settings', False):
            return
        try:
            if not self._is_dirty:
                if recovery.has_copy():
                    recovery.remove()
                self._autosaved_epoch = -1
            elif self._autosaved_epoch != self.__dict__.get('_dirty_epoch', 0) or not recovery.has_copy():
                self._write_recovery_copy()
            else:
                recovery.touch()
        except Exception:  # noqa: BLE001 - the safety net must never get in the way of the work
            logging.getLogger('plotviz').warning('automatic copy failed', exc_info=True)

    def _write_recovery_copy(self):
        """Write the chart, with all its columns, to this session's recovery file."""
        settings = self._collect_settings()
        settings['_file_type'] = 'project'
        settings['annotations'] = self._collect_annotations_meta()
        settings['data_sources'] = dict(self.dataset_sources)
        series_meta = self._collect_series_meta()
        image_paths = [a.get('filepath', '') for a in self.canvas.annotations if a['type'] == 'image']
        target = recovery.chart_path()
        tmp = str(target) + '.tmp'
        try:
            write_project_zip(tmp, settings, series_meta, encode_datasets(dict(self.datasets)),
                              palette_json=self._active_palette_json(), image_paths=image_paths)
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        recovery.write_meta(getattr(self, '_current_filepath', None) or '')
        self._autosaved_epoch = self.__dict__.get('_dirty_epoch', 0)

    def _discard_recovery_copy(self):
        """The chart was saved or the program is closing normally: the copy is not needed."""
        try:
            recovery.remove()
        except Exception:  # noqa: BLE001
            logging.getLogger('plotviz').debug('ignored exception', exc_info=True)

    def _offer_recovery(self):
        """At start-up: if an earlier plotviz left a copy behind, offer to restore the latest."""
        try:
            left = recovery.orphans()
        except OSError:
            return
        if not left:
            return
        newest = left[0]
        when = time.strftime('%d %b %Y, %H:%M', time.localtime(newest['saved_at']))
        name = os.path.basename(newest['original']) if newest['original'] else 'a new chart'
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle('Recover chart')
        box.setText('plotviz did not close properly last time.')
        box.setInformativeText(f'A copy of {name} was saved automatically on {when}, with changes that were '
                               'not saved to the file.\n\nRestore it?')
        restore = box.addButton('Restore', QMessageBox.ButtonRole.AcceptRole)
        box.addButton('Discard', QMessageBox.ButtonRole.DestructiveRole)
        box.setDefaultButton(restore)
        box.exec()
        if box.clickedButton() is restore:
            try:
                self._load_project_inner(newest['file'], silent=True)
            except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
                QMessageBox.warning(self, 'Recover chart', f'The copy could not be restored:\n{e}')
                return                                         # it stays for the next start
            original = newest['original']
            self._current_filepath = original if original and os.path.isfile(original) else None
            self._update_window_title()
            self._is_dirty = True                              # it differs from the file: Save writes it
            self.statusBar().showMessage(f'Restored the chart saved automatically on {when}', 8000)
        for item in left:
            recovery.remove(item['pid'])
