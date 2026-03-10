# xd-chart

Publication-quality chart generator built with Python, matplotlib, and PyQt6.

## Features

- Line, scatter, bar, histogram, box, violin, pie, area, step, stem, and 3D chart types
- Multi-subplot layouts with independent axes
- Dual Y-axis support per subplot
- Curve fitting (linear, polynomial, exponential, logarithmic, power, sinusoidal)
- Custom colour palettes with per-series overrides
- Chart export: PNG, PDF, SVG, EPS at any DPI
- Save/load chart sessions as `.xdchart` files (JSON + series metadata)

---

## Requirements

- macOS 11.0 or later
- [uv](https://docs.astral.sh/uv/) package manager

---

## Running from source

```bash
# Clone and enter the repo
git clone https://github.com/yourname/xd-chart.git
cd xd-chart

# Install dependencies
uv sync

# Run
uv run python src/xd-chart/main.py
```

---

## Building the macOS app

```bash
cd ~/xd-chart
bash build_macos.sh
```

Output: `dist/xd-chart.app`

### Test the build

```bash
# Run directly — shows crash output in terminal
./dist/xd-chart.app/Contents/MacOS/xd-chart

# Or open normally
open dist/xd-chart.app
```

### Remove Gatekeeper quarantine (for local use)

```bash
xattr -cr dist/xd-chart.app
open dist/xd-chart.app
```

---

## Project structure

```
xd-chart/                        ← repo root
├── README.md
├── pyproject.toml               ← dependencies + build config
├── build_macos.sh               ← one-command macOS build script
├── xd-chart.spec                ← PyInstaller spec
├── entitlements.plist           ← required for code signing
└── src/
    └── xd-chart/                ← application source
        ├── main.py              ← entry point (dev + bundle)
        ├── ui/
        │   ├── main_window.py   ← main window, event handlers
        │   ├── tab_builders.py  ← all UI tab construction
        │   ├── plot_engine.py   ← matplotlib rendering
        │   ├── serialization.py ← save/load sessions
        │   └── canvas.py        ← matplotlib Qt canvas + annotations
        ├── data/
        │   ├── loader.py        ← CSV/Excel data loading
        │   └── scientific.py    ← curve fitting engine
        └── styling/
            └── presets.py       ← chart style presets
```

---

## Signing and distribution

### Ad-hoc sign (run on your own machine only)

```bash
codesign --force --deep --sign - dist/xd-chart.app
```

### Developer ID sign + notarize (distribute to others)

Requires a paid Apple Developer account.

```bash
# Sign
IDENTITY="Developer ID Application: Your Name (TEAMID)"
codesign \
    --force --deep \
    --options runtime \
    --sign "$IDENTITY" \
    --entitlements entitlements.plist \
    dist/xd-chart.app

# Zip for upload
ditto -c -k --keepParent dist/xd-chart.app dist/xd-chart.zip

# Notarize
xcrun notarytool submit dist/xd-chart.zip \
    --apple-id "you@example.com" \
    --team-id  "YOURTEAMID" \
    --password "@keychain:AC_PASSWORD" \
    --wait

# Staple
xcrun stapler staple dist/xd-chart.app
```

### Package as DMG

```bash
brew install create-dmg

create-dmg \
    --volname "xd-chart" \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "xd-chart.app" 175 190 \
    --app-drop-link 425 190 \
    "dist/xd-chart-1.3.0.dmg" \
    "dist/xd-chart.app"
```

---

## Adding an app icon

1. Create `assets/icon.png` (1024×1024 px)
2. Generate `.icns`:
   ```bash
   mkdir icon.iconset
   for s in 16 32 64 128 256 512; do
       sips -z $s $s assets/icon.png --out icon.iconset/icon_${s}x${s}.png
       sips -z $((s*2)) $((s*2)) assets/icon.png --out icon.iconset/icon_${s}x${s}@2x.png
   done
   iconutil -c icns icon.iconset -o assets/icon.icns
   rm -r icon.iconset
   ```
3. In `xd-chart.spec`, set both `icon=None` lines to `icon='assets/icon.icns'`

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `"can't be opened because Apple cannot check it"` | `xattr -cr dist/xd-chart.app` |
| Axes / fonts not rendering after double-click | Rebuild — `main.py` sets `MATPLOTLIBDATA` at launch |
| `ImportError: No module named 'X'` | Add `'X'` to `hiddenimports` in `xd-chart.spec` and rebuild |
| App crashes silently | Run `./dist/xd-chart.app/Contents/MacOS/xd-chart` in terminal to see traceback |
| Build fails with `OSError: Readme file does not exist` | Ensure `README.md` exists at repo root |
| Crash on Apple Silicon | Check Python slice: `file $(uv run python -c "import sys;print(sys.executable)")` |
