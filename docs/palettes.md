# Color Palettes

A color palette is an ordered list of 16 colors used as the default cycle for series in a chart. When a new series is added, the next color in the active palette is assigned automatically.

---

## Selecting a palette

In the **Chart** tab, choose a palette from the **Color palette** dropdown. The chart updates immediately, reassigning colors to all series that do not have a locked color.

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

You can create your own palettes and save them for reuse.

### Creating a custom palette

1. In the **Chart** tab, click **Edit palettes…** (or the palette management button).
2. Click **New palette** and give it a name.
3. Click each of the 16 color swatches to set the colors.
4. Click **Save**.

The custom palette appears in the palette dropdown and is saved to user preferences immediately.

### Sharing palettes

Custom palettes can be exported to a `.pvizp` file and imported on another machine.

**Export:** In the Chart tab, click **💾 Export palettes (.pvizp)**. All current custom palettes are saved to the file.

**Import:** Click **📂 Import palettes (.pvizp)**. The palettes from the file are merged into your current custom palette collection. Built-in palettes are not overwritten.

See [File Formats](file-formats.md) for the `.pvizp` format specification.

---

## Color locking

By default, switching palettes reassigns all series colors to match the new palette. To preserve a specific series' color across palette switches, tick **Lock color** in the **Series** tab for that series.

Locked colors are shown with a lock icon in the series color swatch. They are never modified by palette changes, but can still be changed manually by clicking the swatch.

---

## Recent colors in the color picker

The color picker dialog shows a **Recent colors** row above the Custom colors section. It stores the last 8 colors you selected (across all color pickers in the app) and persists them between sessions. Click any recent swatch to instantly reuse that color.
