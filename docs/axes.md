# Axes

The **Axes** tab controls per-subplot axis configuration: labels, limits, scale, ticks, and the secondary Y axis. When the chart has more than one subplot, a **Subplot** selector at the top lets you switch between panels. Changing the selector in the Axes tab automatically syncs with the selectors in the Annotations and Series tabs.

---

## Axis labels

Each axis (X, Y, Y2) has three controls:

| Control | Description |
|---------|-------------|
| **Show label** | Checkbox — hide the label without clearing the text |
| **Text field** | The label text (placeholder shows the column name when empty) |
| **Font / Size / Color** | Typography for the label |

X and Y label fonts and colors are global — they apply to all subplots. Per-subplot overrides are not available for axis labels.

---

## Axis limits

| Control | Description |
|---------|-------------|
| **Auto** | Checkbox — let matplotlib choose limits automatically (default on) |
| **Min / Max** | Manual limit values, active only when Auto is off |

Uncheck **Auto** and set Min/Max to zoom into a specific data range without changing the data itself.

---

## Axis scale

Four radio buttons set the scale for each axis:

| Scale | Description |
|-------|-------------|
| **Linear** | Uniform spacing (default) |
| **Log** | Logarithmic spacing — requires all data > 0 |
| **Logit** | Logit scale for probabilities (0–1) |
| **Inverted** | Linear scale with the axis reversed (high values at the left/bottom) |

---

## Tick marks

| Control | Description |
|---------|-------------|
| **Show ticks** | Checkbox — hide tick marks and labels entirely |
| **Tick size** | Font size for tick labels (pt) |
| **Tick direction** | `out` (default), `in`, or `inout` |
| **Minor ticks** | Checkbox — show minor tick marks between major ticks |
| **Rotation** | Angle of tick labels in degrees (useful for long X labels) |
| **Step** | Force a fixed interval between major ticks (0 = automatic) |

---

## Tick formatters

The **Formatter** dropdown on each axis controls how tick values are displayed:

| Formatter | Example output |
|-----------|---------------|
| auto | matplotlib default |
| plain | `1234567` (no scientific notation) |
| sci | `1.23 × 10⁶` |
| eng | `1.23 M` (SI prefix) |
| percent | `12.3%` |
| date | `2024-01` (for date-encoded floats) |

---

## Secondary Y axis (Y2)

Enable the secondary Y axis by ticking the **Y2** checkbox on one or more series rows in the Data tab. The Y2 axis appears on the right side of the plot.

In the Axes tab, the Y2 section provides the same controls as the primary Y axis: label text/font/size/color, limits (auto or manual).

---

## Subplot spacing

When the chart has more than one subplot, two sliders in the Axes tab control the spacing between panels:

| Control | Description |
|---------|-------------|
| **H space** | Vertical gap between rows of subplots (height fraction) |
| **W space** | Horizontal gap between columns of subplots (width fraction) |
