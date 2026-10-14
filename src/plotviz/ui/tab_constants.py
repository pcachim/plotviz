"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_constants.py  –  plotviz
Shared constants, palettes and small helpers for the tab-builder mixins.
(Re-exported by ui.tab_builders so existing imports keep working.)
"""
from PyQt6.QtCore import QObject, QEvent

ALL_CHART_TYPES = [
    # ── Per-series mixable ────────────────────────────────────────────
    'Line', 'Scatter', 'Bar', 'Errorbar', 'Area', 'Fill Between',
    'Step', 'Stem', 'Bubble', 'Waterfall',
    # ── Whole-chart / specialised ─────────────────────────────────────
    'Histogram', 'Hist2D', 'Hexbin',
    'Boxplot', 'Violin',
    'Pie', 'Polar', 'Radar',
    'Heatmap', 'Contour', 'Tricontour', '3D Surface',
    'ECDF', 'Quiver', 'Barbs', 'Streamplot',
]

# Types available per-series in the table Type column (all types)
PER_SERIES_TYPES = ALL_CHART_TYPES

# Types that take over the whole chart (no per-series mixing)
WHOLE_CHART_TYPES = {
    'Histogram', 'Hist2D', 'Hexbin',
    'Boxplot', 'Violin',
    'Pie', 'Polar', 'Radar',
    'Heatmap', 'Contour', 'Tricontour', '3D Surface',
    'ECDF', 'Quiver', 'Barbs', 'Streamplot',
}

# Re-exported from the canonical source so existing `from ui.tab_builders
# import _NO_X_TYPES` call sites keep working.
from core.constants import _NO_X_TYPES  # noqa: F401

# Master colormap list — sorted alphabetically (case-insensitive).
_CMAP_LIST = sorted([
    'viridis', 'plasma', 'inferno', 'magma', 'cividis', 'turbo',
    'Blues', 'Greens', 'Reds', 'Purples', 'Oranges', 'Greys',
    'YlOrRd', 'YlGnBu', 'BuPu', 'RdPu', 'PuBu',
    'hot', 'cool', 'copper', 'bone', 'gray',
    'coolwarm', 'RdBu', 'RdYlBu', 'RdYlGn', 'Spectral',
    'PiYG', 'PRGn', 'BrBG', 'PuOr', 'bwr', 'seismic',
    'twilight', 'hsv',
    'rainbow', 'nipy_spectral',
], key=str.casefold)

# ── Plot-mode groups ──────────────────────────────────────────────────────────
# "Standard" covers all freely-mixable per-series types. The remaining modes
# are for whole-chart exclusive types that can't be mixed with anything else.
PLOT_MODE_GROUPS = {
    'Standard':          ['Line', 'Scatter', 'Bar', 'Area', 'Fill Between',
                          'Errorbar', 'Step', 'Stem', 'Bubble', 'Waterfall'],
    'Histogram':         ['Histogram'],
    'Statistical':       ['Boxplot', 'Violin', 'ECDF'],
    'Heatmap & Contour': ['Heatmap', 'Contour', 'Tricontour', 'Hist2D', 'Hexbin', '3D Surface'],
    'Polar & Radar':     ['Polar', 'Radar'],
    'Pie':               ['Pie'],
    'Quiver':            ['Quiver', 'Barbs', 'Streamplot'],
}

# Reverse: given a series type, which plot mode contains it?
TYPE_TO_PLOT_MODE = {t: m for m, types in PLOT_MODE_GROUPS.items() for t in types}

# ── Named colour palettes available in the Data tab (16 colours = Qt custom slots)
COLOR_PALETTES = {
    'Matplotlib':  ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd',
                    '#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf',
                    '#aec7e8','#ffbb78','#98df8a','#ff9896','#c5b0d5',
                    '#c49c94'],
    'Pastel':      ['#aec6cf','#ffb347','#b5ead7','#ff9aa2','#c7ceea',
                    '#ffdac1','#e2f0cb','#f8c8d4','#d4a5c9','#b5d8cc',
                    '#a8d8ea','#f9e4b7','#c8e6c9','#f8bbd0','#d1c4e9',
                    '#ffe0b2'],
    'Bold':        ['#e6194b','#3cb44b','#4363d8','#f58231','#911eb4',
                    '#42d4f4','#f032e6','#bfef45','#fabed4','#469990',
                    '#9a6324','#fffac8','#800000','#aaffc3','#808000',
                    '#ffd8b1'],
    'Earth':       ['#8b4513','#cd853f','#556b2f','#6b8e23','#8fbc8f',
                    '#bc8f5f','#a0522d','#deb887','#696969','#808000',
                    '#d2691e','#f4a460','#228b22','#90ee90','#a9a9a9',
                    '#c8a882'],
    'Ocean':       ['#003f5c','#2f4b7c','#665191','#a05195','#d45087',
                    '#f95d6a','#ff7c43','#ffa600','#488f8f','#2b9999',
                    '#005f73','#0a9396','#94d2bd','#e9d8a6','#ee9b00',
                    '#ca6702'],
    'Warm':        ['#d62728','#ff7f0e','#e377c2','#bcbd22','#f7b731',
                    '#e55039','#f39c12','#c0392b','#e74c3c','#d35400',
                    '#f1c40f','#e67e22','#e91e63','#ff5722','#ffc107',
                    '#ff6b6b'],
    'Cool':        ['#1f77b4','#17becf','#2ca02c','#9467bd','#4169e1',
                    '#00ced1','#3cb371','#6a5acd','#20b2aa','#1e90ff',
                    '#5c85d6','#4fc3f7','#81c784','#ba68c8','#4dd0e1',
                    '#26c6da'],
    'Colorblind':  ['#0077bb','#ee7733','#009988','#cc3311','#33bbee',
                    '#ee3377','#bbbbbb','#000000','#994455','#ddaa33',
                    '#004488','#bb5566','#6699cc','#eecc66','#997700',
                    '#44bb99'],
    'Nature':      ['#4e9a8d','#f4a261','#e76f51','#264653','#2a9d8f',
                    '#e9c46a','#a8dadc','#457b9d','#1d3557','#f1faee',
                    '#606c38','#dda15e','#bc6c25','#283618','#fefae0',
                    '#588157'],
    'Publication': ['#000000','#e41a1c','#377eb8','#4daf4a','#984ea3',
                    '#ff7f00','#a65628','#f781bf','#999999','#ffff33',
                    '#66c2a5','#fc8d62','#8da0cb','#e78ac3','#a6d854',
                    '#ffd92f'],
    'Grayscale':   ['#000000','#111111','#222222','#404040','#606060',
                    '#808080','#909090','#999999','#b0b0b0','#c0c0c0',
                    '#c8c8c8','#d0d0d0','#d8d8d8','#e0e0e0','#e8e8e8',
                    '#f0f0f0'],
}

# Runtime-added custom palettes (loaded from palette.json in .pvizp or user prefs)
_CUSTOM_PALETTES: dict = {}


def get_all_palettes() -> dict:
    """Return built-in + custom palettes merged."""
    return {**COLOR_PALETTES, **_CUSTOM_PALETTES}


def add_custom_palette(name: str, colors: list):
    """Register a custom palette at runtime."""
    _CUSTOM_PALETTES[name] = colors[:16]

_FONTS = ['sans-serif', 'serif', 'monospace']


class _ClampWidth(QObject):
    """Event-filter that keeps a widget's width <= the watched object's width.
    Used to prevent content widgets inside QScrollArea from growing horizontally
    beyond the viewport, which would trigger unwanted horizontal scrolling."""
    def __init__(self, target, parent=None):
        super().__init__(parent)
        self._target = target
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            self._target.setMaximumWidth(obj.width())
        return False
