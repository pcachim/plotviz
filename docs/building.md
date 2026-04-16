# Building & Packaging

plotviz ships two build scripts that produce distributable packages from the source tree:

- `create_pkg.sh` — macOS `.app` bundle and `.dmg` disk image
- `create_pkg_win.bat` — Windows one-folder app, NSIS `.exe` installer, and portable `.zip`

Both scripts use **PyInstaller** to bundle the Python interpreter and all dependencies into a self-contained package that runs without a Python installation.

---

## Requirements

### Common

- [uv](https://astral.sh/uv) — used by both scripts to manage the virtual environment and run Python/PyInstaller.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
winget install astral-sh.uv
```

### macOS

- Python 3.10+ (via uv or system)
- `create-dmg` (optional — for `.dmg` creation): `brew install create-dmg`

### Windows

- Python 3.10+ (via uv)
- [NSIS](https://nsis.sourceforge.io) (optional — for `.exe` installer): `winget install NSIS.NSIS`

---

## macOS — create_pkg.sh

Run from the repository root:

```bash
chmod +x create_pkg.sh
./create_pkg.sh
```

### What it produces

| Output | Description |
|--------|-------------|
| `dist/plotviz.app` | Self-contained macOS application bundle |
| `dist/plotviz-VERSION.dmg` | Drag-to-install disk image (if `create-dmg` is found) |

### Steps performed

1. `uv sync` — installs all dependencies.
2. `pyinstaller plotviz.spec` — builds the `.app` bundle.
3. Copies file-type icons (`pviz.icns`, `pvizt.icns`, `pvizc.icns`, `pvizp.icns`) into the bundle's Resources folder.
4. Code-signs the bundle with an ad-hoc signature (`codesign --force --deep -s -`).
5. Optionally creates a `.dmg` with `create-dmg`.

### File-type registration

The `plotviz.spec` file registers four document types in the app's `Info.plist`:

| Extension | Type | UTI |
|-----------|------|-----|
| `.pviz` | plotviz Chart | `com.pviz.app.pviz` |
| `.pvizt` | plotviz Template | `com.pviz.app.pvizt` |
| `.pvizc` | plotviz Color Scheme | `com.pviz.app.pvizc` |
| `.pvizp` | plotviz Palette Bundle | `com.pviz.app.pvizp` |

After installing the `.app`, macOS automatically associates these extensions with plotviz.

### Generating file-type icons

The source icons are produced by two utility scripts in `util/`:

```bash
# Step 1: generate 1024×1024 PNGs for each file type
python util/make_file_icons.py

# Step 2: convert PNGs to .icns (macOS only)
chmod +x util/make_file_icns.sh
./util/make_file_icns.sh
```

The four `.icns` files are written to `assets/`.

---

## Windows — create_pkg_win.bat

Run from the repository root in Command Prompt (not PowerShell):

```bat
create_pkg_win.bat
```

### What it produces

| Output | Description |
|--------|-------------|
| `dist\plotviz\` | One-folder app (PyInstaller output) |
| `dist\plotviz-VERSION-setup.exe` | NSIS installer (if NSIS is installed) |
| `dist\plotviz-VERSION-win.zip` | Portable zip (always produced) |
| `dist\plotviz\register_filetypes.reg` | Registry script for manual file-type association |

### Steps performed

1. `uv sync` — installs all dependencies.
2. Converts `assets/plotviz.icns` → `assets/plotviz.ico` (using Pillow).
3. Generates `assets/pviz.ico`, `pvizt.ico`, `pvizc.ico`, `pvizp.ico` as document-type icons.
4. Generates `plotviz_win.spec` — the PyInstaller spec file with all hidden imports and data files.
5. Cleans previous build artifacts.
6. Runs `pyinstaller plotviz_win.spec`.
7. Writes `dist\plotviz\register_filetypes.reg` for manual file-type registration.
8. Writes `dist\installer.nsi` and runs `makensis` to produce the `.exe` installer (if NSIS is found).
9. Creates the portable `.zip` using PowerShell or 7-Zip.

### NSIS installer

The installer performs a full silent installation including:

- Copying the app to `%PROGRAMFILES64%\plotviz`
- Creating Start Menu shortcuts
- Creating a Desktop shortcut
- Registering `.pviz`, `.pvizt`, `.pvizc`, and `.pvizp` file associations in the registry
- Adding an Add/Remove Programs entry for clean uninstallation

NSIS is detected automatically from its default install paths (`%PROGRAMFILES%\NSIS\makensis.exe` and `%PROGRAMFILES(X86)%\NSIS\makensis.exe`) as well as from the system `PATH`.

### Portable zip

If neither PowerShell nor 7-Zip is found, the zip step is skipped with a warning. PowerShell is available on all modern Windows systems by default.

### File-type associations without the installer

Run `dist\plotviz\register_filetypes.reg` as Administrator to register the file associations manually (for the portable zip distribution).

---

## Automated releases with GitHub Actions

The repository includes two GitHub Actions workflows that run automatically in the cloud — no local build machine is required for releases.

### `.github/workflows/release.yml` — build and publish

Triggered by any tag push matching `v*` (e.g. `git push origin v2.7.0`).

GitHub spins up a **macOS virtual machine** and a **Windows virtual machine** in parallel. Each machine checks out the code, installs `uv`, syncs dependencies, and runs PyInstaller. Once both builds succeed, a third job creates a GitHub Release and attaches the artifacts.

| Artifact | Built on | Produced by |
|----------|----------|-------------|
| `plotviz-VERSION-macos.dmg` | `macos-latest` (Apple Silicon) | `plotviz.spec` + `create-dmg` |
| `plotviz-VERSION-windows.zip` | `windows-latest` | `plotviz.spec` (BUNDLE step skipped on Windows) |

**To publish a release:**

```bash
# 1. Bump __version__ in src/plotviz/config/_version.py
# 2. Commit and push
git add src/plotviz/config/_version.py
git commit -m "chore: bump version to 2.7.0"
git push

# 3. Tag and push — this triggers the workflow
git tag v2.7.0
git push origin v2.7.0
```

Monitor progress at `https://github.com/pcachim/plotviz/actions`. The finished release appears at `https://github.com/pcachim/plotviz/releases`.

### `.github/workflows/docs.yml` — publish documentation

Triggered by pushes to `main` and by tag pushes.

- **Push to `main`** → deploys docs to GitHub Pages under the `latest` alias.
- **Tag push** → deploys a frozen versioned snapshot (e.g. `2.7.0`) and updates the `stable` alias.

Versioning is handled by `mike`. The published site is available at `https://pcachim.github.io/plotviz/`.

One-time setup: go to **Settings → Pages → Source** and set the source to the `gh-pages` branch.

---

## Troubleshooting

### PyInstaller build fails

Run with verbose logging:

```bash
# macOS / Linux
uv run pyinstaller plotviz.spec --noconfirm --clean --log-level DEBUG

# Windows
uv run pyinstaller plotviz_win.spec --noconfirm --clean --log-level DEBUG
```

### Missing icons on Windows taskbar

Ensure `assets/plotviz.ico` exists. The build script generates it from `plotviz.icns` using Pillow. If the `.icns` file is missing, the icon conversion step is skipped and the app runs without a taskbar icon.

### App not opening files on macOS

Run `killall Finder && killall SystemUIServer` after installing the `.app` to force macOS to re-index file-type associations.
