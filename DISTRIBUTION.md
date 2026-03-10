# xd-chart

Publication-quality chart generator built with Python, matplotlib, and PyQt6.

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
