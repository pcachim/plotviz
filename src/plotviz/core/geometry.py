"""
Copyright (c) 2026 Paulo Cachim
core/geometry.py  –  plotviz

Pure figure-size unit conversions, shared by the UI (figure-size spinboxes,
preset/unit switching) and the standalone-script generator. Centralising them
removes the cm/inch/pixel arithmetic that was duplicated inline in several
places and could drift between the app and the generated script.

No Qt, no ui/ imports.
"""
from __future__ import annotations

#: Centimetres per inch (matplotlib works in inches).
CM_PER_INCH = 2.54

#: Figure-size units understood by plotviz.
UNITS = ("cm", "inches", "pixels")


def to_inches(value: float, unit: str, dpi: float = 300) -> float:
    """Convert a length expressed in *unit* to inches.

    cm     -> value / 2.54
    pixels -> value / dpi
    inches -> value (unchanged)
    """
    if unit == "cm":
        return value / CM_PER_INCH
    if unit == "pixels":
        return value / dpi
    return value  # already inches (or unknown unit treated as inches)


def from_inches(inches: float, unit: str, dpi: float = 300) -> float:
    """Convert a length in inches into *unit* (inverse of :func:`to_inches`)."""
    if unit == "cm":
        return inches * CM_PER_INCH
    if unit == "pixels":
        return inches * dpi
    return inches


def convert(value: float, from_unit: str, to_unit: str, dpi: float = 300) -> float:
    """Convert *value* directly from one unit to another."""
    return from_inches(to_inches(value, from_unit, dpi), to_unit, dpi)


def point_segment_distance(px, py, ax, ay, bx, by) -> float:
    """Euclidean distance from point (px, py) to the segment (ax, ay)-(bx, by).

    Used for hit-testing arrow annotations along their whole length rather than
    only near an endpoint. Caller may pre-normalise coordinates (e.g. divide by
    a per-axis tolerance) so the distance is comparable across axes with
    different scales.
    """
    dx, dy = bx - ax, by - ay
    seg_sq = dx * dx + dy * dy
    if seg_sq <= 1e-30:
        # Degenerate segment → distance to the (coincident) endpoint.
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    # Projection parameter t of the point onto the segment, clamped to [0, 1].
    t = ((px - ax) * dx + (py - ay) * dy) / seg_sq
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5
