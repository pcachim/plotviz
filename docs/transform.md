# Transform and Statistics

The **Data** tab has four pages: **Datasets**, **Transform**, **Statistics** and **Generate**. This page covers the two that work on series you have already loaded: **Transform** creates new series from existing ones, and **Statistics** summarises them.

---

## Transform

The Transform page applies an operation (smoothing, decimation, calculus, scaling, cleaning, resampling…) to a series and stores the result as a **new series**. The original is never changed, so you can plot both together.

### Using it

1. **x** — the horizontal axis (for example the time or position series). Optional: choose `(none: use index)` when the series has no x column. Operations that need an x (resampling, cropping, sorting, aligning) report an error without it. Derivatives and integrals use the index as the spacing when there is no x.
2. **y** — the series to transform (the values: the signal, the measurement). Swapping x and y gives odd results, because the result is calculated *as a function of x*: resampling `y_irregular` over `t_irregular` is a different curve from resampling `t_irregular` over `y_irregular`.
3. **Operation** — pick it from the list, which is grouped by type (the group names are bold headers).
4. Set the parameters, which change with the operation.
5. Optionally type a **Name** for the result; the default is the series name plus a suffix, for example `signal_MA5`.
6. Click **Apply**.

The status line under the button says what was created and how many points it has. New series appear at once in the Datasets list and in the series table.

### Dates

When x is a date column, the operations that keep or select x values keep it as dates: the new x series from cropping, decimating, resampling, aligning, removing NaN or finding peaks is a date series, and plots with a date axis. Notes:

- **Crop x range**: type the limits as dates, for example `2024-03-01` or `1 Mar 2024 12:00`. Leave a box empty for no limit.
- **Resample (uniform x)**, derivatives, integrals and filters work in **days**: the derivative is per day, and the Butterworth cutoff is in cycles per day.
- **FFT amplitude spectrum**: the frequencies are in cycles per day, and are not dates.
- Moving average, median and the other window operations count **points**, not time, so they assume regular sampling; use *Resample (uniform x)* first if the dates are irregular.

!!! note "Results are calculated once"
    A transformed series is a copy. If you later change or reload the original data, the transformed series is not recalculated — apply the operation again.

### When x changes

Some operations change the number or position of the points (decimating, cropping, resampling, removing NaN, FFT, peaks…). When that happens a **new x series** is created next to the new y, named after the x series and the suffix, for example `t_every3` and `y_every3`. Plot the pair together.

- **FFT** and **Find peaks** create their own x even if you chose none: frequencies for the FFT, and the x of each peak (the point index when there is no x series).
- **Align to another x** reuses the x of the series you chose instead of creating a duplicate; the status line tells you which series to use as x.

### Operations

#### Smoothing

| Operation | Parameters | Notes |
|-----------|-----------|-------|
| Moving average | Window, centered/trailing, ends | Ends: `partial` averages the points that exist, `nan` leaves NaN where the window is incomplete, `trim` removes those points (and their x) |
| Moving median | Window | Robust against isolated spikes; the window is rounded up to an odd number |
| Exponential smoothing | Alpha (0–1) | `s[i] = α·y[i] + (1−α)·s[i−1]`; a smaller alpha smooths more |
| Savitzky-Golay | Window, polynomial order | Local polynomial fit; keeps peak heights and widths better than a plain average. The order must be lower than the window |
| Gaussian | Sigma (in points) | Gaussian kernel |
| Low/high-pass filter (Butterworth) | Type, cutoff, order | Zero-phase. The cutoff is in cycles per x unit (cycles per point with no x) and must be below half the sampling rate. x should be evenly spaced and y must have no NaN |

#### Reduce and resample

| Operation | Parameters | Notes |
|-----------|-----------|-------|
| Every N points | N, start at | Keeps one point out of every N |
| Block average | Block size | Replaces each block by its mean, x included; a short last block is kept |
| Resample (uniform x) | Points | Linear interpolation onto equally spaced x; needs x |
| Decimate (anti-aliased) | Factor | Low-pass filters first, then keeps every N-th point. y must have no NaN |
| Align to another x | Series, interpolation | Interpolates y onto the x of another series (`linear` or `pchip`); NaN outside the range of the original x. Needs x |
| Crop x range | x min, x max | Keeps `x min ≤ x ≤ x max`; leave a bound on `auto` to leave it open. Needs x |

#### Calculus

| Operation | Notes |
|-----------|-------|
| Derivative dy/dx | Central differences |
| Second derivative d2y/dx2 | Needs at least 3 points |
| Integral (cumulative) | Trapezoid rule, starting at 0 |
| Difference | `y[i] − y[i−1]`; the first point is NaN |
| Percent change | `100·(y[i] − y[i−1]) / abs(y[i−1])`; the first point is NaN |
| Log return | `ln(y[i] / y[i−1])`; all values must be positive |
| Cumulative sum | Running total |

#### Scale and baseline

| Operation | Parameters | Notes |
|-----------|-----------|-------|
| Normalize | Method | `min-max` → 0 to 1; `z-score` → mean 0, std 1; `first` → divide by the first value; `max` → divide by the largest absolute value |
| Scale and shift | a, b | `a·y + b` |
| Subtract baseline | Baseline | First value, last value, mean, median or minimum |
| Absolute value | — | |
| Remove trend (polynomial) | Degree | Subtracts a least-squares polynomial; degree 1 is a straight line |

#### Cleaning

| Operation | Parameters | Notes |
|-----------|-----------|-------|
| Remove NaN | — | Drops points where y or x is NaN/inf, from both series |
| Interpolate NaN | — | Fills gaps linearly using x (or the index); the ends hold the nearest valid value |
| Limit to a range | Lower, upper | Clips y; leave a limit on `auto` to leave it open |
| Sort by x | — | Reorders the points so x increases. Needs x |
| Outlier filter (Hampel) | Window, sigmas | Replaces a point by the local median when it is more than *sigmas* robust standard deviations away from it |

#### Rolling statistics

| Operation | Parameters | Notes |
|-----------|-----------|-------|
| Rolling std deviation | Window | Centered; the ends use the points that exist |
| Rolling minimum / maximum | Window | Same |
| Running minimum / maximum | — | Cumulative: the smallest or largest value so far |

#### Signal analysis

| Operation | Parameters | Notes |
|-----------|-----------|-------|
| FFT amplitude spectrum | Remove mean | Single-sided amplitude. x gives the sampling interval, so it should be evenly spaced; y must have no NaN. Output: frequency and amplitude |
| Find peaks | Min height, min prominence, min distance | Local maxima. Output: only the peak points. An error is shown if there are none |

!!! tip "Recipes"
    - **Remove spikes, then smooth:** *Outlier filter (Hampel)*, then *Savitzky-Golay* on the result.
    - **Find the dominant frequency:** *Remove trend*, then *FFT amplitude spectrum*, and plot the spectrum.
    - **Uneven sampling:** *Resample (uniform x)* before a Butterworth filter or an FFT.
    - **Compare two series with different x:** *Align to another x* puts one on the x of the other.

---

## Statistics

The Statistics page summarises the loaded series. It works on the series **selected in the Datasets list**, or on all of them when none is selected. It refreshes when you open the page; click **↻ Refresh** after changing the selection or the data.

### Summary table

One column per series and one row per statistic:

| Statistic | Meaning |
|-----------|---------|
| count | Valid values (NaN and infinity are not counted) |
| missing | NaN, infinity or empty values |
| mean, std | Mean and sample standard deviation (n − 1) |
| min, 25%, median, 75%, max | Range and quartiles |
| skew, kurtosis | Skewness and excess kurtosis (a normal distribution has 0 for both) |

Text series only get *count* and *missing*. For **date** series the mean, minimum, quartiles, median and maximum are shown as dates, and the standard deviation is in days. Cells that cannot be computed (the std of one value, the skew of a constant series) are left blank.

**📋 Copy summary** copies the table to the clipboard, tab-separated, ready to paste into a spreadsheet.

### Correlation matrix

Below the summary, the correlation between every pair of numeric series, with cells shaded red for positive and blue for negative values. Choose the **Method**:

- **pearson** — linear correlation.
- **spearman** — rank correlation; detects any monotonic relationship, linear or not, and is less sensitive to outliers.

Each pair uses only the points where both series are valid. A cell is blank when the two series have different lengths, one of them is constant, or there are fewer than 3 common points.
