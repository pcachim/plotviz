# plotviz

**plotviz** is a desktop chart editor for scientists, engineers, and analysts. Load tabular data, build publication-quality charts through a point-and-click interface, and export to PNG, SVG, PDF, or JPEG — no code required.

---

## Features

- **22 chart types** — line, scatter, bar, area, histogram, box, violin, heatmap, waterfall, bubble, and more, with per-series mixing in multi-panel layouts
- **Seaborn Explorer** — dedicated dialog for statistical charts (KDE, regression, pairplot, joint, catplot, and more), fully isolated from the main canvas
- **Python Code Runner** — write and run arbitrary matplotlib/seaborn code in a built-in editor with a live preview pane
- **Python Export Bundle** — export any chart as a self-contained `.pvizx` ZIP with a standalone `plot.py` script and data CSVs; no plotviz dependency required to re-run
- **Subplots & mosaic layouts** — multi-panel figures with shared axes and custom grid arrangements
- **Curve fitting** — per-series polynomial, exponential, and custom fits via scipy
- **Annotations** — text, arrows, images, legends, and subplot titles
- **Custom color palettes** — built-in schemes plus user-defined palettes
- **Cross-platform** — macOS 11+, Windows 10+, and Linux (X11/Wayland)

---

## Quick start

```bash
# from PyPI
pip install plotviz

# from source (recommended for development)
git clone https://github.com/yourorg/plotviz.git
cd plotviz
uv sync
uv run plotviz
```

See [Getting Started](getting-started.md) for full installation and interface details.

---

## Documentation

Full documentation is available at **https://yourorg.github.io/plotviz/**

| Document | Contents |
|----------|----------|
| [Getting Started](getting-started.md) | Installation, first chart, interface overview |
| [Data](data.md) | Loading files, the series table, column types |
| [Chart Types](chart-types.md) | All 22 chart types and their options |
| [Style & Appearance](style.md) | Colors, fonts, grid, figure size, color schemes |
| [Axes](axes.md) | Labels, limits, scales, ticks, formatters |
| [Annotations](annotations.md) | Subplot titles, legends, text, arrows, images |
| [Series](series.md) | Per-curve style, markers, curve fitting |
| [Subplots](subplots.md) | Multi-panel layouts, mosaic, shared axes |
| [Advanced](advanced.md) | Function generator, manual data entry table |
| [Seaborn Explorer](seaborn-explorer.md) | Statistical charts via seaborn |
| [Python Code Runner](code-runner.md) | Built-in Python editor with live preview |
| [Python Export Bundle](python-export.md) | Export charts as standalone Python projects |
| [File Formats](file-formats.md) | .pviz, .pvizt, .pvizc, .pvizp, .pvizx |
| [Color Palettes](palettes.md) | Built-in palettes, custom palettes |
| [Keyboard Shortcuts](shortcuts.md) | All keyboard shortcuts |
| [Building & Packaging](building.md) | macOS .app and Windows .exe |

---

## Requirements

- Python 3.10 or later
- macOS 11+, Windows 10+, or Linux (X11/Wayland)

Dependencies are installed automatically via pip:

| Package | Version | Purpose |
|---------|---------|---------|
| PyQt6 | ≥ 6.5 | UI framework |
| matplotlib | ≥ 3.7 | Chart rendering |
| seaborn | ≥ 0.13 | Statistical charts |
| numpy | ≥ 1.24 | Numerical arrays |
| pandas | ≥ 2.0 | Data loading |
| scipy | ≥ 1.10 | Curve fitting and statistics |
| statsmodels | ≥ 0.14 | Regression and LOWESS |
| openpyxl | ≥ 3.1 | Excel file support |
| platformdirs | ≥ 3.0 | Settings directory |

---

## License

MIT — see [LICENSE.md](LICENSE.md).

---

## Version

Current release: **2.5.10**
