"""Series transforms (data/transforms.py): pure numpy, no Qt."""
import unittest

import numpy as np

import _bootstrap  # noqa: F401
from data import transforms as tf


class TestSmoothing(unittest.TestCase):
    def test_moving_average_centered_partial_ends(self):
        _, y = tf.moving_average(None, [1, 2, 3, 4, 5], window=3)
        np.testing.assert_allclose(y, [1.5, 2, 3, 4, 4.5])

    def test_moving_average_trailing_nan_and_trim(self):
        x = [0, 1, 2, 3, 4]
        _, y = tf.moving_average(None, [1, 2, 3, 4, 5], window=3, align='trailing', edges='nan')
        self.assertTrue(np.isnan(y[:2]).all())
        np.testing.assert_allclose(y[2:], [2, 3, 4])
        xo, yo = tf.moving_average(x, [1, 2, 3, 4, 5], window=3, edges='trim')
        np.testing.assert_allclose(xo, [1, 2, 3])
        np.testing.assert_allclose(yo, [2, 3, 4])

    def test_window_longer_than_series_is_an_error(self):
        with self.assertRaises(ValueError):
            tf.moving_average(None, [1, 2], window=5)

    def test_median_kills_a_spike(self):
        _, y = tf.median_filter(None, [1, 1, 100, 1, 1], window=3)
        self.assertEqual(y[2], 1)

    def test_exponential_smooth_first_point_and_recurrence(self):
        _, y = tf.exponential_smooth(None, [10, 0, 0], alpha=0.5)
        np.testing.assert_allclose(y, [10, 5, 2.5])

    def test_savgol_keeps_a_polynomial_exactly(self):
        x = np.linspace(0, 1, 30)
        _, y = tf.savitzky_golay(None, x ** 2, window=7, polyorder=2)
        np.testing.assert_allclose(y, x ** 2, atol=1e-12)
        with self.assertRaises(ValueError):
            tf.savitzky_golay(None, x, window=3, polyorder=3)


class TestReduction(unittest.TestCase):
    def test_every_n_with_offset_keeps_x_aligned(self):
        xo, yo = tf.every_n([0, 1, 2, 3, 4, 5, 6], [10, 11, 12, 13, 14, 15, 16], step=3, offset=1)
        np.testing.assert_allclose(xo, [1, 4])
        np.testing.assert_allclose(yo, [11, 14])

    def test_block_average_keeps_short_last_block(self):
        xo, yo = tf.block_average([0, 1, 2, 3, 4], [1, 3, 5, 7, 9], size=2)
        np.testing.assert_allclose(yo, [2, 6, 9])
        np.testing.assert_allclose(xo, [0.5, 2.5, 4])

    def test_resample_uniform_sorts_and_interpolates(self):
        xo, yo = tf.resample_uniform([2, 0, 1], [20, 0, 10], points=5)
        np.testing.assert_allclose(xo, [0, 0.5, 1, 1.5, 2])
        np.testing.assert_allclose(yo, [0, 5, 10, 15, 20])

    def test_resample_needs_x(self):
        with self.assertRaises(ValueError):
            tf.resample_uniform(None, [1, 2, 3])


class TestCalculusAndScaling(unittest.TestCase):
    def test_derivative_and_integral_are_inverse(self):
        x = np.linspace(0, 2, 201)
        _, d = tf.derivative(x, x ** 2)
        np.testing.assert_allclose(d[1:-1], 2 * x[1:-1], atol=1e-9)
        _, i = tf.cumulative_integral(x, 2 * x)
        np.testing.assert_allclose(i, x ** 2, atol=1e-9)

    def test_without_x_the_index_is_the_spacing(self):
        _, d = tf.derivative(None, [0, 2, 4, 6])
        np.testing.assert_allclose(d, 2)

    def test_difference_keeps_length(self):
        _, y = tf.difference(None, [1, 4, 9])
        self.assertTrue(np.isnan(y[0]))
        np.testing.assert_allclose(y[1:], [3, 5])

    def test_normalize_methods(self):
        _, y = tf.normalize(None, [2, 4, 6])
        np.testing.assert_allclose(y, [0, 0.5, 1])
        _, z = tf.normalize(None, [2, 4, 6], method='z-score')
        self.assertAlmostEqual(z.mean(), 0)
        self.assertAlmostEqual(z.std(), 1)
        _, f = tf.normalize(None, [2, 4], method='first')
        np.testing.assert_allclose(f, [1, 2])

    def test_scale_shift(self):
        _, y = tf.scale_shift(None, [1, 2], a=2, b=1)
        np.testing.assert_allclose(y, [3, 5])


class TestNewOperations(unittest.TestCase):
    def test_gaussian_smooths_noise(self):
        rng = np.random.default_rng(0)
        y = np.sin(np.linspace(0, 6, 300)) + 0.3 * rng.standard_normal(300)
        _, g = tf.gaussian_smooth(None, y, sigma=4)
        self.assertLess(np.std(np.diff(g)), np.std(np.diff(y)))

    def test_detrend_removes_a_line_and_a_parabola(self):
        x = np.linspace(0, 5, 50)
        _, r = tf.detrend(x, 3 * x + 2)
        np.testing.assert_allclose(r, 0, atol=1e-9)
        _, r = tf.detrend(x, x ** 2 - x, degree=2)
        np.testing.assert_allclose(r, 0, atol=1e-9)

    def test_remove_nan_trims_x_with_y(self):
        xo, yo = tf.remove_nan([0, 1, 2, 3], [1, np.nan, 3, 4])
        np.testing.assert_allclose(xo, [0, 2, 3])
        np.testing.assert_allclose(yo, [1, 3, 4])
        with self.assertRaises(ValueError):
            tf.remove_nan(None, [np.nan])

    def test_interpolate_nan_uses_x(self):
        _, y = tf.interpolate_nan([0, 1, 3], [0, np.nan, 6])
        np.testing.assert_allclose(y, [0, 2, 6])
        _, y = tf.interpolate_nan(None, [np.nan, 1, np.nan, 3])
        np.testing.assert_allclose(y, [1, 1, 2, 3])

    def test_crop_x_open_bounds(self):
        xo, yo = tf.crop_x([0, 1, 2, 3], [10, 11, 12, 13], xmin=1, xmax=2)
        np.testing.assert_allclose(xo, [1, 2])
        xo, _ = tf.crop_x([0, 1, 2, 3], [10, 11, 12, 13], xmin=2)
        np.testing.assert_allclose(xo, [2, 3])
        with self.assertRaises(ValueError):
            tf.crop_x([0, 1], [1, 2], xmin=5)

    def test_rolling_statistics(self):
        y = [1, 5, 2, 8, 3]
        _, mx = tf.rolling_max(None, y, window=3)
        np.testing.assert_allclose(mx, [5, 5, 8, 8, 8])
        _, mn = tf.rolling_min(None, y, window=3)
        np.testing.assert_allclose(mn, [1, 1, 2, 2, 3])
        _, sd = tf.rolling_std(None, [2, 2, 2, 2], window=3)
        np.testing.assert_allclose(sd, 0)

    def test_hampel_replaces_the_outlier_and_leaves_most_of_the_rest(self):
        rng = np.random.default_rng(1)
        y = np.sin(np.linspace(0, 6, 200)) + 0.1 * rng.standard_normal(200)
        bad = y.copy()
        bad[100] += 5
        _, out = tf.hampel(None, bad, window=7)
        self.assertLess(abs(out[100] - y[100]), 0.5)
        self.assertGreater(np.mean(out == bad), 0.85)

    def test_fft_finds_the_frequency_and_amplitude(self):
        t = np.arange(0, 10, 0.01)                       # 100 Hz sampling, 1000 points
        f, a = tf.fft_spectrum(t, 2.5 * np.sin(2 * np.pi * 5 * t))
        self.assertAlmostEqual(f[np.argmax(a)], 5.0)
        self.assertAlmostEqual(a.max(), 2.5, places=6)

    def test_peaks_with_and_without_x(self):
        y = [0, 3, 0, 1, 0, 5, 0]
        xo, yo = tf.peaks([10, 11, 12, 13, 14, 15, 16], y, min_height=2)
        np.testing.assert_allclose(xo, [11, 15])
        np.testing.assert_allclose(yo, [3, 5])
        xo, _ = tf.peaks(None, y)
        np.testing.assert_allclose(xo, [1, 3, 5])        # the index stands in for x
        with self.assertRaises(ValueError):
            tf.peaks(None, [1, 2, 3])


class TestMoreOperations(unittest.TestCase):
    def test_butterworth_lowpass_and_highpass_split_two_tones(self):
        t = np.arange(0, 10, 0.01)
        slow, fast = np.sin(2 * np.pi * 0.5 * t), np.sin(2 * np.pi * 20 * t)
        _, lo = tf.butterworth(t, slow + fast, 'lowpass', cutoff=3)
        _, hi = tf.butterworth(t, slow + fast, 'highpass', cutoff=3)
        self.assertLess(np.abs(lo[100:-100] - slow[100:-100]).max(), 0.05)
        self.assertLess(np.abs(hi[100:-100] - fast[100:-100]).max(), 0.05)
        with self.assertRaises(ValueError):
            tf.butterworth(t, slow, cutoff=60)            # above Nyquist (50)

    def test_decimate_length_and_x(self):
        t = np.arange(100.0)
        xo, yo = tf.decimate(t, np.sin(t / 20), factor=4)
        self.assertEqual(len(xo), 25)
        self.assertEqual(len(yo), 25)
        np.testing.assert_allclose(xo, t[::4])

    def test_align_to_x_interpolates_and_leaves_nan_outside(self):
        xo, yo = tf.align_to_x([0, 1, 2], [0, 10, 20], target_x=[-1, 0.5, 2, 3])
        np.testing.assert_allclose(xo, [-1, 0.5, 2, 3])
        self.assertTrue(np.isnan(yo[0]) and np.isnan(yo[3]))
        np.testing.assert_allclose(yo[1:3], [5, 20])
        _, p = tf.align_to_x([0, 1, 2, 3], [0, 1, 4, 9], target_x=[1.5], method='pchip')
        self.assertTrue(1 < p[0] < 4)
        with self.assertRaises(ValueError):
            tf.align_to_x([0, 1], [1, 2])

    def test_sort_by_x(self):
        xo, yo = tf.sort_by_x([2, 0, 1], [20, 0, 10])
        np.testing.assert_allclose(xo, [0, 1, 2])
        np.testing.assert_allclose(yo, [0, 10, 20])

    def test_second_derivative_of_a_parabola(self):
        x = np.linspace(0, 3, 61)
        _, d2 = tf.second_derivative(x, x ** 2)
        np.testing.assert_allclose(d2[2:-2], 2, atol=1e-6)

    def test_percent_change_and_log_return(self):
        _, p = tf.percent_change(None, [100, 110, 99])
        self.assertTrue(np.isnan(p[0]))
        np.testing.assert_allclose(p[1:], [10, -10])
        _, r = tf.log_return(None, [1, np.e, np.e ** 3])
        np.testing.assert_allclose(r[1:], [1, 2])
        with self.assertRaises(ValueError):
            tf.log_return(None, [1, -1])

    def test_subtract_baseline_and_absolute(self):
        _, y = tf.subtract_baseline(None, [5, 7, 9], 'first')
        np.testing.assert_allclose(y, [0, 2, 4])
        _, y = tf.subtract_baseline(None, [1, 2, 6], 'mean')
        self.assertAlmostEqual(y.mean(), 0)
        _, a = tf.absolute(None, [-1, 2, -3])
        np.testing.assert_allclose(a, [1, 2, 3])

    def test_clip_values(self):
        _, y = tf.clip_values(None, [-5, 0, 5], lower=-1, upper=1)
        np.testing.assert_allclose(y, [-1, 0, 1])
        _, y = tf.clip_values(None, [-5, 0, 5], upper=1)
        np.testing.assert_allclose(y, [-5, 0, 1])
        with self.assertRaises(ValueError):
            tf.clip_values(None, [1])

    def test_running_min_max(self):
        _, mx = tf.cumulative_max(None, [1, 3, 2, 5, 4])
        np.testing.assert_allclose(mx, [1, 3, 3, 5, 5])
        _, mn = tf.cumulative_min(None, [4, 5, 2, 3, 1])
        np.testing.assert_allclose(mn, [4, 4, 2, 2, 1])


class TestFixedReferences(unittest.TestCase):
    """Baseline, normalisation and trend can use a value or a stretch of x that the user chooses."""

    X = np.arange(10.0)
    Y = np.array([5, 5, 5, 5, 9, 5, 5, 5, 5, 5], dtype=float)         # a pulse on a baseline of 5

    def test_baseline_from_a_value(self):
        _, y = tf.subtract_baseline(self.X, self.Y, 'value', value=4.5)
        np.testing.assert_allclose(y[:2], [0.5, 0.5])

    def test_baseline_from_a_range_ignores_the_pulse(self):
        for method in ('mean of range', 'median of range'):
            _, y = tf.subtract_baseline(self.X, self.Y, method, x_from=0, x_to=2)
            self.assertEqual((y[0], y[4]), (0.0, 4.0), method)
        _, y = tf.subtract_baseline(self.X, self.Y, 'mean')            # the global mean is pulled up
        self.assertGreater(y[0], -1)
        self.assertNotEqual(y[0], 0.0)

    def test_range_open_ends_and_index_as_x(self):
        _, y = tf.subtract_baseline(None, self.Y, 'median of range', x_to=3)        # index positions
        self.assertEqual(y[0], 0.0)
        _, y = tf.subtract_baseline(self.X, self.Y, 'mean of range', x_from=5)
        self.assertEqual(y[0], 0.0)

    def test_empty_range_is_an_error(self):
        with self.assertRaises(ValueError):
            tf.subtract_baseline(self.X, self.Y, 'mean of range', x_from=50, x_to=60)

    def test_normalize_by_a_value_or_a_range(self):
        _, y = tf.normalize(self.X, self.Y, 'value', value=5.0)
        self.assertEqual((y[0], y[4]), (1.0, 1.8))
        _, y = tf.normalize(self.X, self.Y, 'mean of range', x_from=0, x_to=3)
        self.assertEqual((y[0], y[4]), (1.0, 1.8))
        with self.assertRaises(ValueError):
            tf.normalize(self.X, self.Y, 'value', value=0)

    def test_detrend_fits_only_the_chosen_stretch(self):
        x = np.arange(100.0)
        y = 0.5 * x + 3
        y[40:44] += 20                                        # a pulse that would tilt a global fit
        _, whole = tf.detrend(x, y, 1)
        _, quiet = tf.detrend(x, y, 1, x_from=0, x_to=30)
        self.assertGreater(np.abs(whole[:30]).max(), 0.5)
        np.testing.assert_allclose(quiet[:30], 0, atol=1e-9)
        np.testing.assert_allclose(quiet[40:44], 20, atol=1e-9)


class TestNoiseThresholdAndSteps(unittest.TestCase):
    def test_noise_sigma_matches_the_std_and_ignores_pulses(self):
        rng = np.random.default_rng(3)
        y = rng.normal(0, 0.1, 5000)
        self.assertAlmostEqual(tf.noise_sigma(y), 0.1, delta=0.01)
        y[100:104] += 5
        self.assertAlmostEqual(tf.noise_sigma(y), 0.1, delta=0.01)       # an std would be 0.14+

    def test_peaks_by_noise_threshold(self):
        rng = np.random.default_rng(11)
        y = 2.5 + 0.02 * rng.standard_normal(1000)
        y[300:304] += [0.10, 0.25, 0.25, 0.12]
        y[720:723] += [0.12, 0.20, 0.10]
        x = np.arange(1000) / 1000.0
        px, _ = tf.peaks(x, y, min_distance=4, min_height_noise=6)
        np.testing.assert_allclose(px, [0.301, 0.721], atol=0.003)
        with self.assertRaisesRegex(ValueError, 'above'):
            tf.peaks(x, y, min_height_noise=1000)
        # with both limits, the higher one applies
        px, _ = tf.peaks(x, y, min_distance=4, min_height_noise=6, min_height=2.7)
        np.testing.assert_allclose(px, [0.301], atol=0.003)

    def test_integral_starts_where_asked(self):
        x = np.linspace(0, 2, 201)
        _, i = tf.cumulative_integral(x, np.ones_like(x), start=3.0)
        self.assertEqual(i[0], 3.0)
        self.assertAlmostEqual(i[-1], 5.0)

    def test_resample_by_step(self):
        x = np.array([0.0, 0.4, 1.0, 2.0])
        gx, gy = tf.resample_uniform(x, x * 10, step=0.5)
        np.testing.assert_allclose(gx, [0, 0.5, 1.0, 1.5, 2.0])
        np.testing.assert_allclose(gy, [0, 5, 10, 15, 20])
        gx, _ = tf.resample_uniform(x, x, points=3, step=1.0)            # the step wins
        self.assertEqual(len(gx), 3)
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                tf.resample_uniform(x, x, step=bad)
        with self.assertRaises(ValueError):
            tf.resample_uniform(x, x, step=1e-9)                         # absurdly many points


class TestRegistry(unittest.TestCase):
    def test_groups_are_contiguous_and_every_operation_has_one(self):
        seen, last = [], None
        for op in tf.OPERATIONS:
            if op['group'] != last:
                self.assertNotIn(op['group'], seen, f"group {op['group']} is split")
                seen.append(op['group'])
                last = op['group']
        self.assertGreaterEqual(len(seen), 5)

    def test_every_operation_runs_with_its_defaults(self):
        x = np.linspace(0, 10, 50)
        y = np.sin(x) + 2                              # positive: log return needs it
        required = {'clip_values': {'lower': 1.0}}     # no default limit to run with
        for op in tf.OPERATIONS:
            params = {p[0]: (x if p[2] == 'series' else p[3]) for p in op['params']}
            params.update(required.get(op['key'], {}))
            with self.subTest(op=op['key']):
                xo, yo = tf.apply_operation(op['key'], x, y, **params)
                self.assertEqual(len(xo), len(yo))
                self.assertTrue(tf.default_suffix(op['key'], params))

    def test_suffix_uses_parameters(self):
        self.assertEqual(tf.default_suffix('moving_average', {'window': 7}), 'MA7')


if __name__ == '__main__':
    unittest.main()
