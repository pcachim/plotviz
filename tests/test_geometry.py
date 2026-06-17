"""Tests for the pure figure-size unit conversions in core.geometry."""
import unittest

import _bootstrap  # noqa: F401

geo = _bootstrap.load_module("core/geometry.py", "core.geometry")


class TestToInches(unittest.TestCase):
    def test_inches_identity(self):
        self.assertEqual(geo.to_inches(5, "inches"), 5)

    def test_cm(self):
        self.assertAlmostEqual(geo.to_inches(2.54, "cm"), 1.0)

    def test_pixels(self):
        self.assertAlmostEqual(geo.to_inches(300, "pixels", dpi=300), 1.0)

    def test_unknown_unit_treated_as_inches(self):
        self.assertEqual(geo.to_inches(7, "furlong"), 7)


class TestFromInches(unittest.TestCase):
    def test_cm(self):
        self.assertAlmostEqual(geo.from_inches(1.0, "cm"), 2.54)

    def test_pixels(self):
        self.assertAlmostEqual(geo.from_inches(2.0, "pixels", dpi=150), 300)


class TestRoundTrip(unittest.TestCase):
    def test_roundtrip_each_unit(self):
        for unit in geo.UNITS:
            for val in (1.0, 12.5, 300):
                back = geo.from_inches(geo.to_inches(val, unit, 200), unit, 200)
                self.assertAlmostEqual(back, val, msg=f"{val} {unit}")

    def test_convert_cm_to_pixels(self):
        # 2.54 cm = 1 inch = dpi pixels
        self.assertAlmostEqual(geo.convert(2.54, "cm", "pixels", dpi=120), 120)

    def test_convert_matches_old_preset_math(self):
        # Old code: pixels = w_cm / 2.54 * dpi
        self.assertAlmostEqual(geo.convert(10, "cm", "pixels", dpi=300),
                               10 / 2.54 * 300)


class TestPointSegmentDistance(unittest.TestCase):
    def test_endpoint(self):
        self.assertAlmostEqual(geo.point_segment_distance(0, 0, 0, 0, 10, 0), 0)

    def test_on_segment(self):
        self.assertAlmostEqual(geo.point_segment_distance(5, 0, 0, 0, 10, 0), 0)

    def test_perpendicular(self):
        self.assertAlmostEqual(geo.point_segment_distance(5, 3, 0, 0, 10, 0), 3)

    def test_beyond_endpoint_clamps(self):
        # point past the B end projects onto B, not the infinite line
        self.assertAlmostEqual(geo.point_segment_distance(13, 0, 0, 0, 10, 0), 3)

    def test_degenerate_segment(self):
        self.assertAlmostEqual(geo.point_segment_distance(3, 4, 1, 1, 1, 1),
                               ((3 - 1) ** 2 + (4 - 1) ** 2) ** 0.5)

    def test_diagonal_midpoint(self):
        # midpoint of the segment lies on it → distance 0
        self.assertAlmostEqual(geo.point_segment_distance(5, 5, 0, 0, 10, 10), 0)


if __name__ == "__main__":
    unittest.main()
