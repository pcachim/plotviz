"""Round-trip tests for the pure project (de)serialization in core.serialize."""
import os
import tempfile
import unittest

import numpy as np

import _bootstrap  # noqa: F401

sz = _bootstrap.load_module("core/serialize.py", "core.serialize")


class TestDatasetEncoding(unittest.TestCase):
    def test_float_roundtrip(self):
        ds = {"x": np.array([1.0, 2.0, 3.0])}
        out = sz.decode_datasets(sz.encode_datasets(ds))
        self.assertEqual(out["x"].dtype.kind, "f")
        np.testing.assert_array_equal(out["x"], ds["x"])

    def test_object_roundtrip(self):
        ds = {"cat": np.array(["a", "b", "c"], dtype=object)}
        out = sz.decode_datasets(sz.encode_datasets(ds))
        self.assertEqual(list(out["cat"]), ["a", "b", "c"])

    def test_plain_list_input(self):
        out = sz.encode_datasets({"x": [1, 2, 3]})
        self.assertEqual(out["x"], {"dtype": "float", "values": [1, 2, 3]})

    def test_legacy_plain_list_decode(self):
        out = sz.decode_datasets({"x": [1, 2, 3]})  # old format: bare list
        np.testing.assert_array_equal(out["x"], np.array([1.0, 2.0, 3.0]))


class TestProjectRoundTrip(unittest.TestCase):
    def _bundle(self):
        settings = {
            "chart_type": "Line", "title_text": "T",
            "annotations": [
                {"type": "text", "axes_index": 0, "x": 1, "y": 2,
                 "label": "note", "style": {}},
            ],
        }
        series_meta = {"series": [{"x_col": "x", "y_col": "y", "plot_num": 1}],
                       "z_col": "(none)"}
        datasets = {"x": np.array([0.0, 1.0, 2.0]),
                    "y": np.array([0.0, 1.0, 4.0]),
                    "g": np.array(["a", "b", "c"], dtype=object)}
        return settings, series_meta, datasets

    def test_full_roundtrip_preserves_state(self):
        settings, series_meta, datasets = self._bundle()
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "p.pviz")
            sz.write_project_zip(fp, settings, series_meta,
                                 sz.encode_datasets(datasets))
            got = sz.read_project_zip(fp)
        self.assertEqual(got["settings"], settings)            # incl. annotations
        self.assertEqual(got["series_meta"], series_meta)
        decoded = sz.decode_datasets(got["datasets_raw"])
        self.assertEqual(set(decoded), {"x", "y", "g"})
        np.testing.assert_array_equal(decoded["x"], datasets["x"])
        self.assertEqual(list(decoded["g"]), ["a", "b", "c"])

    def test_annotations_survive_roundtrip(self):
        # Regression guard for the original bug: annotation metadata must persist.
        settings, series_meta, datasets = self._bundle()
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "p.pviz")
            sz.write_project_zip(fp, settings, series_meta,
                                 sz.encode_datasets(datasets))
            got = sz.read_project_zip(fp)
        self.assertEqual(got["settings"]["annotations"][0]["label"], "note")

    def test_palette_optional(self):
        settings, series_meta, datasets = self._bundle()
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "p.pviz")
            sz.write_project_zip(fp, settings, series_meta,
                                 sz.encode_datasets(datasets), palette_json="{}")
            got = sz.read_project_zip(fp)
        self.assertIsNone(got["palette_json"])  # "{}" is not written

    def test_image_embedding(self):
        settings, series_meta, datasets = self._bundle()
        with tempfile.TemporaryDirectory() as d:
            img = os.path.join(d, "logo.png")
            with open(img, "wb") as fh:
                fh.write(b"\x89PNG\r\n\x1a\nFAKE")
            fp = os.path.join(d, "p.pviz")
            sz.write_project_zip(fp, settings, series_meta,
                                 sz.encode_datasets(datasets), image_paths=[img])
            got = sz.read_project_zip(fp)
        self.assertIn("logo.png", got["images"])
        self.assertTrue(got["images"]["logo.png"].startswith(b"\x89PNG"))

    def test_missing_settings_raises(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "bad.pviz")
            with zipfile.ZipFile(fp, "w") as zf:
                zf.writestr("nope.txt", "x")
            with self.assertRaises(ValueError):
                sz.read_project_zip(fp)

    def test_legacy_series_in_settings(self):
        import zipfile
        import json
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "old.pviz")
            with zipfile.ZipFile(fp, "w") as zf:
                zf.writestr("settings.json", json.dumps(
                    {"chart_type": "Line", "series": [{"x_col": "x"}]}))
            got = sz.read_project_zip(fp)
        self.assertEqual(got["series_meta"]["series"], [{"x_col": "x"}])


if __name__ == "__main__":
    unittest.main()
