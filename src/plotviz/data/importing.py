"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.

data/importing.py  –  plotviz
Reading a data file into columns: the import dialog and "Reload data" share this code, so a file
read again later gives the same columns as when it was imported.
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass, fields
from typing import Any

import numpy as np
import pandas as pd

from core.dates import parse_series


@dataclass
class ImportOptions:
    """How a file was read (the settings of the import dialog)."""
    sheet: str = ''                 # Excel: the sheet name, '' for the first one
    sep: str | None = None          # CSV / text: the separator, None to detect it
    decimal: str = '.'
    encoding: str = 'utf-8-sig'
    header: int = 0
    skiprows: int = 0
    json_orient: str | None = None  # JSON: pandas 'orient', None for the default
    parse_dates: bool = True
    dayfirst: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> 'ImportOptions':
        """Options from a saved dict; names this version does not know are ignored."""
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in known})


def read_table(path: str, opts: ImportOptions) -> pd.DataFrame:
    """The file as a table, read with *opts*."""
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.xlsx', '.xls'):
        return pd.read_excel(path, sheet_name=opts.sheet or 0,
                             header=opts.header, skiprows=opts.skiprows or None)
    if ext == '.json':
        with open(path) as f:
            raw = json.load(f)
        if isinstance(raw, list):
            return pd.DataFrame(raw)
        kw: dict[str, Any] = {'orient': opts.json_orient} if opts.json_orient else {}
        return pd.read_json(path, **kw)
    sep = opts.sep
    if sep is None:                                   # detect it
        try:
            with open(path, newline='', encoding=opts.encoding) as f:
                sep = csv.Sniffer().sniff(f.read(4096)).delimiter
        except (csv.Error, OSError, UnicodeError):
            sep = ','
    csv_kw: dict[str, Any] = dict(header=opts.header, skiprows=opts.skiprows or None,
                                  decimal=opts.decimal, encoding=opts.encoding)
    if sep == r'\s+':
        return pd.read_csv(path, sep=r'\s+', engine='python', **csv_kw)
    return pd.read_csv(path, sep=sep, **csv_kw)


def column_data(df: pd.DataFrame, opts: ImportOptions) -> dict[str, np.ndarray]:
    """{column name: values}: dates as dates, numbers as floats, anything else as text."""
    out: dict[str, np.ndarray] = {}
    for col in df.columns:
        series = df[col]
        if opts.parse_dates:
            dates = parse_series(series, dayfirst=opts.dayfirst)
            if dates is not None:
                out[str(col)] = dates
                continue
        numeric = pd.to_numeric(series, errors='coerce')
        non_null = series.notna().sum()
        if non_null > 0 and numeric.notna().sum() == non_null:
            out[str(col)] = numeric.to_numpy(dtype=float, na_value=np.nan)
        else:
            out[str(col)] = series.fillna('').astype(str).to_numpy()
    return out
