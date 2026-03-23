# Series

The **Series** tab controls the visual appearance of individual curves and provides curve fitting tools.

When the chart has more than one subplot, a **Subplot** selector at the top switches context. The curve selector below it lists all series assigned to the active subplot.

---

## Per-curve style

Select a series from the **Curve** dropdown to edit its style. Changes take effect on the live preview immediately.

### Line

| Control | Description |
|---------|-------------|
| **Line style** | Solid (`-`), dashed (`--`), dotted (`:`) , dash-dot (`-.`), or none |
| **Line width** | Stroke thickness in points |
| **Color** | Line color — click the swatch to open the color picker |
| **Lock color** | When checked, auto-palette assignment does not override the manually chosen color |

### Marker

| Control | Description |
|---------|-------------|
| **Marker** | Point shape: circle, square, triangle up/down/left/right, diamond, pentagon, hexagon, star, plus, cross, x, or None |
| **Marker size** | Point size in points |
| **Marker color** | Independent color for the marker fill (defaults to the line color) |

### Color auto-assignment

When a palette is active (set in the Chart tab), plotviz assigns the next palette color to each new series automatically. If **Lock color** is off, switching palettes reassigns all unlocked series colors to match the new palette. Lock a color to keep it fixed across palette changes.

---

## Curve fitting

The curve fitting section lets you fit a mathematical model to any series and overlay the result on the chart.

### Workflow

1. Select a series from the **Fit series** dropdown.
2. Choose a model from the **Model** dropdown.
3. Click **Apply Fit**.
4. The fitted curve appears on the chart and the equation and statistics are shown in the results box.

### Available models

| Model | Equation |
|-------|---------|
| Linear | y = a·x + b |
| Quadratic | y = a·x² + b·x + c |
| Cubic | y = a·x³ + b·x² + c·x + d |
| Exponential | y = a·e^(b·x) |
| Power Law | y = a·x^b |
| Logarithmic | y = a·ln(x) + b |
| Sigmoid | y = a / (1 + e^(−(x − b)/c)) |

Fitted parameters are shown in the results box along with R², RMSE, and other statistics.

### Fit curve style

The appearance of the fitted curve is set independently from the data series:

| Control | Description |
|---------|-------------|
| **Color** | Color of the fit line |
| **Line style** | Solid, dashed, dotted, etc. |
| **Line width** | Stroke thickness |

### Confidence and prediction bands

| Control | Description |
|---------|-------------|
| **Confidence band** | Shaded region showing the confidence interval around the fit (None, 90%, 95%, 99%) |
| **Prediction band** | Shaded region showing where new observations are expected to fall (None, 90%, 95%, 99%) |
| **Band alpha** | Opacity of the shaded bands (0.0–1.0) |

The confidence band is tighter (it bounds the mean prediction); the prediction band is wider (it bounds individual future observations).

### Fit results

The results box at the bottom of the section shows:

- Model equation with fitted parameter values
- R² (coefficient of determination)
- RMSE (root mean square error)
- Parameter values and standard errors
- Additional statistics (AIC, BIC if available)

The fit result is saved with the `.pviz` project file and restored on reload.
