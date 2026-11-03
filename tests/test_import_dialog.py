"""CSV import dialog: decimal separator and text encoding.

Runs only where a real PyQt6 is installed; skipped otherwise.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "src", "plotviz")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _have_real_qt():
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:  # noqa: BLE001 - any import failure means "no usable Qt"
        return False
    return hasattr(QApplication, "instance")


@unittest.skipUnless(_have_real_qt(), "real PyQt6 not available")
class TestImportDialogOptions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance() or QApplication([])

    def _dialog(self, text, encoding):
        from ui.dialogs import DataImportDialog
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        self.addCleanup(os.remove, path)
        with open(path, "w", encoding=encoding, newline="") as f:
            f.write(text)
        return DataImportDialog(path)

    def test_european_csv_needs_the_decimal_comma(self):
        d = self._dialog("a;b\n1,5;2,5\n3,5;4,5\n", "utf-8")
        d._sep_combo.setCurrentIndex(2)                        # semicolon
        self.assertEqual(d.get_selected_data()["a"].dtype, object)   # "1,5" stays text
        d._dec_combo.setCurrentIndex(1)                        # comma
        data = d.get_selected_data()
        self.assertEqual(list(data["a"]), [1.5, 3.5])
        self.assertEqual(list(data["b"]), [2.5, 4.5])

    def test_latin1_accents_need_the_right_encoding(self):
        d = self._dialog("temperatura,pressão\n1,2\n3,4\n", "latin-1")
        self.assertNotIn("pressão", d.get_selected_data())     # utf-8-sig cannot decode it
        d._enc_combo.setCurrentText("latin-1")
        self.assertIn("pressão", d.get_selected_data())

    def test_utf8_bom_is_dropped_by_default(self):
        d = self._dialog("x,y\n1,2\n", "utf-8-sig")
        self.assertIn("x", d.get_selected_data())             # not "﻿x"


if __name__ == "__main__":
    unittest.main()
