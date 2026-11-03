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

When a palette is active (set in the Layout & Style tab), plotviz assigns the next palette color to each new series automatically. If **Lock color** is off, switching palettes reassigns all unlocked series colors to match the new palette. Lock a color to keep it fixed across palette changes.

---

## Curve fitting

The curve fitting section lets you fit a mathematical model to any series and overlay the result on the chart.

### Workflow

1. Select the series to fit in the **Per-Curve** selector above. (If a fit curve is selected, the series it came from is fitted.)
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

### How the data are handled

- **Missing values.** Points where x or y is NaN are ignored, and the results say how many.
- **Starting values** for the Exponential, Power Law and Sigmoid models come from the data (for example the Exponential starts from a straight-line fit of ln y), so they work for any amplitude and x range, for decreasing sigmoids, and for negative data.
- **x far from zero** (years, or a date column, which is a number of days since 1970): the fit is done on `x − x₀`, where x₀ is about the centre of the data, because `e^(b·19800)` overflows and polynomials in such x are badly conditioned. The equation then shows `(x − x₀)` and the results box gives x₀. The curve and the bands are still drawn against the real x.
- **Logarithmic and Power Law** need every x to be greater than 0; if not, the fit reports it instead of returning a meaningless curve.
- A fit that does not converge is reported with a message, never drawn as a curve with a nonsense R².
- The fit curve and its bands are drawn from left to right even when the data are not sorted by x.

### Several fits of the same series

You can apply as many models as you like to a series, to compare them. Every fit is kept, with its own parameters, statistics, bands and style, and all of them are saved in the `.pviz` file.

The **Fits** list under the buttons shows them side by side:

| Column | Meaning |
|--------|---------|
| **Show** | Untick to hide the fit and its bands from the chart (and from the exported script) without deleting it |
| **Model**, **Series** | What was fitted to what |
| **R²**, **RMSE**, **AIC** | The numbers to compare by. The **bold AIC** is the lowest among the fits of that series: a better fit relative to its number of parameters. A higher-order model always has a higher R², so look at the AIC before choosing it |

Click a row to select that fit: the confidence limits, the prediction band, the style controls and the results below then act on it. Selecting a fit curve in the **Per-Curve** list does the same.

- Each new fit takes a colour that the series and its other fits do not use, so they can be told apart.
- Applying **the same model** to the same series again replaces the previous one, and the results say so.
- **Remove Fit** removes the selected fit only. With the data series selected it removes all its fits, after asking.
- The results box shows the selected fit; it never shows another one instead.

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
| **Confidence limits** | Shaded region around the fit: Off, 1σ (68%), 2σ (95%) or 3σ (99.7%) |
| **Prediction band** | Shaded region where new observations are expected to fall: Off, 1σ, 2σ or 3σ |
| **Band opacity** | Opacity of the shaded bands (0.05–1.0; 0.35 by default, the prediction band is drawn at half of it) |

The bands belong to the fit curve and are drawn whatever line type you give that curve, and they follow it if you rename it. If the data lie exactly on the curve (for example data made by the function generator, with no noise) the bands have no width and cannot be seen; the results box says so.

When a fit curve is selected and you click **Apply Fit** with another model, the new model is fitted to the data the curve came from, not to the curve (a curve fitted to its own fit would fit perfectly and have bands of no width).

The percentages hold for few points too: the bands use the Student-t quantile for the degrees of freedom of the fit, which for many points is the same as 1, 2 or 3 normal standard deviations.

The confidence band is tighter (it bounds the mean prediction); the prediction band is wider (it bounds individual future observations).

### Fit results

The results box at the bottom of the section shows:

- Model equation with fitted parameter values
- Goodness of fit: n, parameters, degrees of freedom, R², adjusted R², RMSE, MSE, SSE, SST, AIC and BIC (from the Gaussian log-likelihood, as in statsmodels)
- F-statistic and its p-value, for the models that contain an intercept-only model (Linear, Quadratic, Cubic, Logarithmic); the Exponential, Power Law and Sigmoid have no such test and show `—`
- For each parameter: value, standard error, t, p and the confidence interval

The fit result is saved with the `.pviz` project file and restored on reload.
