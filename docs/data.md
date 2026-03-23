# Data

## Loading files

Open the **Data** tab and click **Browse Files** to load one or more data files. Supported formats:

| Format | Extensions | Notes |
|--------|-----------|-------|
| CSV | `.csv` | Comma-separated, auto-detected header |
| Excel | `.xlsx`, `.xls` | First sheet loaded |
| JSON | `.json` | Array of objects or column-oriented dict |
| Plain text | `.txt` | Whitespace-separated columns |

All columns from the file are imported. Numeric columns become float arrays; text columns are treated as categorical. Column names are taken from the first row.

You can load multiple files in one session — each file's columns are pooled into the shared column list and available in all series rows.

### Removing datasets

Select one or more entries in the **Datasets** list and click **Remove selected**. Any series that reference removed columns will show empty dropdowns but are not deleted from the table.

### Inspecting columns

Select a column (or multiple columns) in the Datasets list and click **Inspect values** to see a summary: count, min, max, mean, and a preview of the first values.

---

## The series table

The series table in the **Data** tab maps data columns to visual series. Each row is one plotted series.

| Column | Purpose |
|--------|---------|
| **X** | Column used as the horizontal axis values |
| **Y** | Column used as the vertical axis values |
| **Label** | Text shown in the chart legend |
| **Type** | Chart type for this series (Line, Scatter, Bar, …) |
| **Plot #** | Which subplot panel this series appears in (1-based) |
| **Y2** | Checkbox — plots this series on the secondary Y axis |

### Adding and removing series

- **+ Add series** — appends a new row with empty column selections.
- **✕** button on a row — removes that series.

### Mixing chart types

Each row in the series table has its own **Type** dropdown, so you can mix chart types within the same panel — for example, a Line series and a Scatter series sharing the same axes.

Types that take over the whole chart (Histogram, Pie, Heatmap, etc.) cannot be mixed with other types in the same subplot.

### Secondary Y axis (Y2)

Tick the **Y2** checkbox on any series row to plot it against a second Y axis on the right side of the chart. The Y2 axis label is set in the **Axes** tab.

### Z column and error column

Below the series table are two extra dropdowns:

- **Z** — used by Heatmap, Hist2D, Hexbin, Contour, and Bubble charts as the third data dimension.
- **Error** — used by the Errorbar chart as the error/uncertainty values.

---

## Chart type selection

The **Chart type** dropdown at the top of the Data tab sets the default type for the entire chart. Individual series can override this with their own Type cell.

See [Chart Types](chart-types.md) for a full description of every chart type and its options.
