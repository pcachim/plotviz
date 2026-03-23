# Annotations

The **Annotations** tab manages everything that sits above and around the data: subplot titles, legend configuration, and free-form text, arrow, and image annotations placed directly on the chart.

When the chart has more than one subplot, the **Subplot** selector at the top of the tab switches context. All controls — titles, legend, annotation visibility — apply to the currently selected subplot.

---

## Subplot title

The subplot title section is only visible when the chart has more than one panel. For a single-panel chart, the global chart title is set in the **Style** tab.

| Control | Description |
|---------|-------------|
| **Show title** | Checkbox — toggle title visibility |
| **Text field** | Title text for this subplot |
| **Font / Size** | Typography |
| **Color** | Title text color |

---

## Legend

### Visibility and position

| Control | Description |
|---------|-------------|
| **Show legend** | Checkbox — toggle legend on/off for this subplot |
| **Position** | Placement preset: best, upper right, upper left, upper center, lower right, lower left, lower center, center right, center left, center, manual |
| **X / Y** | Fine position adjustment as a figure fraction (0.0–1.5). Active for all positions except **best**. |

When **Position** is set to anything other than **best**, the X and Y spinboxes act as `bbox_to_anchor` coordinates — the selected corner of the legend box is pinned to that point. For example, "upper right" at X=0.98, Y=0.98 places the top-right corner of the legend near the top-right of the axes.

When **Position** is **best**, matplotlib automatically finds the location with the least overlap with the data.

### Style

| Control | Description |
|---------|-------------|
| **Font sz** | Font size for legend entries (pt) |
| **Cols** | Number of columns in the legend (1–8) |
| **Frame** | Checkbox — show the legend box border |
| **Text color** | Color of legend label text |
| **BG color** | Background fill color of the legend box |
| **α** | Background opacity (0.0–1.0) |
| **Edge color** | Border color of the legend box |

---

## Annotation visibility

The **Show annotations on this subplot** checkbox hides or shows all text, arrow, and image annotations on the selected subplot without deleting them.

---

## Placing annotations

Four mode buttons select the current annotation tool:

| Button | Mode |
|--------|------|
| 🖱 Normal/Drag | Selection and drag mode — click an annotation to select it, drag to move |
| 📝 Text | Click anywhere on the chart to place a text label |
| ➡ Arrow | Click the start point, then click the end point to draw an arrow |
| 🖼 Image | Opens a file picker; click on the chart to place the image |

### Text annotations

After clicking in text mode, a dialog opens to enter the label text. The annotation is placed at the clicked coordinates.

### Arrow annotations

Click once to set the arrow tail (start), then click again to set the arrowhead (end). A text label can be attached to the arrow tail.

### Image annotations

Select an image file (PNG, JPEG, etc.), then click on the chart to place it. Use the **Img zoom** spinbox to set the initial display size as a fraction of the figure.

### Manual coordinate placement

Enter exact data-coordinate values in the **X** and **Y** fields and click **📍 Place** to position the next text annotation precisely.

---

## Annotation style

Controls in the **Style for new annotations** section set the default appearance applied to annotations placed after the change. They do not retroactively change existing annotations.

| Control | Description |
|---------|-------------|
| **Font / Sz** | Font family and size |
| **Font color** | Text color |
| **BG / α** | Background fill color and opacity |
| **Border** | Box border color |

---

## Managing annotations

The **Annotations** list at the bottom of the tab shows all annotations on the current subplot. Each entry shows the type icon and either the label text or coordinates.

**Double-click** any entry to open an edit dialog where you can change the text, position, font, colors, and border of that annotation.

The **✏️ Edit selected** and **🗑 Delete selected** buttons provide the same actions via keyboard/click.

**↩ Undo last** removes the most recently placed annotation.

**🗑 Clear all** removes every annotation from the current subplot.
