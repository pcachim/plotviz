"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.


data/transforms.py - Series transformations (smoothing, decimation, calculus, scaling, resampling)

Every transform has the signature ``fn(x, y, **params) -> (x_out, y_out)``.
``x`` may be None (the index is used where a spacing is needed); ``x_out`` is trimmed or
resampled together with ``y`` when the length changes, and is None when ``x`` was None
(except for operations that create their own x: fft_spectrum and peaks).
OPERATIONS describes each transform so a UI can be built from it.
"""
import warnings

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy import signal, integrate, ndimage


def _as_float(a):
    return np.asarray(a, dtype=float)


def _need_x(x):
    if x is None:
        raise ValueError('this operation needs an x series')
    return _as_float(x)


def _range_values(x, y, x_from, x_to, what='range'):
    """y inside x_from <= x <= x_to (either limit may be None); the index stands in for x."""
    y = _as_float(y)
    pos = np.arange(len(y), dtype=float) if x is None else _as_float(x)
    keep = np.isfinite(y) & np.isfinite(pos)
    if x_from is not None:
        keep &= pos >= x_from
    if x_to is not None:
        keep &= pos <= x_to
    if not keep.any():
        raise ValueError(f'no points inside the {what} (x from {x_from} to {x_to})')
    return y[keep]


def _spacing(x, n):
    return np.arange(n, dtype=float) if x is None else _as_float(x)


# ── Smoothing ────────────────────────────────────────────────────────────────

def moving_average(x, y, window=5, align='centered', edges='partial'):
    """Rolling mean.  edges: 'partial' averages the points available at the ends,
    'nan' leaves NaN where the window is incomplete, 'trim' drops those points."""
    y = _as_float(y)
    n, w = len(y), int(window)
    if w < 1:
        raise ValueError('window must be at least 1')
    if w > n:
        raise ValueError(f'window ({w}) is longer than the series ({n} points)')
    idx = np.arange(n)
    lo = idx - w // 2 if align == 'centered' else idx - w + 1
    hi = lo + w - 1
    full = (lo >= 0) & (hi <= n - 1)
    lo, hi = np.clip(lo, 0, n - 1), np.clip(hi, 0, n - 1)
    csum = np.concatenate([[0.0], np.cumsum(y)])
    out = (csum[hi + 1] - csum[lo]) / (hi - lo + 1)
    if edges == 'nan':
        out = np.where(full, out, np.nan)
    elif edges == 'trim':
        return (None if x is None else _as_float(x)[full]), out[full]
    return (None if x is None else _as_float(x)), out


def median_filter(x, y, window=5):
    """Rolling median (window is rounded up to odd); robust against outliers."""
    y = _as_float(y)
    w = int(window) | 1
    if w > len(y):
        raise ValueError(f'window ({w}) is longer than the series ({len(y)} points)')
    return (None if x is None else _as_float(x)), signal.medfilt(y, w)


def exponential_smooth(x, y, alpha=0.3):
    """Exponential moving average: s[i] = alpha*y[i] + (1-alpha)*s[i-1]."""
    if not 0 < alpha <= 1:
        raise ValueError('alpha must be in (0, 1]')
    y = _as_float(y)
    out = signal.lfilter([alpha], [1, alpha - 1], y, zi=[(1 - alpha) * y[0]])[0] if len(y) else y
    return (None if x is None else _as_float(x)), out


def savitzky_golay(x, y, window=11, polyorder=3):
    """Savitzky-Golay filter: local polynomial fit, preserves peaks better than a mean."""
    y = _as_float(y)
    w, p = int(window) | 1, int(polyorder)
    if p >= w:
        raise ValueError(f'polynomial order ({p}) must be lower than the window ({w})')
    if w > len(y):
        raise ValueError(f'window ({w}) is longer than the series ({len(y)} points)')
    return (None if x is None else _as_float(x)), signal.savgol_filter(y, w, p)


def gaussian_smooth(x, y, sigma=2.0):
    """Gaussian filter; sigma is in points."""
    if sigma <= 0:
        raise ValueError('sigma must be positive')
    return (None if x is None else _as_float(x)), ndimage.gaussian_filter1d(
        _as_float(y), sigma, mode='nearest')


def _rolling(y, window, reducer):
    """Centered rolling reduction; the ends use the points that exist."""
    y = _as_float(y)
    w = int(window)
    if w < 1:
        raise ValueError('window must be at least 1')
    if w > len(y):
        raise ValueError(f'window ({w}) is longer than the series ({len(y)} points)')
    pad_lo, pad_hi = w // 2, w - 1 - w // 2
    padded = np.concatenate([np.full(pad_lo, np.nan), y, np.full(pad_hi, np.nan)])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)       # all-NaN windows -> NaN
        return reducer(sliding_window_view(padded, w), axis=1)


def rolling_std(x, y, window=5):
    return (None if x is None else _as_float(x)), _rolling(y, window, np.nanstd)


def rolling_min(x, y, window=5):
    return (None if x is None else _as_float(x)), _rolling(y, window, np.nanmin)


def rolling_max(x, y, window=5):
    return (None if x is None else _as_float(x)), _rolling(y, window, np.nanmax)


def butterworth(x, y, kind='lowpass', cutoff=0.1, order=4):
    """Zero-phase Butterworth filter.  ``cutoff`` is in cycles per x unit (cycles per point
    without an x series) and must be below half the sampling rate; x should be uniform."""
    y = _as_float(y)
    if not np.isfinite(y).all():
        raise ValueError('the series has NaN values; remove or interpolate them first')
    dt = 1.0 if x is None else float(np.median(np.diff(_as_float(x))))
    if dt <= 0:
        raise ValueError('x must be increasing')
    nyquist = 0.5 / dt
    if not 0 < cutoff < nyquist:
        raise ValueError(f'cutoff must be between 0 and {nyquist:.6g} (half the sampling rate)')
    sos = signal.butter(int(order), cutoff / nyquist, btype=kind, output='sos')
    return (None if x is None else _as_float(x)), signal.sosfiltfilt(sos, y)


# ── Reduction / resampling ───────────────────────────────────────────────────

def every_n(x, y, step=2, offset=0):
    """Keep one point out of every ``step``, starting at ``offset``."""
    step, offset = int(step), int(offset)
    if step < 1:
        raise ValueError('step must be at least 1')
    sel = slice(offset, None, step)
    y = _as_float(y)[sel]
    if not len(y):
        raise ValueError('offset is beyond the end of the series')
    return (None if x is None else _as_float(x)[sel]), y


def decimate(x, y, factor=2):
    """Keep every ``factor``-th point after a zero-phase anti-aliasing low-pass filter."""
    q = int(factor)
    if q < 1:
        raise ValueError('factor must be at least 1')
    y = _as_float(y)
    if not np.isfinite(y).all():
        raise ValueError('the series has NaN values; remove or interpolate them first')
    return (None if x is None else _as_float(x)[::q]), signal.decimate(y, q, ftype='fir', zero_phase=True)


def block_average(x, y, size=5):
    """Replace each block of ``size`` points by its mean (x too); a short last block is kept."""
    size = int(size)
    if size < 1:
        raise ValueError('block size must be at least 1')
    y = _as_float(y)
    starts = np.arange(0, len(y), size)
    ycol = np.add.reduceat(y, starts) / np.diff(np.append(starts, len(y)))
    if x is None:
        return None, ycol
    x = _as_float(x)
    return np.add.reduceat(x, starts) / np.diff(np.append(starts, len(x))), ycol


def resample_uniform(x, y, points=200, step=None):
    """Linear interpolation onto equally spaced x values: ``points`` of them, or, when
    ``step`` is given, one every ``step`` x units from the first x (step wins)."""
    x, y = _need_x(x), _as_float(y)
    order = np.argsort(x, kind='stable')
    xs, ys = x[order], y[order]
    if step is not None:
        if step <= 0:
            raise ValueError('step must be positive')
        count = int(np.floor((xs[-1] - xs[0]) / step + 1e-9)) + 1
        if count > 5_000_000:
            raise ValueError(f'a step of {step:g} would give {count} points')
        grid = xs[0] + step * np.arange(count)
    else:
        points = int(points)
        if points < 2:
            raise ValueError('need at least 2 points')
        grid = np.linspace(xs[0], xs[-1], points)
    return grid, np.interp(grid, xs, ys)


def align_to_x(x, y, target_x=None, method='linear'):
    """Interpolate y onto the x values of another series (NaN outside the range of x)."""
    x, y = _need_x(x), _as_float(y)
    if target_x is None:
        raise ValueError('choose the series whose x values to use')
    target = _as_float(target_x)
    order = np.argsort(x, kind='stable')
    xs, ys = x[order], y[order]
    if method == 'pchip':
        from scipy.interpolate import PchipInterpolator
        out = PchipInterpolator(xs, ys, extrapolate=False)(target)
    else:
        out = np.interp(target, xs, ys, left=np.nan, right=np.nan)
    return target, out


def sort_by_x(x, y):
    """Reorder the points so that x increases."""
    x, y = _need_x(x), _as_float(y)
    order = np.argsort(x, kind='stable')
    return x[order], y[order]


# ── Calculus ─────────────────────────────────────────────────────────────────

def derivative(x, y):
    """dy/dx by central differences (dy/dindex when there is no x)."""
    y = _as_float(y)
    if len(y) < 2:
        raise ValueError('need at least 2 points')
    return (None if x is None else _as_float(x)), np.gradient(y, _spacing(x, len(y)))


def cumulative_integral(x, y, start=0.0):
    """Running integral by the trapezoid rule, starting at ``start`` (the constant of integration)."""
    y = _as_float(y)
    out = integrate.cumulative_trapezoid(y, _spacing(x, len(y)), initial=0) + start
    return (None if x is None else _as_float(x)), out


def second_derivative(x, y):
    """d2y/dx2 by repeated central differences (needs at least 3 points)."""
    y = _as_float(y)
    if len(y) < 3:
        raise ValueError('need at least 3 points')
    pos = _spacing(x, len(y))
    return (None if x is None else _as_float(x)), np.gradient(np.gradient(y, pos), pos)


def percent_change(x, y):
    """100 * (y[i] - y[i-1]) / |y[i-1]|; the first point is NaN."""
    y = _as_float(y)
    with np.errstate(divide='ignore', invalid='ignore'):
        out = 100 * np.diff(y) / np.abs(y[:-1])
    return (None if x is None else _as_float(x)), np.concatenate([[np.nan], out])


def log_return(x, y):
    """ln(y[i] / y[i-1]); needs y > 0.  The first point is NaN."""
    y = _as_float(y)
    if (y[np.isfinite(y)] <= 0).any():
        raise ValueError('log return needs every value to be positive')
    return (None if x is None else _as_float(x)), np.concatenate([[np.nan], np.diff(np.log(y))])


def difference(x, y):
    """y[i] - y[i-1]; the first point is NaN so the series keeps its length."""
    y = _as_float(y)
    return (None if x is None else _as_float(x)), np.concatenate([[np.nan], np.diff(y)])


def cumulative_sum(x, y):
    return (None if x is None else _as_float(x)), np.cumsum(_as_float(y))


# ── Scaling ──────────────────────────────────────────────────────────────────

def normalize(x, y, method='min-max', value=1.0, x_from=None, x_to=None):
    """min-max -> [0, 1]; z-score -> mean 0, std 1; first -> y/y[0]; max -> y/max|y|;
    value -> y/value; mean of range -> y divided by its mean between x_from and x_to."""
    y = _as_float(y)
    if method == 'min-max':
        lo, hi = np.nanmin(y), np.nanmax(y)
        out = (y - lo) / (hi - lo) if hi != lo else np.zeros_like(y)
    elif method == 'z-score':
        sd = np.nanstd(y)
        out = (y - np.nanmean(y)) / sd if sd else np.zeros_like(y)
    elif method == 'first':
        if y[0] == 0:
            raise ValueError('first value is 0')
        out = y / y[0]
    elif method == 'max':
        m = np.nanmax(np.abs(y))
        if m == 0:
            raise ValueError('series is all zeros')
        out = y / m
    elif method == 'value':
        if value == 0:
            raise ValueError('cannot divide by 0')
        out = y / value
    elif method == 'mean of range':
        ref = np.mean(_range_values(x, y, x_from, x_to))
        if ref == 0:
            raise ValueError('the mean of the range is 0')
        out = y / ref
    else:
        raise ValueError(f'unknown method: {method}')
    return (None if x is None else _as_float(x)), out


def subtract_baseline(x, y, method='first', value=0.0, x_from=None, x_to=None):
    """Subtract the first value, last value, mean, median or minimum; a fixed ``value``;
    or the mean / median of the points between x_from and x_to (a quiet stretch)."""
    y = _as_float(y)
    base = {'first': lambda: y[0], 'last': lambda: y[-1], 'mean': lambda: np.nanmean(y),
            'median': lambda: np.nanmedian(y), 'min': lambda: np.nanmin(y),
            'value': lambda: value,
            'mean of range': lambda: np.mean(_range_values(x, y, x_from, x_to)),
            'median of range': lambda: np.median(_range_values(x, y, x_from, x_to))}.get(method)
    if base is None:
        raise ValueError(f'unknown baseline: {method}')
    return (None if x is None else _as_float(x)), y - base()


def absolute(x, y):
    return (None if x is None else _as_float(x)), np.abs(_as_float(y))


def scale_shift(x, y, a=1.0, b=0.0):
    """a*y + b."""
    return (None if x is None else _as_float(x)), a * _as_float(y) + b


def crop_x(x, y, xmin=None, xmax=None):
    """Keep the points with xmin <= x <= xmax (either bound may be left open)."""
    x, y = _need_x(x), _as_float(y)
    keep = np.ones(len(x), dtype=bool)
    if xmin is not None:
        keep &= x >= xmin
    if xmax is not None:
        keep &= x <= xmax
    if not keep.any():
        raise ValueError('no points inside that x range')
    return x[keep], y[keep]


# ── Cleaning ─────────────────────────────────────────────────────────────────

def remove_nan(x, y):
    """Drop the points where y (or x) is NaN/inf."""
    y = _as_float(y)
    keep = np.isfinite(y)
    if x is not None:
        x = _as_float(x)
        keep &= np.isfinite(x)
    if not keep.any():
        raise ValueError('every point is NaN')
    return (None if x is None else x[keep]), y[keep]


def interpolate_nan(x, y):
    """Fill NaN/inf in y by linear interpolation (the ends hold the nearest valid value)."""
    y = _as_float(y).copy()
    pos = np.arange(len(y), dtype=float) if x is None else _as_float(x)
    ok = np.isfinite(y)
    if not ok.any():
        raise ValueError('every point is NaN')
    order = np.argsort(pos[ok], kind='stable')
    y[~ok] = np.interp(pos[~ok], pos[ok][order], y[ok][order])
    return (None if x is None else _as_float(x)), y


def clip_values(x, y, lower=None, upper=None):
    """Limit y to [lower, upper] (either bound may be left open)."""
    if lower is None and upper is None:
        raise ValueError('set a lower and/or an upper limit')
    if lower is not None and upper is not None and lower > upper:
        raise ValueError('lower limit is above the upper limit')
    return (None if x is None else _as_float(x)), np.clip(_as_float(y), lower, upper)


def hampel(x, y, window=7, n_sigmas=3.0):
    """Replace outliers by the local median.  A point is an outlier when it is more than
    n_sigmas robust standard deviations (1.4826 * MAD) from the rolling median."""
    y = _as_float(y)
    w = int(window) | 1
    if w > len(y):
        raise ValueError(f'window ({w}) is longer than the series ({len(y)} points)')
    med = ndimage.median_filter(y, size=w, mode='nearest')
    mad = ndimage.median_filter(np.abs(y - med), size=w, mode='nearest')
    out = np.where(np.abs(y - med) > n_sigmas * 1.4826 * mad, med, y)
    return (None if x is None else _as_float(x)), out


# ── Baseline ─────────────────────────────────────────────────────────────────

def detrend(x, y, degree=1, x_from=None, x_to=None):
    """Subtract a least-squares polynomial of the given degree (1 = straight line).  The fit
    can be limited to x_from..x_to (so that a peak does not pull it); it is subtracted everywhere."""
    y = _as_float(y)
    pos = np.arange(len(y), dtype=float) if x is None else _as_float(x)
    ok = np.isfinite(y) & np.isfinite(pos)
    if x_from is not None:
        ok &= pos >= x_from
    if x_to is not None:
        ok &= pos <= x_to
    degree = int(degree)
    if ok.sum() <= degree:
        raise ValueError(f'need more than {degree} valid points for a degree-{degree} fit')
    centre = pos[ok].mean()
    coeffs = np.polyfit(pos[ok] - centre, y[ok], degree)
    return (None if x is None else _as_float(x)), y - np.polyval(coeffs, pos - centre)


def cumulative_max(x, y):
    return (None if x is None else _as_float(x)), np.fmax.accumulate(_as_float(y))


def cumulative_min(x, y):
    return (None if x is None else _as_float(x)), np.fmin.accumulate(_as_float(y))


# ── Signal analysis ──────────────────────────────────────────────────────────

def fft_spectrum(x, y, remove_mean='yes'):
    """Single-sided amplitude spectrum.  Returns (frequency, amplitude); x must be
    (roughly) uniform and gives the sampling interval, otherwise 1 per point is assumed."""
    y = _as_float(y)
    if len(y) < 2:
        raise ValueError('need at least 2 points')
    if not np.isfinite(y).all():
        raise ValueError('the series has NaN values; remove or interpolate them first')
    dt = 1.0 if x is None else float(np.median(np.diff(_as_float(x))))
    if dt <= 0:
        raise ValueError('x must be increasing')
    if remove_mean == 'yes':
        y = y - y.mean()
    amp = np.abs(np.fft.rfft(y)) * 2 / len(y)
    amp[0] /= 2                                  # DC term is not doubled
    if len(y) % 2 == 0:
        amp[-1] /= 2                             # nor is Nyquist
    return np.fft.rfftfreq(len(y), dt), amp


def noise_sigma(y):
    """Noise level of a series: the median absolute deviation about the median, scaled to a
    standard deviation.  A few peaks do not inflate it, but a drift does (remove it first)."""
    y = _as_float(y)
    y = y[np.isfinite(y)]
    if not len(y):
        raise ValueError('every point is NaN')
    return float(1.4826 * np.median(np.abs(y - np.median(y))))


def peaks(x, y, min_height=None, min_prominence=None, min_distance=1, min_height_noise=None):
    """Local maxima of y.  Returns (x, y) of the peaks only (x = point index without an x series).

    ``min_height_noise`` sets the height threshold as median + k * noise (see noise_sigma); with
    ``min_height`` as well, the higher of the two applies."""
    y = _as_float(y)
    height = min_height
    if min_height_noise is not None:
        limit = float(np.nanmedian(y)) + min_height_noise * noise_sigma(y)
        height = limit if height is None else max(height, limit)
    idx, _ = signal.find_peaks(y, height=height, prominence=min_prominence,
                               distance=max(int(min_distance), 1))
    if not len(idx):
        where = '' if height is None else f' above {height:.6g}'
        raise ValueError(f'no peaks found{where}; try lower thresholds')
    return (idx.astype(float) if x is None else _as_float(x)[idx]), y[idx]


# ── For drawing a long series ────────────────────────────────────────────────

def downsample_minmax(x, y, max_points=2000):
    """At most about *max_points* of the points to draw: the lowest and the highest point of every
    block of the series, in order, so no peak or dip is lost.  (Drawing only; never for results.)"""
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    n = len(y)
    if n <= max_points:
        return x, y
    edges = np.linspace(0, n, max(max_points // 2, 1) + 1).astype(int)
    keep = []
    for a, b in zip(edges[:-1], edges[1:]):
        if b <= a:
            continue
        segment = y[a:b]
        if np.all(np.isnan(segment)):
            keep.append(a)
            continue
        keep.extend((a + int(np.nanargmin(segment)), a + int(np.nanargmax(segment))))
    index = np.array(sorted(set(keep)))
    return x[index], y[index]


# ── Registry (drives the UI) ─────────────────────────────────────────────────
# param = (name, label, kind, default, extra[, show_when]): kind 'int'/'float' -> extra=(min, max);
# show_when = {other_param: [values]} shows the row only while that choice parameter has one of them;
# 'optfloat' is a float that may be left unset (None); 'optx' is an optional x value (the UI
# accepts a date when x is a date column); 'choice' -> extra=list of values;
# 'series' -> another loaded series, passed to the function as an array.
# Operations are listed by group, and the UI shows the groups as headers.

def _op(group, key, label, fn, suffix, params=(), needs_x=False):
    return {'group': group, 'key': key, 'label': label, 'fn': fn, 'suffix': suffix,
            'needs_x': needs_x, 'params': list(params)}


_WIN = ('window', 'Window', 'int', 5, (1, 100000))

OPERATIONS = [
    _op('Smoothing', 'moving_average', 'Moving average', moving_average, 'MA{window}', [
        _WIN,
        ('align', 'Window', 'choice', 'centered', ['centered', 'trailing']),
        ('edges', 'Ends', 'choice', 'partial', ['partial', 'nan', 'trim'])]),
    _op('Smoothing', 'median_filter', 'Moving median', median_filter, 'med{window}', [_WIN]),
    _op('Smoothing', 'exponential_smooth', 'Exponential smoothing', exponential_smooth, 'EMA', [
        ('alpha', 'Alpha', 'float', 0.3, (0.001, 1.0))]),
    _op('Smoothing', 'savitzky_golay', 'Savitzky-Golay', savitzky_golay, 'SG{window}', [
        ('window', 'Window', 'int', 11, (3, 100000)),
        ('polyorder', 'Poly order', 'int', 3, (1, 20))]),
    _op('Smoothing', 'gaussian_smooth', 'Gaussian', gaussian_smooth, 'gauss', [
        ('sigma', 'Sigma (points)', 'float', 2.0, (0.1, 100000.0))]),

    _op('Smoothing', 'butterworth', 'Low/high-pass filter (Butterworth)', butterworth, 'bw', [
        ('kind', 'Type', 'choice', 'lowpass', ['lowpass', 'highpass']),
        ('cutoff', 'Cutoff (cycles per x)', 'float', 0.1, (1e-9, 1e12)),
        ('order', 'Order', 'int', 4, (1, 12))]),

    _op('Reduce and resample', 'every_n', 'Every N points', every_n, 'every{step}', [
        ('step', 'N', 'int', 2, (1, 1000000)),
        ('offset', 'Start at', 'int', 0, (0, 1000000))]),
    _op('Reduce and resample', 'block_average', 'Block average', block_average, 'blk{size}', [
        ('size', 'Block size', 'int', 5, (1, 1000000))]),
    _op('Reduce and resample', 'resample_uniform', 'Resample (uniform x)', resample_uniform, 'rs', [
        ('points', 'Points', 'int', 200, (2, 10000000)),
        ('step', 'Step (instead of points)', 'optfloat', None, (1e-12, 1e12))], needs_x=True),
    _op('Reduce and resample', 'decimate', 'Decimate (anti-aliased)', decimate, 'dec{factor}', [
        ('factor', 'Factor', 'int', 2, (1, 1000))]),
    _op('Reduce and resample', 'align_to_x', 'Align to another x', align_to_x, 'al', [
        ('target_x', 'Use x of', 'series', None, None),
        ('method', 'Interpolation', 'choice', 'linear', ['linear', 'pchip'])], needs_x=True),
    _op('Reduce and resample', 'crop_x', 'Crop x range', crop_x, 'crop', [
        ('xmin', 'x min', 'optx', None, None),
        ('xmax', 'x max', 'optx', None, None)], needs_x=True),

    _op('Calculus', 'derivative', 'Derivative dy/dx', derivative, 'd'),
    _op('Calculus', 'cumulative_integral', 'Integral (cumulative)', cumulative_integral, 'int', [
        ('start', 'Starts at', 'float', 0.0, (-1e12, 1e12))]),
    _op('Calculus', 'second_derivative', 'Second derivative d2y/dx2', second_derivative, 'd2'),
    _op('Calculus', 'percent_change', 'Percent change', percent_change, 'pct'),
    _op('Calculus', 'log_return', 'Log return', log_return, 'logret'),
    _op('Calculus', 'difference', 'Difference', difference, 'diff'),
    _op('Calculus', 'cumulative_sum', 'Cumulative sum', cumulative_sum, 'cumsum'),

    _op('Scale and baseline', 'normalize', 'Normalize', normalize, 'norm', [
        ('method', 'Method', 'choice', 'min-max',
         ['min-max', 'z-score', 'first', 'max', 'value', 'mean of range']),
        ('value', 'Divide by', 'float', 1.0, (-1e12, 1e12), {'method': ['value']}),
        ('x_from', 'x from', 'optx', None, None, {'method': ['mean of range']}),
        ('x_to', 'x to', 'optx', None, None, {'method': ['mean of range']})]),
    _op('Scale and baseline', 'scale_shift', 'Scale and shift (a·y + b)', scale_shift, 'ab', [
        ('a', 'a', 'float', 1.0, (-1e12, 1e12)),
        ('b', 'b', 'float', 0.0, (-1e12, 1e12))]),
    _op('Scale and baseline', 'subtract_baseline', 'Subtract baseline', subtract_baseline, 'bl', [
        ('method', 'Baseline', 'choice', 'first',
         ['first', 'last', 'mean', 'median', 'min', 'value', 'mean of range', 'median of range']),
        ('value', 'Value', 'float', 0.0, (-1e12, 1e12), {'method': ['value']}),
        ('x_from', 'x from', 'optx', None, None, {'method': ['mean of range', 'median of range']}),
        ('x_to', 'x to', 'optx', None, None, {'method': ['mean of range', 'median of range']})]),
    _op('Scale and baseline', 'absolute', 'Absolute value', absolute, 'abs'),
    _op('Scale and baseline', 'detrend', 'Remove trend (polynomial)', detrend, 'detr', [
        ('degree', 'Degree', 'int', 1, (0, 20)),
        ('x_from', 'Fit from x', 'optx', None, None),
        ('x_to', 'Fit to x', 'optx', None, None)]),

    _op('Cleaning', 'remove_nan', 'Remove NaN', remove_nan, 'noNaN'),
    _op('Cleaning', 'interpolate_nan', 'Interpolate NaN', interpolate_nan, 'interp'),
    _op('Cleaning', 'clip_values', 'Limit to a range', clip_values, 'clip', [
        ('lower', 'Lower', 'optfloat', None, (-1e12, 1e12)),
        ('upper', 'Upper', 'optfloat', None, (-1e12, 1e12))]),
    _op('Cleaning', 'sort_by_x', 'Sort by x', sort_by_x, 'sorted', needs_x=True),
    _op('Cleaning', 'hampel', 'Outlier filter (Hampel)', hampel, 'hampel', [
        ('window', 'Window', 'int', 7, (3, 100000)),
        ('n_sigmas', 'Sigmas', 'float', 3.0, (0.5, 100.0))]),

    _op('Rolling statistics', 'rolling_std', 'Rolling std deviation', rolling_std, 'std{window}', [_WIN]),
    _op('Rolling statistics', 'rolling_min', 'Rolling minimum', rolling_min, 'rmin{window}', [_WIN]),
    _op('Rolling statistics', 'rolling_max', 'Rolling maximum', rolling_max, 'rmax{window}', [_WIN]),
    _op('Rolling statistics', 'cumulative_min', 'Running minimum', cumulative_min, 'cummin'),
    _op('Rolling statistics', 'cumulative_max', 'Running maximum', cumulative_max, 'cummax'),

    _op('Signal analysis', 'fft_spectrum', 'FFT amplitude spectrum', fft_spectrum, 'fft', [
        ('remove_mean', 'Remove mean', 'choice', 'yes', ['yes', 'no'])]),
    _op('Signal analysis', 'peaks', 'Find peaks', peaks, 'peaks', [
        ('min_height_noise', 'Min height (× noise)', 'optfloat', None, (0.0, 1e6)),
        ('min_height', 'Min height', 'optfloat', None, (-1e12, 1e12)),
        ('min_prominence', 'Min prominence', 'optfloat', None, (0.0, 1e12)),
        ('min_distance', 'Min distance', 'int', 1, (1, 1000000))]),
]

OPERATIONS_BY_KEY = {op['key']: op for op in OPERATIONS}


def apply_operation(key, x, y, **params):
    """Run the registered operation ``key``; returns (x_out, y_out)."""
    return OPERATIONS_BY_KEY[key]['fn'](x, y, **params)


def default_suffix(key, params):
    """Output-name suffix for an operation, e.g. 'MA5' for a 5-point moving average."""
    suffix = OPERATIONS_BY_KEY[key]['suffix']
    try:
        return suffix.format(**params)
    except (KeyError, IndexError):
        return suffix
