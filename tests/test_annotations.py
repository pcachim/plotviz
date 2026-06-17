"""Tests for annotation code emitted into the standalone script."""
import unittest

import _bootstrap  # noqa: F401

pe = _bootstrap.script_gen()


def _text(idx=0, label="note", **style):
    return {"type": "text", "axes_index": idx, "x": 1.0, "y": 2.0,
            "label": label, "style": style}


def _arrow(idx=0, label="a", **style):
    return {"type": "arrow", "axes_index": idx, "x0": 0, "y0": 0,
            "x1": 1, "y1": 1, "label": label, "style": style}


def _image(idx=0):
    return {"type": "image", "axes_index": idx, "x": 0.5, "y": 0.5,
            "image_file": "images/logo.png", "zoom": 0.2, "style": {}}


class TestAnnotationGen(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(pe._gen_annotations({"annotations": []}, 1), [])

    def test_compiles_all_types(self):
        s = {"annotations": [_text(), _arrow(), _image()],
             "subplot_ann_visible": {"0": True}}
        code = "\n".join(pe._gen_annotations(s, 1))
        compile(code, "<ann>", "exec")  # must be valid Python
        self.assertEqual(code.count(".annotate("), 2)
        self.assertIn("AnnotationBbox", code)

    def test_image_imports_emitted_only_when_needed(self):
        no_img = "\n".join(pe._gen_annotations({"annotations": [_text()]}, 1))
        self.assertNotIn("AnnotationBbox", no_img)
        with_img = "\n".join(pe._gen_annotations({"annotations": [_image()]}, 1))
        self.assertIn("import matplotlib.image", with_img)

    def test_label_escaping(self):
        s = {"annotations": [_text(label="it's \\ here")]}
        code = "\n".join(pe._gen_annotations(s, 1))
        compile(code, "<ann>", "exec")

    def test_visibility_toggle_skips(self):
        s = {"annotations": [_text()], "subplot_ann_visible": {"0": False}}
        code = "\n".join(pe._gen_annotations(s, 1))
        self.assertNotIn(".annotate(", code)

    def test_single_subplot_ignores_other_axes(self):
        s = {"annotations": [_text(idx=3)]}
        code = "\n".join(pe._gen_annotations(s, 1))
        self.assertNotIn(".annotate(", code)

    def test_multi_subplot_uses_axis_var(self):
        s = {"annotations": [_text(idx=1)], "subplot_ann_visible": {"1": True}}
        code = "\n".join(pe._gen_annotations(s, 4))
        self.assertIn("ax1.annotate(", code)

    def test_arrow_emits_label_font_and_arrowprops(self):
        s = {"annotations": [_arrow(label="here", fontsize=14,
                                    fontfamily="Serif", fontcolor="#112233")]}
        code = "\n".join(pe._gen_annotations(s, 1))
        compile(code, "<ann>", "exec")
        self.assertIn("'here'", code)            # label text
        self.assertIn("fontsize=14", code)
        self.assertIn("fontfamily='Serif'", code)
        self.assertIn("color='#112233'", code)   # text + arrow share the colour
        self.assertIn("arrowprops=", code)

    def test_arrow_label_background(self):
        # bg_alpha == 0 -> no box; > 0 -> styled bbox dict
        plain = "\n".join(pe._gen_annotations({"annotations": [_arrow()]}, 1))
        self.assertIn("bbox=None", plain)
        boxed = "\n".join(pe._gen_annotations(
            {"annotations": [_arrow(bg_alpha=0.8, bg_color="#fff0aa")]}, 1))
        self.assertIn("facecolor='#fff0aa'", boxed)
        self.assertIn("boxstyle='round,pad=0.3'", boxed)


if __name__ == "__main__":
    unittest.main()
