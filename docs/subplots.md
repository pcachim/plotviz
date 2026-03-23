# Subplots

plotviz supports multi-panel layouts with up to 9 subplots per chart. Each subplot is an independent axes with its own series, title, labels, limits, legend, and annotations.

---

## Opening the layout dialog

In the **Chart** tab, click **⚙️ Configure Subplot Layout…** to open the layout picker.

---

## Layout presets

The **Presets** tab shows a visual gallery of 18 built-in layouts. Click a preview thumbnail to select it; the chart updates immediately.

### Regular grids

| Preset | Description |
|--------|-------------|
| Single | 1 × 1 (default) |
| 1 × 2 | One row, two columns |
| 1 × 3 | One row, three columns |
| 2 × 1 | Two rows, one column |
| 2 × 2 | Two rows, two columns |
| 2 × 3 | Two rows, three columns |
| 3 × 1 | Three rows, one column |
| 3 × 2 | Three rows, two columns |
| 3 × 3 | Three rows, three columns |

### Mosaic presets (unequal panels)

| Preset | Description |
|--------|-------------|
| 1 top / 2 down | Wide panel on top, two panels below |
| 2 top / 1 down | Two panels on top, wide panel below |
| 1 left / 2 right | Tall panel on the left, two panels stacked on the right |
| 2 left / 1 right | Two panels stacked on the left, tall panel on the right |
| 1 top / 3 down | Wide panel on top, three panels in a row below |
| 3 top / 1 down | Three panels in a row on top, wide panel below |
| 2×2 mosaic 1+1+2 | Two equal panels above, one wide panel below |
| 3 rows / 1 wide top | Three rows: wide top, two-column middle, two-column bottom |
| 3 rows / 1 wide bottom | Three rows: two-column top, two-column middle, wide bottom |

---

## Custom mosaic editor

The **Custom mosaic** tab provides a grid editor for building any layout.

1. Set the **Rows** and **Columns** spinboxes to define the grid dimensions.
2. Each cell in the grid shows a letter label. Click cells to assign them to the same panel (merge) or reset them to individual panels.
3. The mosaic is described as a 2D list of letters, e.g. `[['A','A'],['B','C']]` for a wide top panel over two equal bottom panels.

### Live preview

A small preview thumbnail updates as you edit the mosaic, showing the resulting panel layout.

---

## Shared axes

Two checkboxes in the layout dialog configure axis sharing:

| Option | Effect |
|--------|--------|
| **Share X axis** | All subplots in the same column share their X limits and tick marks |
| **Share Y axis** | All subplots in the same row share their Y limits and tick marks |

Shared axes keep panels visually aligned and make comparisons easier.

---

## Assigning series to subplots

In the **Data** tab series table, the **Plot #** column sets which subplot (1-based) a series appears in. Increment the number to move a series to a different panel.

The **Axes** and **Annotations** tabs both have a **Subplot** selector at the top that lets you configure each panel independently. All three selectors (Axes, Annotations, Series) stay in sync — changing one updates the others.

---

## Per-subplot settings

Each subplot has its own independent settings for:

- Title text, font, size, and color
- X, Y, and Y2 axis labels
- Axis limits (auto or manual) for X, Y, and Y2
- Axis scale (linear, log, logit, inverted)
- Tick configuration (size, direction, minor ticks, rotation, step, formatter)
- Legend (show/hide, position, style)
- Annotation visibility

Changes made in the **Axes** and **Annotations** tabs always apply to the subplot currently shown in the selector.
