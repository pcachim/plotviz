# Getting Started

## Requirements

- Python 3.10 or later
- macOS 11+, Windows 10+, or Linux (X11/Wayland)

## Installation

### From PyPI

```bash
pip install plotviz
```

### From source (recommended for development)

```bash
git clone https://github.com/yourorg/plotviz.git
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
| numpy | ≥ 1.24 | Numerical arrays |
| pandas | ≥ 2.0 | Data loading |
| scipy | ≥ 1.10 | Curve fitting and statistics |
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
| Chart | Open/save files, export, subplot layout, color schemes, palette |
| Data | Load datasets, series table, chart type |
| Style | Figure size, margins, colors, grid, borders |
| Series | Per-curve line style, marker, color, curve fitting |
| Axes | Labels, limits, scales, ticks, secondary Y axis |
| Annotations | Subplot titles, legend, text/arrow/image annotations |
| Advanced | Function generator, manual data entry table |

**Right panel — canvas**

The live chart preview updates as you change settings. Use the matplotlib toolbar at the top of the canvas to pan, zoom, and reset the view.

---

## Your first chart

### 1. Load data

Click **Data** tab → **Browse Files** and open a CSV, Excel, JSON or TXT file. plotviz reads all numeric and categorical columns and lists them in the dataset panel.

### 2. Assign columns to series

In the series table, use the **X** and **Y** dropdowns to pick which columns to plot. The **Label** column sets the legend entry. Add more rows with the **+ Add series** button.

### 3. Choose a chart type

In the **Data** tab, select a chart type from the dropdown — Line, Scatter, Bar, and so on. The canvas updates instantly.

### 4. Style the chart

- **Style** tab: set background color, grid, figure size.
- **Series** tab: change line color, width, marker style.
- **Axes** tab: set axis labels, limits and scale.
- **Annotations** tab: add a legend, subplot title, or text annotations.

### 5. Export

In the **Chart** tab, choose a format (PNG, SVG, PDF, JPEG) and click **Export Chart**. The DPI and figure dimensions set in the Style tab are used for the exported file.

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
