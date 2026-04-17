# plotviz

[![Latest Release](https://img.shields.io/github/v/release/pcachim/plotviz?label=download&style=flat-square)](https://github.com/pcachim/plotviz/releases/latest)

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

**Download the latest release** (no Python required):
[macOS DMG / Windows ZIP → GitHub Releases](https://github.com/pcachim/plotviz/releases/latest)

See [Getting Started](docs/getting-started.md) for full installation and interface details.

---

## Documentation

Full documentation is available at **https://pcachim.github.io/plotviz/**

| Document | Contents |
|----------|----------|
| [Getting Started](docs/getting-started.md) | Installation, first chart, interface overview |
| [Data](docs/data.md) | Loading files, the series table, column types |
| [Chart Types](docs/chart-types.md) | All 22 chart types and their options |
| [Style & Appearance](docs/style.md) | Colors, fonts, grid, figure size, color schemes |
| [Axes](docs/axes.md) | Labels, limits, scales, ticks, formatters |
| [Annotations](docs/annotations.md) | Subplot titles, legends, text, arrows, images |
| [Series](docs/series.md) | Per-curve style, markers, curve fitting |
| [Subplots](docs/subplots.md) | Multi-panel layouts, mosaic, shared axes |
| [Advanced](docs/advanced.md) | Function generator, manual data entry table |
| [Seaborn Explorer](docs/seaborn-explorer.md) | Statistical charts via seaborn |
| [Python Code Runner](docs/code-runner.md) | Built-in Python editor with live preview |
| [Python Export Bundle](docs/python-export.md) | Export charts as standalone Python projects |
| [File Formats](docs/file-formats.md) | .pviz, .pvizt, .pvizc, .pvizp, .pvizx |
| [Color Palettes](docs/palettes.md) | Built-in palettes, custom palettes |
| [Keyboard Shortcuts](docs/shortcuts.md) | All keyboard shortcuts |
| [Building & Packaging](docs/building.md) | macOS .app and Windows .exe |

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

Current release: **2.7.2**
