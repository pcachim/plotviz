"""Descriptive statistics and correlation (data/descriptive.py): pure numpy/scipy, no Qt."""
import unittest

import numpy as np

import _bootstrap  # noqa: F401
from data import descriptive as ds


class TestDescribe(unittest.TestCase):
    def test_basic_numbers(self):
        d = ds.describe([1, 2, 3, 4, 5])
        self.assertEqual((d['count'], d['missing']), (5, 0))
        self.assertEqual((d['mean'], d['median'], d['min'], d['max']), (3, 3, 1, 5))
        self.assertAlmostEqual(d['std'], np.std([1, 2, 3, 4, 5], ddof=1))
        self.assertEqual((d['25%'], d['75%']), (2, 4))
        self.assertAlmostEqual(d['skew'], 0)

    def test_nan_and_inf_count_as_missing(self):
        d = ds.describe([1, np.nan, 3, np.inf])
        self.assertEqual((d['count'], d['missing']), (2, 2))
        self.assertEqual(d['mean'], 2)

    def test_degenerate_series(self):
        self.assertIsNone(ds.describe([np.nan])['mean'])
        one = ds.describe([4.0])
        self.assertEqual(one['mean'], 4.0)
        self.assertIsNone(one['std'])
        self.assertIsNone(ds.describe([2, 2, 2])['skew'])        # constant: undefined

    def test_text_series_only_counts(self):
        d = ds.describe(np.array(['a', 'b', 'a', None], dtype=object))
        self.assertEqual((d['count'], d['missing'], d['unique']), (3, 1, 2))
        self.assertIsNone(d['mean'])

    def test_numeric_strings_are_numbers(self):
        self.assertEqual(ds.describe(np.array(['1', '3'], dtype=object))['mean'], 2)

    def test_describe_all_keeps_order_and_skips_unknown(self):
        out = ds.describe_all({'a': [1], 'b': [2]}, ['b', 'zzz', 'a'])
        self.assertEqual(list(out), ['b', 'a'])


class TestCorrelation(unittest.TestCase):
    def test_pearson_perfect_and_inverse(self):
        data = {'x': [1, 2, 3, 4], 'y': [2, 4, 6, 8], 'z': [4, 3, 2, 1]}
        used, m = ds.correlation_matrix(data, ['x', 'y', 'z'])
        self.assertEqual(used, ['x', 'y', 'z'])
        np.testing.assert_allclose(np.diag(m), 1)
        self.assertAlmostEqual(m[0, 1], 1)
        self.assertAlmostEqual(m[0, 2], -1)
        np.testing.assert_allclose(m, m.T)

    def test_spearman_sees_monotonic_nonlinear(self):
        x = np.arange(1, 11.0)
        data = {'x': x, 'y': np.exp(x)}
        _, p = ds.correlation_matrix(data, ['x', 'y'], 'pearson')
        _, s = ds.correlation_matrix(data, ['x', 'y'], 'spearman')
        self.assertLess(p[0, 1], 0.99)
        self.assertAlmostEqual(s[0, 1], 1)

    def test_pairs_use_common_finite_points(self):
        data = {'a': [1, 2, 3, 4, np.nan], 'b': [2, 4, 6, 8, 100]}
        _, m = ds.correlation_matrix(data, ['a', 'b'])
        self.assertAlmostEqual(m[0, 1], 1)

    def test_unusable_pairs_are_nan_and_text_is_dropped(self):
        data = {'a': [1, 2, 3], 'b': [1, 2], 'c': [5, 5, 5], 't': np.array(['u', 'v', 'w'], dtype=object)}
        used, m = ds.correlation_matrix(data, ['a', 'b', 'c', 't'])
        self.assertEqual(used, ['a', 'b', 'c'])
        self.assertTrue(np.isnan(m[0, 1]))                       # different lengths
        self.assertTrue(np.isnan(m[0, 2]))                       # constant series

    def test_unknown_method(self):
        with self.assertRaises(ValueError):
            ds.correlation_matrix({'a': [1, 2, 3]}, ['a'], 'kendall')


if __name__ == '__main__':
    unittest.main()
