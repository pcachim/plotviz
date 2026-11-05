# Licenses

## plotviz

plotviz is free software, licensed under the **GNU General Public License v3.0 or later**. You may use, study, share and change it under the terms of that licence. The text is in `LICENSE.md`, and the source code of the version you are running is at the address in `SOURCE.md` (both are in the application folder and in the [repository](https://github.com/pcachim/plotviz)). Each release has a matching tag, `vYYYY.MM.n`.

The licence of the program applies to the program. The charts you make with it, and your data, are yours.

## What a release contains

The macOS and Windows programs contain, besides plotviz, the Python runtime and the open-source packages below, each under its own licence. Most are permissive (BSD, MIT, Apache): they allow use and redistribution provided that the copyright notice and the text of the licence are kept, which is what the file **`THIRD-PARTY-NOTICES.md`** is for. It comes with the program and is also in the [repository](https://github.com/pcachim/plotviz/blob/main/THIRD-PARTY-NOTICES.md), with the version of each package and the full text of each licence.

<!-- licenses:start (written by util/make_third_party_notices.py) -->

| Package | Licence |
|---------|---------|
| contourpy | BSD-3-Clause |
| cycler | BSD-3-Clause |
| et_xmlfile | MIT |
| fonttools | MIT |
| kiwisolver | BSD-3-Clause |
| matplotlib | Matplotlib licence (PSF-based) |
| numpy | BSD (with components under 0BSD, MIT, Zlib and CC0-1.0) |
| openpyxl | MIT |
| packaging | Apache-2.0 OR BSD-2-Clause |
| pandas | BSD-3-Clause |
| patsy | BSD-2-Clause |
| pillow | MIT-CMU (HPND) |
| platformdirs | MIT |
| pyparsing | MIT |
| PyQt6 | GPL-3.0-only (or a commercial licence from Riverbank) |
| PyQt6-Qt6 | LGPL-3.0 (the Qt libraries) |
| PyQt6_sip | BSD-2-Clause |
| python-dateutil | Apache-2.0 OR BSD-3-Clause |
| scipy | BSD-3-Clause |
| seaborn | BSD-3-Clause |
| six | MIT |
| statsmodels | BSD-3-Clause |
| tzdata | Apache-2.0 |
| pyinstaller (build tool) | GPL-2.0-or-later, with a bootloader exception (run-time hooks: Apache-2.0) |

<!-- licenses:end -->

## Qt and PyQt

The window of plotviz is made with **Qt 6**, through **PyQt6**.

- **PyQt6** (the Python binding) is licensed under the GNU GPL v3, or under a commercial licence from Riverbank Computing. plotviz uses it under the GPL v3, which is why plotviz itself is distributed under the GPL.
- The **Qt libraries** (`PyQt6-Qt6`) are licensed under the GNU Lesser General Public License v3. The programs ship them as separate library files inside the application folder, so they can be replaced by another build of the same Qt version. Their source code is at [download.qt.io](https://download.qt.io/), and the sources of PyQt6 at [riverbankcomputing.com](https://www.riverbankcomputing.com/software/pyqt/).

## PyInstaller

The programs are packed with **PyInstaller**, which is licensed under the GPL v2 or later. Its *bootloader exception* gives unlimited permission to embed the compiled bootloader and related files in a program and to distribute it under any licence; its run-time hooks are under the Apache License 2.0.

## Fonts

matplotlib brings the **DejaVu** fonts (a derivative of Bitstream Vera, with its own licence that allows free use and redistribution) and the **STIX** fonts (SIL Open Font License). Their licence texts are in `THIRD-PARTY-NOTICES.md`, under matplotlib.

## Sample data

The files in the `seaborn` folder of the sample datasets (tips, penguins, iris, mpg, titanic and the others) come from the [seaborn-data](https://github.com/mwaskom/seaborn-data) collection. It gathers public datasets, each with its own origin and terms of use: check them before reusing the data outside plotviz. The other sample files and the sample charts were made for plotviz and are distributed under the same licence as the program.

## Logo and icons

The plotviz logo and the file-type icons were made for plotviz and are distributed with it under the same licence as the program, GPL-3.0-or-later.
