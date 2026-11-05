"""Render the figures of the Transform page of the guide.

Each figure applies several operations of one group to the same signal, with the code that the
app itself uses (data/transforms.py), and draws the original in grey with the result over it.
The signals are synthetic with a fixed seed, so the pictures are the same every time.

    uv run python util/make_doc_transforms.py

Files: docs/images/transform/<group>.png
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "plotviz"))

from data.transforms import apply_operation  # noqa: E402

OUT = ROOT / "docs" / "images" / "transform"
DPI = 100
GREY, RESULT = "#9a9a9a", "#ff7f0e"
GROUPS = ["smoothing", "resample", "calculus", "scale-baseline", "cleaning", "rolling", "signal-analysis"]


def noisy_signal():
    """A slow wave, a narrow bump, a two-point spike (an outlier) and noise: 500 points over 10 s."""
    rng = np.random.default_rng(7)
    t = np.linspace(0, 10, 500)
    y = np.sin(2 * np.pi * t / 5) + 1.2 * np.exp(-((t - 7) / 0.25) ** 2) + rng.normal(0, 0.15, t.size)
    y[150:152] += 6.0
    return t, y


def two_tone_signal():
    """A 0.4 Hz wave plus a 7.3 Hz one, sampled at 50 Hz, so that taking every 10th point aliases it."""
    t = np.linspace(0, 10, 500, endpoint=False)
    return t, np.sin(2 * np.pi * 0.4 * t) + 0.5 * np.sin(2 * np.pi * 7.3 * t)


def panel(ax, title, x, y, xo, yo, markers=False, original_style=None):
    ax.plot(x, y, color=GREY, lw=0.9, label="original", **(original_style or {}))
    ax.plot(xo, yo, color=RESULT, lw=1.4, marker="o" if markers else None, ms=3, label="result")
    ax.set_title(title, fontsize=9)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.25, lw=0.5)


def finish(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    path = OUT / f"{name}.png"
    fig.savefig(path, dpi=DPI, facecolor="white")
    plt.close(fig)
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"{name:<16} {shown}  {path.stat().st_size // 1024} KB")


def smoothing():
    t, y = noisy_signal()
    cases = [
        ("Moving average, window 15", "moving_average", {"window": 15}),
        ("Moving median, window 15", "median_filter", {"window": 15}),
        ("Exponential smoothing, alpha 0.15", "exponential_smooth", {"alpha": 0.15}),
        ("Savitzky-Golay, window 31, order 3", "savitzky_golay", {"window": 31, "polyorder": 3}),
        ("Gaussian, sigma 6", "gaussian_smooth", {"sigma": 6.0}),
        ("Butterworth low-pass, cutoff 1 Hz", "butterworth", {"kind": "lowpass", "cutoff": 1.0, "order": 4}),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.6), sharex=True, sharey=True)
    for ax, (title, key, params) in zip(axes.ravel(), cases):
        xo, yo = apply_operation(key, t, y, **params)
        panel(ax, title, t, y, t if xo is None else xo, yo)
    axes[0, 0].set_ylim(-1.6, 2.6)               # the spike (to 6) leaves the frame, on purpose
    axes[0, 0].legend(fontsize=7, frameon=False, loc="upper left")
    finish(fig, "smoothing")


def resample():
    t, y = two_tone_signal()
    fig, axes = plt.subplots(2, 2, figsize=(9.6, 5.6))
    window = slice(0, 100)                      # the first two seconds: enough to see the shapes
    for ax, (title, key, params) in zip(axes.ravel()[:3], [
            ("Every N points, N = 10", "every_n", {"step": 10}),
            ("Block average, size 10", "block_average", {"size": 10}),
            ("Decimate (anti-aliased), factor 10", "decimate", {"factor": 10})]):
        xo, yo = apply_operation(key, t, y, **params)
        keep = xo <= t[window][-1]
        panel(ax, title, t[window], y[window], xo[keep], yo[keep], markers=True)
    rng = np.random.default_rng(3)
    xi = np.sort(rng.uniform(0, 10, 70))        # unevenly spaced samples
    yi = np.sin(2 * np.pi * xi / 5) + rng.normal(0, 0.05, xi.size)
    xo, yo = apply_operation("resample_uniform", xi, yi, points=25)
    ax = axes[1, 1]
    ax.plot(xi, yi, "o", color=GREY, ms=3, label="original (uneven x)")
    ax.plot(xo, yo, color=RESULT, lw=1.4, marker="o", ms=3, label="result")
    ax.set_title("Resample (uniform x), 25 points", fontsize=9)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.25, lw=0.5)
    axes[0, 0].legend(fontsize=7, frameon=False, loc="upper right")
    ax.legend(fontsize=7, frameon=False, loc="upper right")
    for ax in axes.ravel()[:3]:
        ax.set_xlabel("t (s)", fontsize=8)
    finish(fig, "resample")


def small_panel(ax, title, x, y, xo=None, yo=None, result_kw=None, **kw):
    """One panel: *y* in grey and, when given, the result over it."""
    ax.plot(x, y, color=GREY if yo is not None else RESULT, lw=0.9 if yo is not None else 1.4, **kw)
    if yo is not None:
        ax.plot(x if xo is None else xo, yo, color=RESULT, lw=1.4, **(result_kw or {}))
    ax.set_title(title, fontsize=9)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.25, lw=0.5)


def calculus():
    t = np.linspace(0, 10, 200)
    y = 2 + np.sin(t) + 0.2 * t
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.6))
    small_panel(axes[0, 0], "Original: y = 2 + sin t + 0.2 t", t, y)
    for ax, (title, key) in zip(axes.ravel()[1:], [
            ("Derivative dy/dx", "derivative"), ("Second derivative d2y/dx2", "second_derivative"),
            ("Integral (cumulative)", "cumulative_integral"), ("Difference", "difference"),
            ("Percent change", "percent_change")]):
        xo, yo = apply_operation(key, t, y)
        small_panel(ax, title, t if xo is None else xo, yo)
    finish(fig, "calculus")


def scale_baseline():
    rng = np.random.default_rng(5)
    t = np.linspace(0, 10, 300)
    y = 5 + 0.3 * t + 3 * np.exp(-((t - 6) / 0.3) ** 2) + rng.normal(0, 0.08, t.size)
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.6))
    small_panel(axes[0, 0], "Original: offset, drift and a peak", t, y)
    cases = [
        ("Normalize, min-max", "normalize", {"method": "min-max"}),
        ("Normalize, z-score", "normalize", {"method": "z-score"}),
        ("Subtract baseline, mean of x 0 to 2", "subtract_baseline", {"method": "mean of range", "x_from": 0.0, "x_to": 2.0}),
        ("Remove trend, degree 1, fitted on x 0 to 4", "detrend", {"degree": 1, "x_from": 0.0, "x_to": 4.0}),
    ]
    for ax, (title, key, params) in zip(axes.ravel()[1:5], cases):
        xo, yo = apply_operation(key, t, y, **params)
        small_panel(ax, title, t if xo is None else xo, yo)
    xo, yo = apply_operation("scale_shift", t, y, a=0.5, b=-2.0)
    small_panel(axes[1, 2], "Scale and shift, 0.5·y − 2", t, yo)
    finish(fig, "scale-baseline")


def cleaning():
    rng = np.random.default_rng(11)
    t = np.linspace(0, 10, 200)
    y = np.sin(t) + rng.normal(0, 0.05, t.size)
    y[[70, 140, 170]] += [2.5, -2.2, 1.8]            # three outliers
    y[40:55] = np.nan                                 # two gaps
    y[110:120] = np.nan
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.6), sharey=True)
    small_panel(axes[0, 0], "Original: gaps (NaN) and outliers", t, y)
    for ax, (title, key, params) in zip(axes.ravel()[1:5], [
            ("Remove NaN", "remove_nan", {}), ("Interpolate NaN", "interpolate_nan", {}),
            ("Limit to a range, -1.3 to 1.3", "clip_values", {"lower": -1.3, "upper": 1.3}),
            ("Outlier filter (Hampel), window 7, 3 sigmas", "hampel", {"window": 7, "n_sigmas": 3.0})]):
        xo, yo = apply_operation(key, t, y, **params)
        dots = {"marker": ".", "ms": 3} if key in ("remove_nan", "interpolate_nan") else None
        small_panel(ax, title, t, y, xo, yo, result_kw=dots)
    order = rng.permutation(60)                      # points that arrive out of order
    xs, ys = np.linspace(0, 10, 60)[order], np.sin(np.linspace(0, 10, 60)[order])
    xo, yo = apply_operation("sort_by_x", xs, ys)
    small_panel(axes[1, 2], "Sort by x", xs, ys, xo, yo)
    for ax in axes.ravel():
        ax.set_ylim(-2.4, 3.0)
    finish(fig, "cleaning")


def rolling():
    t, y = noisy_signal()
    y = y.copy()
    y[150:152] -= 6.0                                # no spike here: the point is the envelope
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.4), sharex=True)
    xo, yo = apply_operation("rolling_std", t, y, window=25)
    small_panel(axes[0], "Rolling std deviation, window 25", t, yo)
    xo, lo = apply_operation("rolling_min", t, y, window=25)
    xo, hi = apply_operation("rolling_max", t, y, window=25)
    axes[1].plot(t, y, color=GREY, lw=0.9)
    axes[1].fill_between(t, lo, hi, color=RESULT, alpha=0.35, lw=0)
    axes[1].plot(t, lo, color=RESULT, lw=1.1)
    axes[1].plot(t, hi, color=RESULT, lw=1.1)
    axes[1].set_title("Rolling minimum and maximum, window 25", fontsize=9)
    xo, lo = apply_operation("cumulative_min", t, y)
    xo, hi = apply_operation("cumulative_max", t, y)
    axes[2].plot(t, y, color=GREY, lw=0.9)
    axes[2].plot(t, lo, color=RESULT, lw=1.4)
    axes[2].plot(t, hi, color=RESULT, lw=1.4)
    axes[2].set_title("Running minimum and maximum", fontsize=9)
    for ax in axes[1:]:
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.25, lw=0.5)
    finish(fig, "rolling")


def signal_analysis():
    t, y = two_tone_signal()
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6))
    freq, amp = apply_operation("fft_spectrum", t, y)
    ax = axes[0]
    ax.plot(freq, amp, color=RESULT, lw=1.4)
    ax.set_xlim(0, 12)
    ax.set_title("FFT amplitude spectrum", fontsize=9)
    ax.set_xlabel("frequency (Hz)", fontsize=8)
    ax.set_ylabel("amplitude", fontsize=8)
    ax.annotate("0.4 Hz", (0.4, 1.0), xytext=(1.6, 0.95), fontsize=8, arrowprops={"arrowstyle": "->", "lw": 0.7})
    ax.annotate("7.3 Hz", (7.3, 0.5), xytext=(8.4, 0.62), fontsize=8, arrowprops={"arrowstyle": "->", "lw": 0.7})
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.25, lw=0.5)
    pulse = ROOT / "data" / "datasets" / "pulse_signal.csv"
    data = np.genfromtxt(pulse, delimiter=",", names=True)
    xs, ys = data["time_s"], data["voltage"]
    px, py = apply_operation("peaks", xs, ys, min_height_noise=5.0)
    ax = axes[1]
    ax.plot(xs, ys, color=GREY, lw=0.9, label="voltage")
    ax.plot(px, py, "o", color=RESULT, ms=6, label=f"{len(px)} peak(s)")
    ax.set_title("Find peaks, 5 × noise above the baseline", fontsize=9)
    ax.set_xlabel("time (s)", fontsize=8)
    ax.legend(fontsize=7, frameon=False, loc="upper right")
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.25, lw=0.5)
    finish(fig, "signal-analysis")


def main(only: list[str]) -> int:
    unknown = [g for g in only if g not in GROUPS]
    if unknown:
        print("unknown figure(s):", ", ".join(unknown), "| known:", ", ".join(GROUPS))
        return 2
    makers = {"smoothing": smoothing, "resample": resample, "calculus": calculus, "scale-baseline": scale_baseline,
              "cleaning": cleaning, "rolling": rolling, "signal-analysis": signal_analysis}
    for name in GROUPS:
        if not only or name in only:
            makers[name]()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
