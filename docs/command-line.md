# Command Line

`plotviz render` draws saved charts to image files without opening the program. It is meant for scripts: redo every figure of a paper after the data changed, or turn a folder of `.pviz` files into PDFs, with one command.

```bash
plotviz render chart.pviz -o figure.pdf
```

The chart is drawn by the same code as **File → Export Image**, so the file is the one that the program would write for the same format, resolution and size. Nothing is shown on the screen and nothing is written to the settings of the program.

## Examples

```bash
# one chart, the format is taken from the name of the file
plotviz render chart.pviz -o figure.svg

# many charts, into a folder, as 600 dpi PNG files (chart.png, other.png, …)
plotviz render chart.pviz other.pviz --outdir figures --format png --dpi 600

# a column width of 8.5 cm, in the style of a template, after reading the data files again
plotviz render chart.pviz -o fig1.pdf --width 8.5 --height 6 --template journal.pvizt --reload

# every subplot also in its own file: fig_1.png, fig_2.png, …
plotviz render chart.pviz -o fig.png --each-subplot
```

## Options

| Option | Meaning |
|--------|---------|
| `CHART …` | One or more `.pviz` files |
| `-o`, `--output FILE` | The image to write (one chart only). The extension gives the format |
| `--outdir DIR` | The folder for the images, created if needed. Each file is named after its chart. Without `-o` and `--outdir` the images go next to the charts |
| `-f`, `--format` | `png`, `svg`, `pdf`, `jpeg`, `tiff` or `eps`. Without it the format comes from `-o`, and otherwise it is `png` |
| `--dpi N` | The resolution of raster images (300 by default, whatever the chart or the program last used) |
| `--width W`, `--height H` | The size of the figure; the chart's own size where not given |
| `--unit` | `cm` (default), `mm` or `in`, for `--width` and `--height` |
| `--each-subplot` | Also write every subplot to its own file, as in the export dialog |
| `--reload` | Read the data files that the columns came from again before drawing; see [Reloading data files](datasets.md#reloading-data-files) |
| `--template FILE` | Apply the style of a `.pvizt` template to every chart before drawing |
| `-q`, `--quiet` | Print only the errors |

## Result

Each chart that is drawn is reported as `chart.pviz -> figure.png`. The command ends with status **0** when every chart was drawn, **1** when at least one could not be (the others are still drawn, and each failure is written to the error output with the name of the chart), and **2** when the command itself is wrong (two charts with `-o`, an unknown format, a template that does not exist).

With `--reload`, a data file that has moved, was deleted or lost a column stops that chart: it is not drawn, because the figure would show old data without saying so.

## Running it

* **Installed with pip** (`pip install plotviz`): the command `plotviz` is available in the terminal.
* **From the source:** `uv run plotviz render …`, or `python src/plotviz/main.py render …`.
* **The macOS application:** run the program inside the bundle, `/Applications/plotviz.app/Contents/MacOS/plotviz render …`. See the limitations below.
* **The Windows application:** it has no console and prints nothing, so it is not suited to scripts. Use the pip or the source installation on Windows.

## Known limitations

* **Windows, packaged program.** The Windows build is a program without a console, so `plotviz render` run from it writes the images but shows no messages and does not return its status to the shell: a script cannot tell whether it worked. Use the pip or the source installation for scripts.
* **macOS, packaged program.** Running `render` through the executable inside `plotviz.app` is expected to work but has not been tested on a built application. The pip and source installations are the tested ones.
* **Only charts.** The input is a `.pviz` chart. Templates, colour schemes, palette bundles and Python bundles are not drawn by themselves (a template is applied with `--template`).
* **No other overrides.** The format, resolution and size can be changed from the command line, and a template can be applied; titles, labels, colours, series and data cannot. For another look, change the chart (or the template) in the program and save it.
* **The resolution is not the chart's.** The default is 300 dpi whatever the chart or the program used last; give `--dpi` for another value. Vector formats (`pdf`, `svg`, `eps`) do not depend on it, except for the parts of a chart that are images.
* **Data are those in the file.** A `.pviz` file carries its data. `--reload` reads the data files again, but only for columns that were imported from a file by a version of plotviz that keeps where they came from (see [Reloading data files](datasets.md#reloading-data-files)); columns made by Generate or Transform, and charts saved by older versions, keep the values saved in the file.
* **Fonts and palettes of the machine.** The chart is drawn with the fonts installed where the command runs (a font that is missing is replaced by the default) and with the colour palettes and schemes of the user who runs it. Two machines can give slightly different images.
* **Drawn one after the other.** Several charts are drawn in a single run, one at a time. Starting the program takes a second or two, which is worth knowing when a script calls it once per chart.
* **No screen needed, but a display library is.** The command does not open a window and works on a machine without a screen (a server, a continuous integration job), but the Qt libraries that plotviz depends on must be installed. On a minimal Linux system they may need extra system packages; the error message of Qt names the one that is missing.
* **Not covered by the command:** the Seaborn Explorer and Python Code Runner (they are not part of the chart), and the automatic copy and recovery of charts (nothing is written to the recovery folder).
