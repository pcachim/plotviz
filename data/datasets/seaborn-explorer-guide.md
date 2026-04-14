# Seaborn Explorer Guide

The **Seaborn Explorer** is a standalone window inside plotviz that hosts all 8
Seaborn chart types in their own canvas. Open it from the menu bar:

**Tools → Seaborn Explorer…**   (shortcut: `Ctrl+Shift+S`)

The explorer is non-modal — you can keep it open alongside the main chart window.
It reads live from whatever datasets are loaded in the main window, so loading new
data in the main window automatically refreshes the column dropdowns.

---

## Quick workflow

1. Load data in the main window (**Data** tab → **Browse Files**).
2. Open the explorer: **Tools → Seaborn Explorer…**
3. Choose a chart type from the **Chart type** dropdown.
4. Select X / Y columns (where applicable).
5. Adjust options in the panel below.
6. Click **🔄 Redraw** or change any option to refresh.
7. Click **💾 Export…** to save as PNG / SVG / PDF / JPEG.

---

## Chart types & recommended datasets

### KDE — Kernel Density Estimate
Smoothed probability density for a single numeric column.

**Dataset:** `sns_distributions.csv`  
**Y column:** `income`, `spending`, or `savings`

Options: Fill · Fill alpha · Line width · BW adjust · Cumulative · Common norm

---

### Regression
Scatter plot with OLS, polynomial, or LOWESS regression line and confidence band.

**Dataset:** `sns_timeseries.csv`  
**X:** `t`  **Y:** `linear` (or `quadratic` / `sinusoidal`)

Options: Poly order · CI % · Marker size · Alpha · Robust fit · LOWESS · Show scatter

> Set **Poly order** to 2 with `quadratic` for a near-perfect fit.  
> Enable **LOWESS** with `sinusoidal` to trace the wave without specifying a model.

---

### Strip
Categorical scatter with jitter — one dot per observation.

**Dataset:** `sns_categorical.csv`  
**X:** `day`  **Y:** `score_A`

Options: Marker size · Alpha · Jitter · Dodge

---

### Swarm
Beeswarm plot — like Strip but points are placed precisely without overlap.

**Dataset:** `sns_categorical.csv`  
**X:** `day`  **Y:** `score_A`

Options: Marker size · Alpha · Dodge

> Use Swarm for ≤ 200 points per category. Strip scales better for large datasets.

---

### Heatmap
Pearson correlation matrix built automatically from all numeric columns.

**Dataset:** `sns_distributions.csv`  
*(Column selectors are hidden — all numeric columns are used automatically.)*

Options: Colormap · Format · Line width · Annotate cells · Square cells · Colorbar · Robust scale

---

### Pairplot
All-vs-all scatterplot grid with diagonal distributions.

**Dataset:** `sns_distributions.csv`  
*(Column selectors are hidden — all numeric columns are used automatically.)*

Options: Diagonal kind · Off-diagonal kind · Alpha

> Pairplot renders a separate figure and may take 1–2 seconds for 5+ columns.

---

### Joint
Bivariate joint distribution — central scatter/KDE/hex panel with marginal distributions on top and right edges.

**Dataset:** `sns_distributions.csv`  
**X:** `income`  **Y:** `spending`

Options: Kind · Alpha · Ratio · Marginal KDE fill

> `kde` kind gives smooth 2D density contours ideal for presentations.

---

### Catplot
Figure-level categorical plot supporting multiple sub-types.

**Dataset:** `sns_categorical.csv`  
**X:** `day`  **Y:** `score_A`

Options: Kind (box / boxen / violin / bar / point / count / strip / swarm) · Alpha · Saturation · CI · Dodge

---

## Export

Click **💾 Export…** to save the current chart. Supported formats:

| Format | Best for |
|--------|----------|
| PNG    | Reports, presentations |
| SVG    | Web, scalable graphics |
| PDF    | Print, LaTeX |
| JPEG   | Smaller file size |
