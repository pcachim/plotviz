# Tests

Regression tests for the pure (non-Qt) logic in plotviz — currently the
standalone-script generator (`ui/python_export.py`), which powers the
**Export Python Bundle** and **Code Runner from chart** features.

## Running

No Qt or display required. The tests load the generator module directly by
file path and stub the few PyQt6 names it imports (see `_bootstrap.py`).

```bash
# with pytest (preferred, used in CI)
pytest

# or with the stdlib runner (no extra dependencies)
cd tests && python -m unittest discover -p "test_*.py"
```

Only `matplotlib`, `numpy` and `pandas` are needed to run the smoke tests
(they execute the generated `plot.py` in a subprocess with the Agg backend).

## Layout

- `_bootstrap.py` — sys.path + PyQt6 stub + file-path module loader.
- `test_helpers.py` — `_esc`, `_col_ref`, `_projection_for`.
- `test_annotations.py` — annotation code emission (text / arrow / image).
- `test_script_gen.py` — decoration emission + end-to-end smoke run of the
  generated script for single and multi-subplot charts.

## Adding tests

Load the module under test via the bootstrap loader to avoid importing the Qt
main window:

```python
import _bootstrap          # noqa: F401
pe = _bootstrap.python_export()
```
