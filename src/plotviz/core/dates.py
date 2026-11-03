"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

core/dates.py  –  plotviz

Date/time columns.  A date column is stored as a float array of *days since
1970-01-01* (the numbers matplotlib uses for dates), tagged by the DateArray
subclass.  Everything that works on float arrays (transforms, fits, statistics,
saving) keeps working, and the plot engine turns a DateArray axis into a date axis.

No Qt, no ui/ imports.
"""
from __future__ import annotations

import re
import warnings

from typing import Any

import numpy as np

_NS_PER_DAY = 86_400_000_000_000.0


class DateArray(np.ndarray):
    """float64 days since 1970-01-01.  The class itself marks the column as dates.

    Slicing and copying keep the tag; arithmetic and reductions return plain arrays,
    so a column computed from a date column is not mistaken for dates."""

    def __new__(cls, values: Any) -> DateArray:
        return np.asarray(values, dtype=float).view(cls)

    def __array_wrap__(self, obj: Any, context: Any = None, return_scalar: bool = False) -> Any:
        out = np.asarray(obj)
        return out[()] if return_scalar and out.ndim == 0 else out


# What a text value must look like to be tried as a date.  pandas/dateutil accept far
# more ('1,5' is read as 5 January), which would turn ordinary text into dates.
_MONTH = r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*'
_DATE_LIKE = re.compile(
    r'\d{4}[-/.]\d{1,2}'                         # 2024-03, 2024/3/1, 2024.03.01
    r'|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}'          # 3/4/24, 03.04.2024
    rf'|\d.*\b{_MONTH}\b|\b{_MONTH}\b.*\d',     # 1 Mar 2024, March 5, 2024
    re.IGNORECASE)


def is_date(arr: Any) -> bool:
    return isinstance(arr, DateArray)


def from_datetime64(values: Any) -> DateArray:
    """datetime64 array (NaT allowed) -> DateArray."""
    dt = np.asarray(values).astype('datetime64[ns]')
    days = dt.astype('int64') / _NS_PER_DAY
    days[np.isnat(dt)] = np.nan
    return DateArray(days)


def to_datetime64(days: Any) -> np.ndarray:
    """Days since 1970-01-01 -> datetime64[ns]; non-finite values become NaT."""
    days = np.asarray(days, dtype=float)
    ok = np.isfinite(days)
    ns = np.zeros(days.shape, dtype='int64')
    ns[ok] = np.round(days[ok] * _NS_PER_DAY).astype('int64')
    out = ns.astype('datetime64[ns]')
    out[~ok] = np.datetime64('NaT')
    return out


_UNIT_SECONDS = {'D': 86400.0, 's': 1.0, 'ms': 1e-3}


def _unit(days: np.ndarray) -> str:
    """Coarsest ISO unit that shows the values exactly (to a microsecond): D, s, ms or us."""
    ok = days[np.isfinite(days)]
    for unit, seconds in _UNIT_SECONDS.items():
        scaled = ok * (86400.0 / seconds)
        if np.abs(scaled - np.round(scaled)).max(initial=0.0) < 1e-6 / seconds:
            return unit
    return 'us'


def to_iso(days: Any) -> list[str]:
    """ISO 8601 strings ('2024-03-01', '2024-03-01T12:30:00', 'NaT') for a date column."""
    days = np.asarray(days, dtype=float)
    unit = _unit(days)
    step = {'D': 86400e9, 's': 1e9, 'ms': 1e6, 'us': 1e3}[unit]      # nanoseconds per unit
    ok = np.isfinite(days)
    ticks = np.zeros(days.shape, dtype='int64')
    ticks[ok] = np.round(days[ok] * _NS_PER_DAY / step).astype('int64')
    dt = ticks.astype(f'datetime64[{unit}]')
    dt[~ok] = np.datetime64('NaT')
    iso: list[str] = np.datetime_as_string(dt).tolist()
    return iso


def from_iso(strings: Any) -> DateArray:
    """Inverse of to_iso."""
    return from_datetime64(np.array(list(strings), dtype='datetime64[ns]'))


def format_date(value: float) -> str:
    """One value as ISO text, for the UI ('' for NaN)."""
    if value is None or not np.isfinite(value):
        return ''
    return to_iso([value])[0].replace('T', ' ')


def parse_date(text: str, dayfirst: bool = False) -> float:
    """One typed date/time ('2024-03-01', '1 Mar 2024 12:30') -> days since 1970-01-01."""
    import pandas as pd
    ts = pd.to_datetime(text.strip(), dayfirst=dayfirst, utc=True)
    if ts is pd.NaT:
        raise ValueError(f'not a date: {text!r}')
    return float(from_datetime64([ts.tz_localize(None).to_datetime64()])[0])


def parse_series(series: Any, dayfirst: bool = False) -> DateArray | None:
    """A pandas Series -> DateArray if every non-empty value is a date, else None.

    Real datetime columns are taken as they are.  Text columns must look like dates in
    every value (so that names such as 'May' or numbers such as '1,5' stay as they are) and
    parse completely.
    Time zones are converted to UTC and dropped."""
    import pandas as pd
    if pd.api.types.is_datetime64_any_dtype(series):
        if getattr(series.dt, 'tz', None) is not None:
            series = series.dt.tz_convert('UTC').dt.tz_localize(None)
        return from_datetime64(series.to_numpy(dtype='datetime64[ns]'))
    if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        return None
    present = series.dropna()
    if present.empty or not present.astype(str).map(lambda v: bool(_DATE_LIKE.search(v))).all():
        return None
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        parsed = None
        # first the format pandas infers from the data, then each value on its own
        # (a column mixing '2024-03-01' and '2024-03-01 12:00' needs the second)
        for fmt in (None, 'mixed'):
            try:
                parsed = pd.to_datetime(series, errors='coerce', dayfirst=dayfirst, utc=True,
                                        format=fmt)
            except (ValueError, TypeError, OverflowError):
                continue
            if parsed.notna().sum() == series.notna().sum():
                break
        else:
            return None
    return from_datetime64(parsed.dt.tz_localize(None).to_numpy(dtype='datetime64[ns]'))
