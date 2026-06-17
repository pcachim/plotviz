"""
Copyright (c) 2026 Paulo Cachim
core/serialize.py  –  plotviz

Pure (Qt-free) read/write of the .pviz project bundle. This module must never
import PyQt6 or anything under ui/ so the project round-trip can be unit-tested
without a Qt installation.

A .pviz file is a zip archive containing:
  settings.json  -- appearance/config (+ annotation metadata)
  series.json    -- series table + per-subplot column assignments
  data.json      -- datasets, encoded as {dtype, values}
  palette.json   -- custom colour palettes (optional)
  images/<name>  -- image files referenced by image annotations (optional)

The UI layer is responsible for gathering the dicts (from widgets) and applying
them back; this module only does the dict<->bytes translation.
"""
from __future__ import annotations

import json
import os
import zipfile

import numpy as np


def encode_datasets(datasets: dict) -> dict:
    """Convert {name: array-like} into the JSON-friendly {name: {dtype, values}}."""
    out = {}
    for k, v in datasets.items():
        is_cat = hasattr(v, "dtype") and v.dtype.kind in ("U", "S", "O")
        out[k] = {
            "dtype": "object" if is_cat else "float",
            "values": v.tolist() if hasattr(v, "tolist") else list(v),
        }
    return out


def decode_datasets(raw: dict) -> dict:
    """Inverse of encode_datasets, with backwards compatibility.

    New format: {'dtype': 'float'|'object', 'values': [...]}.
    Old format: a plain list (dtype inferred).
    Returns {name: numpy.ndarray}.
    """
    out = {}
    for k, v in raw.items():
        if isinstance(v, dict) and "values" in v:
            vals = v["values"]
            if v.get("dtype") == "object":
                out[k] = np.array(vals, dtype=object)
            else:
                out[k] = np.array(vals, dtype=float)
        else:
            try:
                out[k] = np.array(v, dtype=float)
            except (ValueError, TypeError):
                out[k] = np.array(v, dtype=object)
    return out


def write_project_zip(path, settings: dict, series_meta: dict,
                      datasets_encoded: dict, palette_json: str | None = None,
                      image_paths=()) -> None:
    """Write a .pviz archive from already-collected pieces.

    ``datasets_encoded`` is the output of :func:`encode_datasets`.
    ``image_paths`` is an iterable of source file paths for image annotations;
    each is stored under ``images/<basename>`` (deduplicated by basename).
    """
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("settings.json", json.dumps(settings, indent=2))
        zf.writestr("series.json", json.dumps(series_meta, indent=2))
        zf.writestr("data.json", json.dumps(datasets_encoded, indent=2))
        if palette_json and palette_json != "{}":
            zf.writestr("palette.json", palette_json)
        seen = set()
        for src in image_paths:
            if src and os.path.isfile(src):
                bname = os.path.basename(src)
                if bname not in seen:
                    zf.write(src, "images/" + bname)
                    seen.add(bname)


def read_project_zip(path) -> dict:
    """Parse a .pviz archive into plain Python structures (no Qt, no extraction).

    Returns a dict with keys:
      settings       -- parsed settings.json (dict)
      series_meta    -- parsed series.json (dict) or reconstructed from legacy
                        settings, or None
      datasets_raw   -- parsed data.json (dict in {dtype, values} / legacy form)
      palette_json   -- raw palette.json text, or None
      images         -- {basename: bytes} for every images/ member

    Raises ValueError if settings.json is missing.
    """
    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        if "settings.json" not in names:
            raise ValueError("No settings.json in archive.")
        settings = json.loads(zf.read("settings.json"))
        series_meta = json.loads(zf.read("series.json")) if "series.json" in names else None
        # Backwards compat: series embedded inside old settings.json
        if series_meta is None and "series" in settings:
            series_meta = {
                "series": settings.get("series", []),
                "z_col": settings.get("z_col", "(none)"),
                "err_col": settings.get("err_col", "(none)"),
                "y2_cols": settings.get("y2_cols", []),
            }
        datasets_raw = json.loads(zf.read("data.json")) if "data.json" in names else {}
        palette_json = zf.read("palette.json").decode() if "palette.json" in names else None
        images = {
            os.path.basename(n): zf.read(n)
            for n in names
            if n.startswith("images/") and n != "images/"
        }
    return {
        "settings": settings,
        "series_meta": series_meta,
        "datasets_raw": datasets_raw,
        "palette_json": palette_json,
        "images": images,
    }
