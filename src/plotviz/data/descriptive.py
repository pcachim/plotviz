"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.


data/descriptive.py - Descriptive statistics and correlation of loaded series
"""
import numpy as np
from scipy import stats as scipy_stats

STAT_COLUMNS = ['count', 'missing', 'mean', 'std', 'min', '25%', 'median', '75%', 'max',
                'skew', 'kurtosis']


def _numeric(arr):
    """The array as floats, or None for text/categorical data."""
    try:
        return np.asarray(arr, dtype=float)
    except (TypeError, ValueError):
        return None


def describe(arr):
    """Summary of one series: {stat: value} for STAT_COLUMNS.  NaN/inf count as missing.
    Text series only get 'count', 'missing' and 'unique'; the rest of the values are None."""
    numeric = _numeric(arr)
    if numeric is None:
        values = np.asarray(arr, dtype=object)
        present = np.array([v is not None and v == v for v in values], dtype=bool)
        out = {k: None for k in STAT_COLUMNS}
        out.update(count=int(present.sum()), missing=int((~present).sum()),
                   unique=len(set(values[present].tolist())))
        return out
    ok = numeric[np.isfinite(numeric)]
    out = {k: None for k in STAT_COLUMNS}
    out.update(count=int(len(ok)), missing=int(len(numeric) - len(ok)))
    if len(ok):
        q1, med, q3 = np.percentile(ok, [25, 50, 75])
        out.update(mean=float(ok.mean()), min=float(ok.min()), max=float(ok.max()),
                   median=float(med))
        out['25%'], out['75%'] = float(q1), float(q3)
    if len(ok) > 1:
        out['std'] = float(ok.std(ddof=1))
    if len(ok) > 2 and ok.std() > 0:
        out['skew'] = float(scipy_stats.skew(ok))
        out['kurtosis'] = float(scipy_stats.kurtosis(ok))      # excess kurtosis
    return out


def describe_all(datasets, names=None):
    """{name: describe(series)} for ``names`` (default: every series), in that order."""
    names = list(datasets) if names is None else names
    return {n: describe(datasets[n]) for n in names if n in datasets}


def correlation_matrix(datasets, names, method='pearson'):
    """Pairwise correlation between numeric series: (names_used, matrix).

    Each pair uses the points where both values are finite.  Pairs of series with
    different lengths, fewer than 3 common points, or a constant series give NaN.
    Text series are left out of ``names_used``."""
    if method not in ('pearson', 'spearman'):
        raise ValueError(f'unknown method: {method}')
    cols = {}
    for n in names:
        arr = _numeric(datasets[n]) if n in datasets else None
        if arr is not None:
            cols[n] = arr
    used = list(cols)
    mat = np.full((len(used), len(used)), np.nan)
    for i, a in enumerate(used):
        for j, b in enumerate(used):
            if j < i:
                mat[i, j] = mat[j, i]
                continue
            x, y = cols[a], cols[b]
            if len(x) != len(y):
                continue
            ok = np.isfinite(x) & np.isfinite(y)
            if ok.sum() < 3 or x[ok].std() == 0 or y[ok].std() == 0:
                continue
            xs, ys = x[ok], y[ok]
            if method == 'spearman':
                xs, ys = scipy_stats.rankdata(xs), scipy_stats.rankdata(ys)
            mat[i, j] = np.corrcoef(xs, ys)[0, 1]
    return used, mat
