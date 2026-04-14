# Python Export Bundle

The **Python Export Bundle** feature converts any plotviz chart into a self-contained Python project — a ZIP archive (`.pvizx`) that includes a standalone matplotlib script and the chart's data as CSV files. The exported script has no dependency on plotviz and can be run, shared, and modified in any Python environment.

---

## Exporting

### Save to file

Go to **File → Export Python Bundle (.pvizx)…** (or use the corresponding menu shortcut).

A save dialog appears with a suggested filename based on the current chart title. Choose a location and click **Save**.

After the export completes, a confirmation message shows the full file path. The bundle can be extracted and run immediately:

```bash
unzip mychart.pvizx -d mychart
cd mychart
python plot.py
```

### Send directly to Code Runner

Use **Tools → Code Runner from chart** (or the **▶ Open in Code Runner** button in the [Seaborn Explorer](seaborn-explorer.md)) to skip the save dialog entirely. plotviz writes the bundle to a temporary location and opens it in the [Python Code Runner](code-runner.md) so you can inspect and edit the generated script right away.

---

## Bundle contents

A `.pvizx` file is a standard ZIP archive with the following structure:

```
mychart.pvizx
├── plot.py          # Standalone matplotlib script
├── README.md        # Quick-start instructions
├── pyproject.toml   # Optional: dependency declaration
└── data/
    ├── data.csv     # All columns (when they share the same length)
    │   — or —
    ├── column1.csv  # One CSV per column (when lengths differ)
    └── column2.csv
```

### plot.py

The main script is completely standalone — it imports only standard scientific Python packages and reads its data from the `data/` folder relative to its own location. It faithfully reproduces:

- All chart types and subplot layouts
- Axis labels, limits, scales, and tick formatting
- Series colors, line widths, markers, and fill styles
- Curve fits with optional confidence and prediction bands
- Title, legend, grid, and figure size

### data/

Only the columns actually assigned to series in the chart are exported. If all exported columns share the same row count, they are written to a single `data/data.csv`. If they differ in length, each column gets its own CSV file (e.g. `data/pressure.csv`) to avoid NaN padding.

### pyproject.toml

A minimal `pyproject.toml` listing the required packages (`matplotlib`, `numpy`, `pandas`, `scipy`) for use with tools like `uv` or `pip`.

---

## Running the exported script

Requirements (installed automatically if using `pyproject.toml`):

```bash
pip install matplotlib numpy pandas scipy
```

Then run:

```bash
python plot.py
```

The chart is displayed in a matplotlib window. To save it instead, call `plt.savefig('output.png', dpi=300)` at the end of the script.

---

## Opening a .pvizx bundle

You can re-open any `.pvizx` file in the [Python Code Runner](code-runner.md) to edit the generated script interactively:

1. Open the Code Runner: **Tools → Python Code Runner…**
2. Click **📦 Load .pvizx…** and select the bundle.
3. plotviz extracts the archive, loads `plot.py` into the editor, and runs it automatically.

You can also double-click a `.pvizx` file in Finder (macOS) or Explorer (Windows) to open it directly in the Code Runner, if plotviz is set as the default application for that file type.

---

## Supported chart types

All 22 plotviz chart types are supported in the Python export, including:

Line, Scatter, Step, Area, Bar, Stem, Error Bar, Histogram, Boxplot, Violin, Pie, Polar, Radar, Heatmap, Contour, Tricontour, 3D Surface, ECDF, 2D Histogram, Hexbin, Quiver, Barbs, Streamplot

Seaborn charts created in the [Seaborn Explorer](seaborn-explorer.md) can be exported via the **🐍 Generate Python Code** or **▶ Open in Code Runner** buttons in that dialog.

---

## Notes

- The exported script uses absolute file paths resolved relative to `plot.py`, so keep `plot.py` and the `data/` folder together.
- plotviz-specific features like drag-and-drop annotations and the manual data table are reproduced in the script as static data.
- The `.pvizx` extension is not a standard zip alias on all platforms — use an explicit `unzip` command or a ZIP tool if double-clicking does not extract it outside of plotviz.
