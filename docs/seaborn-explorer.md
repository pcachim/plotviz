# Seaborn Explorer

The **Seaborn Explorer** is a dedicated dialog for creating statistical charts powered by [seaborn](https://seaborn.pydata.org/). It runs on its own canvas, fully isolated from the main plotviz chart, so figure-level seaborn plots (Pairplot, Joint, Heatmap, Catplot) never interfere with the main chart's style pipeline.

Open it from the menu bar: **Tools → Seaborn Explorer…**

!!! note "Requirements"
    Seaborn must be installed: `pip install seaborn`. Some regression options (Robust fit, LOWESS) additionally require `pip install statsmodels`.

---

## Interface

The window has two panels:

| Panel | Contents |
|-------|----------|
| **Left — controls** | Chart type, color theme, column selectors, and chart-specific options |
| **Right — preview** | Live seaborn canvas with navigation toolbar and export controls |

Changes to the controls do **not** redraw automatically — click **Redraw** to apply them.

---

## Chart types

| Type | Description |
|------|-------------|
| **KDE** | Kernel Density Estimate — smoothed distribution curve |
| **Regression** | Scatter plot with OLS, polynomial, or LOWESS regression line |
| **Strip** | Categorical scatter plot with jitter |
| **Swarm** | Categorical beeswarm plot (non-overlapping points) |
| **Heatmap** | Correlation matrix heatmap |
| **Pairplot** | All-vs-all scatter grid (uses column picker) |
| **Joint** | Bivariate joint distribution with marginals |
| **Catplot** | Figure-level categorical chart (box, violin, bar, strip, and more) |

---

## Data columns

For chart types that use X/Y axes (KDE, Regression, Strip, Swarm, Joint, Catplot), select columns from the dropdowns:

| Dropdown | Accepts |
|----------|---------|
| **X column** | Any loaded column (numeric or categorical) |
| **Y column** | Numeric columns only |
| **Hue (category)** | Categorical columns — splits data into color groups |
| **Size (category)** | Categorical columns — varies marker size by group |
| **Style (category)** | Categorical columns — varies marker shape/line style by group |

For **Heatmap** and **Pairplot**, a multi-select column list replaces the X/Y dropdowns. Use **All** / **None** buttons to quickly select or deselect all numeric columns.

---

## Color theme

The **Palette** dropdown controls the color scheme used for all chart types. The first option, **plotviz**, applies your current plotviz color palette. All other options are standard seaborn/matplotlib named palettes:

`deep`, `muted`, `pastel`, `bright`, `dark`, `colorblind`, `tab10`, `Set1`, `Set2`, `Set3`, `Paired`, `husl`, `hls`, `rocket`, `mako`, `flare`, `crest`, `viridis`, `plasma`, `magma`, `inferno`

---

## Chart-specific options

### KDE options

| Option | Description |
|--------|-------------|
| **Fill alpha** | Opacity of the shaded area under the curve (0–1) |
| **Line width** | Thickness of the KDE line |
| **BW adjust** | Bandwidth smoothing multiplier (higher = smoother) |
| **Fill** | Toggle the shaded fill under the curve |
| **Cumulative** | Show the cumulative distribution instead |
| **Common norm** | Normalize across all hue groups (areas sum to 1 globally) |

### Regression options

| Option | Description |
|--------|-------------|
| **Poly order** | Polynomial degree for the regression line (1 = linear) |
| **CI %** | Confidence interval width (0–99%) |
| **Marker size** | Scatter point size |
| **Alpha** | Scatter point opacity |
| **Robust fit** | Use robust regression (requires statsmodels) |
| **LOWESS** | Non-parametric locally-weighted smoothing (requires statsmodels) |
| **Show scatter** | Toggle the underlying scatter points |

!!! note
    Robust fit and LOWESS are mutually exclusive with each other and with polynomial order > 1.

### Strip options

| Option | Description |
|--------|-------------|
| **Marker size** | Point size |
| **Alpha** | Point opacity |
| **Jitter** | Amount of random horizontal spread to reduce overplotting (0–0.5) |

### Swarm options

| Option | Description |
|--------|-------------|
| **Marker size** | Point size |
| **Alpha** | Point opacity |

### Heatmap options

| Option | Description |
|--------|-------------|
| **Colormap** | Color scale (`coolwarm`, `viridis`, `plasma`, `RdBu`, `Blues`, `Reds`, `YlOrRd`, `magma`, `rocket`, `mako`) |
| **Format** | Number format for cell annotations (`.2f`, `.1f`, `.0f`, `.2g`, `d`, or blank) |
| **Line width** | Width of the cell border lines |
| **Annotate cells** | Show correlation values inside each cell |
| **Square cells** | Force square cell aspect ratio |
| **Show colorbar** | Show the color scale legend |
| **Robust scale** | Use percentile-based color mapping to reduce outlier influence |

### Pairplot options

| Option | Description |
|--------|-------------|
| **Diagonal** | Plot type for the diagonal (auto, hist, kde) |
| **Off-diagonal** | Plot type for off-diagonal cells (scatter, kde, hist, reg) |
| **Alpha** | Point opacity |

### Joint plot options

| Option | Description |
|--------|-------------|
| **Kind** | Joint plot type (scatter, kde, hist, hex, reg, resid) |
| **Alpha** | Opacity |
| **Ratio** | Size ratio of the joint plot to the marginal plots |
| **Marginal KDE fill** | Fill the marginal KDE distributions |

### Catplot options

| Option | Description |
|--------|-------------|
| **Kind** | Categorical plot type (box, boxen, violin, bar, point, count, strip, swarm) |
| **Alpha** | Opacity |
| **Saturation** | Color saturation (0.1–1.0) |
| **CI** | Confidence interval for bar/point plots (95, 99, sd, or None) |
| **Dodge groups** | Separate hue groups side-by-side instead of overlapping |

---

## Canvas controls

The matplotlib navigation toolbar above the preview canvas provides pan, zoom, and reset controls. See [Keyboard Shortcuts](shortcuts.md#canvas-matplotlib-toolbar) for details.

---

## Bottom bar

| Button | Description |
|--------|-------------|
| **Redraw** | Re-render the chart with the current control values |
| **DPI spinner** | Export resolution (72–600 DPI) |
| **Export…** | Save the chart as PNG, SVG, PDF, or JPEG |
| **🐍 Generate Python Code** | Show a standalone Python script that reproduces the current chart |
| **▶ Open in Code Runner** | Export the chart as a `.pvizx` bundle and open it in the [Python Code Runner](code-runner.md) |
| **Close** | Close the Seaborn Explorer |

---

## Generating Python code

Click **🐍 Generate Python Code** to view a standalone Python script that reproduces the current seaborn chart without any dependency on plotviz. You can copy and paste this script into any Python environment.

Click **▶ Open in Code Runner** to send the chart directly to the [Python Code Runner](code-runner.md), where you can edit and re-run the generated code interactively.
