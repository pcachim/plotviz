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
