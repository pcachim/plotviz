# plotviz 2.0 — Chart Types Guide & Sample Datasets

This guide covers all **22 chart types** supported by plotviz. For each type you'll find:

- What dataset to load
- Which columns to assign to X, Y, Z, and Error
- Key options to set
- Notes on combining types

> **Quick workflow reminder:**
>
> 1. Open the **Data** tab → **Browse Files** → pick the CSV below  
> 2. In the series table assign **X** / **Y** columns  
> 3. Set the **Type** dropdown for that series row  
> 4. Adjust style in the **Series** tab and labels in the **Axes** tab

---

## Dataset overview

| File | Rows | Key columns | Charts it covers |
|------|------|-------------|-----------------|
| `line_scatter_step.csv` | 40 | x, y_linear, y_sine, y_noisy, y_err | Line, Scatter, Step, Stem, Area, Errorbar |
| `bar.csv` | 8 | quarter, product_A/B/C | Bar (grouped & stacked) |
| `bubble.csv` | 15 | gdp_per_capita, life_expectancy, population_m | Bubble |
| `waterfall.csv` | 9 | category, change | Waterfall |
| `histogram.csv` | 300 | height_cm, weight_kg | Histogram, ECDF |
| `hist2d_hexbin.csv` | 500 | x, y | Hist2D, Hexbin |
| `boxplot_violin.csv` | 100 | group_A/B/C/D | Boxplot, Violin |
| `pie.csv` | 5 | segment, value | Pie |
| `polar.csv` | 200 | theta_rad, r_rose, r_spiral | Polar |
| `radar.csv` | 3 | Speed, Strength, Agility, Stamina, Defense, Intelligence | Radar |
| `heatmap.csv` | 126 | x_col, y_row, z_value | Heatmap |
| `contour_3d_surface.csv` | 900 | x, y, z | Contour, 3D Surface |
| `ecdf.csv` | 200 | response_time_ms, alt_system_ms | ECDF |
| `quiver.csv` | 81 | x, y, dx, dy | Quiver (see note) |

---

## Per-series chart types

These types are assigned **per row** in the series table and can be freely mixed in the same subplot.

---

### 1 · Line

**Dataset:** `line_scatter_step.csv`

| Role | Column |
|------|--------|
| X | `x` |
| Y | `y_linear` (add a 2nd series with `y_sine`) |

**Steps:**

1. Load the file. Add two series rows.
2. Series 1 → X: `x`, Y: `y_linear`, Type: **Line**
3. Series 2 → X: `x`, Y: `y_sine`, Type: **Line**
4. In **Series** tab → set different colors and line styles (e.g. solid vs dashed).
5. In **Annotations** tab → enable the legend.

**Options to explore:** Line style (solid/dashed/dotted), Line width, Marker shape & size.

---

### 2 · Scatter

**Dataset:** `line_scatter_step.csv`

| Role | Column |
|------|--------|
| X | `x` |
| Y | `y_noisy` |

**Steps:**

1. Add a series row, Type: **Scatter**.
2. In **Series** tab → increase Alpha slightly (e.g. 0.7) to reveal overlapping points.
3. Optionally add a second Scatter series using `y_sine` to compare distributions.

**Tip:** Scatter mixes well with a Line series on the same axes — use `y_linear` as Line and `y_noisy` as Scatter to visualize a trend with noisy observations.

---

### 3 · Bar

**Dataset:** `bar.csv`

| Role | Column |
|------|--------|
| X | `quarter` |
| Y | `product_A` (repeat for B and C) |

**Steps:**

1. Add **three** series rows (one per product).
2. All three → X: `quarter`, Types: **Bar**.
3. plotviz automatically groups them side by side.
4. **Stacked bars:** tick **Stacked** in the chart-type options panel.
5. **Horizontal bars:** tick **Horizontal** — the X axis becomes the value axis.

**Options:** Width (default 0.8), Stacked, Horizontal.

---

### 4 · Errorbar

**Dataset:** `line_scatter_step.csv`

| Role | Column |
|------|--------|
| X | `x` |
| Y | `y_noisy` |
| Error | `y_err` (set via the **Error** dropdown below the series table) |

**Steps:**

1. Add one series → X: `x`, Y: `y_noisy`, Type: **Errorbar**.
2. Below the series table, set the **Error** dropdown to `y_err`.
3. Adjust **Cap size** in the options panel.

---

### 5 · Area

**Dataset:** `line_scatter_step.csv`

| Role | Column |
|------|--------|
| X | `x` |
| Y | `y_linear` and `y_sine` |

**Steps:**

1. Add two series rows, both Type: **Area**.
2. In the type options panel, reduce **Fill alpha** to ~0.4 so both layers are visible.
3. Enable **Stacked** to accumulate the areas vertically.

---

### 6 · Step

**Dataset:** `line_scatter_step.csv`

| Role | Column |
|------|--------|
| X | `x` |
| Y | `y_linear` |

**Steps:**

1. Set Type: **Step**.
2. Works identically to Line, but each segment is drawn as a staircase.
3. Useful for sampled/discrete signals or histogram-style visualizations.

---

### 7 · Stem

**Dataset:** `line_scatter_step.csv`

| Role | Column |
|------|--------|
| X | `x` |
| Y | `y_sine` |

**Steps:**

1. Set Type: **Stem**.
2. Vertical lines drop from each data point to the X axis.
3. Best with sparse data — try using every 4th row by manually filtering, or use `y_sine` for a clear wave pattern.

---

### 8 · Bubble

**Dataset:** `bubble.csv`

| Role | Column |
|------|--------|
| X | `gdp_per_capita` |
| Y | `life_expectancy` |
| Z | `population_m` (set via the **Z** dropdown below the series table) |

**Steps:**

1. Add one series row, Type: **Bubble**.
2. Below the series table, set **Z** to `population_m`.
3. In the options panel, adjust **Scale** (try 0.1–0.5) so bubbles don't overlap excessively.
4. Set **Alpha** to ~0.6 to reveal overlapping bubbles.
5. In **Axes** tab: label X as "GDP per Capita (USD)", Y as "Life Expectancy (years)".

**Tip:** Set **Marker** to `circle` and **Edge color** to a dark shade for a classic bubble chart look.

---

### 9 · Waterfall

**Dataset:** `waterfall.csv`

| Role | Column |
|------|--------|
| X | `category` |
| Y | `change` |

**Steps:**

1. Set Type: **Waterfall**.
2. Positive bars rise (green by default), negative bars fall (red).
3. Enable **Show connectors** to draw horizontal lines between bars.
4. In **Axes** tab: rotate X tick labels 30–45° so category names don't overlap.

**Note:** The last row ("Final Revenue") with value 0 will render as a total bar if plotviz supports it, or can be omitted.

---

## Whole-chart types

These types take over the entire subplot and cannot be mixed with other series types.

---

### 10 · Histogram

**Dataset:** `histogram.csv`

| Role | Column |
|------|--------|
| Y | `height_cm` |

**Steps:**

1. Set Type: **Histogram** from the main Chart type dropdown (not the per-series column).
2. In the options panel, set **Bins** to 25.
3. Toggle **Density** to normalize the Y axis to probability density.
4. To overlay a second distribution, add a second series with Y: `weight_kg` — each gets its own color with transparency.

---

### 11 · Hist2D

**Dataset:** `hist2d_hexbin.csv`

| Role | Column |
|------|--------|
| X | `x` |
| Y | `y` |

**Steps:**

1. Set Type: **Hist2D**.
2. In options, set **Bins** to 30 and choose a **Colormap** (e.g. `viridis` or `plasma`).
3. The two clusters in the dataset will appear as two dense regions.

---

### 12 · Hexbin

**Dataset:** `hist2d_hexbin.csv`

Same column assignments as Hist2D (`x` → X, `y` → Y).

**Steps:**

1. Set Type: **Hexbin**.
2. Adjust **Bins** (controls hexagon size — higher = smaller hexagons).
3. Try `inferno` colormap for a dramatic look.

**When to use Hexbin vs Hist2D:** Hexbin avoids the axis-alignment bias of rectangular bins and often looks cleaner for dense scatter.

---

### 13 · Boxplot

**Dataset:** `boxplot_violin.csv`

| Role | Column |
|------|--------|
| Y | `group_A`, `group_B`, `group_C`, `group_D` (one series per column) |

**Steps:**

1. Add four series rows, one per group column. Leave X empty.
2. Set all Types to **Boxplot**.
3. Set the **Label** for each row to "Group A", "Group B", etc.
4. Boxes appear side by side, showing median, IQR, and outliers automatically.

---

### 14 · Violin

**Dataset:** `boxplot_violin.csv`

Same setup as Boxplot.

**Steps:**

1. Use the same four series rows with Type: **Violin**.
2. In options: enable **Show means** and **Show medians** to add reference lines.
3. Set **bw_method** to `scott` (default) or `silverman`.
4. Toggle **Vertical** off for horizontal violins.

---

### 15 · Pie

**Dataset:** `pie.csv`

| Role | Column |
|------|--------|
| X | `segment` (slice labels) |
| Y | `value` (slice sizes) |

**Steps:**

1. Set Type: **Pie**.
2. Enable **Show %** to print percentages inside slices.
3. Toggle **Shadow** for a subtle drop shadow effect.
4. In **Series** tab: assign distinct colors to each series row (one per slice).

---

### 16 · Polar

**Dataset:** `polar.csv`

| Role | Column |
|------|--------|
| X | `theta_rad` (angle in radians) |
| Y | `r_rose` (add a 2nd series with `r_spiral`) |

**Steps:**

1. Set Type: **Polar**.
2. The `r_rose` column traces a 3-petal rose curve; `r_spiral` traces an Archimedean spiral.
3. Enable **Fill** in options for the rose to create a filled petal shape.
4. Use different colors per series.

---

### 17 · Radar

**Dataset:** `radar.csv`

| Role | Column |
|------|--------|
| Y | All six columns: `Speed`, `Strength`, `Agility`, `Stamina`, `Defense`, `Intelligence` |

**Steps:**

1. Add **three** series rows (one per athlete/row in the dataset).
2. Each series row should include all six columns as Y — plotviz uses all Y columns as radar axes.
3. Set Type: **Radar** for all rows.
4. In **Series** tab: set distinct, semi-transparent colors per series.
5. Enable the legend in **Annotations** tab and label each series (Athlete A/B/C).

---

### 18 · Heatmap

**Dataset:** `heatmap.csv`

| Role | Column |
|------|--------|
| X | `x_col` (day of week) |
| Y | `y_row` (hour of day) |
| Z | `z_value` (traffic level) — set via the **Z** dropdown |

**Steps:**

1. Set Type: **Heatmap**.
2. Set **Z** dropdown to `z_value`.
3. Choose **Colormap** — `YlOrRd` works well for traffic intensity.
4. Enable **Show colorbar** to display the scale legend.
5. In **Axes** tab: label X as "Day", Y as "Hour of Day".

---

### 19 · Contour

**Dataset:** `contour_3d_surface.csv`

| Role | Column |
|------|--------|
| X | `x` |
| Y | `y` |
| Z | `z` — set via the **Z** dropdown |

**Steps:**

1. Set Type: **Contour**.
2. Set **Z** to `z`.
3. In options: set **Contour levels** to 15 and choose `coolwarm` colormap.
4. The dataset shows a sinc-like function — concentric rings radiate from the center.

---

### 20 · 3D Surface

**Dataset:** `contour_3d_surface.csv`

Same column assignments as Contour (`x`, `y`, `z`).

**Steps:**

1. Set Type: **3D Surface**.
2. The canvas switches to a 3D viewport automatically.
3. **Rotate** by clicking and dragging on the canvas.
4. Try `plasma` or `viridis` colormap.

**Tip:** 3D Surface and Contour use the same dataset — you can save two `.pviz` files (one per type) to compare them side by side.

---

### 21 · ECDF

**Dataset:** `ecdf.csv`  
*(or use `histogram.csv` with `height_cm`)*

| Role | Column |
|------|--------|
| Y | `response_time_ms` (add a 2nd series with `alt_system_ms`) |

**Steps:**

1. Add two series, Type: **ECDF** for both.
2. No X column needed — plotviz computes the cumulative fraction automatically.
3. In **Axes** tab: label Y as "Cumulative fraction", X as "Response time (ms)".
4. The crossing point of the two curves shows which system is faster for a given percentile.

---

### 22 · Quiver

**Dataset:** `quiver.csv`

| Role | Column |
|------|--------|
| X | `x` |
| Y | `y` |
| Z | Encoded as complex: `dx + dy·j` |

**Note on Z encoding:** plotviz's Quiver type expects the Z column to contain complex numbers (`real = dx`, `imag = dy`). Since CSV cannot store complex numbers natively, you have two options:

**Option A — Use the Advanced tab manual entry:** Enter a formula or use the function generator to compute `dx + 1j*dy` directly.

**Option B — Preprocess in Python:**

```python
import pandas as pd
import numpy as np

df = pd.read_csv("quiver.csv")
df["z_complex"] = df["dx"] + 1j * df["dy"]
# Save as JSON (plotviz supports JSON with complex-encoded columns)
df[["x", "y", "z_complex"]].to_json("quiver_complex.json", orient="records")
```
Then load `quiver_complex.json` and assign Z to `z_complex`.

The dataset encodes a **clockwise rotation field** — arrows will spiral around the origin.

---

## Mixing chart types

plotviz lets you combine *per-series* types freely in the same subplot. Some useful combos:

| Combo | How to set up |
|-------|--------------|
| **Line + Scatter** | Series 1: Line (trend), Series 2: Scatter (raw points) — same X/Y source |
| **Bar + Line** | Series 1: Bar (absolute values), Series 2: Line (running average) — same X |
| **Area + Line** | Series 1: Area (filled baseline), Series 2: Line (boundary curve) |
| **Errorbar + Scatter** | Series 1: Errorbar (mean ± error), Series 2: Scatter (individual samples) |
| **Step + Scatter** | Series 1: Step (binned count), Series 2: Scatter (raw events) |

**Rule:** Whole-chart types (Histogram, Pie, Heatmap, etc.) cannot be mixed with any other type in the same subplot.

---

## Using subplots

To place charts side by side:

1. In the **Chart** tab, set the **Subplot layout** (e.g. 1×2 or 2×2).
2. In the series table, set the **Plot #** column for each series row (1-based).
3. Configure axis labels independently per subplot in the **Axes** tab (use the **Subplot** selector at the top).

---

## Exporting

**Chart** tab → export dropdown:

| Format | Best for |
|--------|---------|
| PNG | Reports, presentations |
| SVG | Web, scalable graphics |
| PDF | Print, LaTeX |
| JPEG | Lossy, smaller file size |

Set DPI in the **Style** tab before exporting (300 DPI for print, 96–150 for screen).

---

## Saving your work

- **`.pviz`** — full project (data + settings). Use *Save Chart (.pviz)*.
- **`.pvizt`** — template (settings only, no data). Use *Save Template (.pvizt)* to reuse your style.
- **`.pvizc`** — color scheme only. Share palettes across machines.
