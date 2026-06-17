"""
Copyright (c) 2026 Paulo Cachim
ui/data_io.py  –  plotviz

DataMixin: dataset import/management, the app-settings dialog, recent files,
undo/redo snapshots, and series-table data plumbing. Split out of main_window;
mixed into PlotVizApp so its methods share the datasets, series table and
widgets via `self`.
"""
import os
import sys
import csv
import json

import config.settings as settings
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMessageBox, QComboBox, QGroupBox, QPushButton, QFormLayout,
    QDialogButtonBox, QDialog, QTableWidgetItem, QSpinBox, QVBoxLayout,
    QHBoxLayout, QLineEdit, QLabel, QFileDialog, QCheckBox, QApplication,
    QWidget,
)
from ui.helpers import _get_dir, _remember_dir
from ui.dialogs import DataImportDialog
from ui.tab_builders import PLOT_MODE_GROUPS, PER_SERIES_TYPES


class DataMixin:
    def _open_app_settings_dialog(self):
        """App-level settings dialog: paths, defaults, UI options."""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        import config.settings as _cfg
        from config._version import __version__

        dlg = QDialog(self)
        dlg.setWindowTitle('Preferences' if sys.platform == 'darwin' else 'Settings')
        dlg.setMinimumWidth(520)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(12)

        # ── Config paths ─────────────────────────────────────────────────────
        grp_paths = QGroupBox('Configuration files')
        paths_form = QFormLayout(grp_paths)
        paths_form.setSpacing(6)

        def _path_row(label, path_str):
            row = QHBoxLayout()
            row.setSpacing(4)
            le = QLineEdit(path_str)
            le.setReadOnly(True)
            le.setToolTip(path_str)
            btn = QPushButton('📂')
            btn.setFixedWidth(32)
            btn.setToolTip('Open containing folder')
            import os as _os
            folder = _os.path.dirname(path_str)
            btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(folder)))
            row.addWidget(le, 1)
            row.addWidget(btn)
            paths_form.addRow(label, row)

        _path_row('Settings file:', str(_cfg.CFG_FILE))
        _path_row('Config folder:', str(_cfg.CFG_FILE.parent))

        lay.addWidget(grp_paths)

        # ── Appearance ───────────────────────────────────────────────────────
        grp_appearance = QGroupBox('Appearance')
        appearance_form = QFormLayout(grp_appearance)
        appearance_form.setSpacing(6)

        from PyQt6.QtWidgets import QComboBox as _QComboBox
        appearance_combo = _QComboBox()
        appearance_combo.addItems(['System', 'Light', 'Dark'])
        current_theme = _cfg.get('theme') or 'System'
        idx = appearance_combo.findText(current_theme)
        if idx >= 0:
            appearance_combo.setCurrentIndex(idx)
        appearance_combo.setToolTip('Application colour scheme (takes effect immediately)')
        appearance_combo.currentTextChanged.connect(self._apply_colour_scheme)
        appearance_form.addRow('Colour scheme:', appearance_combo)

        lay.addWidget(grp_appearance)

        # ── UI defaults ──────────────────────────────────────────────────────
        grp_ui = QGroupBox('Defaults')
        ui_form = QFormLayout(grp_ui)
        ui_form.setSpacing(6)

        chk_toolbar = QCheckBox()
        chk_toolbar.setChecked(_cfg.get('show_toolbar', True))
        chk_toolbar.setToolTip('Show the navigation toolbar below the chart canvas')
        ui_form.addRow('Show navigation toolbar:', chk_toolbar)

        max_recent_spin = QSpinBox()
        max_recent_spin.setRange(1, 30)
        max_recent_spin.setValue(_cfg.MAX_RECENT)
        max_recent_spin.setFixedWidth(60)
        ui_form.addRow('Max recent files:', max_recent_spin)

        lay.addWidget(grp_ui)

        # ── Maintenance ──────────────────────────────────────────────────────
        grp_maint = QGroupBox('Maintenance')
        maint_lay = QVBoxLayout(grp_maint)
        maint_lay.setSpacing(6)

        recent_row = QHBoxLayout()
        lbl_recent = QLabel(f'{len(_cfg.get_recent_files())} recent file(s) stored')
        btn_clear_recent = QPushButton('Clear recent files')
        def _clear_recent():
            _cfg.set('recent_files', [])
            lbl_recent.setText('0 recent file(s) stored')
            if hasattr(self, '_rebuild_recent_files_ui'):
                self._rebuild_recent_files_ui()
        btn_clear_recent.clicked.connect(_clear_recent)
        recent_row.addWidget(lbl_recent)
        recent_row.addStretch()
        recent_row.addWidget(btn_clear_recent)
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

        _original_theme = current_theme  # snapshot before dialog opens

        if dlg.exec() != QDialog.DialogCode.Accepted:
            # Revert any live appearance change the user previewed then cancelled
            if appearance_combo.currentText() != _original_theme:
                self._apply_colour_scheme(_original_theme)
            return

        # Apply changes
        chosen_theme = appearance_combo.currentText()
        if hasattr(self, 'colour_scheme_combo'):
            idx2 = self.colour_scheme_combo.findText(chosen_theme)
            if idx2 >= 0:
                self.colour_scheme_combo.blockSignals(True)
                self.colour_scheme_combo.setCurrentIndex(idx2)
                self.colour_scheme_combo.blockSignals(False)
        self._apply_colour_scheme(chosen_theme)

        _cfg.set('show_toolbar', chk_toolbar.isChecked())
        if hasattr(self, 'canvas') and hasattr(self.canvas, 'toolbar'):
            tb = self.canvas.toolbar
            if tb:
                tb.setVisible(chk_toolbar.isChecked())
        _cfg.MAX_RECENT = max_recent_spin.value()

    def _show_about(self):
        """Display the About dialog."""
        from config._version import __version__
        dlg = QMessageBox(self)
        dlg.setWindowTitle('About plotviz')
        dlg.setText(
            f'<h2>plotviz&nbsp;{__version__}</h2>'
            '<p>Publication-quality chart generator.</p>'
            '<p>Copyright &copy; 2026 Paulo Cachim<br>'
            'Licensed under the <a href="https://opensource.org/licenses/MIT">MIT License</a>.</p>'
        )
        dlg.setIconPixmap(QApplication.windowIcon().pixmap(64, 64))
        dlg.exec()

    # ── Undo / Redo ─────────────────────────────────────────────────────────────
    def _snapshot(self):
        """Capture current full state for undo.  Called by update_preview."""
        if not hasattr(self, '_undo_suspended') or self._undo_suspended:
            return
        if not hasattr(self, '_collect_settings') or not hasattr(self, 'datasets'):
            return
        if not hasattr(self, '_undo_stack'):
            return
        import copy
        snap = (
            self._collect_settings(),
            self._collect_series_meta(),
            copy.deepcopy(self.datasets),
        )
        # Avoid duplicate consecutive snapshots
        if self._undo_stack and self._undo_stack[-1][0] == snap[0]                 and self._undo_stack[-1][1] == snap[1]:
            return
        self._undo_stack.append(snap)
        if len(self._undo_stack) > self._MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._update_undo_buttons()

    def _restore_snapshot(self, snap):
        """Apply a (settings, series_meta, datasets) snapshot without pushing to undo."""
        import copy
        self._undo_suspended = True
        self._applying_settings = True
        try:
            settings_d, series_d, datasets_d = snap
            self.datasets = copy.deepcopy(datasets_d)
            self.update_lists(keep_selections=False)
            self._apply_settings(settings_d)
            self._apply_series_meta(series_d)
        finally:
            self._applying_settings = False
            self._undo_suspended = False
        self.update_preview()
        # Cancel any pending snapshot timer.  update_preview() just scheduled one,
        # but the restored state is already at the top of the undo stack — letting
        # the timer fire would push a near-duplicate snapshot and wipe the redo stack.
        if hasattr(self, '_snapshot_timer'):
            self._snapshot_timer.stop()
        self._update_undo_buttons()

    def _undo(self):
        if len(self._undo_stack) < 2:
            return
        # Current state is at top; pop it to redo, restore the one before it
        current = self._undo_stack.pop()
        self._redo_stack.append(current)
        self._restore_snapshot(self._undo_stack[-1])

    def _redo(self):
        if not self._redo_stack:
            return
        snap = self._redo_stack.pop()
        self._undo_stack.append(snap)
        self._restore_snapshot(snap)

    def _update_undo_buttons(self):
        if hasattr(self, '_btn_undo'):
            self._btn_undo.setEnabled(len(self._undo_stack) >= 2)
        if hasattr(self, '_btn_redo'):
            self._btn_redo.setEnabled(bool(self._redo_stack))

    def _default_settings(self) -> dict:
        """Return a settings dict matching widget construction defaults — used by New Plot."""
        def _ser(d): return {str(k): v for k, v in d.items()}
        s = {
            '_app': 'plotviz', '_version': '1.3',
            'chart_type':       'Line',
            'title_show':       True,  'title_text':  '',
            'title_font':       'sans-serif', 'title_size': 14, 'title_color': '#000000',
            'title_x':          0.5,   'title_y':     0.97,
            'sp_hspace':        0.35,  'sp_wspace':   0.35,
            'sp_titles':             _ser({0: ''}),
            'subplot_title_show':    _ser({0: True}),
            'subplot_title_font':    _ser({0: 'sans-serif'}),
            'subplot_title_size':    _ser({0: 11}),
            'subplot_title_color':   _ser({0: '#000000'}),
            'subplot_xlabels':       _ser({0: ''}),
            'subplot_xlabel_show':   _ser({0: True}),
            'subplot_ylabels':       _ser({0: ''}),
            'subplot_ylabel_show':   _ser({0: True}),
            'subplot_y2labels':      _ser({0: ''}),
            'subplot_y2label_show':  _ser({0: True}),
            'subplot_legends':       _ser({0: True}),
            'subplot_legend_locs':   _ser({0: 'best'}),
            'subplot_legend_x':      _ser({0: 0.01}),
            'subplot_legend_y':      _ser({0: 0.99}),
            'subplot_legend_fontsize': _ser({0: 9}),
            'subplot_legend_ncols':  _ser({0: 1}),
            'subplot_legend_frameon': _ser({0: True}),
            'subplot_legend_color':  _ser({0: '#000000'}),
            'subplot_legend_facecolor': _ser({0: '#ffffff'}),
            'subplot_legend_alpha':  _ser({0: 0.8}),
            'subplot_legend_edgecolor': _ser({0: '#cccccc'}),
            'subplot_xlims':         _ser({0: None}),
            'subplot_ylims':         _ser({0: None}),
            'subplot_y2lims':        _ser({0: None}),
            'subplot_xscales':       _ser({0: 'linear'}),
            'subplot_yscales':       _ser({0: 'linear'}),
            'subplot_xtick_sizes':   _ser({0: 9}),
            'subplot_ytick_sizes':   _ser({0: 9}),
            'subplot_xtick_dir':     _ser({0: 'out'}),
            'subplot_ytick_dir':     _ser({0: 'out'}),
            'subplot_xtick_minor':   _ser({0: False}),
            'subplot_ytick_minor':   _ser({0: False}),
            'subplot_xtick_rotation':_ser({0: 0}),
            'subplot_ytick_rotation':_ser({0: 0}),
            'subplot_xtick_step':    _ser({0: 0.0}),
            'subplot_ytick_step':    _ser({0: 0.0}),
            'subplot_x_formatter':   _ser({0: 'auto'}),
            'subplot_y_formatter':   _ser({0: 'auto'}),
            'subplot_xticks_show':   _ser({0: True}),
            'subplot_yticks_show':   _ser({0: True}),
            'subplot_ann_visible':   _ser({0: True}),
            'subplot_xaxis_pos':     _ser({0: 'bottom'}),
            'subplot_yaxis_pos':     _ser({0: 'left'}),
            'xlabel_font': 'sans-serif', 'xlabel_size': 11, 'xlabel_color': '#000000',
            'ylabel_font': 'sans-serif', 'ylabel_size': 11, 'ylabel_color': '#000000',
            'y2label_font':'sans-serif', 'y2label_size':11, 'y2label_color':'#000000',
            'color_palette':    'Matplotlib',
            'preset':           'Default',
            'chart_bg_color':   '#ffffff',
            'chart_fg_color':   '#000000',
            'plot_bg_color':    '#ffffff',
            'border_top':    True, 'border_bottom': True,
            'border_left':   True, 'border_right':  True,
            'curve_styles':     {},
            'fig_preset':    '20 × 15 cm',
            'fig_unit':      'cm',
            'fig_width':     20.0, 'fig_height': 15.0,
            'fig_left':      0.10, 'fig_right':  0.95,
            'fig_bottom':    0.10, 'fig_top':    0.95,
            'grid_on':        True,  'grid_color': '#cccccc',
            'grid_linestyle': '--',  'grid_linewidth': 0.5, 'grid_alpha': 0.4,
            'minor_grid_on':  False, 'minor_grid_color': '#e8e8e8',
            'minor_grid_linestyle': ':', 'minor_grid_linewidth': 0.3, 'minor_grid_alpha': 0.2,
            'dpi':           300,
            'fit_ci_index': 0, 'fit_pi_index': 0, 'fit_ci_alpha': 0.25,
            'fit_result':    None,
            'subplot_rows':  1,    'subplot_cols': 1,
            'subplot_mosaic':None, 'sp_sharex':    False, 'sp_sharey': False,
            'hist_bins':     20,   'hist_density':  False,
            'bar_width':     0.8,  'bar_stacked':   False, 'bar_horizontal': False,
            'scatter_size':  20,   'scatter_alpha': 0.8,
            'err_capsize':   4,    'cmap':          'viridis',
            'contour_levels':10,   'heat_colorbar': True,
            'contour_levels_explicit': '',
            'contour_line_color': '#000000', 'contour_line_width': 0.5,
            'heat_vminmax_enable': False, 'heat_vmin': 0.0, 'heat_vmax': 1.0,
            'pie_autopct':   True, 'pie_shadow':    False,
            'area_alpha':    0.4,  'area_stacked':  False,
            'violin_show_means':   True, 'violin_show_medians': True,
            'ann_fontcolor': '#000000', 'ann_fontsize': 10,
            'ann_font':      'sans-serif', 'ann_bgcolor': '#ffffcc',
            'ann_bg_alpha':  0.9,  'ann_edgecolor': '#aaaaaa',
            'line_default_style':  '-',    'line_default_marker': 'None',
            'line_default_lw':     1.5,    'line_default_markersize': 6,
        }
        return s

    def _reset_app(self):
        """Clear all data and start a new chart."""
        if getattr(self, '_is_dirty', False):
            mb = QMessageBox(self)
            mb.setWindowTitle('New Chart')
            mb.setText('You have unsaved changes.')
            mb.setInformativeText('Do you want to save before starting a new chart?')
            btn_save   = mb.addButton('Save',    QMessageBox.ButtonRole.AcceptRole)
            btn_discard = mb.addButton('Discard', QMessageBox.ButtonRole.DestructiveRole)
            mb.addButton('Cancel', QMessageBox.ButtonRole.RejectRole)
            mb.exec()
            clicked = mb.clickedButton()
            if clicked is btn_save:
                self._save_project()
            elif clicked is not btn_discard:
                return  # Cancel
        else:
            if QMessageBox.question(self, 'New Chart', 'Start a new chart?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                    ) != QMessageBox.StandardButton.Yes:
                return
        self._current_filepath = None
        self._update_window_title()
        self._is_dirty = False
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._update_undo_buttons()
        self.datasets.clear()
        self.curve_styles.clear()
        self.canvas.annotations.clear()
        self._last_fit = None
        self._fits = {}
        self._subplot_mosaic = None
        # Clear series table BEFORE _apply_settings triggers any redraws,
        # otherwise stale rows referencing cleared datasets cause a crash.
        self.series_table.setRowCount(0)
        self._refresh_curve_select()
        # Clear chart-type tracking so _apply_settings always initialises a
        # fresh Cartesian/Line state, regardless of what was loaded before.
        self.subplot_chart_types.clear()
        if hasattr(self, 'subplot_plot_modes'):
            self.subplot_plot_modes.clear()
        if hasattr(self, 'subplot_chart_opts'):
            self.subplot_chart_opts.clear()
        # Reset all UI widgets to fresh defaults via _apply_settings
        self._undo_suspended = True
        self._applying_settings = True
        try:
            self._apply_settings(self._default_settings())
        finally:
            self._applying_settings = False
            self._undo_suspended = False
        self.update_lists()
        self.on_subplot_layout_changed()
        self.update_preview()
        self.refresh_annotation_list()
        # Immediately push the blank-chart snapshot so the first user change
        # can always be undone (mirrors the direct _snapshot() call in _load_project_inner).
        if hasattr(self, '_snapshot'):
            self._snapshot()
        self._notify_sns_explorer()

    def load_data(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 'Load Files', _get_dir(), 'Data Files (*.csv *.xlsx *.xls *.json *.txt);;All (*)')
        if not files:
            return
        _remember_dir(files[0])
        for fp in files:
            try:
                dlg = DataImportDialog(fp, self)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    continue
                for name, arr in dlg.get_selected_data().items():
                    base, cnt = name, 1
                    while name in self.datasets:
                        name = f'{base}_{cnt}'
                        cnt += 1
                    self.datasets[name] = arr
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed: {fp}\n{e}')
        self.update_lists()
        if self.series_table.rowCount() == 0:
            self._add_series_row()
        self._notify_sns_explorer()


    def _remove_selected_datasets(self):
        """Remove datasets selected in the dataset list, then refresh."""
        selected = [item.text() for item in self.dataset_list.selectedItems()]
        if not selected:
            return
        for name in selected:
            self.datasets.pop(name, None)
        self.update_lists()
        self.update_preview()
        self._notify_sns_explorer()

    def update_lists(self, keep_selections=False):
        """Refresh dataset list, combo_z, combo_err, and series table combos."""
        cols = sorted(self.datasets)
        zp  = self.combo_z.currentText()
        ep = self.combo_err.currentText()
        fy2p = getattr(self, 'combo_fill_y2', None)
        fy2p = fy2p.currentText() if fy2p else '(none)'
        bymp = getattr(self, 'combo_bar_ymin', None)
        bymp = bymp.currentText() if bymp else '(none)'
        qup = getattr(self.quiver_u_combo,  'currentText', lambda: '(none)')()
        qvp = getattr(self.quiver_v_combo,  'currentText', lambda: '(none)')()
        bup = getattr(self.barbs_u_combo,   'currentText', lambda: '(none)')()
        bvp = getattr(self.barbs_v_combo,   'currentText', lambda: '(none)')()
        sup = getattr(self.stream_u_combo,  'currentText', lambda: '(none)')()
        svp = getattr(self.stream_v_combo,  'currentText', lambda: '(none)')()
        bsp = getattr(self.bubble_size_combo, 'currentText', lambda: '(uniform)')()

        self.dataset_list.clear()
        self.combo_x.clear()
        self.y_list.clear()
        self.combo_z.clear()
        self.combo_z.addItem('(none)')
        self.combo_err.clear()
        self.combo_err.addItem('(none)')
        if hasattr(self, 'combo_fill_y2'):
            self.combo_fill_y2.blockSignals(True)
            self.combo_fill_y2.clear()
            self.combo_fill_y2.addItem('(none)')
        if hasattr(self, 'combo_bar_ymin'):
            self.combo_bar_ymin.blockSignals(True)
            self.combo_bar_ymin.clear()
            self.combo_bar_ymin.addItem('(none)')

        for col in cols:
            self.dataset_list.addItem(col)
            self.combo_x.addItem(col)
            self.y_list.addItem(col)
            self.combo_z.addItem(col)
            self.combo_err.addItem(col)
            if hasattr(self, 'combo_fill_y2'):
                self.combo_fill_y2.addItem(col)
            if hasattr(self, 'combo_bar_ymin'):
                self.combo_bar_ymin.addItem(col)

        if hasattr(self, 'combo_fill_y2'):
            i = self.combo_fill_y2.findText(fy2p)
            self.combo_fill_y2.setCurrentIndex(i if i >= 0 else 0)
            self.combo_fill_y2.blockSignals(False)
        if hasattr(self, 'combo_bar_ymin'):
            i = self.combo_bar_ymin.findText(bymp)
            self.combo_bar_ymin.setCurrentIndex(i if i >= 0 else 0)
            self.combo_bar_ymin.blockSignals(False)

        for combo, prev in [(self.combo_z, zp), (self.combo_err, ep)]:
            i = combo.findText(prev)
            if i >= 0: combo.setCurrentIndex(i)

        # Refresh quiver/barbs/streamplot U/V and bubble size combos
        for combo, sentinel, prev in [
            (self.quiver_u_combo,    '(none)',    qup),
            (self.quiver_v_combo,    '(none)',    qvp),
            (self.barbs_u_combo,     '(none)',    bup),
            (self.barbs_v_combo,     '(none)',    bvp),
            (self.stream_u_combo,    '(none)',    sup),
            (self.stream_v_combo,    '(none)',    svp),
            (self.bubble_size_combo, '(uniform)', bsp),
            (self.err_xerr_combo, '(none)', getattr(self.err_xerr_combo, '_prev', '(none)')),
        ]:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(sentinel)
            combo.addItems(cols)
            i = combo.findText(prev)
            combo.setCurrentIndex(i if i >= 0 else 0)
            combo.blockSignals(False)

        # Refresh series table combos
        self._refresh_series_combos()
        self._refresh_curve_select()

        # Keep fn_source_combo and fxy combos in sync (Advanced tab)
        prev_fn = self.fn_source_combo.currentText()
        self.fn_source_combo.blockSignals(True)
        self.fn_source_combo.clear()
        self.fn_source_combo.addItems(cols)
        i_fn = self.fn_source_combo.findText(prev_fn)
        self.fn_source_combo.setCurrentIndex(i_fn if i_fn >= 0 else 0)
        self.fn_source_combo.blockSignals(False)
        for _fxy_attr, _fxy_prev in [
            ('fxy_x_combo', getattr(getattr(self, 'fxy_x_combo', None), 'currentText', lambda: '')()),
            ('fxy_y_combo', getattr(getattr(self, 'fxy_y_combo', None), 'currentText', lambda: '')()),
            ('fuv_x_combo', getattr(getattr(self, 'fuv_x_combo', None), 'currentText', lambda: '')()),
            ('fuv_y_combo', getattr(getattr(self, 'fuv_y_combo', None), 'currentText', lambda: '')()),
        ]:
            _cb = getattr(self, _fxy_attr, None)
            if _cb is None: continue
            _cb.blockSignals(True)
            _cb.clear()
            _cb.addItems(cols)
            _i = _cb.findText(_fxy_prev)
            _cb.setCurrentIndex(_i if _i >= 0 else 0)
            _cb.blockSignals(False)

        # Notify Seaborn Explorer if it is open
        self._notify_sns_explorer()

    def _refresh_series_combos(self):
        """Re-populate the X/Y QComboBox widgets in every series row and sync Plot spin ranges."""
        cols = sorted(self.datasets)
        n = max(1, self.subplot_rows * self.subplot_cols)
        self.series_table.blockSignals(True)
        for row in range(self.series_table.rowCount()):
            for col_idx in (0, 1):
                cb = self.series_table.cellWidget(row, col_idx)
                if cb is None:
                    cb = QComboBox()
                    handler = self._on_x_col_changed if col_idx == 0 else self.update_preview
                    cb.currentIndexChanged.connect(handler)
                    self.series_table.setCellWidget(row, col_idx, cb)
                prev = cb.currentText()
                cb.blockSignals(True)
                cb.clear()
                cb.addItems(cols)
                i = cb.findText(prev)
                cb.setCurrentIndex(i if i >= 0 else 0)
                cb.blockSignals(False)
            # Keep Plot spinbox range in sync
            spin = self.series_table.cellWidget(row, 4)
            if spin:
                spin.blockSignals(True)
                spin.setRange(1, n)
                spin.blockSignals(False)
        self.series_table.blockSignals(False)

    def _on_series_item_changed(self, item):
        """Handles itemChanged on the series table. Only acts when the row is
        fully constructed (all 6 cell widgets/items present) to avoid firing
        update_preview mid-insertion."""
        if item is None:
            return
        row = item.row()
        # A complete row has: cellWidget(0), cellWidget(1), item(2),
        # cellWidget(3), cellWidget(4), item(5)
        if (self.series_table.cellWidget(row, 0) is None or
                self.series_table.cellWidget(row, 1) is None or
                self.series_table.cellWidget(row, 3) is None or
                self.series_table.cellWidget(row, 4) is None or
                self.series_table.item(row, 5) is None):
            return
        # Only respond to label (col 2) and Y2 checkbox (col 5)
        if item.column() in (2, 5):
            # When label (col 2) is edited, rename the curve_styles key so
            # per-series style, color, opts etc. follow the new label.
            if item.column() == 2:
                new_label = item.text()
                # Find what the old label was — any curve_styles key that
                # isn't the new name and whose row still maps to this row.
                # Heuristic: scan curve_styles for a key that no other row
                # currently uses and rename it to new_label.
                current_labels = set()
                for r in range(self.series_table.rowCount()):
                    if r == row:
                        continue
                    it = self.series_table.item(r, 2)
                    current_labels.add(it.text() if it else f'Series {r+1}')
                # The old key is the one in curve_styles that is neither the
                # new label nor any other current row label.  Fallback: look
                # for the previous text stored by Qt before the edit — we do
                # this by finding any key that would be orphaned after rename.
                orphaned = [k for k in list(self.curve_styles)
                            if k not in current_labels and k != new_label]
                if len(orphaned) == 1:
                    old_label = orphaned[0]
                    self.curve_styles[new_label] = self.curve_styles.pop(old_label)
                elif new_label not in self.curve_styles:
                    # Try to inherit from a key with "Series N" pattern for this row
                    fallback_key = f'Series {row + 1}'
                    if fallback_key in self.curve_styles:
                        self.curve_styles[new_label] = self.curve_styles.pop(fallback_key)
            # When Y2 is checked for the first time, preserve the series color
            if item.column() == 5 and item.checkState() == Qt.CheckState.Checked:
                lbl_item = self.series_table.item(row, 2)
                label = lbl_item.text() if lbl_item else f'Series {row+1}'
                if label not in self.curve_styles:
                    # Copy current default color so it's preserved on y2 axis
                    self.curve_styles[label] = {
                        'color': getattr(self, 'curve_color', '#1f77b4'),
                        'linestyle': '-', 'marker': 'None',
                        'linewidth': 1.5, 'markersize': 6,
                        'marker_color': getattr(self, 'curve_color', '#1f77b4'),
                    }
            self._refresh_curve_select()
            self.update_preview()

    def _refresh_curve_select(self):
        """Sync the per-curve style combo with series labels on the active subplot.
        When multiple subplots exist, only series whose Plot spinbox matches the
        currently selected subplot in the Series tab are shown.
        """
        n = self.subplot_rows * self.subplot_cols
        active_sp = None
        if n > 1 and hasattr(self, 'series_curve_sp_active'):
            active_sp = self.series_curve_sp_active.currentIndex() + 1  # 1-based

        labels = []
        for row in range(self.series_table.rowCount()):
            if active_sp is not None:
                spin = self.series_table.cellWidget(row, 4)
                row_sp = spin.value() if spin else 1
                if row_sp != active_sp:
                    continue
            item = self.series_table.item(row, 2)
            labels.append(item.text() if item else f'Series {row+1}')

        self.curve_select.blockSignals(True)
        prev = self.curve_select.currentText()
        self.curve_select.clear()
        self.curve_select.addItems(labels)
        idx = self.curve_select.findText(prev)
        self.curve_select.setCurrentIndex(idx if idx >= 0 else 0)
        self.curve_select.blockSignals(False)
        self.load_curve_style()
        self._on_fit_series_changed()

    def _add_series_row(self):
        cols = sorted(self.datasets)
        row = self.series_table.rowCount()
        self.series_table.blockSignals(True)
        self.series_table.insertRow(row)

        # ── Determine sensible defaults (avoid duplicating row 0) ──────────────
        row0_x = ''
        row0_y = ''
        if row > 0:
            xcb0 = self.series_table.cellWidget(0, 0)
            ycb0 = self.series_table.cellWidget(0, 1)
            if xcb0: row0_x = xcb0.currentText()
            if ycb0: row0_y = ycb0.currentText()

        default_x_col = row0_x if (row0_x and row0_x in self.datasets) else (cols[0] if cols else '')

        row0_y_is_cat = self._is_categorical(self.datasets[row0_y]) if (row0_y and row0_y in self.datasets) else None
        default_y_col = ''
        # Pass 1: same type as row0-Y but different column
        for c in cols:
            if c == row0_y: continue
            if row0_y_is_cat is not None and self._is_categorical(self.datasets[c]) == row0_y_is_cat:
                default_y_col = c
                break
        # Pass 2: any column different from row0-Y
        if not default_y_col:
            for c in cols:
                if c != row0_y:
                    default_y_col = c
                    break
        if not default_y_col:
            default_y_col = row0_y or (cols[0] if cols else '')

        # ── Build all widgets with their signals BLOCKED, then setCellWidget ───
        # X combo
        cb_x = QComboBox()
        cb_x.blockSignals(True)
        cb_x.addItems(cols)
        idx_x = cb_x.findText(default_x_col)
        if idx_x >= 0: cb_x.setCurrentIndex(idx_x)
        cb_x.blockSignals(False)
        # Connect AFTER index is set so no spurious signal fires during construction
        cb_x.currentIndexChanged.connect(self._on_x_col_changed)
        self.series_table.setCellWidget(row, 0, cb_x)

        # Y combo
        cb_y = QComboBox()
        cb_y.blockSignals(True)
        cb_y.addItems(cols)
        idx_y = cb_y.findText(default_y_col)
        if idx_y >= 0: cb_y.setCurrentIndex(idx_y)
        cb_y.blockSignals(False)
        cb_y.currentIndexChanged.connect(self.update_preview)
        cb_y.currentIndexChanged.connect(lambda _: self._update_label_placeholders())
        self.series_table.setCellWidget(row, 1, cb_y)

        # Label — explicitly set editable flag so double-click editing works reliably
        _lbl_item = QTableWidgetItem(f'Series {row+1}')
        _lbl_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
        self.series_table.setItem(row, 2, _lbl_item)

        # Type combo — constrained to the current plot mode's allowed types
        allowed_types = list(PLOT_MODE_GROUPS.get(
            self.plot_mode_combo.currentText() if hasattr(self, 'plot_mode_combo') else 'Standard',
            PER_SERIES_TYPES
        ))
        type_cb = QComboBox()
        type_cb.addItems(allowed_types)
        if hasattr(self, 'chart_type_combo'):
            current_type = self.chart_type_combo.currentText()
            i = type_cb.findText(current_type)
            if i >= 0: type_cb.setCurrentIndex(i)
        type_cb.currentTextChanged.connect(self._on_series_row_type_changed)
        self.series_table.setCellWidget(row, 3, type_cb)

        # Plot spinbox — default to whichever subplot is active in the Subplots tab
        active_subplot = self.sp_active.currentIndex() + 1  # sp_active is 0-based, spinbox is 1-based
        plot_spin = QSpinBox()
        plot_spin.setRange(1, max(1, self.subplot_rows * self.subplot_cols))
        plot_spin.setValue(max(1, active_subplot))
        plot_spin.setMinimumWidth(36)
        plot_spin.valueChanged.connect(self.update_preview)
        plot_spin.valueChanged.connect(lambda _: self._filter_series_table_by_subplot())
        self.series_table.setCellWidget(row, 4, plot_spin)

        # Y2 checkbox item
        y2_item = QTableWidgetItem()
        y2_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        y2_item.setCheckState(Qt.CheckState.Unchecked)
        self.series_table.setItem(row, 5, y2_item)

        # Auto-assign a palette color to this series (stored in curve_styles)
        lbl = f'Series {row+1}'
        auto_color = self._palette_color(self._local_palette_index(row))
        existing = self.curve_styles.get(lbl, {})
        if not existing.get('color_locked', False):
            existing.setdefault('color', auto_color)
            existing.setdefault('marker_color', auto_color)
            self.curve_styles[lbl] = existing

        self.series_table.blockSignals(False)
        self._refresh_curve_select()
        self._filter_series_table_by_subplot()
        self.update_preview()

    def _on_x_col_changed(self):
        """Called when any X column combo changes. Captures sender immediately
        (self.sender() is only valid synchronously), then defers all logic via
        QTimer so the combo is off the call stack before any row manipulation."""
        from PyQt6.QtCore import QTimer
        sender = self.sender()
        # Guard: if a deferred call is already queued, don't queue another
        if getattr(self, '_x_col_change_pending', False):
            return
        self._x_col_change_pending = True
        QTimer.singleShot(0, lambda: self._on_x_col_changed_deferred(sender))

    def _on_x_col_changed_deferred(self, sender):
        """Actual type-mismatch logic, runs after signal call stack is clear."""
        self._x_col_change_pending = False
        n_subplots = self.subplot_rows * self.subplot_cols

        # Find which row the changed combo belongs to
        changed_row = -1
        if sender is not None:
            for r in range(self.series_table.rowCount()):
                if self.series_table.cellWidget(r, 0) is sender:
                    changed_row = r
                    break

        if changed_row < 0:
            self.update_preview()
            return

        changed_spin = self.series_table.cellWidget(changed_row, 4)
        changed_subplot = (changed_spin.value() - 1) if (changed_spin and n_subplots > 1) else 0

        # Collect (row_index, is_categorical) for every row on the same subplot
        row_types = []
        for row in range(self.series_table.rowCount()):
            xcb = self.series_table.cellWidget(row, 0)
            if xcb is None: continue
            spin = self.series_table.cellWidget(row, 4)
            row_subplot = (spin.value() - 1) if (spin and n_subplots > 1) else 0
            if row_subplot != changed_subplot: continue
            col = xcb.currentText()
            if col not in self.datasets: continue
            row_types.append((row, self._is_categorical(self.datasets[col])))

        if len(row_types) < 2:
            self.update_preview()
            return

        has_cat = any(t for _, t in row_types)
        has_num = any(not t for _, t in row_types)
        if not (has_cat and has_num):
            self.update_preview()
            return

        # changed_type = the NEW type of the row that just changed
        changed_type = next((t for r, t in row_types if r == changed_row), row_types[-1][1])
        keep_name = 'categorical' if changed_type else 'numerical'
        drop_name = 'numerical' if changed_type else 'categorical'
        subplot_label = f'Subplot {changed_subplot + 1}' if n_subplots > 1 else 'this chart'

        ans = QMessageBox.question(
            self, 'Incompatible X types',
            f'In {subplot_label}, the selected X column is {keep_name}, '
            f'but other series use {drop_name} X data.\n\n'
            f'Remove the {drop_name} series and keep only {keep_name}?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if ans == QMessageBox.StandardButton.Yes:
            rows_to_remove = sorted(
                [r for r, t in row_types if t != changed_type],
                reverse=True
            )
            # Disconnect signals from widgets about to be destroyed
            for r in rows_to_remove:
                xcb = self.series_table.cellWidget(r, 0)
                ycb = self.series_table.cellWidget(r, 1)
                for w in (xcb, ycb):
                    if w is not None:
                        try: w.currentIndexChanged.disconnect()
                        except Exception: pass
            self.series_table.blockSignals(True)
            for r in rows_to_remove:
                self.series_table.removeRow(r)
            self.series_table.blockSignals(False)
            self._refresh_curve_select()
        else:
            # Revert the changed combo back to a column matching the OLD type
            old_type = not changed_type
            if sender is not None:
                sender.blockSignals(True)
                reverted = False
                for col in sorted(self.datasets):
                    if self._is_categorical(self.datasets[col]) == old_type:
                        idx = sender.findText(col)
                        if idx >= 0:
                            sender.setCurrentIndex(idx)
                            reverted = True
                            break
                if not reverted:
                    sender.setCurrentIndex(0)
                sender.blockSignals(False)

        self.update_preview()

    def _del_series_row(self):
        rows = sorted({idx.row() for idx in self.series_table.selectedIndexes()}, reverse=True)
        # Collect labels before removing rows so we can cascade to fitted curves
        labels_to_remove = []
        for r in rows:
            item = self.series_table.item(r, 2)
            if item:
                labels_to_remove.append(item.text())
        for r in rows:
            self.series_table.removeRow(r)
        # Remove any fitted curves derived from the deleted series
        if labels_to_remove:
            self._remove_fits_for_labels(labels_to_remove)
        self._refresh_curve_select()
        self.update_preview()

    def _get_y2_cols_from_table(self):
        """Return list of Y column names whose Y2 checkbox is checked."""
        result = []
        for row in range(self.series_table.rowCount()):
            y2_item = self.series_table.item(row, 5)
            if y2_item and y2_item.checkState() == Qt.CheckState.Checked:
                ycb = self.series_table.cellWidget(row, 1)
                if ycb:
                    result.append(ycb.currentText())
        return result

    def _get_series_type(self, row):
        """Return the per-series chart type for a row (col 3 QComboBox)."""
        type_cb = self.series_table.cellWidget(row, 3)
        return type_cb.currentText() if type_cb else 'Line'

    def _get_series(self, primary_only=False):
        """Return list of (xdata, ydata, label, series_ct) for every valid series row.
        If primary_only=True, skip rows where Y2 checkbox is checked."""
        result = []
        for row in range(self.series_table.rowCount()):
            xcb = self.series_table.cellWidget(row, 0)
            ycb = self.series_table.cellWidget(row, 1)
            lbl_item = self.series_table.item(row, 2)
            if xcb is None or ycb is None: continue
            if primary_only:
                y2_item = self.series_table.item(row, 5)
                if y2_item and y2_item.checkState() == Qt.CheckState.Checked:
                    continue
            xc = xcb.currentText()
            yc = ycb.currentText()
            if xc not in self.datasets or yc not in self.datasets: continue
            label = lbl_item.text() if lbl_item and lbl_item.text() else yc
            result.append((self.datasets[xc], self.datasets[yc], label, self._get_series_type(row)))
        return result

    def _get_series_full(self):
        """Return list of (xdata, ydata, label, xc, yc) — includes column names."""
        result = []
        for row in range(self.series_table.rowCount()):
            xcb = self.series_table.cellWidget(row, 0)
            ycb = self.series_table.cellWidget(row, 1)
            lbl_item = self.series_table.item(row, 2)
            if xcb is None or ycb is None: continue
            xc = xcb.currentText()
            yc = ycb.currentText()
            if xc not in self.datasets or yc not in self.datasets: continue
            label = lbl_item.text() if lbl_item and lbl_item.text() else yc
            result.append((self.datasets[xc], self.datasets[yc], label, xc, yc))
        return result
