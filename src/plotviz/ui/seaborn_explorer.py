"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.

ui/seaborn_explorer.py  –  plotviz
Seaborn Explorer: a self-contained QDialog that hosts all Seaborn chart types
on their own FigureCanvas, fully isolated from the main chart canvas so that
figure-level SNS plots (Pairplot, Joint, Catplot, Heatmap) never conflict with
plotviz's _decorate / _apply_canvas_style pipeline.
"""

from __future__ import annotations

import io
import logging
import re
import traceback
import numpy as np

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QListWidget,
    QListWidgetItem, QPushButton, QSplitter, QWidget, QScrollArea,
    QFileDialog, QMessageBox, QSizePolicy, QAbstractItemView,
)
from PyQt6.QtCore import Qt

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

try:
    import seaborn as sns
    _SNS_OK = True
except ImportError:
    _SNS_OK = False

try:
    import statsmodels  # noqa: F401
    _STATSMODELS_OK = True
except ImportError:
    _STATSMODELS_OK = False

log = logging.getLogger('plotviz')

# ── Chart-type metadata ───────────────────────────────────────────────────────
# Each entry: (label, needs_xy, has_col_picker, description)
_CHART_TYPES = [
    ('KDE',        True,  False, 'Kernel Density Estimate — smoothed distribution curve'),
    ('Regression', True,  False, 'Scatter + OLS/polynomial/LOWESS regression line'),
    ('Strip',      True,  False, 'Categorical scatter with jitter'),
    ('Swarm',      True,  False, 'Categorical beeswarm (non-overlapping)'),
    ('Heatmap',    False, True,  'Correlation matrix heatmap — pick columns below'),
    ('Pairplot',   False, True,  'All-vs-all scatterplot grid — pick columns below'),
    ('Joint',      True,  False, 'Bivariate joint distribution with marginals'),
    ('Catplot',    True,  False, 'Figure-level categorical plot (box/violin/bar/strip/...)'),
]
_CHART_NAMES = [t[0] for t in _CHART_TYPES]

# ── Seaborn named palettes available as color themes ─────────────────────────
_SNS_THEMES = [
    'plotviz',      # uses the current plotviz palette (default)
    'deep',
    'muted',
    'pastel',
    'bright',
    'dark',
    'colorblind',
    'tab10',
    'Set1',
    'Set2',
    'Set3',
    'Paired',
    'husl',
    'hls',
    'rocket',
    'mako',
    'flare',
    'crest',
    'viridis',
    'plasma',
    'magma',
    'inferno',
]

# Strip characters that break matplotlib's LaTeX renderer
_LATEX_UNSAFE = re.compile(r'[\^~_\\{}&\$%#\x00-\x1f]')

def _safe_text(s: str) -> str:
    return _LATEX_UNSAFE.sub(' ', str(s))


class _Spin(QDoubleSpinBox):
    def __init__(self, lo, hi, val, step=0.05):
        super().__init__()
        self.setRange(lo, hi); self.setValue(val); self.setSingleStep(step)
        self.setDecimals(2)

class _ISpin(QSpinBox):
    def __init__(self, lo, hi, val):
        super().__init__()
        self.setRange(lo, hi); self.setValue(val)

def _combo(items, current=0):
    c = QComboBox(); c.addItems(items); c.setCurrentIndex(current); return c


class SeabornExplorer(QDialog):
    def __init__(self, datasets: dict, palette: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle('Seaborn Explorer')
        self.resize(1200, 740)
        self.setMinimumSize(900, 560)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.datasets = datasets
        self.palette  = palette
        self._build_ui()
        self._populate_col_combos()
        self._on_type_changed()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left panel
        ctrl_scroll = QScrollArea()
        ctrl_scroll.setWidgetResizable(True)
        ctrl_scroll.setFixedWidth(310)
        ctrl_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        ctrl_widget = QWidget()
        ctrl_scroll.setWidget(ctrl_widget)
        self._ctrl_layout = QVBoxLayout(ctrl_widget)
        self._ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._ctrl_layout.setSpacing(6)

        self._build_type_selector()
        self._build_theme_selector()
        self._build_column_selectors()
        self._build_col_picker()
        self._build_kde_panel()
        self._build_regression_panel()
        self._build_strip_panel()
        self._build_swarm_panel()
        self._build_heatmap_panel()
        self._build_pairplot_panel()
        self._build_joint_panel()
        self._build_catplot_panel()
        self._ctrl_layout.addStretch()
        splitter.addWidget(ctrl_scroll)

        # Right panel
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(2)

        self._canvas_fig = Figure(figsize=(8, 6), dpi=100)
        self._canvas = FigureCanvas(self._canvas_fig)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._toolbar = NavigationToolbar2QT(self._canvas, right)
        rl.addWidget(self._toolbar)
        rl.addWidget(self._canvas)

        btn_row = QHBoxLayout()
        self._btn_draw      = QPushButton('Redraw')
        self._btn_export    = QPushButton('Export...')
        self._btn_py_code   = QPushButton('🐍 Generate Python Code')
        self._btn_to_runner = QPushButton('▶ Open in Code Runner')
        self._btn_close     = QPushButton('Close')
        for b in (self._btn_draw, self._btn_export, self._btn_py_code,
                  self._btn_to_runner, self._btn_close):
            b.setFixedHeight(28)
        self._btn_to_runner.setToolTip(
            'Export the current seaborn chart as a .pvizx bundle and open it in the Code Runner')
        self._btn_to_runner.setStyleSheet(
            'QPushButton { background: #2ecc71; color: white; font-weight: bold; border-radius: 3px; }'
            'QPushButton:hover { background: #27ae60; }'
            'QPushButton:pressed { background: #1e8449; }'
        )

        _initial_dpi = 150
        _p = self.parent()
        if _p is not None and hasattr(_p, 'dpi_spin'):
            _initial_dpi = _p.dpi_spin.value()
        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(72, 600)
        self._dpi_spin.setValue(_initial_dpi)
        self._dpi_spin.setSuffix(' DPI')
        self._dpi_spin.setFixedWidth(90)
        self._dpi_spin.setFixedHeight(28)
        self._dpi_spin.setToolTip('Export resolution (dots per inch)')

        btn_row.addWidget(self._btn_draw)
        btn_row.addSpacing(4)
        btn_row.addWidget(self._dpi_spin)
        btn_row.addWidget(self._btn_export)
        btn_row.addWidget(self._btn_py_code)
        btn_row.addWidget(self._btn_to_runner)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_close)
        rl.addLayout(btn_row)

        splitter.addWidget(right)
        splitter.setSizes([310, 890])
        root.addWidget(splitter)

        self._btn_draw.clicked.connect(self._draw)
        self._btn_export.clicked.connect(self._export)
        self._btn_py_code.clicked.connect(self._generate_python_code)
        self._btn_to_runner.clicked.connect(self._send_to_code_runner)
        self._btn_close.clicked.connect(self.close)

    def _section(self, title):
        gb = QGroupBox(title)
        fl = QFormLayout(gb)
        fl.setVerticalSpacing(4)
        self._ctrl_layout.addWidget(gb)
        return gb, fl

    def _build_type_selector(self):
        gb, fl = self._section('Chart type')
        self._type_combo = _combo(_CHART_NAMES)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        fl.addRow('Type:', self._type_combo)
        self._type_desc = QLabel()
        self._type_desc.setWordWrap(True)
        self._type_desc.setStyleSheet('color: #888; font-size: 11px;')
        fl.addRow(self._type_desc)

    def _build_theme_selector(self):
        gb, fl = self._section('Color theme')
        self._theme_combo = _combo(_SNS_THEMES)
        self._theme_combo.setToolTip(
            '"plotviz" uses your current palette.\n'
            'All other options are seaborn named palettes.'
        )
        self._theme_combo.currentIndexChanged.connect(self._draw)
        fl.addRow('Palette:', self._theme_combo)

    def _build_column_selectors(self):
        gb, fl = self._section('Data columns')
        self._x_combo = QComboBox(); self._x_combo.addItem('(none)')
        self._y_combo = QComboBox(); self._y_combo.addItem('(none)')
        self._hue_combo = QComboBox(); self._hue_combo.addItem('(none)')
        self._style_combo = QComboBox(); self._style_combo.addItem('(none)')
        self._size_combo = QComboBox(); self._size_combo.addItem('(none)')
        fl.addRow('X column:', self._x_combo)
        fl.addRow('Y column:', self._y_combo)
        fl.addRow('Hue (category):', self._hue_combo)
        fl.addRow('Size (category):', self._size_combo)
        fl.addRow('Style (category):', self._style_combo)
        self._col_group = gb

    def _build_col_picker(self):
        gb = QGroupBox('Columns (select >= 2)')
        vl = QVBoxLayout(gb)
        vl.setSpacing(3)
        self._col_list = QListWidget()
        self._col_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._col_list.setFixedHeight(110)
        self._col_list.setToolTip('Select which numeric columns to include.\nHold Cmd/Ctrl to toggle individual items.')
        hint = QLabel('Hold Cmd/Ctrl to toggle items')
        hint.setStyleSheet('color: #888; font-size: 10px;')
        sel_row = QHBoxLayout()
        btn_all  = QPushButton('All');  btn_all.setFixedHeight(22)
        btn_none = QPushButton('None'); btn_none.setFixedHeight(22)
        btn_all.clicked.connect(self._col_list.selectAll)
        btn_none.clicked.connect(self._col_list.clearSelection)
        sel_row.addWidget(btn_all); sel_row.addWidget(btn_none); sel_row.addStretch()
        vl.addWidget(self._col_list)
        vl.addWidget(hint)
        vl.addLayout(sel_row)
        self._ctrl_layout.addWidget(gb)
        self._col_picker_group = gb

    def _build_kde_panel(self):
        gb, fl = self._section('KDE options')
        self._kde_fill   = QCheckBox('Fill'); self._kde_fill.setChecked(True)
        self._kde_cumul  = QCheckBox('Cumulative')
        self._kde_common = QCheckBox('Common norm'); self._kde_common.setChecked(True)
        self._kde_alpha  = _Spin(0.0, 1.0, 0.3)
        self._kde_lw     = _Spin(0.5, 6.0, 1.5, 0.25)
        self._kde_bw     = _Spin(0.1, 5.0, 1.0, 0.1)
        fl.addRow('Fill alpha:', self._kde_alpha)
        fl.addRow('Line width:', self._kde_lw)
        fl.addRow('BW adjust:',  self._kde_bw)
        fl.addRow(self._kde_fill); fl.addRow(self._kde_cumul); fl.addRow(self._kde_common)
        self._kde_panel = gb

    def _build_regression_panel(self):
        gb, fl = self._section('Regression options')
        self._reg_order   = _ISpin(1, 6, 1)
        self._reg_ci      = _ISpin(0, 99, 95)
        self._reg_size    = _ISpin(10, 300, 40)
        self._reg_alpha   = _Spin(0.05, 1.0, 0.6)
        self._reg_robust  = QCheckBox('Robust fit')
        self._reg_lowess  = QCheckBox('LOWESS')
        self._reg_scatter = QCheckBox('Show scatter'); self._reg_scatter.setChecked(True)
        if not _STATSMODELS_OK:
            _tip = 'Requires statsmodels: pip install statsmodels'
            for chk in (self._reg_robust, self._reg_lowess):
                chk.setEnabled(False)
                chk.setToolTip(_tip)
            self._reg_order.setToolTip('')
        else:
            self._reg_lowess.toggled.connect(self._on_reg_lowess_toggled)
            self._reg_robust.toggled.connect(self._on_reg_robust_toggled)
        fl.addRow('Poly order:',  self._reg_order)
        fl.addRow('CI %:',        self._reg_ci)
        fl.addRow('Marker size:', self._reg_size)
        fl.addRow('Alpha:',       self._reg_alpha)
        fl.addRow(self._reg_robust); fl.addRow(self._reg_lowess); fl.addRow(self._reg_scatter)
        if not _STATSMODELS_OK:
            note = QLabel('statsmodels not installed')
            note.setStyleSheet('color: #e67e22; font-size: 10px;')
            fl.addRow(note)
        self._reg_panel = gb

    def _on_reg_lowess_toggled(self, checked: bool):
        if checked:
            self._reg_robust.setChecked(False)
            self._reg_order.setEnabled(False)
            self._reg_order.setToolTip('Disabled when LOWESS is active')
        else:
            self._reg_order.setEnabled(True)
            self._reg_order.setToolTip('')

    def _on_reg_robust_toggled(self, checked: bool):
        if checked:
            self._reg_lowess.setChecked(False)
            self._reg_order.setValue(1)
            self._reg_order.setEnabled(False)
            self._reg_order.setToolTip('Disabled when Robust fit is active')
        else:
            self._reg_order.setEnabled(True)
            self._reg_order.setToolTip('')

    def _build_strip_panel(self):
        gb, fl = self._section('Strip options')
        self._strip_size   = _Spin(1.0, 20.0, 5.0, 0.5)
        self._strip_alpha  = _Spin(0.05, 1.0, 0.7)
        self._strip_jitter = _Spin(0.0, 0.5, 0.2)
        fl.addRow('Marker size:', self._strip_size)
        fl.addRow('Alpha:',       self._strip_alpha)
        fl.addRow('Jitter:',      self._strip_jitter)
        self._strip_panel = gb

    def _build_swarm_panel(self):
        gb, fl = self._section('Swarm options')
        self._swarm_size  = _Spin(1.0, 20.0, 5.0, 0.5)
        self._swarm_alpha = _Spin(0.05, 1.0, 0.8)
        fl.addRow('Marker size:', self._swarm_size)
        fl.addRow('Alpha:',       self._swarm_alpha)
        self._swarm_panel = gb

    def _build_heatmap_panel(self):
        gb, fl = self._section('Heatmap options')
        self._heat_cmap   = _combo(['coolwarm','viridis','plasma','RdBu','Blues',
                                    'Reds','YlOrRd','magma','rocket','mako'])
        self._heat_fmt    = _combo(['.2f', '.1f', '.0f', '.2g', 'd', ''])
        self._heat_lw     = _Spin(0.0, 3.0, 0.5, 0.25)
        self._heat_annot  = QCheckBox('Annotate cells'); self._heat_annot.setChecked(True)
        self._heat_square = QCheckBox('Square cells');   self._heat_square.setChecked(True)
        self._heat_cbar   = QCheckBox('Show colorbar');  self._heat_cbar.setChecked(True)
        self._heat_robust = QCheckBox('Robust scale')
        fl.addRow('Colormap:', self._heat_cmap); fl.addRow('Format:', self._heat_fmt)
        fl.addRow('Line width:', self._heat_lw)
        fl.addRow(self._heat_annot); fl.addRow(self._heat_square)
        fl.addRow(self._heat_cbar);  fl.addRow(self._heat_robust)
        self._heat_panel = gb

    def _build_pairplot_panel(self):
        gb, fl = self._section('Pairplot options')
        self._pair_diag  = _combo(['auto', 'hist', 'kde'])
        self._pair_kind  = _combo(['scatter', 'kde', 'hist', 'reg'])
        self._pair_alpha = _Spin(0.05, 1.0, 0.7)
        fl.addRow('Diagonal:', self._pair_diag)
        fl.addRow('Off-diag:', self._pair_kind)
        fl.addRow('Alpha:',    self._pair_alpha)
        self._pair_panel = gb

    def _build_joint_panel(self):
        gb, fl = self._section('Joint plot options')
        self._joint_kind    = _combo(['scatter','kde','hist','hex','reg','resid'])
        self._joint_alpha   = _Spin(0.05, 1.0, 0.6)
        self._joint_ratio   = _ISpin(2, 10, 5)
        self._joint_margkde = QCheckBox('Marginal KDE fill')
        fl.addRow('Kind:',  self._joint_kind); fl.addRow('Alpha:', self._joint_alpha)
        fl.addRow('Ratio:', self._joint_ratio); fl.addRow(self._joint_margkde)
        self._joint_panel = gb

    def _build_catplot_panel(self):
        gb, fl = self._section('Catplot options')
        self._cat_kind  = _combo(['box','boxen','violin','bar','point','count','strip','swarm'])
        self._cat_alpha = _Spin(0.05, 1.0, 0.8)
        self._cat_sat   = _Spin(0.1, 1.0, 0.75)
        self._cat_ci    = _combo(['95', '99', 'sd', 'None'])
        self._cat_dodge = QCheckBox('Dodge groups')
        fl.addRow('Kind:', self._cat_kind); fl.addRow('Alpha:', self._cat_alpha)
        fl.addRow('Saturation:', self._cat_sat); fl.addRow('CI:', self._cat_ci)
        fl.addRow(self._cat_dodge)
        self._cat_panel = gb

    # ── State helpers ─────────────────────────────────────────────────────────

    def _all_option_panels(self):
        return [self._kde_panel, self._reg_panel, self._strip_panel,
                self._swarm_panel, self._heat_panel, self._pair_panel,
                self._joint_panel, self._cat_panel]

    def _panel_for(self, name):
        return {'KDE': self._kde_panel, 'Regression': self._reg_panel,
                'Strip': self._strip_panel, 'Swarm': self._swarm_panel,
                'Heatmap': self._heat_panel, 'Pairplot': self._pair_panel,
                'Joint': self._joint_panel, 'Catplot': self._cat_panel}[name]

    def _on_type_changed(self):
        name = self._type_combo.currentText()
        has_col_picker = False
        for lbl, uses_xy, cp, desc in _CHART_TYPES:
            if lbl == name:
                self._type_desc.setText(desc)
                has_col_picker = cp
                break
        for p in self._all_option_panels():
            p.setVisible(False)
        self._panel_for(name).setVisible(True)
        self._col_group.setVisible(not has_col_picker)
        self._col_picker_group.setVisible(has_col_picker)
        self._draw()

    def _populate_col_combos(self):
        numeric_cols = [k for k, v in self.datasets.items()
                        if v is not None and len(v) > 0 and not self._is_cat(v)]
        all_cols = list(self.datasets.keys())
        cat_cols = [k for k, v in self.datasets.items()
                    if v is not None and len(v) > 0 and self._is_cat(v)]

        for combo, cols in [
                (self._x_combo, all_cols),
                (self._y_combo, numeric_cols),
                (self._hue_combo, cat_cols),
                (self._size_combo, cat_cols),
                (self._style_combo, cat_cols),
                ]:
            prev = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem('(none)')
            combo.addItems(cols)
            idx = combo.findText(prev)
            combo.setCurrentIndex(max(idx, 0))
            combo.blockSignals(False)

        prev_selected = {self._col_list.item(i).text()
                         for i in range(self._col_list.count())
                         if self._col_list.item(i).isSelected()}
        self._col_list.blockSignals(True)
        self._col_list.clear()
        for col in numeric_cols:
            item = QListWidgetItem(col)
            self._col_list.addItem(item)
            # Select all by default on first load; otherwise restore prior selection
            if not prev_selected or col in prev_selected:
                item.setSelected(True)
        self._col_list.blockSignals(False)

    def _get_hue(self):
        name = self._hue_combo.currentText()
        if name == '(none)' or name not in self.datasets:
            return None, ''
        return self.datasets[name], name

    def _get_size(self):
        name = self._size_combo.currentText()
        if name == '(none)' or name not in self.datasets:
            return None, ''
        return self.datasets[name], name

    def _get_style(self):
        name = self._style_combo.currentText()
        if name == '(none)' or name not in self.datasets:
            return None, ''
        return self.datasets[name], name

    @staticmethod
    def _is_cat(arr):
        try:
            return arr is not None and hasattr(arr, 'dtype') and arr.dtype.kind in ('U', 'S', 'O')
        except Exception:
            return False

    def _get_col(self, combo):
        name = combo.currentText()
        if name == '(none)' or name not in self.datasets:
            return None, ''
        return self.datasets[name], name

    def _selected_numeric_df(self):
        import pandas as pd
        selected = {self._col_list.item(i).text()
                    for i in range(self._col_list.count())
                    if self._col_list.item(i).isSelected()}
        cols = {k: v for k, v in self.datasets.items()
                if k in selected and v is not None and len(v) > 0 and not self._is_cat(v)}
        if not cols:
            return None
        min_len = min(len(v) for v in cols.values())
        return pd.DataFrame({k: v[:min_len].astype(float) for k, v in cols.items()})

    def _sns_palette(self, n=10):
        """Return a list of colours honoring the selected colour theme."""
        theme = self._theme_combo.currentText() if hasattr(self, '_theme_combo') else 'plotviz'
        if theme == 'plotviz':
            pal = self.palette[:n] if len(self.palette) >= n else self.palette
            return pal
        try:
            import seaborn as _sns
            pal = _sns.color_palette(theme, n)
            return [f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}' for r,g,b in pal]
        except Exception:
            return self.palette[:n] if len(self.palette) >= n else self.palette

    def _sns_palette_name(self):
        """Return the seaborn palette name, or None if using plotviz colours."""
        theme = self._theme_combo.currentText() if hasattr(self, '_theme_combo') else 'plotviz'
        return None if theme == 'plotviz' else theme

    # ── Python Bundle Export (.pvizx) ─────────────────────────────────────────

    def _collect_sns_export_data(self) -> tuple[str, dict] | None:
        """Collect (chart_name, datasets_to_export) for the current chart state.

        Returns None and shows a warning dialog if no data is available.
        """
        from PyQt6.QtWidgets import QMessageBox
        name = self._type_combo.currentText()
        datasets_to_export: dict = {}

        def _add(combo):
            if combo is None:
                return
            txt = combo.currentText()
            if txt and txt != '(none)' and txt in self.datasets:
                datasets_to_export[txt] = self.datasets[txt]

        _add(self._x_combo)
        _add(self._y_combo)
        if name in ('Heatmap', 'Pairplot'):
            for i in range(self._col_list.count()):
                item = self._col_list.item(i)
                if item.isSelected():
                    col = item.text()
                    if col in self.datasets:
                        datasets_to_export[col] = self.datasets[col]
        if name == 'Pairplot':
            _add(self._hue_combo)
        if not datasets_to_export:
            datasets_to_export = dict(self.datasets)
        if not datasets_to_export:
            QMessageBox.warning(self, 'No data',
                'No datasets are loaded — nothing to export.')
            return None
        return name, datasets_to_export

    def _build_sns_pvizx(self, name: str, datasets_to_export: dict) -> bytes:
        """Build and return the raw bytes of a .pvizx zip for the current seaborn chart."""
        import csv as _csv
        import io as _io
        import zipfile as _zf
        import textwrap as _tw
        from .python_export import generate_sns_plot_script

        script = generate_sns_plot_script(self, name, datasets_to_export)
        readme = _tw.dedent(f"""\
        # SNS {name} — Python Export

        This bundle was exported from **plotviz** (Seaborn Explorer) and contains
        a standalone seaborn script that reproduces your chart without needing plotviz.

        ## Contents

        | File | Description |
        |------|-------------|
        | `plot.py` | Standalone Python script |
        | `data/` | CSV files with the chart datasets |
        | `README.md` | This file |

        ## Requirements

            pip install matplotlib seaborn numpy pandas

        ## Running

            python plot.py

        The script loads data from the `data/` folder relative to its own location,
        so keep `plot.py` and `data/` together.

        ## Datasets ({len(datasets_to_export)} column(s))

        {"".join(f"- `{k}` ({len(v)} rows)\n" for k, v in datasets_to_export.items())}
        ---
        *Generated by plotviz Seaborn Explorer*
        """)

        lengths = {len(v) for v in datasets_to_export.values() if v is not None}
        use_combined = len(lengths) == 1
        buf_zip = _io.BytesIO()
        with _zf.ZipFile(buf_zip, 'w', _zf.ZIP_DEFLATED) as zf:
            zf.writestr('plot.py', script)
            zf.writestr('README.md', readme)
            if use_combined:
                buf = _io.StringIO()
                writer = _csv.writer(buf)
                col_names = list(datasets_to_export.keys())
                writer.writerow(col_names)
                n_rows = len(next(iter(datasets_to_export.values())))
                for row_idx in range(n_rows):
                    writer.writerow([
                        datasets_to_export[c][row_idx]
                        if row_idx < len(datasets_to_export[c]) else ''
                        for c in col_names
                    ])
                zf.writestr('data/data.csv', buf.getvalue())
            else:
                for col_name, arr in datasets_to_export.items():
                    buf = _io.StringIO()
                    writer = _csv.writer(buf)
                    writer.writerow([col_name])
                    for v in arr:
                        writer.writerow([v])
                    safe = ''.join(
                        c if c.isalnum() or c in '-_.' else '_'
                        for c in col_name)
                    zf.writestr(f'data/{safe}.csv', buf.getvalue())
        return buf_zip.getvalue()

    def _generate_python_code(self):
        """Export a .pvizx zip bundle: plot.py + data CSVs + README."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        result = self._collect_sns_export_data()
        if result is None:
            return
        name, datasets_to_export = result

        fp, _ = QFileDialog.getSaveFileName(
            self, 'Export Seaborn Python Bundle',
            f'sns_{name.lower()}.pvizx',
            'plotviz Python Bundle (*.pvizx);;All Files (*)')
        if not fp:
            return
        if not fp.endswith('.pvizx'):
            fp += '.pvizx'

        try:
            data = self._build_sns_pvizx(name, datasets_to_export)
            with open(fp, 'wb') as fh:
                fh.write(data)
            QMessageBox.information(self, 'Exported',
                f'Seaborn bundle saved to:\n{fp}\n\n'
                f'Extract the zip and run:  python plot.py')
        except Exception as exc:
            import traceback as _tb
            QMessageBox.critical(self, 'Export error',
                f'{exc}\n\n{_tb.format_exc()}')

    def _send_to_code_runner(self):
        """Build a .pvizx bundle for the current seaborn chart and open it in Code Runner."""
        import tempfile, os
        from PyQt6.QtWidgets import QMessageBox

        result = self._collect_sns_export_data()
        if result is None:
            return
        name, datasets_to_export = result

        main_win = self.parent()
        if main_win is None or not hasattr(main_win, '_open_pvizx_in_code_runner'):
            QMessageBox.warning(self, 'Code Runner unavailable',
                'Cannot reach the main window Code Runner from here.')
            return

        try:
            data = self._build_sns_pvizx(name, datasets_to_export)
            tmp_fd, tmp_fp = tempfile.mkstemp(suffix='.pvizx', prefix='plotviz_sns_cr_')
            os.close(tmp_fd)
            with open(tmp_fp, 'wb') as fh:
                fh.write(data)
            main_win._open_pvizx_in_code_runner(tmp_fp)
        except Exception as exc:
            import traceback as _tb
            QMessageBox.critical(self, 'Code Runner export error',
                f'{exc}\n\n{_tb.format_exc()}')


    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw(self):
        if not _SNS_OK:
            self._show_error('seaborn is not installed.\nRun: pip install seaborn>=0.13')
            return
        if not self.datasets:
            self._show_error('No data loaded.\nLoad a dataset in the main window first.')
            return
        self._populate_col_combos()
        name = self._type_combo.currentText()
        log.debug('SeabornExplorer: drawing %s', name)
        # Disable LaTeX globally inside the explorer — prevents crashes when
        # error messages or axis labels contain LaTeX-special characters.
        with matplotlib.rc_context({'text.usetex': False}):
            try:
                plt.close('all')
                dispatch = {
                    'KDE':        self._draw_kde,
                    'Regression': self._draw_regression,
                    'Strip':      self._draw_strip,
                    'Swarm':      self._draw_swarm,
                    'Heatmap':    self._draw_heatmap,
                    'Pairplot':   self._draw_pairplot,
                    'Joint':      self._draw_joint,
                    'Catplot':    self._draw_catplot,
                }
                dispatch[name]()
            except Exception as e:
                log.exception('SeabornExplorer render error (%s)', name)
                self._show_error(f'Render error ({name}):\n{e}')

    def _reset_canvas(self):
        self._canvas_fig.clear()
        return self._canvas_fig.add_subplot(111)

    def _refresh(self):
        self._canvas_fig.tight_layout()
        self._canvas.draw()

    def _draw_kde(self):
        yd, yn = self._get_col(self._y_combo)
        if yd is None:
            self._show_error('Select a Y column for KDE.')
            return
        ax = self._reset_canvas()
        sns.kdeplot(
            x=yd.astype(float), ax=ax,
            fill=self._kde_fill.isChecked(),
            alpha=self._kde_alpha.value(),
            linewidth=self._kde_lw.value(),
            bw_adjust=self._kde_bw.value(),
            cumulative=self._kde_cumul.isChecked(),
            common_norm=self._kde_common.isChecked(),
            color=self._sns_palette()[0],
        )
        ax.set_xlabel(yn); ax.set_ylabel('Density')
        self._refresh()

    def _draw_regression(self):
        xd, xn = self._get_col(self._x_combo)
        yd, yn = self._get_col(self._y_combo)
        if xd is None or yd is None:
            self._show_error('Select both X and Y columns for Regression.')
            return
        if self._is_cat(xd) or self._is_cat(yd):
            self._show_error('Regression requires numeric X and Y columns.')
            return
        ax     = self._reset_canvas()
        n      = min(len(xd), len(yd))
        lowess = self._reg_lowess.isChecked() and _STATSMODELS_OK
        robust = self._reg_robust.isChecked() and _STATSMODELS_OK
        order  = 1 if (lowess or robust) else self._reg_order.value()
        # lowess and robust both conflict with ci — seaborn raises if ci != None
        ci_val = None if (lowess or robust) else (self._reg_ci.value() or None)
        sns.regplot(
            x=xd[:n].astype(float), y=yd[:n].astype(float), ax=ax,
            scatter_kws={'s': self._reg_size.value(), 'alpha': self._reg_alpha.value()},
            line_kws={'linewidth': 1.8},
            ci=ci_val,
            order=order, robust=robust, lowess=lowess,
            scatter=self._reg_scatter.isChecked(),
            color=self._sns_palette()[0],
        )
        ax.set_xlabel(xn); ax.set_ylabel(yn)
        self._refresh()

    def _draw_strip(self):
        import pandas as pd
        xd, xn = self._get_col(self._x_combo)
        yd, yn = self._get_col(self._y_combo)
        if xd is None or yd is None:
            self._show_error('Select X (category) and Y (numeric) columns for Strip.')
            return
        n  = min(len(xd), len(yd))
        df = pd.DataFrame({'x': xd[:n].astype(str) if self._is_cat(xd) else xd[:n], 'y': yd[:n]})
        ax = self._reset_canvas()
        # Use color= not palette= when there is no hue to avoid the
        # seaborn >= 0.13 "Ignoring palette because no hue" warning.
        sns.stripplot(data=df, x='x', y='y', ax=ax,
                      color=self._sns_palette()[0],
                      size=self._strip_size.value(),
                      alpha=self._strip_alpha.value(),
                      jitter=self._strip_jitter.value())
        ax.set_xlabel(xn); ax.set_ylabel(yn)
        self._refresh()

    def _draw_swarm(self):
        import pandas as pd
        xd, xn = self._get_col(self._x_combo)
        yd, yn = self._get_col(self._y_combo)
        if xd is None or yd is None:
            self._show_error('Select X (category) and Y (numeric) columns for Swarm.')
            return
        n  = min(len(xd), len(yd))
        df = pd.DataFrame({'x': xd[:n].astype(str) if self._is_cat(xd) else xd[:n], 'y': yd[:n]})
        ax = self._reset_canvas()
        sns.swarmplot(data=df, x='x', y='y', ax=ax,
                      color=self._sns_palette()[0],
                      size=self._swarm_size.value(),
                      alpha=self._swarm_alpha.value())
        ax.set_xlabel(xn); ax.set_ylabel(yn)
        self._refresh()

    def _swap_figure(self, sns_fig):
        """Render a seaborn figure into the explorer canvas via PNG buffer."""
        buf = io.BytesIO()
        with matplotlib.rc_context({'text.usetex': False}):
            sns_fig.savefig(buf, format='png', dpi=120, bbox_inches='tight',
                            facecolor=sns_fig.get_facecolor())
        buf.seek(0)
        import matplotlib.image as mpimg
        img = mpimg.imread(buf)
        self._canvas_fig.clear()
        ax = self._canvas_fig.add_axes([0, 0, 1, 1])
        ax.imshow(img, aspect='equal', interpolation='lanczos')
        ax.axis('off')
        self._canvas.draw()
        plt.close(sns_fig)

    def _draw_heatmap(self):
        df = self._selected_numeric_df()
        if df is None or df.shape[1] < 2:
            self._show_error('Heatmap needs >= 2 numeric columns.\nSelect them in the Columns list.')
            return
        corr = df.corr()
        fig, ax = plt.subplots(figsize=(max(6, corr.shape[1]), max(5, corr.shape[0])))
        fmt = self._heat_fmt.currentText()
        sns.heatmap(corr, ax=ax,
                    cmap=self._heat_cmap.currentText(),
                    annot=self._heat_annot.isChecked(),
                    fmt=fmt if self._heat_annot.isChecked() else '',
                    linewidths=self._heat_lw.value(),
                    square=self._heat_square.isChecked(),
                    cbar=self._heat_cbar.isChecked(),
                    robust=self._heat_robust.isChecked())
        ax.set_title('Correlation Heatmap', fontsize=11, pad=8)
        self._swap_figure(fig)

    def _draw_pairplot(self):
        df = self._selected_numeric_df()
        if df is None or df.shape[1] < 2:
            self._show_error('Pairplot needs >= 2 numeric columns.\nSelect them in the Columns list.')
            return
        _pal = self._sns_palette_name() or self._sns_palette(df.shape[1])
        hd, hn = self._get_hue()
        if hd is not None:
            df[hn] = hd[:].astype(str)
            hue_val = hn
        else:
            hue_val = None
        pg = sns.pairplot(df,
                        hue=hue_val,
                        diag_kind=self._pair_diag.currentText(),
                        kind=self._pair_kind.currentText(),
                        palette=_pal,
                        plot_kws={'alpha': self._pair_alpha.value()})
        # if hd is not None:
        #     df['hue'] = hd[:].astype(str)
        #     pg = sns.pairplot(df,
        #                     hue='hue',
        #                     diag_kind=self._pair_diag.currentText(),
        #                     kind=self._pair_kind.currentText(),
        #                     palette=_pal,
        #                     plot_kws={'alpha': self._pair_alpha.value()})
        # else:
        #     pg = sns.pairplot(df,
        #                     diag_kind=self._pair_diag.currentText(),
        #                     kind=self._pair_kind.currentText(),
        #                     palette=_pal,
        #                     plot_kws={'alpha': self._pair_alpha.value()})
        self._swap_figure(pg.figure)

    def _draw_joint(self):
        xd, xn = self._get_col(self._x_combo)
        yd, yn = self._get_col(self._y_combo)
        if xd is None or yd is None:
            self._show_error('Select X and Y numeric columns for Joint plot.')
            return
        if self._is_cat(xd) or self._is_cat(yd):
            self._show_error('Joint plot requires numeric X and Y columns.')
            return
        n  = min(len(xd), len(yd))
        jg = sns.jointplot(x=xd[:n].astype(float), y=yd[:n].astype(float),
                           kind=self._joint_kind.currentText(),
                           ratio=self._joint_ratio.value(),
                           marginal_kws={'fill': self._joint_margkde.isChecked()},
                           alpha=self._joint_alpha.value(),
                           color=self._sns_palette()[0])
        jg.set_axis_labels(xn, yn)
        self._swap_figure(jg.figure)

    def _draw_catplot(self):
        import pandas as pd
        xd, xn = self._get_col(self._x_combo)
        yd, yn = self._get_col(self._y_combo)
        if xd is None or yd is None:
            self._show_error('Select X (category) and Y (numeric) columns for Catplot.')
            return
        n  = min(len(xd), len(yd))
        df = pd.DataFrame({'x': xd[:n].astype(str) if self._is_cat(xd) else xd[:n], 'y': yd[:n]})
        kind    = self._cat_kind.currentText()
        ci_str  = self._cat_ci.currentText()
        errorbar = ('ci', 95) if ci_str == '95' else \
                   ('ci', 99) if ci_str == '99' else \
                   'sd' if ci_str == 'sd' else None
        _pal_name = self._sns_palette_name()  # str if named palette, None if plotviz
        kw = dict(data=df, x='x', y='y', kind=kind,
                  alpha=self._cat_alpha.value(),
                  saturation=self._cat_sat.value())
        # palette and color are mutually exclusive in seaborn catplot
        if _pal_name is not None:
            kw['palette'] = _pal_name
        else:
            kw['palette'] = self._sns_palette(10)
        if kind in ('bar', 'point') and errorbar is not None:
            kw['errorbar'] = errorbar
        fg = sns.catplot(**kw)
        fg.set_axis_labels(xn, yn)
        self._swap_figure(fg.figure)

    # ── Export ────────────────────────────────────────────────────────────────

    def reject(self):
        """Route Escape → hide (not destroy) so the window can be re-opened."""
        self.hide()

    def closeEvent(self, event):
        """Hide instead of destroy so state is preserved between opens."""
        self.hide()
        event.ignore()

    def _export(self):
        fp, _ = QFileDialog.getSaveFileName(
            self, 'Export Seaborn Chart', '',
            'PNG (*.png);;SVG (*.svg);;PDF (*.pdf);;JPEG (*.jpg)')
        if not fp:
            return
        ext = fp.rsplit('.', 1)[-1].lower() if '.' in fp else 'png'
        fmt = 'jpeg' if ext == 'jpg' else ext
        try:
            with matplotlib.rc_context({'text.usetex': False}):
                self._canvas_fig.savefig(fp, dpi=self._dpi_spin.value(),
                                         format=fmt, bbox_inches='tight')
            log.info('SeabornExplorer: exported to %s', fp)
            QMessageBox.information(self, 'Export', f'Saved to:\n{fp}')
        except Exception as e:
            log.exception('SeabornExplorer export error')
            QMessageBox.warning(self, 'Export error', str(e))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _show_error(self, msg: str):
        """Display an error on the canvas — safe against LaTeX crashes."""
        safe_msg = _safe_text(msg)
        log.warning('SeabornExplorer: %s', safe_msg)
        with matplotlib.rc_context({'text.usetex': False}):
            self._canvas_fig.clear()
            ax = self._canvas_fig.add_subplot(111)
            ax.text(0.5, 0.5, safe_msg,
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=10, color='#c0392b',
                    bbox=dict(boxstyle='round,pad=0.5', fc='#fdf2f2', ec='#e74c3c'),
                    wrap=True)
            ax.axis('off')
            self._canvas.draw()

    def refresh_datasets(self, datasets: dict, palette: list[str]):
        self.datasets = datasets
        self.palette  = palette
        self._populate_col_combos()
