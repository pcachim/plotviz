# Advanced

The **Advanced** tab provides two tools for generating data without loading a file: the **Function Generator** and the **Data Table**.

---

## Function Generator

The function generator evaluates a mathematical expression over a range of X values and adds the result as a new dataset.

### Controls

| Control | Description |
|---------|-------------|
| **f(x)** | Python/NumPy expression — `x` is the independent variable array |
| **X min** | Start of the X range |
| **X max** | End of the X range |
| **N points** | Number of evenly spaced points in the range |
| **X col name** | Column name for the X dataset |
| **Y col name** | Column name for the generated Y dataset |

### Expression syntax

The expression field accepts any valid NumPy expression. The variable `x` is a NumPy array. Common functions available without a prefix:

```
sin(x)          cos(x)          tan(x)
exp(x)          log(x)          log10(x)
sqrt(x)         abs(x)          sign(x)
pi              e
```

Examples:

```
sin(x) * exp(-0.1 * x)
x**2 - 3*x + 2
log(x + 1) / (1 + cos(x))
```

### Workflow

1. Enter an expression in the **f(x)** field.
2. Set the X range and number of points.
3. Name the X and Y columns.
4. Click **Generate** — the columns appear in the Datasets list and can be assigned to series in the Data tab.

Clicking **Generate** again with the same column names replaces the previous data.

---

## Data Table

The data table provides a manual spreadsheet-style entry grid for small datasets.

### Creating a table

1. Set the **Cols** and **Rows** spinboxes.
2. Click **New** to create a blank table.
3. Click any cell and type to enter values.
4. Double-click a column header to rename it.

### Editing

| Button | Action |
|--------|--------|
| **＋R** | Add a row at the bottom |
| **－R** | Delete selected rows (or the last row if none selected) |
| **＋C** | Add a column on the right |
| **－C** | Delete the rightmost column |
| **🗑** | Clear all cell contents |

### Importing data

- **📋 (Paste)** — paste tab- or comma-separated text from the clipboard directly into the table.
- **📥 Load** — open a CSV or Excel file; its contents fill the table.

### Exporting

- **📤 CSV** — copies the entire table as CSV text to the clipboard, ready to paste into another application.

### Using the table data

Click **Apply to chart** (or the equivalent generate button depending on the UI layout) to load the table's columns into the Datasets list. They become available in the series table X/Y dropdowns just like data loaded from a file.

Column names are taken from the table headers. Values that cannot be parsed as numbers are treated as categorical strings.
