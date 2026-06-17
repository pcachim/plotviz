"""
Copyright (c) 2026 Paulo Cachim
core/settings_schema.py  –  plotviz

A typed view over the loose ``settings`` dict for the per-subplot styling that
the pure layer consumes. This is the first increment of replacing scattered
``settings.get(key, default)`` calls (whose defaults could drift between the
generator, the engine and the serializer) with a single, validated model whose
defaults live in exactly one place.

Pure data — no Qt, no ui/ imports — so it is shared by core.script_gen and is
unit-testable without a display.
"""
from __future__ import annotations

from dataclasses import dataclass


def subplot_get(settings: dict, dict_key: str, idx, default):
    """Read a per-subplot value from ``settings[dict_key]``.

    The per-subplot dicts are keyed by stringified index after serialization
    but may be int-keyed in memory, so both are tried.
    """
    d = settings.get(dict_key) or {}
    return d.get(str(idx), d.get(idx, default))


@dataclass(frozen=True)
class SubplotStyle:
    """Resolved per-subplot decoration styling (labels, scales, ticks, grid).

    Build with :meth:`from_settings`; the label/title *text* is intentionally
    not part of this model (the caller resolves it from columns).
    """
    # Axis labels
    xlabel_show: bool = True
    xlabel_size: float = 11
    xlabel_color: str = "#000000"
    xlabel_font: str = "sans-serif"
    xlabel_rotation: float = 0
    xlabel_labelpad: float = 4
    xlabel_loc: str = "center"
    xlabel_ha: str = "center"
    ylabel_show: bool = True
    ylabel_size: float = 11
    ylabel_color: str = "#000000"
    ylabel_font: str = "sans-serif"
    ylabel_rotation: float = 90
    ylabel_labelpad: float = 4
    ylabel_loc: str = "center"
    ylabel_ha: str = "center"
    # Subplot title
    title_font: str = "sans-serif"
    title_size: float = 11
    title_color: str = "#000000"
    title_pad: float = 6
    title_rotation: float = 0
    title_loc: str = "center"
    # Scales / limits / aspect
    xscale: str = "linear"
    yscale: str = "linear"
    xlim: tuple | list | None = None
    ylim: tuple | list | None = None
    equal_aspect: bool = False
    # Colours
    fg: str = "#000000"
    plot_bg: str = "#ffffff"
    # Ticks
    xtick_size: float = 9
    ytick_size: float = 9
    xtick_dir: str = "out"
    ytick_dir: str = "out"
    xtick_rotation: float = 0
    ytick_rotation: float = 0
    xticks_show: bool = True
    yticks_show: bool = True
    xtick_minor: bool = False
    ytick_minor: bool = False
    xtick_step: float = 0.0
    ytick_step: float = 0.0
    x_formatter: str = "auto"
    y_formatter: str = "auto"
    # Grid (global Layout settings)
    grid_on: bool = False
    grid_color: str = "#cccccc"
    grid_linestyle: str = "-"
    grid_linewidth: float = 0.8
    grid_alpha: float = 1.0
    minor_grid_on: bool = False
    minor_grid_color: str = "#e8e8e8"
    minor_grid_linestyle: str = "-"
    minor_grid_linewidth: float = 0.5
    minor_grid_alpha: float = 1.0
    # Spines
    border_top: bool = True
    border_bottom: bool = True
    border_left: bool = True
    border_right: bool = True

    @classmethod
    def from_settings(cls, settings: dict, idx) -> "SubplotStyle":
        """Resolve the styling for subplot *idx* from the loose settings dict."""
        def sp(key, default):
            return subplot_get(settings, key, idx, default)

        def g(key, default):
            return settings.get(key, default)

        return cls(
            xlabel_show=sp("subplot_xlabel_show", True),
            xlabel_size=g("xlabel_size", 11),
            xlabel_color=g("xlabel_color", "#000000"),
            xlabel_font=g("xlabel_font", "sans-serif"),
            xlabel_rotation=sp("subplot_xlabel_rotation", 0),
            xlabel_labelpad=sp("subplot_xlabel_labelpad", 4),
            xlabel_loc=sp("subplot_xlabel_loc", "center"),
            xlabel_ha=sp("subplot_xlabel_ha", "center"),
            ylabel_show=sp("subplot_ylabel_show", True),
            ylabel_size=g("ylabel_size", 11),
            ylabel_color=g("ylabel_color", "#000000"),
            ylabel_font=g("ylabel_font", "sans-serif"),
            ylabel_rotation=sp("subplot_ylabel_rotation", 90),
            ylabel_labelpad=sp("subplot_ylabel_labelpad", 4),
            ylabel_loc=sp("subplot_ylabel_loc", "center"),
            ylabel_ha=sp("subplot_ylabel_ha", "center"),
            title_font=sp("subplot_title_font", "sans-serif"),
            title_size=sp("subplot_title_size", 11),
            title_color=sp("subplot_title_color", "#000000"),
            title_pad=sp("subplot_title_pad", 6),
            title_rotation=sp("subplot_title_rotation", 0),
            title_loc=sp("subplot_title_ha", "center"),
            xscale=sp("subplot_xscales", "linear"),
            yscale=sp("subplot_yscales", "linear"),
            xlim=sp("subplot_xlims", None),
            ylim=sp("subplot_ylims", None),
            equal_aspect=sp("subplot_equal_aspect", False),
            fg=g("chart_fg_color", "#000000"),
            plot_bg=g("plot_bg_color", "#ffffff"),
            xtick_size=sp("subplot_xtick_sizes", g("xtick_size", 9)),
            ytick_size=sp("subplot_ytick_sizes", g("ytick_size", 9)),
            xtick_dir=sp("subplot_xtick_dir", "out"),
            ytick_dir=sp("subplot_ytick_dir", "out"),
            xtick_rotation=sp("subplot_xtick_rotation", 0),
            ytick_rotation=sp("subplot_ytick_rotation", 0),
            xticks_show=sp("subplot_xticks_show", True),
            yticks_show=sp("subplot_yticks_show", True),
            xtick_minor=sp("subplot_xtick_minor", False),
            ytick_minor=sp("subplot_ytick_minor", False),
            xtick_step=sp("subplot_xtick_step", 0.0),
            ytick_step=sp("subplot_ytick_step", 0.0),
            x_formatter=sp("subplot_x_formatter", "auto"),
            y_formatter=sp("subplot_y_formatter", "auto"),
            grid_on=g("grid_on", False),
            grid_color=g("grid_color", "#cccccc"),
            grid_linestyle=g("grid_linestyle", "-"),
            grid_linewidth=g("grid_linewidth", 0.8),
            grid_alpha=g("grid_alpha", 1.0),
            minor_grid_on=g("minor_grid_on", False),
            minor_grid_color=g("minor_grid_color", "#e8e8e8"),
            minor_grid_linestyle=g("minor_grid_linestyle", "-"),
            minor_grid_linewidth=g("minor_grid_linewidth", 0.5),
            minor_grid_alpha=g("minor_grid_alpha", 1.0),
            border_top=g("border_top", True),
            border_bottom=g("border_bottom", True),
            border_left=g("border_left", True),
            border_right=g("border_right", True),
        )
