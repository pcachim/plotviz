# plotviz

**plotviz** is a desktop chart editor for scientists, engineers and analysts. Load tabular data, build publication-quality charts through a point-and-click interface, and export to PNG, SVG, PDF, JPEG, TIFF or EPS — no code required.

---

## Highlights

- **26 chart types** — Line, Scatter, Bar, Histogram, Boxplot, Violin, Pie, Polar, Radar, Heatmap, Contour, 3D Surface, and more
- **Data tools** — load CSV, Excel, JSON or text files (dates included), generate series from expressions, summarise them with **Statistics**, and derive new ones with 36 **Transform** operations (smoothing, resampling, calculus, baselines, peaks, FFT), each with a live preview
- **Curve fitting** — linear, polynomial, exponential, power, logarithmic, sigmoid, Gaussian, sinusoid, your own expression, and LOWESS smoothing; fit only part of the data, weight by errors, ignore outliers, compare fits by R² and AIC, and draw confidence and prediction bands
- **Multi-panel layouts** — 18 preset layouts plus a custom mosaic editor; each subplot is independently configured
- **Full style control** — 13 built-in color schemes, 11 color palettes, per-curve style, grid, borders, fonts, and margins
- **Annotations** — text labels, arrows, and image overlays with a drag-and-drop editor
- **Export** — PNG, SVG, PDF, JPEG, TIFF or EPS at any DPI and figure size, or a standalone Python script of the chart
- **Undo and redo** — up to 50 steps, for data and settings alike
- **Tools** — a Seaborn Explorer for statistical charts and a Python Code Runner

---

## Installation

**Pre-built binaries (no Python required):**
[Download macOS DMG / Windows ZIP → GitHub Releases](https://github.com/pcachim/plotviz/releases/latest)

```bash
# from PyPI
pip install plotviz
```

Or run directly from source:

```bash
git clone https://github.com/pcachim/plotviz.git
cd plotviz
uv sync
uv run plotviz
```

See [Getting Started](getting-started.md) for full setup instructions.

---

## Quick navigation

<div class="grid cards" markdown>

- :material-rocket-launch: **[Getting Started](getting-started.md)**

    Install plotviz and create your first chart in minutes.

- :material-school: **[Worked Examples](examples.md)**

    Find pulses in a signal, compare fits, smooth a daily series.

- :material-table: **[Data](datasets.md)**

    Load files, generate series, summarise them and transform them.

- :material-chart-line: **[Plot and Chart Types](plot.md)**

    The series table and the reference for all 26 chart types.

- :material-chart-scatter-plot: **[Curves and Fitting](curves.md)**

    Per-curve style and curve fitting with confidence and prediction bands.

- :material-axis-arrow: **[Axes](axes.md)**

    Labels, limits, scales, ticks, formatters, secondary Y axis.

- :material-grid: **[Canvas & Grid](canvas-grid.md)**

    Plot area colour, borders and grid of each subplot.

- :material-text-box: **[Legend and Notes](legend-notes.md)**

    Legends, text, arrows, and images.

- :material-page-layout-body: **[Layout & Style](layout-style.md)**

    Figure size, margins, title position.

- :material-view-grid: **[Subplots](subplots.md)**

    Multi-panel layouts and mosaic editor.

- :material-palette: **[Color Schemes and Palettes](color-schemes.md)**

    Coordinated colour presets and the colour cycle of the curves.

- :material-file: **[File Formats](file-formats.md)**

    .pviz, .pvizt, .pvizc, .pvizp format reference.

- :material-export: **[Export Image](export.md)**

    Formats, resolution, clipboard, one file per subplot.

- :material-help-circle: **[Troubleshooting](troubleshooting.md)**

    The messages of the app and what to do.

- :material-menu: **[Menus](menus.md)**

    Every menu item, the samples and the preferences.

- :material-keyboard: **[Keyboard Shortcuts](shortcuts.md)**

    All keyboard shortcuts and canvas controls.

</div>

---

## File types

| Extension | Type | Description |
|-----------|------|-------------|
| `.pviz` | Chart project | Full chart with data, series, and all settings |
| `.pvizt` | Template | Style and layout settings only — no data |
| `.pvizc` | Color scheme | Coordinated color preset |
| `.pvizp` | Palette bundle | Shareable custom color palettes |

---

## Version

The latest release is on the [Releases page](https://github.com/pcachim/plotviz/releases/latest); **Help → About plotviz** shows the version you are running.  
Requires Python **3.10+**
