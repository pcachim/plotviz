# Glossary

| Term | Meaning |
|------|---------|
| **Dataset** | A column of values with a name, loaded from a file or created by Generate, Transform or a fit. The **Datasets** list holds all of them |
| **Series** | One row of the series table: an X column, a Y column, a label and a chart type. One series is one curve, set of points or bars |
| **Digitize** | Read the values of a chart that exists only as a picture, by marking points on it. See [Digitize Image](digitize.md) |
| **Subplot** | One panel of the figure. A chart has one or several; each has its own axes, grid and legend |
| **Plot mode** | The group of chart types that a subplot uses: Standard, Histogram, Statistical, Heatmap & Contour, Polar & Radar, Pie or Quiver |
| **Chart type** | The kind of picture a series draws: Line, Scatter, Bar, Histogram, and so on |
| **Figure** | The whole page that is exported, made of the subplots, the title and the margins |
| **Canvas** | The preview of the figure on the right of the window; also the plot area of a subplot (**Canvas & Grid**) |
| **Color scheme** | A named set of colours for the background, the plot area, the text, the grid and the borders |
| **Color palette** | The ordered colours given to the series, one after the other |
| **Template** | A file (`.pvizt`) with the style and layout of a chart, without its data |
| **Fit** | A model (a line, a parabola, …) adjusted to a series. A chart can hold several |
| **R², RMSE, AIC** | Measures of how well a fit follows the data. R² is the share of the variation explained (1 is perfect); RMSE is the typical distance of the points from the curve; the AIC compares fits of different complexity (the lowest is best) |
| **Confidence limits** | The band in which the fitted curve lies with the stated probability |
| **Prediction band** | The wider band in which a new measurement is expected to fall |
| **Preview** | The small plot of Transform and Generate that shows what the button would create, without creating it |
| **Live** | The option of a preview to redraw itself a moment after every change |
| **Meshgrid** | Every x combined with every y, to evaluate a function of two variables on a grid |
| **Bundle** (`.pvizx`) | A zip with a standalone Python script of the chart and its data; see [Python Export Bundle](python-export.md) |
