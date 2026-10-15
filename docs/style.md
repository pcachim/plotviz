# Style & Appearance

## The Layout & Style tab

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

The figure background and the foreground are edited in **Edit scheme…**. The plot area is in the Canvas & Grid tab.

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

The **Color palette** dropdown in the Layout & Style tab sets the default cycle of colors assigned to new series. plotviz includes 11 built-in palettes and supports user-created custom palettes.

See [Color Palettes](palettes.md) for the full palette reference.

---

## Color schemes

A color scheme is a named preset that applies a coordinated set of colors to the chart background, plot area, foreground, grid, and text all at once. Color schemes do not affect individual series colors or axis limits.

### Built-in color schemes

| Name | Character | Palette |
|------|-----------|---------|
| Default (white) | Clean white background | Matplotlib |
| Ivory | Ivory, no grid, only left/bottom spines | Publication |
| Blueprint (light) | Ice-blue, solid major and minor grid | Cool |
| Grey panel | Grey plot area, thick white grid, no spines | Matplotlib |
| Graph paper | Pale green, dense fine grid | Earth |
| Newsprint | Cream-salmon, bottom spine only | Colorblind |
| Solarized (light) | Solarized beige, dashed grid | Warm |
| Lavender | Lilac, white plot area, dotted grid | Ocean |
| Sage | Grey-green, white plot area | Nature |
| Dark (charcoal) | Deep charcoal `#1e1e2e`, light text | Bold |
| Dark (slate) | Navy `#0f172a`, slate plot area | Bold |
| Midnight blue | Deep blue, cyan axis labels | Bold |
| High contrast | Black background, white text | Bold |

### Applying a color scheme

1. Open the **Layout & Style** tab.
2. Choose a scheme from the **Color Schemes** dropdown. It is applied at once; use Ctrl+Z to undo.
3. With several subplots, **Apply to** chooses *All subplots* (the default) or *Active subplot only*. The second changes just that subplot's plot area, axes colour, borders, grid and title colour; the figure background, palette, fonts and axis-label colours belong to the whole figure and stay as they are. Pick the active subplot with the **Editing** selector in the Plots tab.

The five colored swatches next to the dropdown show a preview of BG, Plot, FG, Grid, and Title colors for the selected scheme.

### The active scheme

The scheme shown in the dropdown is the **active scheme**: the colours of the chart *are* that scheme. It tracks the eight colours (figure and plot background, foreground, title, X and Y labels, grid and minor grid), whether the grid, minor grid and each border are shown, and the palette. Fonts, sizes and grid line style are applied with a scheme but are not tracked.

- **Built-in schemes are read-only.** The first time you change anything they track, plotviz makes an editable copy, `<name> – edited`, and makes it active. Every further change goes into that copy. If you change everything back, the copy is dropped.
- **Your own schemes** (made with **Edit scheme…** or loaded from a file) are edited in place.
- **Switching schemes never loses anything** during the session: the scheme you leave stays in the dropdown.
- A **\*** after a name means the scheme is not in the **schemes folder**, so it will not be there next time. Saving it into the folder removes the *.
- With several subplots, the grid, plot background, foreground and borders are per subplot. Changing them there is a local adjustment and does not touch the scheme, and **Apply to: Active subplot only** leaves the active scheme as it is.
- A chart file (`.pviz`) stores its active scheme, name and values, so the chart looks the same when reopened.

### Editing a color scheme

Click **Edit** in the Color Schemes section to create or change a scheme in one place: the eight colours, grid and border switches and the palette. **Load from** starts from another scheme. **Save & apply** names the scheme, makes it active and applies it. Built-in names cannot be replaced.

### Saving a color scheme

Click **Save** in the Color Schemes section. The dialog opens in the schemes folder (`~/Library/Application Support/plotviz/schemes/` on macOS; Preferences shows it and can open it), and every `.pvizc` there is loaded when plotviz starts. You may save elsewhere, but then the scheme keeps its * and is not loaded at start-up. Built-in schemes cannot be saved. To delete a scheme, delete its file.

### Loading a color scheme

Click **Load** and select a single `.pvizc` file, for instance one from outside the folder. You are asked whether to apply it, and applying it makes it the active scheme. A `.pvizt` template file can also be loaded as a color source — only the color-related settings are extracted.

---

## Appearance (UI theme)

The **Appearance** dropdown in the Chart tab controls the application's light/dark mode:

- **System** — follows the OS theme (default).
- **Light** — forces the light theme regardless of OS setting.
- **Dark** — forces the dark theme.

This setting affects the UI chrome only, not the chart colors. Chart colors are set independently with color schemes and the Layout & Style tab.
