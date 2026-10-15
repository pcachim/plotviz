# Keyboard Shortcuts

## Global shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + N` | New chart |
| `Ctrl + O` | Open chart |
| `Ctrl + S` | Save chart (rewrites the open file; asks where the first time) |
| `Ctrl + Shift + S` | Save chart as… |
| `Ctrl + L` | Load data |
| `Ctrl + E` | Export image |
| `Ctrl + Shift + E` | Export Python bundle |
| `Ctrl + Z` | Undo |
| `Ctrl + Y` or `Ctrl + Shift + Z` | Redo |
| `Ctrl + Shift + C` | Copy the chart as an image (`Ctrl + C` keeps copying text in fields and tables) |
| `Ctrl + ,` (macOS) / `Ctrl + Alt + S` | Preferences / Settings |
| `Ctrl + Shift + B` | Seaborn Explorer |
| `Ctrl + Shift + P` | Python Code Runner |
| `Ctrl + Shift + R` | Code Runner from the current chart |

## Tab navigation (View menu)

The **View** menu lists the three tabs as checkable items; the active one is ticked.

| Menu item | Tab |
|-----------|-----|
| View → Data | Datasets and the Generate page |
| View → Layout & Style | Figure size, margins, title, subplot grid, colour scheme, palette |
| View → Plots | Per-subplot settings: Plot, Curves, Axes, Annotations |

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

## Annotation mode shortcuts

While in the Annotations tab:

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
