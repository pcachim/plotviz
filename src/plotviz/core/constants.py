"""
Copyright (c) 2026 Paulo Cachim
core/constants.py  –  plotviz

Single source of truth for the chart-type category sets used to gate rendering
and decoration behaviour. Pure data — no Qt, no ui/ imports — so both the
interactive engine (ui/) and the standalone-script generator (core/) share the
exact same definitions and cannot drift apart.

Names are exported both in a clear public form (e.g. NO_X_TYPES) and under the
historical underscore aliases (e.g. _NO_X_TYPES) that the existing modules use,
so callers can import whichever they prefer.
"""

#: Chart types rendered on a 3D projection.
THREE_D_TYPES = {"3D Surface"}

#: Chart types rendered on a polar projection.
POLAR_TYPES = {"Polar", "Radar"}

#: Chart types that have no meaningful x column (x label/scale suppressed).
NO_X_TYPES = {"Histogram", "Boxplot", "Violin", "Pie", "ECDF"}

#: Chart types whose legend is handled specially (auto-legend suppressed).
NO_LEGEND_TYPES = {
    "Pie", "Heatmap", "Hist2D", "Hexbin", "Contour", "Tricontour",
    "3D Surface", "Violin", "Boxplot", "Radar", "Quiver", "Barbs", "Streamplot",
}

#: Decoration guards (mirrors plot_engine): types for which axis scale / grid /
#: tick styling is skipped.
DECOR_NO_SCALE = {
    "Pie", "Heatmap", "Hist2D", "Hexbin", "Polar", "Radar", "3D Surface", "Tricontour",
}
#: Types for which explicit axis limits are skipped.
DECOR_NO_LIMITS = {"Pie", "Heatmap"}
#: Types for which tick styling / spine styling is skipped.
DECOR_NO_TICKS = {"Pie", "Polar", "Radar", "3D Surface"}

#: Non-Cartesian / pixel-space types for which axis scale + inversion are
#: skipped in the multi-subplot (mosaic / grid) paths.
AXSCALE_SKIP_TYPES = {"Pie", "Heatmap", "Polar", "Radar", "3D Surface"}

#: The "heatmap group": types drawn in pixel/data space that carry a colorbar
#: and must be excluded from shared axes (sharex/sharey).
HEATMAP_GROUP_TYPES = {"Heatmap", "Contour", "Tricontour", "Hist2D", "Hexbin"}

# ── Historical underscore aliases ───────────────────────────────────────────
_3D_TYPES = THREE_D_TYPES
_POLAR_TYPES = POLAR_TYPES
_NO_X_TYPES = NO_X_TYPES
_NO_LEGEND_TYPES = NO_LEGEND_TYPES
_DECOR_NO_SCALE = DECOR_NO_SCALE
_DECOR_NO_LIMITS = DECOR_NO_LIMITS
_DECOR_NO_TICKS = DECOR_NO_TICKS
_AXSCALE_SKIP_TYPES = AXSCALE_SKIP_TYPES
_HEATMAP_GROUP_TYPES = HEATMAP_GROUP_TYPES
