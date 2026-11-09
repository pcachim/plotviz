# Changelog

All notable changes to plotviz. Versions are named `YYYY.MM.n`; each release has a matching tag `vYYYY.MM.n`. Newest first.

To cite a specific version, use its DOI on the [Zenodo](https://doi.org/10.5281/zenodo.23378412) page (see [Citing plotviz](docs/citing.md)).

## 2026.11.9 — 2026-11-09

### Added
- **Licenses:** `THIRD-PARTY-NOTICES.md` is shipped with the program; a Licenses page in the documentation and in the help window; a *Licenses…* item in the Help menu and a button in *About*.
- **Data:** reload data files that changed on disk.
- **Recovery:** automatic copy of the chart, with restore after a crash; a save prompt when closing with unsaved changes.
- **Tools → Digitize Image:** read the values of a chart that exists only as a picture. Calibration from reference points (three or four points, so rotated or tilted pictures work), points marked by hand or by colour, a magnifier, draggable points, and several curves per image, each added to the data as `<name>_x` and `<name>_y` columns.
- **Command line:** `plotviz render` draws saved charts to image files without opening the program.
- **Documentation:** Digitize Image, reload and recovery, and the command line (with its known limitations), in the README, index, shortcuts, glossary and troubleshooting pages; a *Citing plotviz* page, a *Referencing* section in the README and a `CITATION.cff`.

### Changed
- Help window: spacing between blocks, padded tables, monospaced code and a comfortable reading width.

## 2026.11.7 — 2026-11-05

### Added
- **Curves:** *Add to chart…* puts the equation and parameters of a fit on the chart as an annotation.
- **Documentation:** compares *Regression* in the Seaborn Explorer with the curve fit in Curves; figures for the Seaborn Explorer, the Code Runner and the Transform pages (calculus, scale/baseline, cleaning, rolling statistics); worked examples, export page, troubleshooting, glossary and plot options.

### Changed
- Documentation refreshed: outdated claims corrected; the Z axis, 3D viewpoint, menus and math text are now documented.

### Fixed
- Tests and documentation scripts no longer touch the user's real settings.

## 2026.11.6 — 2026-11-05

### Added
- **Help:** in-app documentation window (F1); the online version is its own menu entry.
- **Documentation:** one figure per chart type; the guide is organised by the tabs of the app (Data, Layout & Style, Plots, Tools).

### Fixed
- Tests: the "preview changes nothing" test no longer depends on timing.

## 2026.11.5 — 2026-11-04

### Added
- **Data and curve fitting:** dates in curves, per-subplot canvas, and a comparison of fits.
- **Transform:** preview with a mini plot and a *Live* option.
- **Generate:** the same preview (shared preview panel), also for `z = f(x, y)` and `(u, v) = f(x, y)`.

### Fixed
- Inner tabs stay light in dark mode.

## 2026.11.4 — 2026-11-03

### Added
- **Data tab:** *Transform* and *Statistics* pages and date columns.

### Changed
- Tab and typing cleanup in the Data tab.

## 2026.10.16 — 2026-10-15

### Added
- Colour schemes: eight distinct schemes replace the light ones.
- **Canvas & Grid** moved to its own tab under Plots.

### Changed
- Layout & Style and Axes: collapsible sections and a clearer order.

## 2026.10.15 — 2026-10-15

### Added
- Open, Save and Export buttons in the top bar; *Open Recent*.
- Export dialog: copy to the clipboard as an alternative to saving, with an explanation, and the estimated file size shown beside the pixels.
- *Save* is a real save; new *Save Chart As*.
- Colour schemes apply as soon as they are chosen (no Apply button), also to the active subplot only; palette and scheme colours are shown beside their names.
- Margin mask outlines everything the margins place.

### Changed
- Interface restructured into three tabs, **Data**, **Layout & Style** and **Plots**, with a shared subplot selector; Data holds the generators.
- Margins and title position are stored as fractions of the figure; the figure size no longer follows the window; the preview page is drawn at its true scale.
- Colour schemes reach every chart type; text stays on the page.
- Generated scripts lay the chart out like the export.
- LaTeX typesetting is never used; exports ignore `text.usetex`.
- File menu labels drop the file extensions; *Help → Sample Charts* and *Sample Datasets* open an Open dialog.

### Fixed
- Margin spinboxes never exceed the figure (left < right, bottom < top).
- Crash on macOS when opening a chart, caused by matplotlib's busy cursor (`SafeNavigationToolbar`); Qt updated.

## 2026.10.14 — 2026-10-14

### Changed
- Licence changed to **GPL-3.0-or-later**; the notice ships with the binaries.
- Exported scripts match the live chart (alpha, histogram edge, layout).
- Silenced exceptions are logged; broad exception handlers narrowed.

### Fixed
- 2D histogram log norm, Excel fallback import, a Python 3.10 f-string syntax error, colorbar target and deprecation warnings.
- Polar and 3D cells in mosaic layouts.

### Internal
- CI: locked dependencies, ruff linting, mypy for `core/`, chart-type tests and `.pviz` round-trip tests.
- Large functions and tab builders split into focused methods and mixins; dead code removed; settings typed with `TypedDict`.

## 2026.06.2 — 2026-06-17

### Changed
- Improved annotation editing and several interface glitches.
- Figure-size unit conversions moved into `core.geometry`.

### Fixed
- Code Runner no longer opens a separate figure window for `plt.show()` (the exported script keeps it).

### Internal
- User interface and core separated; the main window split into focused mixins; headless Qt smoke tests.

## 2026.06.1 — 2026-06-16

### Fixed
- Annotations in *Export Image* and in the Python bundle.

## 1.5 – 2.7.4 — March to April 2026

The first releases, before the move to date-based version numbers: rapid growth of chart types, data handling and export options, the MkDocs documentation, and macOS and Windows builds produced by CI. Tags `v2.7.0` to `v2.7.4`.
