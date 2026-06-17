"""Guardrail: the core/ package must stay free of Qt and ui/ dependencies.

If this fails, something pulled a UI dependency into the pure layer — the exact
coupling that #3 (separate pure logic from Qt) exists to prevent.
"""
import ast
import os
import subprocess
import sys
import unittest

import _bootstrap  # noqa: F401

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "src", "plotviz")
_CORE = os.path.join(_SRC, "core")


class TestCorePurity(unittest.TestCase):
    def test_importing_core_does_not_import_qt(self):
        # Fresh interpreter so nothing else has imported PyQt6 first.
        code = (
            "import sys; sys.path.insert(0, %r);"
            "import core.script_gen;"
            "assert 'PyQt6' not in sys.modules, 'core imported PyQt6';"
            "print('ok')" % _SRC
        )
        res = subprocess.run([sys.executable, "-c", code],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("ok", res.stdout)

    def test_core_sources_have_no_forbidden_imports(self):
        forbidden_roots = {"PyQt6", "ui"}
        for fname in os.listdir(_CORE):
            if not fname.endswith(".py"):
                continue
            tree = ast.parse(open(os.path.join(_CORE, fname), encoding="utf-8").read())
            modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules += [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    modules.append(node.module)
            for mod in modules:
                root = mod.split(".")[0]
                self.assertNotIn(root, forbidden_roots,
                                 f"{fname} imports forbidden module '{mod}'")


if __name__ == "__main__":
    unittest.main()
