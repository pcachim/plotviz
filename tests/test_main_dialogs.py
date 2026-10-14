"""Which file dialogs the app uses (see main._use_native_file_dialogs).

Runs only where a real PyQt6 is installed; skipped otherwise.
"""
import os
import sys
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
class TestNativeFileDialogChoice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import main
        cls.choose = staticmethod(main._use_native_file_dialogs)

    def test_macos_uses_qt_dialogs_by_default(self):
        self.assertFalse(self.choose("darwin", {}))

    def test_macos_can_be_forced_back_to_native(self):
        self.assertTrue(self.choose("darwin", {"PLOTVIZ_NATIVE_DIALOGS": "1"}))
        self.assertFalse(self.choose("darwin", {"PLOTVIZ_NATIVE_DIALOGS": "0"}))

    def test_other_platforms_keep_native_dialogs(self):
        self.assertTrue(self.choose("win32", {}))
        self.assertTrue(self.choose("linux", {}))


if __name__ == "__main__":
    unittest.main()
