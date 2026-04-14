# plotviz

**plotviz** is a desktop chart editor for scientists, engineers and analysts. Load tabular data, build publication-quality charts through a point-and-click interface, and export to PNG, SVG, PDF or JPEG — no code required.

---

## Highlights

- **22 chart types** — Line, Scatter, Bar, Histogram, Boxplot, Violin, Pie, Polar, Radar, Heatmap, Contour, 3D Surface, and more
- **Curve fitting** — 7 built-in models (Linear, Quadratic, Cubic, Exponential, Power Law, Logarithmic, Sigmoid) with confidence and prediction bands
- **Multi-panel layouts** — 18 preset mosaic layouts plus a custom mosaic editor; each subplot is independently configured
- **Full style control** — 10 built-in color schemes, 11 color palettes, per-curve style, grid, borders, fonts, and margins
- **Annotations** — text labels, arrows, and image overlays with a drag-and-drop editor
- **Export** — PNG, SVG, PDF, JPEG at any DPI and figure size

---

## Installation

```bash
pip install plotviz
```

Or run directly from source:

```bash
git clone https://github.com/yourorg/plotviz.git
cd plotviz
uv sync
uv run plotviz
```

See [Getting Started](getting-started.md) for full setup instructions.

---

## Quick navigation

<div class="grid cards" markdown>

- **[Getting Started](getting-started.md)**

    Install plotviz and create your first chart in minutes.

- **[Loading Data](data.md)**

    Load CSV, Excel, JSON or TXT files and build the series table.

- **[Chart Types](chart-types.md)**

    Reference for all 22 chart types and their options.

- **[Style & Appearance](style.md)**

    Colors, themes, grid, figure size, and color schemes.

- **[Axes](axes.md)**

    Labels, limits, scales, ticks, formatters, secondary Y axis.

- **[Annotations](annotations.md)**

    Subplot titles, legends, text, arrows, and images.

- **[Series & Curve Fitting](series.md)**

    Per-curve style and 7 curve-fit models.

- **[Subplots](subplots.md)**

    Multi-panel layouts and mosaic editor.

- **[Advanced Tools](advanced.md)**

    Function generator and manual data table.

- **[File Formats](file-formats.md)**

    .pviz, .pvizt, .pvizc, .pvizp format reference.

- **[Keyboard Shortcuts](shortcuts.md)**

    All keyboard shortcuts and canvas controls.

- **[Building & Packaging](building.md)**

    Create macOS .app and Windows .exe distributions.

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

Current release: **1.6.1**  
Requires Python **3.10+**
