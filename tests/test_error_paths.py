"""Failure paths of code that used to swallow every Exception.

The handlers were narrowed to the errors each operation can really raise. These
tests pin both halves: expected data problems still degrade gracefully, and a
programming error (here an AttributeError) is no longer silently turned into an
empty result.
"""
import unittest
from unittest import mock

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

import _bootstrap  # noqa: F401
from data.scientific import CurveFitter
from styling.presets import ChartPresets

NO_FIT = (None, None, None, '', None)
X = np.linspace(0, 10, 20)


class TestCurveFitterFailures(unittest.TestCase):
    def test_good_fit(self):
        popt, pcov, func, eq, r2 = CurveFitter.fit(X, 2 * X + 1, 'Linear')
        self.assertAlmostEqual(float(popt[0]), 2.0, places=6)
        self.assertAlmostEqual(r2, 1.0, places=9)

    def test_unknown_model(self):
        self.assertEqual(CurveFitter.fit(X, X, 'NoSuchModel'), NO_FIT)

    def test_length_mismatch_is_reported_not_raised(self):
        self.assertEqual(CurveFitter.fit(X, X[:-3], 'Linear'), NO_FIT)

    def test_nan_data_is_reported_not_raised(self):
        y = X.copy()
        y[3] = np.nan
        self.assertEqual(CurveFitter.fit(X, y, 'Linear'), NO_FIT)

    def test_non_numeric_data_is_reported_not_raised(self):
        self.assertEqual(CurveFitter.fit(['a', 'b', 'c'], [1, 2, 3], 'Linear'), NO_FIT)

    def test_programming_errors_are_not_swallowed(self):
        def buggy_model(x, a, b):
            raise AttributeError("bug")
        broken = dict(CurveFitter.MODELS)
        broken['Linear'] = buggy_model
        with mock.patch.object(CurveFitter, 'MODELS', broken):
            with self.assertRaises(AttributeError):
                CurveFitter.fit(X, X, 'Linear')


class TestChartPresets(unittest.TestCase):
    def test_unknown_preset(self):
        self.assertFalse(ChartPresets.apply('NoSuchPreset'))

    def test_known_presets_apply_and_skip_bad_keys(self):
        for name in ChartPresets.PRESETS:
            with matplotlib.rc_context():
                self.assertTrue(ChartPresets.apply(name), name)

    def test_bad_rc_key_is_skipped_with_a_warning(self):
        with matplotlib.rc_context(), \
                mock.patch.dict(ChartPresets.PRESETS, {'bad': {'not.a.real.key': 1}}):
            self.assertTrue(ChartPresets.apply('bad'))

    def test_programming_errors_are_not_swallowed(self):
        class Boom:
            def __setitem__(self, k, v):
                raise AttributeError("bug")
        with mock.patch.object(plt, 'rcParams', Boom()), \
                mock.patch.dict(ChartPresets.PRESETS, {'one': {'font.size': 9}}):
            with self.assertRaises(AttributeError):
                ChartPresets.apply('one')


if __name__ == "__main__":
    unittest.main()
