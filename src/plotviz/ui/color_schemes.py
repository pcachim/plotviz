"""
Copyright (c) 2026 Paulo Cachim
ui/color_schemes.py  –  plotviz

ColorSchemeMixin: built-in colour schemes plus save/load/apply of .pvizc
colour-scheme files. Split out of main_window to keep that module smaller;
mixed into PlotVizApp, so methods share its widgets and `self` state.
"""
import os

from PyQt6.QtWidgets import QFileDialog, QMessageBox


class ColorSchemeMixin:
    # Keys extracted from a full settings dict that constitute a "color scheme".
    # Anything not in this list is left untouched when a scheme is applied.
    _COLOR_SCHEME_KEYS = [
        'chart_bg_color', 'chart_fg_color', 'plot_bg_color',
        'grid_color', 'grid_on', 'grid_linestyle', 'grid_linewidth', 'grid_alpha',
        'minor_grid_color', 'minor_grid_on',
        'minor_grid_linestyle', 'minor_grid_linewidth', 'minor_grid_alpha',
        'title_color', 'xlabel_color', 'ylabel_color', 'y2label_color',
        'title_font', 'xlabel_font', 'ylabel_font',
        'title_size', 'xlabel_size', 'ylabel_size',
        'border_top', 'border_bottom', 'border_left', 'border_right',
        'color_palette',
        'ann_fontcolor', 'ann_bgcolor', 'ann_edgecolor',
    ]

    # Built-in named schemes: name → partial settings dict
    _BUILTIN_COLOR_SCHEMES = {
        # ── Light → Dark (ordered by background luminance) ────────────────────
        'Default (white)': {
            'chart_bg_color': '#ffffff', 'chart_fg_color': '#000000', 'plot_bg_color': '#ffffff',
            'grid_color': '#cccccc', 'grid_on': True, 'grid_linestyle': '--',
            'grid_linewidth': 0.5, 'grid_alpha': 0.4,
            'minor_grid_color': '#e8e8e8', 'minor_grid_on': False,
            'title_color': '#000000', 'xlabel_color': '#000000', 'ylabel_color': '#000000',
            'color_palette': 'Matplotlib',
        },
        'Nature / print': {
            'chart_bg_color': '#ffffff', 'chart_fg_color': '#000000', 'plot_bg_color': '#ffffff',
            'grid_color': '#cccccc', 'grid_on': False, 'grid_linestyle': '--',
            'grid_linewidth': 0.4, 'grid_alpha': 0.3,
            'minor_grid_color': '#eeeeee', 'minor_grid_on': False,
            'title_color': '#000000', 'xlabel_color': '#000000', 'ylabel_color': '#000000',
            'border_top': False, 'border_right': False,
            'color_palette': 'Matplotlib',
        },
        'Scientific (minimal)': {
            'chart_bg_color': '#ffffff', 'chart_fg_color': '#000000', 'plot_bg_color': '#ffffff',
            'grid_color': '#dddddd', 'grid_on': True, 'grid_linestyle': '--',
            'grid_linewidth': 0.4, 'grid_alpha': 0.3,
            'minor_grid_color': '#eeeeee', 'minor_grid_on': False,
            'title_color': '#111111', 'xlabel_color': '#333333', 'ylabel_color': '#333333',
            'border_top': False, 'border_right': False,
            'color_palette': 'Matplotlib',
        },
        'Pastel soft': {
            'chart_bg_color': '#fdfbf7', 'chart_fg_color': '#444444', 'plot_bg_color': '#fdfbf7',
            'grid_color': '#ddd5e8', 'grid_on': True, 'grid_linestyle': '--',
            'grid_linewidth': 0.5, 'grid_alpha': 0.5,
            'minor_grid_color': '#f0ecf5', 'minor_grid_on': False,
            'title_color': '#444444', 'xlabel_color': '#666666', 'ylabel_color': '#666666',
            'color_palette': 'Pastel',
        },
        'Warm parchment': {
            'chart_bg_color': '#f5f0e8', 'chart_fg_color': '#3d2b1f', 'plot_bg_color': '#faf7f0',
            'grid_color': '#c8b89a', 'grid_on': True, 'grid_linestyle': '--',
            'grid_linewidth': 0.5, 'grid_alpha': 0.4,
            'minor_grid_color': '#e0d5c2', 'minor_grid_on': False,
            'title_color': '#3d2b1f', 'xlabel_color': '#5c4033', 'ylabel_color': '#5c4033',
            'color_palette': 'Pastel',
        },
        'Dark (charcoal)': {
            'chart_bg_color': '#1e1e2e', 'chart_fg_color': '#cdd6f4', 'plot_bg_color': '#181825',
            'grid_color': '#45475a', 'grid_on': True, 'grid_linestyle': '--',
            'grid_linewidth': 0.5, 'grid_alpha': 0.5,
            'minor_grid_color': '#313244', 'minor_grid_on': False,
            'title_color': '#cdd6f4', 'xlabel_color': '#a6adc8', 'ylabel_color': '#a6adc8',
            'border_top': False, 'border_right': False,
            'color_palette': 'Bold',
        },
        'Dark (slate)': {
            'chart_bg_color': '#0f172a', 'chart_fg_color': '#e2e8f0', 'plot_bg_color': '#1e293b',
            'grid_color': '#334155', 'grid_on': True, 'grid_linestyle': ':',
            'grid_linewidth': 0.6, 'grid_alpha': 0.6,
            'minor_grid_color': '#1e293b', 'minor_grid_on': False,
            'title_color': '#f8fafc', 'xlabel_color': '#94a3b8', 'ylabel_color': '#94a3b8',
            'border_top': False, 'border_right': False,
            'color_palette': 'Bold',
        },
        'Midnight blue': {
            'chart_bg_color': '#0d1b2a', 'chart_fg_color': '#e0e0e0', 'plot_bg_color': '#0d1b2a',
            'grid_color': '#1b3a5c', 'grid_on': True, 'grid_linestyle': '-',
            'grid_linewidth': 0.4, 'grid_alpha': 0.4,
            'minor_grid_color': '#112233', 'minor_grid_on': False,
            'title_color': '#ffffff', 'xlabel_color': '#aac8e4', 'ylabel_color': '#aac8e4',
            'border_top': False, 'border_right': False,
            'color_palette': 'Bold',
        },
        'High contrast': {
            'chart_bg_color': '#000000', 'chart_fg_color': '#ffffff', 'plot_bg_color': '#000000',
            'grid_color': '#444444', 'grid_on': True, 'grid_linestyle': ':',
            'grid_linewidth': 0.5, 'grid_alpha': 0.6,
            'minor_grid_color': '#222222', 'minor_grid_on': False,
            'title_color': '#ffffff', 'xlabel_color': '#cccccc', 'ylabel_color': '#cccccc',
            'border_top': True, 'border_right': True,
            'color_palette': 'Bold',
        },
    }

    # Registry of all schemes (built-in + user-loaded); populated by _init_color_schemes
    _COLOR_SCHEME_REGISTRY: dict = {}

    def _init_color_schemes(self):
        """Populate the color scheme combo with built-ins and refresh the swatch."""
        self._COLOR_SCHEME_REGISTRY = dict(self._BUILTIN_COLOR_SCHEMES)
        self._cs_combo.blockSignals(True)
        self._cs_combo.clear()
        self._cs_combo.addItems(list(self._COLOR_SCHEME_REGISTRY.keys()))
        self._cs_combo.blockSignals(False)
        self._cs_combo.currentIndexChanged.connect(self._refresh_cs_swatches)
        self._refresh_cs_swatches()

    def _refresh_cs_swatches(self):
        """Update the 5 preview swatches for the currently selected scheme."""
        name = self._cs_combo.currentText()
        scheme = self._COLOR_SCHEME_REGISTRY.get(name, {})
        colors = [
            scheme.get('chart_bg_color', '#ffffff'),
            scheme.get('plot_bg_color',  '#ffffff'),
            scheme.get('chart_fg_color', '#000000'),
            scheme.get('grid_color',     '#cccccc'),
            scheme.get('title_color',    '#000000'),
        ]
        for sw, color in zip(self._cs_swatches, colors):
            sw.setStyleSheet(
                f'background:{color}; border:1px solid #888; border-radius:2px;')

    def _scheme_from_current_settings(self) -> dict:
        """Extract only the color-scheme keys from the current UI state."""
        full = self._collect_settings()
        return {k: full[k] for k in self._COLOR_SCHEME_KEYS if k in full}

    def _apply_color_scheme_dict(self, scheme: dict):
        """Apply a partial settings dict containing only color-scheme keys."""
        # Build a full settings dict from current state, overwrite scheme keys only
        full = self._collect_settings()
        full.update(scheme)
        self._applying_settings = True
        try:
            self._apply_settings(full)
        finally:
            self._applying_settings = False
        self.update_preview()

    def _apply_color_scheme_selected(self):
        """Apply the scheme currently selected in the combo."""
        name = self._cs_combo.currentText()
        scheme = self._COLOR_SCHEME_REGISTRY.get(name)
        if scheme:
            self._apply_color_scheme_dict(scheme)

    def _save_color_scheme(self):
        """Save the current chart colors as a .pvizc color-scheme file."""
        import zipfile as _zf, json as _json
        from ui.helpers import _get_dir, _remember_dir

        _stem = (os.path.splitext(os.path.basename(self._current_filepath))[0]
                 if getattr(self, '_current_filepath', None) else 'new chart')
        name = _stem  # scheme name matches file stem; no separate prompt needed

        fp, _ = QFileDialog.getSaveFileName(
            self, 'Save Color Scheme', os.path.join(_get_dir(), _stem + '.pvizc'),
            'plotviz Color Scheme (*.pvizc);;All Files (*)')
        if not fp:
            return
        _remember_dir(fp)
        if not fp.endswith('.pvizc'):
            fp += '.pvizc'

        # Use the actual saved filename stem as the scheme name (user may have
        # changed it in the file dialog)
        name = os.path.splitext(os.path.basename(fp))[0]

        try:
            scheme = self._scheme_from_current_settings()
            payload = {
                '_app': 'plotviz',
                '_file_type': 'color_scheme',
                '_scheme_name': name,
            }
            payload.update(scheme)
            with _zf.ZipFile(fp, 'w', _zf.ZIP_DEFLATED) as zf:
                zf.writestr('settings.json', _json.dumps(payload, indent=2))

            # Register in the combo so it can be re-applied this session
            self._COLOR_SCHEME_REGISTRY[name] = scheme
            if self._cs_combo.findText(name) < 0:
                self._cs_combo.addItem(name)
            self._cs_combo.setCurrentText(name)
            QMessageBox.information(self, 'Saved', f'Color scheme saved:\n{fp}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _load_color_scheme(self):
        """Load a .pvizc color-scheme file and register it in the combo."""
        import zipfile as _zf, json as _json
        from ui.helpers import _get_dir, _remember_dir

        fp, _ = QFileDialog.getOpenFileName(
            self, 'Load Color Scheme', _get_dir(),
            'plotviz Color Scheme (*.pvizc);;All Files (*)')
        if not fp:
            return
        _remember_dir(fp)

        try:
            with _zf.ZipFile(fp, 'r') as zf:
                payload = _json.loads(zf.read('settings.json'))

            # Accept both color_scheme and full template files
            name = payload.get('_scheme_name') or os.path.splitext(
                os.path.basename(fp))[0]

            # Extract only the color-scheme keys (ignore layout, data, etc.)
            scheme = {k: payload[k] for k in self._COLOR_SCHEME_KEYS if k in payload}
            if not scheme:
                QMessageBox.warning(self, 'Invalid',
                    'No color settings found in this file.')
                return

            self._COLOR_SCHEME_REGISTRY[name] = scheme
            if self._cs_combo.findText(name) < 0:
                self._cs_combo.addItem(name)
            self._cs_combo.setCurrentText(name)
            self._refresh_cs_swatches()

            reply = QMessageBox.question(
                self, 'Apply?',
                f'Scheme "{name}" loaded.\nApply it now?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._apply_color_scheme_dict(scheme)
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _load_color_scheme_from_path(self, fp: str):
        """Load a .pvizc directly from *fp* (no dialog — Finder/cold-launch)."""
        import zipfile as _zf, json as _json
        try:
            with _zf.ZipFile(fp, 'r') as zf:
                payload = _json.loads(zf.read('settings.json'))
            name = payload.get('_scheme_name') or os.path.splitext(
                os.path.basename(fp))[0]
            scheme = {k: payload[k] for k in self._COLOR_SCHEME_KEYS if k in payload}
            if not scheme:
                return
            self._COLOR_SCHEME_REGISTRY[name] = scheme
            if self._cs_combo.findText(name) < 0:
                self._cs_combo.addItem(name)
            self._cs_combo.setCurrentText(name)
            self._refresh_cs_swatches()
            self._apply_color_scheme_dict(scheme)
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))
