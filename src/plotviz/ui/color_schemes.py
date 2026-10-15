"""
Copyright (c) 2026 Paulo Cachim
ui/color_schemes.py  –  plotviz

ColorSchemeMixin: built-in colour schemes plus save/load/apply of .pvizc
colour-scheme files. Split out of main_window to keep that module smaller;
mixed into PlotVizApp, so methods share its widgets and `self` state.
"""
import os
import re

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
            'border_top': True, 'border_bottom': True, 'border_left': True, 'border_right': True,
        },
        'Ivory': {
            'chart_bg_color': '#fffff8', 'chart_fg_color': '#222222', 'plot_bg_color': '#fffff8',
            'grid_color': '#cccccc', 'grid_on': False, 'grid_linestyle': '-',
            'grid_linewidth': 0.5, 'grid_alpha': 0.4,
            'minor_grid_color': '#eeeeee', 'minor_grid_on': False,
            'title_color': '#222222', 'xlabel_color': '#222222', 'ylabel_color': '#222222',
            'border_top': False, 'border_bottom': True, 'border_left': True, 'border_right': False,
            'color_palette': 'Publication',
        },
        'Blueprint (light)': {
            'chart_bg_color': '#e6eff9', 'chart_fg_color': '#10304f', 'plot_bg_color': '#f6faff',
            'grid_color': '#8fb0d3', 'grid_on': True, 'grid_linestyle': '-',
            'grid_linewidth': 0.8, 'grid_alpha': 0.7,
            'minor_grid_color': '#c9dbee', 'minor_grid_on': True,
            'title_color': '#10304f', 'xlabel_color': '#10304f', 'ylabel_color': '#10304f',
            'border_top': True, 'border_bottom': True, 'border_left': True, 'border_right': True,
            'color_palette': 'Cool',
        },
        'Grey panel': {
            'chart_bg_color': '#ffffff', 'chart_fg_color': '#333333', 'plot_bg_color': '#ebebeb',
            'grid_color': '#ffffff', 'grid_on': True, 'grid_linestyle': '-',
            'grid_linewidth': 1.4, 'grid_alpha': 1.0,
            'minor_grid_color': '#f5f5f5', 'minor_grid_on': False,
            'title_color': '#333333', 'xlabel_color': '#333333', 'ylabel_color': '#333333',
            'border_top': False, 'border_bottom': False, 'border_left': False, 'border_right': False,
            'color_palette': 'Matplotlib',
        },
        'Graph paper': {
            'chart_bg_color': '#f7fbf2', 'chart_fg_color': '#243b24', 'plot_bg_color': '#fdfff9',
            'grid_color': '#a9d0a0', 'grid_on': True, 'grid_linestyle': '-',
            'grid_linewidth': 0.8, 'grid_alpha': 0.8,
            'minor_grid_color': '#d8ebd3', 'minor_grid_on': True,
            'title_color': '#243b24', 'xlabel_color': '#243b24', 'ylabel_color': '#243b24',
            'border_top': True, 'border_bottom': True, 'border_left': True, 'border_right': True,
            'color_palette': 'Earth',
        },
        'Newsprint': {
            'chart_bg_color': '#fff1e5', 'chart_fg_color': '#33302e', 'plot_bg_color': '#fff1e5',
            'grid_color': '#e3cdb7', 'grid_on': True, 'grid_linestyle': '-',
            'grid_linewidth': 0.8, 'grid_alpha': 0.9,
            'minor_grid_color': '#f0e0d0', 'minor_grid_on': False,
            'title_color': '#33302e', 'xlabel_color': '#33302e', 'ylabel_color': '#33302e',
            'border_top': False, 'border_bottom': True, 'border_left': False, 'border_right': False,
            'color_palette': 'Colorblind',
        },
        'Solarized (light)': {
            'chart_bg_color': '#fdf6e3', 'chart_fg_color': '#586e75', 'plot_bg_color': '#fdf6e3',
            'grid_color': '#d9d2bd', 'grid_on': True, 'grid_linestyle': '--',
            'grid_linewidth': 0.8, 'grid_alpha': 0.9,
            'minor_grid_color': '#eee8d5', 'minor_grid_on': False,
            'title_color': '#073642', 'xlabel_color': '#586e75', 'ylabel_color': '#586e75',
            'border_top': False, 'border_bottom': True, 'border_left': True, 'border_right': False,
            'color_palette': 'Warm',
        },
        'Lavender': {
            'chart_bg_color': '#f1effb', 'chart_fg_color': '#2d2a52', 'plot_bg_color': '#ffffff',
            'grid_color': '#cfc9ee', 'grid_on': True, 'grid_linestyle': ':',
            'grid_linewidth': 1.4, 'grid_alpha': 1.0,
            'minor_grid_color': '#e6e2f7', 'minor_grid_on': False,
            'title_color': '#2d2a52', 'xlabel_color': '#2d2a52', 'ylabel_color': '#2d2a52',
            'border_top': True, 'border_bottom': True, 'border_left': True, 'border_right': True,
            'color_palette': 'Ocean',
        },
        'Sage': {
            'chart_bg_color': '#eef4ef', 'chart_fg_color': '#1f3d2e', 'plot_bg_color': '#ffffff',
            'grid_color': '#c5dccb', 'grid_on': True, 'grid_linestyle': '-',
            'grid_linewidth': 0.8, 'grid_alpha': 0.9,
            'minor_grid_color': '#e0ece3', 'minor_grid_on': False,
            'title_color': '#1f3d2e', 'xlabel_color': '#1f3d2e', 'ylabel_color': '#1f3d2e',
            'border_top': False, 'border_bottom': True, 'border_left': True, 'border_right': False,
            'color_palette': 'Nature',
        },
        'Dark (charcoal)': {
            'chart_bg_color': '#1e1e2e', 'chart_fg_color': '#cdd6f4', 'plot_bg_color': '#181825',
            'grid_color': '#45475a', 'grid_on': True, 'grid_linestyle': '--',
            'grid_linewidth': 0.5, 'grid_alpha': 0.5,
            'minor_grid_color': '#313244', 'minor_grid_on': False,
            'title_color': '#cdd6f4', 'xlabel_color': '#a6adc8', 'ylabel_color': '#a6adc8',
            'border_top': False, 'border_bottom': True, 'border_left': True, 'border_right': False,
            'color_palette': 'Bold',
        },
        'Dark (slate)': {
            'chart_bg_color': '#0f172a', 'chart_fg_color': '#e2e8f0', 'plot_bg_color': '#1e293b',
            'grid_color': '#334155', 'grid_on': True, 'grid_linestyle': ':',
            'grid_linewidth': 0.6, 'grid_alpha': 0.6,
            'minor_grid_color': '#1e293b', 'minor_grid_on': False,
            'title_color': '#f8fafc', 'xlabel_color': '#94a3b8', 'ylabel_color': '#94a3b8',
            'border_top': False, 'border_bottom': True, 'border_left': True, 'border_right': False,
            'color_palette': 'Bold',
        },
        'Midnight blue': {
            'chart_bg_color': '#0d1b2a', 'chart_fg_color': '#e0e0e0', 'plot_bg_color': '#0d1b2a',
            'grid_color': '#1b3a5c', 'grid_on': True, 'grid_linestyle': '-',
            'grid_linewidth': 0.4, 'grid_alpha': 0.4,
            'minor_grid_color': '#112233', 'minor_grid_on': False,
            'title_color': '#ffffff', 'xlabel_color': '#aac8e4', 'ylabel_color': '#aac8e4',
            'border_top': False, 'border_bottom': True, 'border_left': True, 'border_right': False,
            'color_palette': 'Bold',
        },
        'High contrast': {
            'chart_bg_color': '#000000', 'chart_fg_color': '#ffffff', 'plot_bg_color': '#000000',
            'grid_color': '#444444', 'grid_on': True, 'grid_linestyle': ':',
            'grid_linewidth': 0.5, 'grid_alpha': 0.6,
            'minor_grid_color': '#222222', 'minor_grid_on': False,
            'title_color': '#ffffff', 'xlabel_color': '#cccccc', 'ylabel_color': '#cccccc',
            'border_top': True, 'border_bottom': True, 'border_left': True, 'border_right': True,
            'color_palette': 'Bold',
        },
    }

    # Registry of all schemes (built-in + user-loaded); populated by _init_color_schemes
    _COLOR_SCHEME_REGISTRY: dict = {}

    # What the active scheme tracks: edits to any of these change the scheme (see
    # _sync_active_scheme). Fonts, sizes and grid line style are applied with a scheme
    # but are not tracked. Missing keys in a scheme take these values.
    _TRACKED_DEFAULTS = {
        'chart_bg_color': '#ffffff', 'plot_bg_color': '#ffffff', 'chart_fg_color': '#000000',
        'title_color': '#000000', 'xlabel_color': '#000000', 'ylabel_color': '#000000',
        'grid_color': '#cccccc', 'minor_grid_color': '#e8e8e8',
        'grid_on': True, 'minor_grid_on': False,
        'border_top': True, 'border_bottom': True, 'border_left': True, 'border_right': True,
        'color_palette': 'Matplotlib',
    }
    # With several subplots the rest is per subplot: edits there are local adjustments
    # and do not touch the scheme.
    _FIGURE_LEVEL_KEYS = ('chart_bg_color', 'title_color', 'xlabel_color', 'ylabel_color',
                          'color_palette')

    def _normalise_scheme(self, scheme: dict) -> dict:
        """A copy of *scheme* with every tracked key present."""
        return {**self._TRACKED_DEFAULTS, **scheme}

    def _init_color_schemes(self):
        """Register the built-in schemes, fill the combo and make the first one active."""
        self._COLOR_SCHEME_REGISTRY = {n: self._normalise_scheme(sch)
                                       for n, sch in self._BUILTIN_COLOR_SCHEMES.items()}
        self._scheme_unsaved = set()     # schemes that exist only in this session
        self._scheme_origin = {}         # edited copy → the built-in it was made from
        self._active_scheme = next(iter(self._COLOR_SCHEME_REGISTRY))
        self._rebuild_scheme_combo()
        self._cs_combo.currentIndexChanged.connect(self._refresh_combo_icons)
        # `activated` fires only when the user picks an entry, never when the combo is
        # updated by code (loading a file, saving a scheme), so those never re-apply.
        self._cs_combo.activated.connect(lambda _i: self._apply_color_scheme_selected())

    def _active_scheme_name(self) -> str:
        return getattr(self, '_active_scheme', '')

    def _rebuild_scheme_combo(self):
        """Refill the combo from the registry; unsaved schemes are marked with a *."""
        combo = self._cs_combo
        combo.blockSignals(True)
        combo.clear()
        for name in self._COLOR_SCHEME_REGISTRY:
            combo.addItem(name + (' *' if name in self._scheme_unsaved else ''), name)
        combo.setCurrentIndex(max(0, combo.findData(self._active_scheme)))
        combo.blockSignals(False)
        self._refresh_combo_icons()

    def _select_scheme(self, name: str):
        """Make *name* the active scheme (does not apply it to the chart)."""
        self._active_scheme = name
        self._rebuild_scheme_combo()

    def _register_scheme(self, name: str, scheme: dict, unsaved: bool,
                         origin: str | None = None) -> str:
        """Add or replace a scheme in the registry; returns the name actually used.

        Built-in schemes are read-only: a clash with one gets a ' (file)' suffix.
        """
        if name in self._BUILTIN_COLOR_SCHEMES:
            name += ' (file)'
        self._COLOR_SCHEME_REGISTRY[name] = self._normalise_scheme(scheme)
        (self._scheme_unsaved.add if unsaved else self._scheme_unsaved.discard)(name)
        if origin:
            self._scheme_origin[name] = origin
        else:
            self._scheme_origin.pop(name, None)
        return name

    def _remove_scheme(self, name: str):
        self._COLOR_SCHEME_REGISTRY.pop(name, None)
        self._scheme_unsaved.discard(name)
        self._scheme_origin.pop(name, None)

    def _fork_scheme(self, base_name: str, values: dict) -> str:
        """Create the editable copy '<base> – edited' of a built-in scheme."""
        name, n = f'{base_name} – edited', 1
        while name in self._COLOR_SCHEME_REGISTRY:
            n += 1
            name = f'{base_name} – edited {n}'
        self._register_scheme(name, {**self._COLOR_SCHEME_REGISTRY[base_name], **values},
                              unsaved=True, origin=base_name)
        return name

    def _comparable_keys(self, n_subplots: int):
        return (self._TRACKED_DEFAULTS if n_subplots <= 1 else self._FIGURE_LEVEL_KEYS)

    def _tracked_scheme_values(self):
        """Current chart values of the tracked keys, or None while the UI is being built."""
        try:
            v = {'chart_bg_color': self.chart_bg_color, 'title_color': self.title_color,
                 'xlabel_color': self.xlabel_color, 'ylabel_color': self.ylabel_color,
                 'color_palette': getattr(self, '_color_palette', 'Matplotlib')}
            if self.subplot_rows * self.subplot_cols <= 1:
                v.update({
                    'chart_fg_color': self.chart_fg_color, 'plot_bg_color': self.plot_bg_color,
                    'grid_color': self.grid_color, 'minor_grid_color': self.minor_grid_color,
                    'grid_on': self.grid_check.isChecked(),
                    'minor_grid_on': self.minor_grid_check.isChecked(),
                    'border_top': self.border_top.isChecked(),
                    'border_bottom': self.border_bottom.isChecked(),
                    'border_left': self.border_left.isChecked(),
                    'border_right': self.border_right.isChecked()})
            return v
        except AttributeError:
            return None

    def _scheme_matches(self, scheme: dict, values: dict) -> bool:
        return all(self._same_scheme_value(scheme.get(k), v) for k, v in values.items())

    def _sync_active_scheme(self):
        """Carry edits made anywhere in the UI into the active scheme.

        A scheme of yours (or one loaded from a file) is updated in place. A built-in is
        read-only, so the first edit makes an editable copy, '<name> – edited', and that
        becomes active. A copy edited back to its origin is dropped again.
        """
        if getattr(self, '_applying_settings', False) or not hasattr(self, '_scheme_unsaved'):
            return
        name = self._active_scheme
        base = self._COLOR_SCHEME_REGISTRY.get(name)
        cur = self._tracked_scheme_values()
        if base is None or cur is None or self._scheme_matches(base, cur):
            return
        if name in self._BUILTIN_COLOR_SCHEMES:
            self._select_scheme(self._fork_scheme(name, cur))
            return
        base.update(cur)
        origin = self._scheme_origin.get(name)
        if origin in self._COLOR_SCHEME_REGISTRY and self._scheme_matches(
                self._COLOR_SCHEME_REGISTRY[origin], cur):
            self._remove_scheme(name)
            self._select_scheme(origin)
        elif name not in self._scheme_unsaved:
            self._scheme_unsaved.add(name)
            self._rebuild_scheme_combo()

    def _adopt_scheme_from_settings(self, s: dict):
        """Make the active scheme describe a restored chart (file, template, undo, new).

        A file that carries its scheme (name and values) brings it back. Otherwise the
        scheme whose colours match is selected, or an editable copy of the closest
        built-in (or 'Custom' when none is close) is made.
        """
        n_sub = max(1, int(s.get('subplot_rows', 1)) * int(s.get('subplot_cols', 1)))
        keys = self._comparable_keys(n_sub)
        values = {k: s.get(k, self._TRACKED_DEFAULTS[k]) for k in keys}
        name, sch = s.get('color_scheme_name'), s.get('color_scheme')
        if name and isinstance(sch, dict):
            sch = self._normalise_scheme(sch)
            if name not in self._COLOR_SCHEME_REGISTRY:
                name = self._register_scheme(name, sch, unsaved=True)
            elif not self._scheme_matches(self._COLOR_SCHEME_REGISTRY[name], values):
                if name in self._BUILTIN_COLOR_SCHEMES:
                    name = self._fork_scheme(name, values)
                else:
                    self._COLOR_SCHEME_REGISTRY[name].update(sch)
                    self._scheme_unsaved.add(name)
            self._select_scheme(name)
            return
        order = list(self._COLOR_SCHEME_REGISTRY)
        if self._active_scheme in order:                 # the selected scheme wins a tie
            order.remove(self._active_scheme)
            order.insert(0, self._active_scheme)
        for cand in order:
            if self._scheme_matches(self._COLOR_SCHEME_REGISTRY[cand], values):
                self._select_scheme(cand)
                return
        # No match: an edited copy of the closest built-in, unless nothing is close
        def _distance(cand):
            sch = self._COLOR_SCHEME_REGISTRY[cand]
            return sum(not self._same_scheme_value(sch.get(k), v) for k, v in values.items())
        closest = min(self._BUILTIN_COLOR_SCHEMES, key=_distance)
        if _distance(closest) <= 4:
            self._select_scheme(self._fork_scheme(closest, values))
            return
        if 'Custom' in self._COLOR_SCHEME_REGISTRY:
            self._COLOR_SCHEME_REGISTRY['Custom'].update(values)
            self._scheme_unsaved.add('Custom')
        else:
            self._register_scheme('Custom', {**self._TRACKED_DEFAULTS, **values}, unsaved=True)
        self._select_scheme('Custom')

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

    def _refresh_combo_icons(self):
        """Show each palette's colours and each scheme's colours beside its name."""
        from ui.tab_builders import get_all_palettes
        combo = getattr(self, 'palette_combo', None)
        if combo is not None:
            pals = get_all_palettes()
            combo.setIconSize(QSize(8 * 11 + 1, 12))
            for i in range(combo.count()):
                colors = pals.get(combo.itemData(i))
                if colors:
                    combo.setItemIcon(i, swatch_icon(colors[:8]))
        combo = getattr(self, '_cs_combo', None)
        if combo is not None:
            combo.setIconSize(QSize(5 * 11 + 1, 12))
            for i in range(combo.count()):
                sch = self._COLOR_SCHEME_REGISTRY.get(combo.itemData(i))
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
        full.pop('color_scheme_name', None)         # the active scheme is set by the caller;
        full.pop('color_scheme', None)              # settings then only match it by colours
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

    def _activate_scheme(self, name: str):
        """Apply the registered scheme *name* where the "Apply to" selector says.

        To the whole figure it becomes the active scheme. For one subplot it is only a
        local adjustment: the active scheme stays as it is.
        """
        scheme = self._COLOR_SCHEME_REGISTRY.get(name)
        if not scheme:
            return
        target = self._scheme_target_subplot()
        if target is None:
            self._active_scheme = name
            self._apply_color_scheme_dict(scheme)
        else:
            self._apply_color_scheme_dict(scheme, subplot=target)
        self._rebuild_scheme_combo()

    def _apply_color_scheme_selected(self):
        """Apply the scheme the user picked in the combo."""
        self._activate_scheme(self._cs_combo.currentData())

    def _open_scheme_editor(self):
        """Create or edit a colour scheme; Save && apply registers and applies it."""
        from ui.scheme_editor import SchemeEditorDialog
        from ui.tab_builders import get_all_palettes

        old = self._active_scheme
        name = old if old not in self._BUILTIN_COLOR_SCHEMES else 'My scheme'
        dlg = SchemeEditorDialog(
            self, name, self._scheme_from_current_settings(),
            self._COLOR_SCHEME_REGISTRY, list(get_all_palettes()),
            palette_colors=self._active_palette_colors())
        while dlg.exec() == dlg.DialogCode.Accepted:
            name = dlg.scheme_name()
            if not name:
                QMessageBox.warning(self, 'Name required', 'Please enter a scheme name.')
                continue
            if name in self._BUILTIN_COLOR_SCHEMES:
                QMessageBox.warning(self, 'Built-in scheme',
                    f'"{name}" is a built-in scheme and cannot be replaced.\n'
                    'Please choose another name.')
                continue
            if (old != name and old in self._scheme_origin
                    and self._scheme_target_subplot() is None):
                self._remove_scheme(old)             # naming an edited copy renames it
            self._register_scheme(name, dlg.result_scheme(), unsaved=True)
            self._activate_scheme(name)
            return

    def _adopt_palette_from_scheme_file(self, payload: dict):
        """Register the palette a .pvizc carries when this session does not have it."""
        from ui.tab_builders import get_all_palettes
        pal = payload.get('_palette')
        if (isinstance(pal, dict) and pal.get('name') and pal.get('colors')
                and pal['name'] not in get_all_palettes()):
            self._register_palette(pal['name'], pal['colors'], unsaved=True)
            self._rebuild_palette_combo()

    @staticmethod
    def _safe_file_stem(name: str) -> str:
        return re.sub(r'[\\/:*?"<>|]', '_', name).strip() or 'untitled'

    def _write_scheme_file(self, fp: str, name: str, scheme: dict):
        """Write *scheme* as a .pvizc: its colours, plus the colours of its palette."""
        import zipfile as _zf, json as _json
        from ui.tab_builders import get_all_palettes
        payload = {'_app': 'plotviz', '_file_type': 'color_scheme', '_scheme_name': name}
        payload.update(scheme)
        pal = scheme.get('color_palette')
        if pal in get_all_palettes():           # the file carries the colours, not only the name
            payload['_palette'] = {'name': pal, 'colors': list(get_all_palettes()[pal])}
        with _zf.ZipFile(fp, 'w', _zf.ZIP_DEFLATED) as zf:
            zf.writestr('settings.json', _json.dumps(payload, indent=2))

    def _read_scheme_file(self, fp: str):
        """Read a .pvizc (or a template) → (name, scheme); registers a palette it carries.

        Returns None when the file holds no colour settings.
        """
        import zipfile as _zf, json as _json
        with _zf.ZipFile(fp, 'r') as zf:
            payload = _json.loads(zf.read('settings.json'))
        name = payload.get('_scheme_name') or os.path.splitext(os.path.basename(fp))[0]
        self._adopt_palette_from_scheme_file(payload)
        scheme = {k: payload[k] for k in self._COLOR_SCHEME_KEYS if k in payload}
        return (name, scheme) if scheme else None

    def _scheme_in_library(self, fp: str) -> bool:
        import config.settings as settings
        return settings.in_folder(fp, settings.schemes_dir())

    def _load_library_schemes(self):
        """Register every scheme found in the schemes folder (called at start-up)."""
        import logging
        import config.settings as settings
        for fp in sorted(settings.schemes_dir().glob('*.pvizc'), key=lambda f: f.name.casefold()):
            try:
                got = self._read_scheme_file(str(fp))
            except Exception:  # noqa: BLE001 - one bad file must not stop the others
                logging.getLogger('plotviz').warning('skipped colour scheme %s', fp, exc_info=True)
                continue
            if got:
                self._register_scheme(got[0], got[1], unsaved=False)
        self._rebuild_scheme_combo()

    def _save_color_scheme(self):
        """Save the active scheme as a .pvizc, by default in the schemes folder."""
        import config.settings as settings
        from ui.helpers import _remember_dir

        old = self._active_scheme
        if old in self._BUILTIN_COLOR_SCHEMES:
            QMessageBox.information(
                self, 'Built-in scheme',
                f'"{old}" is a built-in scheme and is always available.\n'
                'Use Edit scheme… to make a copy of your own, then save that.')
            return
        fp, _ = QFileDialog.getSaveFileName(
            self, 'Save Color Scheme',
            os.path.join(str(settings.schemes_dir()), self._safe_file_stem(old) + '.pvizc'),
            'plotviz Color Scheme (*.pvizc);;All Files (*)')
        if not fp:
            return
        _remember_dir(fp)
        if not fp.endswith('.pvizc'):
            fp += '.pvizc'
        name = os.path.splitext(os.path.basename(fp))[0]   # the file name is the scheme name
        try:
            scheme = self._scheme_from_current_settings()
            self._write_scheme_file(fp, name, scheme)
            inside = self._scheme_in_library(fp)
            # A session-only scheme saved under a new name is renamed, not duplicated.
            if old != name and old in self._scheme_unsaved:
                self._remove_scheme(old)
            self._select_scheme(self._register_scheme(name, scheme, unsaved=not inside))
            note = ('' if inside else
                    '\n\nIt is outside the plotviz schemes folder, so it is not loaded '
                    'automatically at start-up (it stays marked with a *).')
            QMessageBox.information(self, 'Saved', f'Color scheme saved:\n{fp}{note}')
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
            QMessageBox.critical(self, 'Error', str(e))

    def _load_color_scheme(self):
        """Load one .pvizc file and register it in the combo."""
        from ui.helpers import _get_dir, _remember_dir

        fp, _ = QFileDialog.getOpenFileName(
            self, 'Load Color Scheme', _get_dir(),
            'plotviz Color Scheme (*.pvizc);;All Files (*)')
        if not fp:
            return
        _remember_dir(fp)
        try:
            got = self._read_scheme_file(fp)
            if not got:
                QMessageBox.warning(self, 'Invalid', 'No color settings found in this file.')
                return
            name = self._register_scheme(got[0], got[1], unsaved=not self._scheme_in_library(fp))
            self._rebuild_scheme_combo()

            target = self._scheme_target_subplot()
            where = 'to the whole figure' if target is None else f'to subplot {target + 1}'
            reply = QMessageBox.question(
                self, 'Apply?',
                f'Scheme "{name}" loaded.\nApply it {where} now?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._activate_scheme(name)
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
            QMessageBox.critical(self, 'Error', str(e))

    def _load_color_scheme_from_path(self, fp: str):
        """Load a .pvizc directly from *fp* (no dialog — Finder/cold-launch)."""
        try:
            got = self._read_scheme_file(fp)
            if not got:
                return
            name = self._register_scheme(got[0], got[1], unsaved=not self._scheme_in_library(fp))
            self._activate_scheme(name)
        except Exception as e:  # noqa: BLE001 - error boundary: the failure is reported to the user
            QMessageBox.critical(self, 'Error', str(e))
