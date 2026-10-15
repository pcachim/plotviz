# Getting Started

## Requirements

- Python 3.10 or later
- macOS 11+, Windows 10+, or Linux (X11/Wayland)

## Installation

### Pre-built binary (recommended — no Python required)

Download the latest release for your platform from GitHub:

[macOS DMG / Windows ZIP → GitHub Releases](https://github.com/pcachim/plotviz/releases/latest)

- **macOS** — open the `.dmg`, drag `plotviz.app` to Applications.
- **Windows** — extract the `.zip` and run `plotviz.exe`.

### From PyPI

```bash
pip install plotviz
```

### From source (recommended for development)

```bash
git clone https://github.com/pcachim/plotviz.git
cd plotviz
uv sync          # installs all dependencies into .venv
uv run plotviz   # launches the app
```

### Dependencies

plotviz installs these packages automatically:

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

## Launching

```bash
# if installed via pip
plotviz

# from source with uv
uv run plotviz

# open a file directly
plotviz mydata.pviz
```

You can also double-click a `.pviz`, `.pvizt`, `.pvizc` or `.pvizp` file in Finder (macOS) or Explorer (Windows) once the app is installed.

---

## Interface overview

The plotviz window has two main areas:

**Left panel — tabs**

| Tab | Purpose |
|-----|---------|
| Data | Loaded datasets, and the **Generate** page (function generators, data table) |
| Layout & Style | Whole-figure settings: size, margins, title, subplot grid, colour scheme, palette |
| Plots | Per-subplot settings, with a **Editing** selector at the top when there are several subplots |

The **Plots** tab has five pages: **Plot** (chart type, series table, options), **Curves** (per-curve line style, marker, colour, curve fitting), **Axes** (labels, limits, scales, ticks, secondary Y axis, Z axis and 3D viewpoint), **Canvas & Grid** (plot-area colour, borders, major and minor grid) and **Annotations** (subplot title, legend, text/arrow/image annotations). Opening, saving and exporting are in the **File** menu.

**Right panel — canvas**

The live chart preview updates as you change settings. Use the matplotlib toolbar at the top of the canvas to pan, zoom, and reset the view.

---

## Your first chart

### 1. Load data

Click the **Data** tab → **Browse Files** and open a CSV, Excel, JSON or TXT file. plotviz reads all numeric and categorical columns and lists them in the dataset panel.

### 2. Assign columns to series

In **Plots → Plot**, in the series table, use the **X** and **Y** dropdowns to pick which columns to plot. The **Label** column sets the legend entry. Add more rows with the **+ Add series** button.

### 3. Choose a chart type

In **Plots → Plot**, select a chart type from the dropdown — Line, Scatter, Bar, and so on. The canvas updates instantly.

### 4. Style the chart

- **Layout & Style** tab: set background color, colour scheme, figure size.
- **Plots → Curves**: change line color, width, marker style.
- **Plots → Axes**: set axis labels, limits, scale, grid and canvas colours.
- **Plots → Annotations**: add a legend, subplot title, or text annotations.

### 5. Export

Click **⬆ Export** in the top bar (or **File → Export Image…**, Ctrl+E), pick a format (PNG, SVG, PDF, JPEG) and a DPI, then **Save…** to write a file or **Copy to clipboard** to paste the image into another app (raster formats only). The DPI and figure dimensions set in the Layout & Style tab are used for the exported file.

With more than one subplot, tick **Also save each subplot as its own file** to get, besides the whole figure, one file per subplot (`name_1`, `name_2`, …). Each keeps its own proportions; raster files are scaled so the longer side matches the longer side of the figure, and vector files (SVG, PDF, EPS) keep the subplot's natural size. A subplot file includes its axis labels, twin axis, legend and colorbar, but not the figure title or a figure-wide legend. Existing files with those names are replaced after you confirm.

### 6. Save your work

Click **Save Chart (.pviz)** to save a `.pviz` project file. Reopening it restores your data, series assignments, and all style settings.

---

## Settings and preferences

plotviz stores user preferences in a JSON file:

| Platform | Location |
|----------|----------|
| macOS | `~/Library/Application Support/plotviz/settings.json` |
| Linux | `~/.config/plotviz/settings.json` |
| Windows | `%APPDATA%\plotviz\settings.json` |

Stored preferences include the last-used directory, theme (System/Light/Dark), color palette, recent files list (up to 12), custom palettes, recent colors, and window geometry.

To reset all settings to defaults, delete the `settings.json` file and restart the app.
