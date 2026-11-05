# Keyboard Shortcuts

## Global shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + N` | New chart |
| `Ctrl + O` | Open chart |
| `Ctrl + S` | Save chart (rewrites the open file; asks where the first time) |
| `Ctrl + Shift + S` | Save chart as… |
| `Ctrl + L` | Load data |
| `Ctrl + Shift + L` | Reload the data files |
| `Ctrl + E` | Export image |
| `Ctrl + Shift + E` | Export Python bundle |
| `Ctrl + Z` | Undo |
| `Ctrl + Y` or `Ctrl + Shift + Z` | Redo |
| `Ctrl + Shift + C` | Copy the chart as an image (`Ctrl + C` keeps copying text in fields and tables) |
| `Ctrl + ,` (macOS) / `Ctrl + Alt + S` | Preferences / Settings |
| `Ctrl + Shift + B` | Seaborn Explorer |
| `Ctrl + Shift + P` | Python Code Runner |
| `Ctrl + Shift + R` | Code Runner from the current chart |
| `Ctrl + Shift + D` | Digitize Image |
| `F1` | Documentation (opens in its own window; **Help → Documentation Online** opens the website) |

## Tab navigation (View menu)

The **View** menu lists the three tabs as checkable items; the active one is ticked.

| Menu item | Tab |
|-----------|-----|
| View → Data | Datasets, Generate, Statistics and Transform pages |
| View → Layout & Style | Figure size, margins, title, subplot grid, colour scheme, palette |
| View → Plots | Per-subplot settings: Plot, Curves, Axes, Canvas & Grid, Legend & Notes |

## Undo and redo

**Edit → Undo** and **Redo** (and the two buttons in the top bar) step through up to 50 changes. Hover over a button to see what it will undo or redo ("Undo: Apply fit"), and the status bar says what was undone.

A step is recorded about half a second after the last change, so a burst of edits (typing, dragging a spin box) is one step. Everything that makes up the chart is in it:

- every setting, per subplot, including the style of each curve;
- the datasets (loading, removing, **Generate**, **Transform**, the data table);
- the series table and the fits (with their bands, and whether each is shown);
- the annotations (adding, moving, editing, deleting).

After an undo you stay on the same subplot and curve, and the lists keep their selection. Undo does not cover zooming or panning with the toolbar, the open/save state of the file, or the palettes you saved to disk.

The history starts again when you open a file or start a new chart. The datasets in the history are not copied: a step only holds the arrays that changed, so a long history does not multiply the memory used by large data.

## Canvas (matplotlib toolbar)

The toolbar above the chart canvas provides standard matplotlib navigation:

| Button | Action |
|--------|--------|
| 🏠 Home | Reset to the original view |
| ◀ Back | Go to the previous view |
| ▶ Forward | Go to the next view |
| ✛ Pan | Click and drag to pan; right-drag to zoom |
| 🔍 Zoom | Draw a rectangle to zoom in |
| ⚙ Subplots | Adjust subplot spacing (matplotlib built-in) |
| 💾 Save | Save the figure via matplotlib's own dialog |

### Reading values from the chart

Move the pointer close to a point of a curve or a scatter plot (within about 14 pixels) and the status bar at the bottom of the window shows the series and the **x** and **y** of that point, not those of the pointer: `Quadratic · x = 4.5, y = 6.1`. On a date axis the value is written as a date. The text disappears when the pointer moves away from the points. Clicking on an empty part of the chart still writes the coordinates of the click.

## Annotation mode shortcuts

While in the Legend & Notes tab:

| Key | Action |
|-----|--------|
| `Esc` | Exit the current annotation placement mode and return to Normal/Drag |

## Color picker

| Key | Action |
|-----|--------|
| `Enter` | Confirm the selected color (OK) |
| `Esc` | Cancel and close the color picker |

## Series click-to-select

Click directly on a plotted series in the canvas to jump to the **Series** tab with that series pre-selected. This works for line, scatter, bar, and most other series types.
