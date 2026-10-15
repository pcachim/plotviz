"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_style.py  –  plotviz
StyleTabMixin: create_style_tab(): the Layout & Style tab (figure size, margins, subplots,
title, colour scheme and palette).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton, QCheckBox, QScrollArea,
)
from ui.collapsible import CollapsibleSection
from ui.tab_constants import (
    _FONTS, COLOR_PALETTES,
)


class StyleTabMixin:
    def _refresh_style_summaries(self):
        """Update the one-line summary each closed Layout & Style section shows."""
        for sec in getattr(self, '_style_sections', ()):
            sec.refresh_summary()

    # ─── Style tab ────────────────────────────────────────────────────────────
    def create_style_tab(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        main = QVBoxLayout(content)
        main.setSpacing(4)
        layout = main          # where the row helpers add: the open section's body
        sections = []

        def open_section(title, key, expanded=True, summary=None):
            """Start a collapsible section; the following rows go into its body."""
            nonlocal layout
            sec = CollapsibleSection(title, key, expanded, summary)
            main.addWidget(sec)
            sections.append(sec)
            layout = sec.body_layout

        # ── Figure: size and margins ──────────────────────────────────────────
        open_section('Figure', 'figure', True, lambda:
                     f'{self.fig_width.value():g} × {self.fig_height.value():g} '
                     f'{self.fig_unit.currentText()}')

        # Presets row
        pr = QHBoxLayout()
        pr.setSpacing(6)
        pr.addWidget(QLabel('Preset:'))
        self.fig_preset_combo = QComboBox()
        self._fig_presets = [
            ('20 × 10 cm',   20.0, 10.0),
            ('20 × 12.5 cm', 20.0, 12.5),
            ('20 × 15 cm',   20.0, 15.0),
            ('20 × 17.5 cm', 20.0, 17.5),
            ('20 × 20 cm',   20.0, 20.0),
            ('Custom',        None, None),
        ]
        self.fig_preset_combo.addItems([p[0] for p in self._fig_presets])
        self.fig_preset_combo.setCurrentIndex(2)   # default: 20 × 15 cm
        self.fig_preset_combo.currentIndexChanged.connect(self._on_fig_preset_changed)
        pr.addWidget(self.fig_preset_combo)
        pr.addStretch()
        layout.addLayout(pr)

        # Units + W + H on one row
        sz_row = QHBoxLayout()
        sz_row.setSpacing(6)
        sz_row.addWidget(QLabel('Units:'))
        self.fig_unit = QComboBox()
        self.fig_unit.addItems(['cm', 'inches', 'pixels'])
        self.fig_unit.setFixedWidth(70)
        self.fig_unit.currentTextChanged.connect(self._on_fig_unit_changed)
        sz_row.addWidget(self.fig_unit)
        sz_row.addWidget(QLabel('W:'))
        self.fig_width = QDoubleSpinBox()
        self.fig_width.setDecimals(1)
        self.fig_width.setRange(2, 200)
        self.fig_width.setValue(20.0)
        self.fig_width.setSingleStep(0.5)
        self.fig_width.valueChanged.connect(self._on_figsize_manual_change)
        sz_row.addWidget(self.fig_width)
        sz_row.addWidget(QLabel('H:'))
        self.fig_height = QDoubleSpinBox()
        self.fig_height.setDecimals(1)
        self.fig_height.setRange(2, 200)
        self.fig_height.setValue(15.0)
        self.fig_height.setSingleStep(0.5)
        self.fig_height.valueChanged.connect(self._on_figsize_manual_change)
        sz_row.addWidget(self.fig_height)
        sz_row.addStretch()
        layout.addLayout(sz_row)
        # ── Margins (2-column layout) ─────────────────────────────────────────
        layout.addWidget(self._sec_label('Margins'))
        margins_grid = QHBoxLayout()
        margins_grid.setSpacing(10)
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()
        # Shown in physical units (fig_unit) but stored as fractions of the figure
        # (self._fig_margins); the defaults are 0.10 / 0.95 / 0.10 / 0.95, i.e.
        # 2 / 19 / 1.5 / 14.25 cm on the default 20 × 15 cm figure.
        for idx, (attr, label, col) in enumerate([
            ('fig_left',   'Left',   left_col),
            ('fig_right',  'Right',  right_col),
            ('fig_bottom', 'Bottom', left_col),
            ('fig_top',    'Top',    right_col),
        ]):
            mr = QHBoxLayout()
            mr.setSpacing(4)
            lbl = QLabel(label)
            lbl.setFixedWidth(44)
            mr.addWidget(lbl)
            sp = QDoubleSpinBox()
            sp.setFixedWidth(66)
            # Range, decimals and value come from _refresh_geometry_widgets below.
            sp.valueChanged.connect(lambda v, i=idx: self._on_margin_edited(i, v))
            setattr(self, attr, sp)
            mr.addWidget(sp)
            col.addLayout(mr)
        margins_grid.addLayout(left_col)
        margins_grid.addLayout(right_col)
        margins_grid.addStretch()
        layout.addLayout(margins_grid)
        self.margin_mask_btn = QPushButton('Show margin mask')
        self.margin_mask_btn.setCheckable(True)
        self.margin_mask_btn.setToolTip(
            'Shade the margins on the preview so you can see which area they control.\n'
            'Preview only: it is never part of an exported file.')
        self.margin_mask_btn.toggled.connect(self.update_preview)
        layout.addWidget(self.margin_mask_btn)
        # ── Subplot Grid ──────────────────────────────────────────────────────
        self._subplot_grid_panel = QWidget()
        pl = QVBoxLayout(self._subplot_grid_panel)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(6)
        # sp_rows / sp_cols / sp_sharex / sp_sharey are kept as hidden widgets so
        # serialisation and on_subplot_layout_changed continue to work unchanged.
        self.sp_rows = QSpinBox()
        self.sp_rows.setRange(1, 8)
        self.sp_rows.setValue(1)
        self.sp_rows.valueChanged.connect(lambda _: self.on_subplot_layout_changed())
        self.sp_rows.setVisible(False)
        self.sp_cols = QSpinBox()
        self.sp_cols.setRange(1, 8)
        self.sp_cols.setValue(1)
        self.sp_cols.valueChanged.connect(lambda _: self.on_subplot_layout_changed())
        self.sp_cols.setVisible(False)
        self.sp_sharex = QCheckBox('Share X')
        self.sp_sharex.stateChanged.connect(self.update_preview)
        self.sp_sharex.setVisible(False)
        self.sp_sharey = QCheckBox('Share Y')
        self.sp_sharey.stateChanged.connect(self.update_preview)
        self.sp_sharey.setVisible(False)
        btn_subplot_cfg = QPushButton('⚙️  Configure Subplot Layout…')
        btn_subplot_cfg.setToolTip('Pick a preset or draw a custom mosaic layout')
        btn_subplot_cfg.clicked.connect(self._open_subplot_config_dialog)
        pl.addWidget(btn_subplot_cfg)

        # ── Subplots: grid and spacing ────────────────────────────────────────
        main.addWidget(self._hline())
        open_section('Subplots', 'subplots', False, lambda:
                     f'{self.sp_rows.value()} × {self.sp_cols.value()}')
        layout.addWidget(self._subplot_grid_panel)

        # Subplot spacing (hspace / wspace)
        sp_row = QHBoxLayout()
        sp_row.setSpacing(6)
        sp_row.addWidget(QLabel('H spacing:'))
        self.sp_hspace = QDoubleSpinBox()
        self.sp_hspace.setRange(0.0, 1.0)
        self.sp_hspace.setSingleStep(0.05)
        self.sp_hspace.setDecimals(2)
        self.sp_hspace.setValue(0.35)
        self.sp_hspace.setFixedWidth(66)
        self.sp_hspace.setToolTip('Vertical gap between subplot rows')
        self.sp_hspace.valueChanged.connect(self.update_preview)
        sp_row.addWidget(self.sp_hspace)
        sp_row.addWidget(QLabel('W spacing:'))
        self.sp_wspace = QDoubleSpinBox()
        self.sp_wspace.setRange(0.0, 1.0)
        self.sp_wspace.setSingleStep(0.05)
        self.sp_wspace.setDecimals(2)
        self.sp_wspace.setValue(0.35)
        self.sp_wspace.setFixedWidth(66)
        self.sp_wspace.setToolTip('Horizontal gap between subplot columns')
        self.sp_wspace.valueChanged.connect(self.update_preview)
        sp_row.addWidget(self.sp_wspace)
        sp_row.addStretch()
        layout.addLayout(sp_row)
        # Dummy preset_combo to keep _collect_settings/_apply_settings happy
        self.preset_combo = QComboBox()
        self.preset_combo.setVisible(False)
        layout.addWidget(self.preset_combo)

        # ── Chart Title ───────────────────────────────────────────────────────
        main.addWidget(self._hline())
        open_section('Title', 'title', False, lambda:
                     (self.title_input.text() or '(empty)') if self.title_check.isChecked()
                     else '(hidden)')
        title_row = QHBoxLayout()
        self.title_check = QCheckBox('Show Title')
        self.title_check.setChecked(True)
        self.title_check.stateChanged.connect(self.update_preview)
        title_row.addWidget(self.title_check)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText('Main title')
        self.title_input.editingFinished.connect(self.update_preview)
        title_row.addWidget(self.title_input)
        layout.addLayout(title_row)
        tfont_row = QHBoxLayout()
        tfont_row.addWidget(QLabel('Font:'))
        self.title_font = QComboBox()
        self.title_font.addItems(_FONTS)
        self.title_font.currentTextChanged.connect(self.update_preview)
        tfont_row.addWidget(self.title_font)
        tfont_row.addWidget(QLabel('Size:'))
        self.title_size = QSpinBox()
        self.title_size.setRange(6,32)
        self.title_size.setValue(14)
        self.title_size.valueChanged.connect(self.update_preview)
        tfont_row.addWidget(self.title_size)
        tfont_row.addStretch()
        layout.addLayout(tfont_row)
        tcolor_row = QHBoxLayout()
        tcolor_row.setSpacing(6)
        tcolor_row.addWidget(QLabel('Color:'))
        self.title_color_swatch = self._color_sw('#000000')
        tcolor_row.addWidget(self.title_color_swatch)
        self.title_color = '#000000'
        tbtn = QPushButton('…')
        tbtn.setFixedWidth(28)
        tbtn.clicked.connect(lambda: self.pick_color('title'))
        tcolor_row.addWidget(tbtn)
        tcolor_row.addStretch()
        layout.addLayout(tcolor_row)

        # Position, rotation and alignment are rarely touched: a nested, closed section.
        title_body = layout
        pos_sec = CollapsibleSection('Position & rotation', 'title_position', False)
        title_body.addWidget(pos_sec)
        layout = pos_sec.body_layout

        # Chart title X / Y position, shown in physical units (fig_unit) but stored as
        # fractions of the figure (self._title_frac). _refresh_geometry_widgets (called
        # once all the size widgets exist) fills in range, decimals and value.
        _DEFAULT_W_CM, _DEFAULT_H_CM = 20.0, 15.0
        tpos_row = QHBoxLayout()
        tpos_row.setSpacing(4)
        tpos_row.addWidget(QLabel('X:'))
        self.title_x = QDoubleSpinBox()
        self.title_x.setRange(0.0, _DEFAULT_W_CM)
        self.title_x.setSingleStep(0.1)
        self.title_x.setDecimals(1)
        self.title_x.setFixedWidth(66)
        self.title_x.valueChanged.connect(lambda v: self._on_title_pos_edited(0, v))
        self.title_x.setToolTip('Horizontal position of title (physical units, 0 = left edge)')
        tpos_row.addWidget(self.title_x)
        tpos_row.addWidget(QLabel('Y:'))
        self.title_y = QDoubleSpinBox()
        self.title_y.setRange(0.0, _DEFAULT_H_CM)
        self.title_y.setSingleStep(0.1)
        self.title_y.setDecimals(1)
        self.title_y.setFixedWidth(66)
        self.title_y.valueChanged.connect(lambda v: self._on_title_pos_edited(1, v))
        self.title_y.setToolTip('Vertical position of title (physical units, 0 = bottom edge)')
        tpos_row.addWidget(self.title_y)
        tpos_row.addStretch()
        layout.addLayout(tpos_row)
        # Keep title_y_offset as hidden alias for serialization compat
        self.title_y_offset = self.title_y

        # ── Title extra: rotation + alignment ────────────────────────────────
        textra_row = QHBoxLayout()
        textra_row.setSpacing(4)
        textra_row.addWidget(QLabel('Rot:'))
        self.title_rotation = QSpinBox()
        self.title_rotation.setRange(-180, 180)
        self.title_rotation.setValue(0)
        self.title_rotation.setFixedWidth(52)
        self.title_rotation.setToolTip('Rotation of the title text in degrees')
        self.title_rotation.valueChanged.connect(self.update_preview)
        textra_row.addWidget(self.title_rotation)
        textra_row.addWidget(QLabel('Align:'))
        self.title_ha = QComboBox()
        self.title_ha.addItems(['center', 'left', 'right'])
        self.title_ha.setFixedWidth(70)
        self.title_ha.setToolTip('Horizontal alignment of the title text')
        self.title_ha.currentTextChanged.connect(self.update_preview)
        textra_row.addWidget(self.title_ha)
        textra_row.addStretch()
        layout.addLayout(textra_row)
        layout = title_body

        # All size, margin and title widgets now exist: start from the default
        # fractions and let them fill in the spinboxes.
        self._fig_margins = list(self._DEFAULT_MARGINS)
        self._title_frac = list(self._DEFAULT_TITLE_FRAC)
        self._refresh_geometry_widgets()

        # ── Color Schemes ─────────────────────────────────────────────────────
        self._scheme_panel = QWidget()
        pl = QVBoxLayout(self._scheme_panel)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(6)
        pl.addWidget(self._sec_label('Color Schemes'))

        cs_sel_row = QHBoxLayout()
        cs_sel_row.setSpacing(4)
        self._cs_combo = QComboBox()
        self._cs_combo.setToolTip('Choose a colour scheme; it is applied at once. Edits to the colours go into the active scheme\n(a built-in is copied first). A * marks a scheme that exists only in this session.')
        cs_sel_row.addWidget(self._cs_combo, 1)
        pl.addLayout(cs_sel_row)

        cs_target_row = QHBoxLayout()
        cs_target_row.setSpacing(4)
        cs_target_row.addWidget(QLabel('Apply to:'))
        self._cs_target = QComboBox()
        self._cs_target.addItems(['All subplots', 'Active subplot only'])
        self._cs_target.setToolTip(
            'Active subplot only changes that subplot\'s plot area, axes colour, borders,\n'
            'grid and title colour. Figure background, palette, fonts and axis-label\n'
            'colours belong to the whole figure and stay as they are.')
        self._cs_target.setEnabled(False)          # needs more than one subplot
        cs_target_row.addWidget(self._cs_target, 1)
        pl.addLayout(cs_target_row)

        cs_btn_row = QHBoxLayout()
        cs_btn_row.setSpacing(4)
        for text, tip, slot in (
                ('✏️ Edit', 'Create or edit a colour scheme: colours, grid, borders and palette',
                 self._open_scheme_editor),
                ('📂 Load', 'Load a .pvizc colour scheme file', self._load_color_scheme),
                ('💾 Save', 'Save the active colour scheme as a .pvizc file '
                            '(a * marks schemes that are not in the schemes folder)',
                 self._save_color_scheme)):
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            cs_btn_row.addWidget(btn, 1)       # three equal buttons across the full width
        pl.addLayout(cs_btn_row)

        # Populate built-in schemes and set initial swatch
        self._init_color_schemes()

        # ── Colour palette ────────────────────────────────────────────────────
        self._palette_panel = QWidget()
        pl = QVBoxLayout(self._palette_panel)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(6)
        pl.addWidget(self._sec_label('Colour Palette'))
        pal_row = QHBoxLayout()
        pal_row.setSpacing(6)
        self.palette_combo = QComboBox()
        self._palette_unsaved = set()        # your palettes that exist only in this session
        self._rebuild_palette_combo()
        self.palette_combo.currentIndexChanged.connect(self._on_palette_picked)
        pal_row.addWidget(self.palette_combo, 1)
        pl.addLayout(pal_row)
        self._palette_swatch_row = QHBoxLayout()
        self._palette_swatch_row.setSpacing(2)
        self._palette_swatches = []
        for _ in range(16):
            sw = QLabel()
            sw.setFixedSize(18, 14)
            sw.setStyleSheet('background:#ccc; border:1px solid #aaa;')
            self._palette_swatches.append(sw)
            self._palette_swatch_row.addWidget(sw)
        self._palette_swatch_row.addStretch()
        pl.addLayout(self._palette_swatch_row)
        pal_btn_row = QHBoxLayout()
        pal_btn_row.setSpacing(4)
        for text, tip, slot in (
                ('✏️ Edit', 'Create or edit a palette of your own (built-in palettes are read-only)',
                 self._open_palette_editor),
                ('📂 Load', 'Load a palette from a .pvizp file', self._import_palette_bundle),
                ('💾 Save', 'Save the active palette to a .pvizp file '
                            '(a * marks palettes that are not in the palettes folder)',
                 self._export_palette_bundle)):
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            pal_btn_row.addWidget(btn, 1)      # three equal buttons across the full width
        pl.addLayout(pal_btn_row)
        btn_reset_locks = QPushButton('↺ Re-apply palette')
        btn_reset_locks.setToolTip('Give every series its palette colour again, including series '
                                   'whose colour you set by hand')
        btn_reset_locks.clicked.connect(self._reset_all_color_locks)
        pl.addWidget(btn_reset_locks)
        self._refresh_palette_swatches()

        # ── Colors: scheme and palette (whole figure), then manual
        # background / foreground overrides ────────────────────────────────────
        main.addWidget(self._hline())
        open_section('Colors', 'colors', True, lambda:
                     f'{self._cs_combo.currentText()} · {self.palette_combo.currentText()}')
        layout.addWidget(self._scheme_panel)
        layout.addWidget(self._hline())
        layout.addWidget(self._palette_panel)

        # Figure background and foreground are edited in the scheme editor. Their state
        # and swatches stay here, unshown, for serialisation and pick_color.
        for attr, default_hex in (('chart_bg_color', '#ffffff'), ('chart_fg_color', '#000000')):
            setattr(self, attr, default_hex)
            sw = self._color_sw(default_hex)
            sw.setVisible(False)
            layout.addWidget(sw)
            setattr(self, attr + '_swatch', sw)

        layout = main
        layout.addStretch()
        self._style_sections = sections
        self._refresh_style_summaries()
        scroll.setWidget(content)
        mlay = QVBoxLayout(widget)
        mlay.addWidget(scroll)
        self.tabs.addTab(widget, 'Layout && Style')   # &&: a single & in Qt tab text
