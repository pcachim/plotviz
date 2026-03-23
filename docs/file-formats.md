# File Formats

plotviz uses four proprietary file formats, all of which are ZIP archives containing JSON metadata. They can be inspected or manipulated with any ZIP tool.

---

## .pviz — Chart project

A `.pviz` file is a complete saved chart. It contains:

| Entry | Contents |
|-------|---------|
| `settings.json` | All style, axis, and layout settings |
| `series.json` | Series table rows, subplot assignments, Z and error column selections |
| `data.json` | Dataset columns (all columns or used-only, depending on save choice) |
| `palette.json` | Custom palette definitions (if any custom palettes are active) |
| `images/` | Embedded image files referenced by image annotations |

### Saving

In the **Chart** tab, click the **Save Chart (.pviz)** option from the save dropdown. A dialog asks whether to save **Used series only** (keeps only the columns currently assigned in the series table) or **All columns** (preserves every loaded column for future reassignment). Used-only files are smaller; all-columns files are more portable.

### Loading

Select **Open Chart (.pviz)** from the open dropdown, or double-click a `.pviz` file in Finder/Explorer. The chart, all datasets, and all settings are restored exactly.

### Recent files

The last 12 opened `.pviz` files appear in the **Recent files** list in the Chart tab for quick access.

---

## .pvizt — Template

A `.pvizt` file saves all style and layout settings but contains no data. Use templates to apply a consistent visual style across multiple charts.

| Entry | Contents |
|-------|---------|
| `settings.json` | Style, axis, layout, and annotation defaults (`_file_type: "template"`) |

### Saving

Select **Save Template (.pvizt)** from the save dropdown.

### Loading

Select **Load Template (.pvizt)** from the open dropdown, or double-click a `.pvizt` file. The template's settings are applied to the current chart; existing data and series assignments are preserved.

---

## .pvizc — Color scheme

A `.pvizc` file is a minimal settings file containing only color-related keys: background, foreground, plot area, grid, title/label colors, border visibility, and palette name. It does not contain axis limits, figure size, data, or series assignments.

| Entry | Contents |
|-------|---------|
| `settings.json` | Color keys only (`_file_type: "color_scheme"`, `_scheme_name`) |

### Saving

In the **Chart** tab, Color Schemes section, click **💾 Save scheme…**, enter a name, and choose a location.

### Loading

Click **📂 Load scheme…** to open a `.pvizc` file. The scheme is registered in the Color Schemes dropdown for the session and you are asked whether to apply it immediately.

Double-clicking a `.pvizc` file in Finder/Explorer applies it to the current chart silently.

---

## .pvizp — Palette bundle

A `.pvizp` file exports your custom color palettes so they can be shared or used on another machine.

| Entry | Contents |
|-------|---------|
| `palettes.json` | All custom palette definitions (name → list of 16 hex colors) |

### Saving

In the **Chart** tab, click **💾 Export palettes (.pvizp)**.

### Loading

Click **📂 Import palettes (.pvizp)**. The palettes are merged into the current session and saved to user preferences so they persist across restarts.

Double-clicking a `.pvizp` file in Finder/Explorer imports and applies the palettes automatically.

---

## Internal structure

All four formats are standard ZIP archives. To inspect a file:

```bash
# macOS / Linux
unzip -p myfile.pviz settings.json | python3 -m json.tool

# Windows PowerShell
Expand-Archive myfile.pviz -DestinationPath .\extracted\
```

The `_app`, `_version`, and `_file_type` keys in `settings.json` identify the format. plotviz reads files with any version and applies safe defaults for keys that are missing, so older files remain compatible with newer releases.
