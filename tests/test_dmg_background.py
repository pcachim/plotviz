"""The background of the disk image is a fixed picture, not something the build draws."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestDmgBackground(unittest.TestCase):
    def test_the_two_pictures_exist_with_the_sizes_the_window_needs(self):
        from PIL import Image
        with Image.open(ROOT / "assets" / "background.png") as one, Image.open(ROOT / "assets" / "background@2x.png") as two:
            self.assertEqual(one.size, (600, 400))
            self.assertEqual(two.size, (1200, 800))

    def test_the_build_script_uses_them_and_does_not_draw_a_new_one(self):
        script = (ROOT / "create_pkg.sh").read_text(encoding="utf-8")
        self.assertNotIn("ImageDraw", script)
        self.assertNotIn("img.save", script)
        self.assertIn("background@2x.png", script)
        self.assertIn('--background "$BACKGROUND"', script)
        self.assertIn("--window-size 600 400", script)

    def test_the_icons_are_where_the_arrow_expects_them(self):
        script = (ROOT / "create_pkg.sh").read_text(encoding="utf-8")
        self.assertIn('--icon "$APP_NAME.app" 150 200', script)
        self.assertIn("--app-drop-link 450 200", script)


if __name__ == "__main__":
    unittest.main()
