# Style & Appearance

## The Style tab

The **Style** tab controls the figure-level appearance: size, margins, background colors, borders, and the grid.

---

## Figure size

| Control | Description |
|---------|-------------|
| **Preset** | Quick size: A4 landscape, Letter, 20×15 cm (default), 16×9 widescreen, square |
| **Unit** | cm, inches, or px |
| **Width / Height** | Exact dimensions in the chosen unit |

The size set here is used for both the live preview and the exported file.

### Margins

Four spinboxes — **Left, Right, Bottom, Top** — control the fraction of the figure occupied by whitespace around the plot area (0.0–1.0). The defaults leave room for axis labels and titles.

### DPI

The **DPI** spinbox (default 100) sets the resolution of exported PNG and JPEG files. SVG and PDF are vector formats and ignore DPI.

---

## Colors

### Chart background

- **Chart BG** — the outer figure background (outside the plot area). Default white.
- **Plot BG** — the inner plot area background. Default white.
- **Foreground** — the default color for axes, tick marks, tick labels, and spines. Default black.

Click any color swatch to open the color picker. The picker includes a **Recent colors** row (up to 8 previously selected colors) above the Custom colors section, so frequently used colors are always one click away.

### Borders (spines)

Four checkboxes — **Top, Bottom, Left, Right** — show or hide the four axis border lines (spines). Hiding the top and right spines is a common convention for scientific plots.

---

## Grid

| Control | Description |
|---------|-------------|
| **Show grid** | Toggle the major grid on/off |
| **Grid color** | Color of major grid lines |
| **Line style** | Solid, dashed, dotted, or dash-dot |
| **Line width** | Stroke thickness (0.1–5.0) |
| **Alpha** | Grid line opacity (0.0–1.0) |
| **Show minor grid** | Toggle the minor grid (sub-divisions between major ticks) |

Minor grid controls (color, style, width, alpha) mirror the major grid controls.

---

## Color palettes

The **Color palette** dropdown in the Chart tab sets the default cycle of colors assigned to new series. plotviz includes 11 built-in palettes and supports user-created custom palettes.

See [Color Palettes](palettes.md) for the full palette reference.

---

## Color schemes

A color scheme is a named preset that applies a coordinated set of colors to the chart background, plot area, foreground, grid, and text all at once. Color schemes do not affect individual series colors or axis limits.

### Built-in color schemes

| Name | Character |
|------|-----------|
| Default (white) | Clean white background, matplotlib palette |
| Dark (charcoal) | Deep charcoal `#1e1e2e`, light text, Bold palette |
| Dark (slate) | Navy `#0f172a`, slate plot area, Bold palette |
| Seaborn (whitegrid) | Muted lavender background, white grid lines |
| Scientific (minimal) | White, no top/right spines, very light grid |
| Nature / print | White, no grid, no top/right spines — publication ready |
| Midnight blue | Deep blue, cyan axis labels |
| Warm parchment | Cream background, brown text |
| High contrast | Black background, white text |
| Pastel soft | Off-white, purple-tinted grid, Pastel palette |

### Applying a color scheme

1. Open the **Chart** tab.
2. Select a scheme from the **Color Schemes** dropdown.
3. Click **Apply**.

The five colored swatches next to the dropdown show a preview of BG, Plot, FG, Grid, and Title colors for the selected scheme.

### Saving a custom color scheme

Style the chart exactly as you want it, then:

1. Click **💾 Save scheme…** in the Color Schemes section.
2. Enter a name for the scheme.
3. Choose a save location — the file is saved as a `.pvizc` file.

The scheme is registered in the dropdown for the rest of the session and can be reloaded in future sessions by clicking **📂 Load scheme…**.

### Loading a color scheme

Click **📂 Load scheme…** and select a `.pvizc` file. You are asked whether to apply it immediately. A `.pvizt` template file can also be loaded as a color source — only the color-related settings are extracted.

---

## Appearance (UI theme)

The **Appearance** dropdown in the Chart tab controls the application's light/dark mode:

- **System** — follows the OS theme (default).
- **Light** — forces the light theme regardless of OS setting.
- **Dark** — forces the dark theme.

This setting affects the UI chrome only, not the chart colors. Chart colors are set independently with color schemes and the Style tab.
