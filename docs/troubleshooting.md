# Troubleshooting

The messages plotviz shows when something cannot be done, what usually causes them and what to do. They are quoted as the app writes them; the words in *italics* stand for a number or a name.

---

## Loading data

| Message or problem | Cause and what to do |
|--------------------|----------------------|
| **Select at least one column to import.** | Every column was unticked in the import dialog. Tick the ones you want |
| **File no longer exists** (from **Open Recent**) | The chart file was moved, renamed or deleted. Open it with **Open Chart…** from where it is now |
| A date column is read as text or as numbers | Only a column in which *every* value looks like a date is read as dates. See [Date and time columns](datasets.md#date-and-time-columns) for the formats and the **Day first** option |

## Generate

| Message or problem | Cause and what to do |
|--------------------|----------------------|
| **x_min must be less than x_max** | The start of the range is not below its end. For *logspace* the two numbers are exponents (10^start to 10^stop) |
| **geomspace requires start and stop > 0** | A geometric range cannot contain 0 or a negative number |
| **No source column selected** | The input is set to *column* but no dataset is loaded or chosen |
| **name '…' is not defined** | The expression uses a name that does not exist. It can use the variable you named (`x` by default), `pi`, `e` and the NumPy functions (`sin`, `exp`, `log`, `sqrt`, …) |
| **Clipboard is empty** | The clipboard button of the Table found no text to paste |

## Transform and Statistics

| Message or problem | Cause and what to do |
|--------------------|----------------------|
| **No y series selected** | Choose the series in the **y** list |
| **x has** *N* **points but y has** *M* | The x and the y series have different lengths. Pick two columns from the same file, or **(none: use index)** for x |
| **this operation needs an x series** | Resampling, cropping, sorting and aligning need an x. Choose it, or use another operation |
| **window (***N***) is longer than the series (***M* **points)** | The window of the filter is bigger than the data. Make it smaller |
| **polynomial order (***p***) must be lower than the window (***w***)** | For Savitzky-Golay, raise the window or lower the order |
| **the series has NaN values; remove or interpolate them first** | The FFT, the Butterworth filter and Decimate cannot work through gaps. Apply **Interpolate NaN** (or **Remove NaN**) first |
| **x must be increasing** | The Butterworth filter and the FFT need x to grow. Apply **Sort by x** first |
| **cutoff must be between 0 and** *…* **(half the sampling rate)** | The cutoff of the Butterworth filter is in cycles per x unit, and must be below half of the sampling rate. See [Transform](transform.md) |
| **choose the series whose x values to use** | **Align to another x** needs the series that gives the new x |
| **log return needs every value to be positive** | A logarithm of 0 or of a negative number does not exist. Use **Percent change**, or remove those points |
| **Live is paused for** *N* **points: click Preview.** | The series is longer than 50,000 points, so the preview does not redraw by itself. Click **Preview**; **Apply** is not affected |
| **Changed: click Preview to update.** | **Live** is off. Click **Preview**, or tick **Live** |

## Curve fitting

| Message or problem | Cause and what to do |
|--------------------|----------------------|
| **Add at least one series in the Data tab first.** | There is nothing to fit yet. Add a series in **Plots → Plot** |
| **Could not fit** *model*: … | The model does not suit the data or did not converge. Try another model, fit only the part of x where the model applies, or give start values; see [Curves and Fitting](curves.md) |
| **The series this curve was fitted to is no longer in the table.** | The fit was made on a series that you have since removed or changed. Select a series that is still in the table |

## Charts

| Message or problem | Cause and what to do |
|--------------------|----------------------|
| Nothing is drawn for a series | Check that its **X** and **Y** columns are set in the series table and that the chart type fits the data (a Heatmap needs a Z column, an Errorbar an error column) |
| The export looks different from the preview | It should not: the file is made from the same figure. Check **Layout & Style → Figure** for the size and [Export Image](export.md) for the resolution |
| **Undo** does not undo a zoom | Zooming and panning with the toolbar are not undo steps; see [Undo and redo](shortcuts.md#undo-and-redo). Use the **Home** button of the toolbar |

## Seaborn Explorer

| Message or problem | Cause and what to do |
|--------------------|----------------------|
| **seaborn is not installed.** | Install it (`pip install seaborn`). The binary releases include it |
| **No data loaded.** | Load a dataset in the main window first |
| **Select X (category) and Y (numeric) columns for Strip.** | Strip, Swarm and Catplot need a category on X and numbers on Y |
| **Regression requires numeric X and Y columns.** | A text column was chosen for X or Y |
| **Heatmap needs >= 2 numeric columns.** | Select at least two columns in the **Columns** list (also for Pairplot) |
| **Render error (***type***):** … | The text that follows is the error of seaborn itself, for instance a combination of options that the type does not accept |

## Python Code Runner

| Message or problem | Cause and what to do |
|--------------------|----------------------|
| **Code ran successfully but produced no figure.** | The code did not create a figure. Call `plt.subplots()` or `plt.figure()`, or a seaborn figure-level function |
| The **Runtime Error** panel | It shows the traceback of your code; the last line is the error and the one above it the line that caused it. **Copy** puts it on the clipboard |

## Digitize Image

| Message or problem | Cause and what to do |
|--------------------|----------------------|
| **Set the X point 1.** / **Type the value of …** | The calibration is not complete. Each axis needs two points marked on the image and their values typed; in the rotated mode, three points with both values |
| **… the two reference points are at the same position** / **the two reference values are equal** | The two points of an axis must be apart, with different values. Mark them near the two ends of the axis |
| **a logarithmic axis needs positive reference values** | Use values above zero for a logarithmic axis, or untick the option |
| **the reference points are on one line** | In the rotated mode the three points must not be on a straight line; spread them over the plot |
| **No pixel of that colour was found** | Raise the tolerance (±), or pick the colour again by clicking on the middle of the curve |
| Trace adds points that are not on the curve | The legend, the grid or another curve has a similar colour. Lower the tolerance, or remove the extra points with a right-click |
| The values are a little off | The picture is small: a point is read to a pixel. Use a larger version of the figure and zoom in before clicking |

## Files

| Message or problem | Cause and what to do |
|--------------------|----------------------|
| **None of the datasets comes from a file that can be read again** | Reload needs the file and the options kept at import. Columns made by Generate or Transform, and charts saved by an older version, do not have them: import the file again once |
| **Some columns could not be read again** | The file was moved or deleted, or a column is no longer in it. The columns that failed keep the values they had; put the file back or import it again |
| **plotviz did not close properly last time** | An automatic copy of the chart was found at start-up. Restore opens it with its changes unsaved; see [File Formats](file-formats.md#automatic-copy-and-recovery) |
| **No settings.json in archive.** | The file is not a plotviz chart or template. Chart and template files are zip archives with a `settings.json` inside; see [File Formats](file-formats.md) |
| **Open error** / **Save error** / **Export error** | The text after the title is the reason given by the system: a file that is open in another program, a folder without write permission, a disk that is full |
