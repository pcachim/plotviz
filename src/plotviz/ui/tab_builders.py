"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

ui/tab_builders.py  –  plotviz
TabBuildersMixin: composes the per-tab builder mixins (create_*_tab() methods).
Shared constants live in ui.tab_constants and are re-exported here.
"""
from ui.tab_helpers import WidgetHelpersMixin
from ui.tab_file import FileTabMixin
from ui.tab_data import DataTabMixin
from ui.tab_chart_options import ChartOptionGroupsMixin
from ui.tab_axes import AxesTabMixin
from ui.tab_style import StyleTabMixin
from ui.tab_series import SeriesTabMixin
from ui.tab_annotations import AnnotationsTabMixin
from ui.tab_layout import LayoutTabMixin
from ui.tab_advanced import AdvancedTabMixin
from ui.tab_constants import (  # noqa: F401  (re-exported for existing importers)
    _NO_X_TYPES,
    ALL_CHART_TYPES,
    COLOR_PALETTES,
    PER_SERIES_TYPES,
    PLOT_MODE_GROUPS,
    TYPE_TO_PLOT_MODE,
    WHOLE_CHART_TYPES,
    _CMAP_LIST,
    _CUSTOM_PALETTES,
    _ClampWidth,
    _FONTS,
    add_custom_palette,
    get_all_palettes,
)


class TabBuildersMixin(WidgetHelpersMixin, FileTabMixin, DataTabMixin, ChartOptionGroupsMixin, AxesTabMixin, StyleTabMixin, SeriesTabMixin, AnnotationsTabMixin, LayoutTabMixin, AdvancedTabMixin):
    """All create_*_tab() builders for PlotVizApp, one mixin per tab."""
