"""
Copyright (c) 2026 Paulo Cachim
ui/color_schemes.py  –  plotviz

ColorSchemeMixin: built-in colour schemes plus save/load/apply of .pvizc
colour-scheme files. Split out of main_window to keep that module smaller;
mixed into PlotVizApp, so methods share its widgets and `self` state.
"""
import os

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QFileDialog, QMessageBox


def swatch_icon(colors, cell=11, height=12) -> QIcon:
    """A strip of small colour squares, for showing a palette or scheme in a combo."""
    pm = QPixmap(cell * len(colors) + 1, height)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    for i, color in enumerate(colors):
        p.fillRect(i * cell, 0, cell, height, QColor(color))
    p.setPen(QColor('#888888'))
    p.drawRect(0, 0, cell * len(colors), height - 1)
    p.end()
    return QIcon(pm)


class ColorSchemeMixin:
    # Keys extracted from a full settings dict that constitute a "color scheme".
    # Anything not in this list is left untouched when a scheme is applied.
    _COLOR_SCHEME_KEYS = [
        'chart_bg_color', 'chart_fg_color', 'plot_bg_color',
        'grid_color', 'grid_on', 'grid_linestyle', 'grid_linewidth', 'grid_alpha',
        'minor_grid_color', 'minor_grid_on',
        'minor_grid_linestyle', 'minor_grid_linewidth', 'minor_grid_alpha',
        'title_color', 'xlabel_color', 'ylabel_color', 'y2label_color', 'zlabel_color',
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
            'title_font': 'sans-serif', 'xlabel_font': 'sans-serif', 'ylabel_font': 'sans-serif',
            'title_size': 14, 'xlabel_size': 11, 'ylabel_size': 11,
            'border_top': True, 'border_bottom': True, 'border_left': True, 'border_right': True,
        },
        'Nature / print': {
            'chart_bg_color': '#ffffff', 'chart_fg_color': '#000000', 'plot_bg_color': '#ffffff',
            'grid_color': '#cccccc', 'grid_on': False, 'grid_linestyle': '--',
            'grid_linewidth': 0.4, 'grid_alpha': 0.3,
            'minor_grid_color': '#eeeeee', 'minor_grid_on': False,
            'title_color': '#000000', 'xlabel_color': '#000000', 'ylabel_color': '#000000',
            'color_palette': 'Nature',
            'title_font': 'sans-serif', 'xlabel_font': 'sans-serif', 'ylabel_font': 'sans-serif',
            'title_size': 10, 'xlabel_size': 8, 'ylabel_size': 8,
            'border_top': False, 'border_bottom': True, 'border_left': True, 'border_right': False,
        },
        'Scientific (minimal)': {
            'chart_bg_color': '#ffffff', 'chart_fg_color': '#000000', 'plot_bg_color': '#ffffff',
            'grid_color': '#bbbbbb', 'grid_on': True, 'grid_linestyle': ':',
            'grid_linewidth': 0.5, 'grid_alpha': 0.5,
            'minor_grid_color': '#eeeeee', 'minor_grid_on': False,
            'title_color': '#111111', 'xlabel_color': '#333333', 'ylabel_color': '#333333',
            'color_palette': 'Colorblind',
            'title_font': 'serif', 'xlabel_font': 'serif', 'ylabel_font': 'serif',
            'title_size': 12, 'xlabel_size': 10, 'ylabel_size': 10,
            'border_top': True, 'border_bottom': True, 'border_left': True, 'border_right': True,
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
        self._cs_combo.currentIndexChanged.connect(self._refresh_combo_icons)
        # `activated` fires only when the user picks an entry, never when the combo is
        # updated by code (loading a file, saving a scheme), so those never re-apply.
        self._cs_combo.activated.connect(lambda _i: self._apply_color_scheme_selected())
        self._refresh_combo_icons()

    _CUSTOM_SCHEME = '(custom)'

    @staticmethod
    def _same_scheme_value(a, b) -> bool:
        """Equal settings values, treating colour spellings ('#fff' / '#FFFFFF') alike."""
        if isinstance(a, str) and isinstance(b, str) and a.startswith('#') and b.startswith('#'):
            from matplotlib.colors import to_hex
            try:
                return to_hex(a) == to_hex(b)
            except ValueError:
                return a == b
        return a == b

    def _sync_color_scheme_combo(self, settings: dict):
        """Select the scheme whose colours *settings* match, or '(custom)'.

        Called after a file or template is loaded, so the combo describes the chart
        on screen instead of keeping the previous selection. The scheme already
        selected wins when several match.
        """
        names = list(self._COLOR_SCHEME_REGISTRY)
        current = self._cs_combo.currentText()
        if current in names:
            names.remove(current)
            names.insert(0, current)
        found = self._CUSTOM_SCHEME
        for name in names:
            scheme = self._COLOR_SCHEME_REGISTRY[name]
            if all(k in settings and self._same_scheme_value(settings[k], v)
                   for k, v in scheme.items()):
                found = name
                break
        if self._cs_combo.findText(found) < 0:
            self._cs_combo.addItem(found)
        self._cs_combo.setCurrentText(found)      # also refreshes the swatches

    def _refresh_combo_icons(self):
        """Show each palette's colours and each scheme's colours beside its name."""
        from ui.tab_builders import get_all_palettes
        combo = getattr(self, 'palette_combo', None)
        if combo is not None:
            pals = get_all_palettes()
            combo.setIconSize(QSize(8 * 11 + 1, 12))
            for i in range(combo.count()):
                colors = pals.get(combo.itemText(i))
                if colors:
                    combo.setItemIcon(i, swatch_icon(colors[:8]))
        combo = getattr(self, '_cs_combo', None)
        if combo is not None:
            combo.setIconSize(QSize(5 * 11 + 1, 12))
            for i in range(combo.count()):
                sch = self._COLOR_SCHEME_REGISTRY.get(combo.itemText(i))
                if sch:
                    combo.setItemIcon(i, swatch_icon([
                        sch.get('chart_bg_color', '#ffffff'), sch.get('plot_bg_color', '#ffffff'),
                        sch.get('chart_fg_color', '#000000'), sch.get('grid_color', '#cccccc'),
                        sch.get('title_color', '#000000')]))

    def _scheme_from_current_settings(self) -> dict:
        """Extract only the color-scheme keys from the current UI state."""
        full = self._collect_settings()
        return {k: full[k] for k in self._COLOR_SCHEME_KEYS if k in full}

    # What a scheme can change for ONE subplot: its plot area, axes colour, borders,
    # grid and title colour. Everything else in a scheme (figure background, palette,
    # fonts, axis-label colours) belongs to the whole figure.
    _SUBPLOT_CANVAS_KEYS = {'chart_fg_color': 'fg', 'plot_bg_color': 'plot_bg',
                            'border_top': 'border_top', 'border_bottom': 'border_bottom',
                            'border_left': 'border_left', 'border_right': 'border_right'}
    _SUBPLOT_GRID_KEYS = {'grid_on': 'enabled', 'grid_color': 'color', 'grid_linestyle': 'ls',
                          'grid_linewidth': 'lw', 'grid_alpha': 'alpha',
                          'minor_grid_on': 'minor_enabled', 'minor_grid_color': 'minor_color',
                          'minor_grid_linestyle': 'minor_ls', 'minor_grid_linewidth': 'minor_lw',
                          'minor_grid_alpha': 'minor_alpha'}

    def _apply_color_scheme_to_subplot(self, scheme: dict, idx: int):
        """Apply the per-subplot part of *scheme* to subplot *idx* only (the active one)."""
        self._save_canvas_grid_opts(idx)            # keep the widgets' current values
        co = dict(self.subplot_canvas_opts.get(idx, self._default_canvas_opts()))
        go = dict(self.subplot_grid_opts.get(idx, self._default_grid_opts()))
        for key, dest in self._SUBPLOT_CANVAS_KEYS.items():
            if key in scheme:
                co[dest] = scheme[key]
        for key, dest in self._SUBPLOT_GRID_KEYS.items():
            if key in scheme:
                go[dest] = scheme[key]
        self.subplot_canvas_opts[idx] = co
        self.subplot_grid_opts[idx] = go
        if 'title_color' in scheme:
            self.subplot_title_color[idx] = scheme['title_color']
            self.sp_title_color = scheme['title_color']       # the Annotations-tab widget state
            if hasattr(self, 'sp_title_color_label'):
                self.sp_title_color_label.setStyleSheet(
                    f"background-color:{scheme['title_color']};border:1px solid #888;"
                    f"border-radius:2px;")
        self._load_canvas_grid_opts(idx)                   # refresh the Axes-tab widgets
        self.update_preview()

    def _apply_color_scheme_dict(self, scheme: dict, subplot: int | None = None):
        """Apply a partial settings dict containing only color-scheme keys.

        With *subplot* only that subplot's share of the scheme is applied
        (see _apply_color_scheme_to_subplot); otherwise the whole figure changes.
        """
        if subplot is not None:
            self._apply_color_scheme_to_subplot(scheme, subplot)
            return
        # Build a full settings dict from current state, overwrite scheme keys only
        full = self._collect_settings()
        full.update(scheme)
        if 'zlabel_color' not in scheme and 'ylabel_color' in scheme:
            full['zlabel_color'] = scheme['ylabel_color']  # 3D z-label follows y-label
        self._applying_settings = True
        try:
            self._apply_settings(full)
        finally:
            self._applying_settings = False
        self.update_preview()

    def _scheme_target_subplot(self) -> int | None:
        """The subplot a scheme is to be applied to, or None for the whole figure.

        Follows the "Apply to" selector; with a single subplot it is always the figure.
        """
        if (getattr(self, '_cs_target', None) is not None
                and self._cs_target.currentIndex() == 1
                and self.subplot_rows * self.subplot_cols > 1):
            return self.global_sp_active.currentIndex()
        return None

    def _apply_color_scheme_selected(self):
        """Apply the scheme currently selected in the combo."""
        name = self._cs_combo.currentText()
        scheme = self._COLOR_SCHEME_REGISTRY.get(name)
        if scheme:
            self._apply_color_scheme_dict(scheme, subplot=self._scheme_target_subplot())

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
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
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
            self._refresh_combo_icons()

            target = self._scheme_target_subplot()
            where = 'to the whole figure' if target is None else f'to subplot {target + 1}'
            reply = QMessageBox.question(
                self, 'Apply?',
                f'Scheme "{name}" loaded.\nApply it {where} now?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._apply_color_scheme_dict(scheme, subplot=target)
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
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
            self._apply_color_scheme_dict(scheme, subplot=self._scheme_target_subplot())
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
            QMessageBox.critical(self, 'Error', str(e))
