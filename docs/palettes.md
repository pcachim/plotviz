# Color Palettes

A color palette is an ordered list of 16 colors used as the default cycle for series in a chart. When a new series is added, the next color in the active palette is assigned automatically.

---

## Selecting a palette

In the **Layout & Style** tab, choose a palette from the **Color palette** dropdown. The chart updates immediately, reassigning colors to all series that do not have a locked color.

---

## Built-in palettes

plotviz ships with 11 palettes:

| Name | Character |
|------|-----------|
| **Matplotlib** | The standard matplotlib default color cycle — blue, orange, green, red, purple, brown, pink, grey, yellow-green, cyan |
| **Pastel** | Soft, desaturated tones — baby blue, peach, mint, rose, periwinkle |
| **Bold** | High-contrast vivid colors — red, green, blue, orange, purple, cyan, magenta, lime |
| **Earth** | Warm browns, greens and greys — saddle brown, olive, khaki, forest green |
| **Ocean** | Deep cool blues through warm orange — navy, indigo, purple, magenta, coral, amber |
| **Warm** | Reds, oranges and yellows — crimson, tangerine, gold, coral, amber |
| **Cool** | Blues, greens and purples — steel blue, teal, sage, lavender, sky |
| **Colorblind** | Optimized for the most common forms of color vision deficiency (deuteranopia, protanopia) |
| **Nature** | Muted greens, blues and earthy tones — teal, burnt orange, coral, dark blue |
| **Publication** | Black + strong, distinct hues suitable for print — black, red, blue, green, purple, orange |
| **Grayscale** | Black through white in even steps — for monochrome print or accessibility |

---

## Custom palettes

Palettes work like colour schemes: the built-in ones are read-only, and your own are files. Every `.pvizp` in the **palettes folder** is loaded when plotviz starts. Its location is shown in Preferences (**Colour palettes**), next to a button that opens it; on macOS it is `~/Library/Application Support/plotviz/palettes/`.

### Creating or editing a palette

1. In the **Layout & Style** tab, click **Edit palette…**. It opens with the colours of the active palette; **Load from** starts from another one.
2. Give it a name and click each of the 16 swatches to set the colours.
3. Click **Save & apply**. The palette becomes the active one.

Opening the editor on one of your own palettes edits it in place. Built-in names cannot be replaced.

A **\*** after a palette's name in the dropdown means it is not in the palettes folder, so it will not be there next time. A new palette starts that way; saving it into the folder removes the *.

### Sharing and keeping palettes

**Save:** click **Save** under *Colour palette*. The dialog opens in the palettes folder; you can save anywhere else too, but a file outside the folder keeps its * and is not loaded at start-up. Built-in palettes cannot be saved, since they are always there. To delete a palette, delete its file.

**Load:** click **Load** and choose a single `.pvizp` file (for instance one from outside the folder). With one palette in the file you are asked whether to apply it.

A chart file (`.pviz`) carries its active palette when it is one of yours, so the chart opens with the same colours.

### Re-applying the palette

Series whose colour you set by hand keep it when you change palette or scheme. **↺ Re-apply palette** (under the Edit / Load / Save buttons) gives every series its palette colour again, those included.

See [File Formats](file-formats.md) for the `.pvizp` format specification.

---

## Color locking

By default, switching palettes reassigns all series colors to match the new palette. To preserve a specific series' color across palette switches, tick **Lock color** in the **Series** tab for that series.

Locked colors are shown with a lock icon in the series color swatch. They are never modified by palette changes, but can still be changed manually by clicking the swatch.

---

## Recent colors in the color picker

The color picker dialog shows a **Recent colors** row above the Custom colors section. It stores the last 8 colors you selected (across all color pickers in the app) and persists them between sessions. Click any recent swatch to instantly reuse that color.
