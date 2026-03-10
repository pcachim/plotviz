#!/usr/bin/env bash
set -euo pipefail

# ── Resolve repository root ───────────────────────────────────────────────────
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   xd-chart macOS package builder"
echo "   Root : $ROOT_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Check uv ─────────────────────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    echo "❌ uv not found."
    echo "   Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "   uv     : $(uv --version)"
echo "   Python : $(uv run python --version)"

# ── Read version from the single source of truth ─────────────────────────────
VERSION=$(uv run python - <<'EOF'
import sys, pathlib
sys.path.insert(0, str(pathlib.Path("src/xd-chart")))
from config._version import __version__
print(__version__)
EOF
)

echo "   Version: $VERSION"

# ── Config ───────────────────────────────────────────────────────────────────
APP_NAME="xd-chart"
SPEC_FILE="xd-chart.spec"
DIST_DIR="dist"
ASSETS_DIR="assets"
ICON="$ASSETS_DIR/xd-chart.icns"
APP="$DIST_DIR/$APP_NAME.app"
DMG="$DIST_DIR/${APP_NAME}-${VERSION}.dmg"

# ── Sync dependencies ─────────────────────────────────────────────────────────
echo ""
echo "▶ Syncing dependencies..."
uv sync

echo ""
echo "▶ PyInstaller $(uv run pyinstaller --version)"

# ── Clean previous builds ─────────────────────────────────────────────────────
echo ""
echo "▶ Cleaning previous build..."
rm -rf build "$DIST_DIR"

# ── Build .app with spec file ─────────────────────────────────────────────────
# The spec file carries all hiddenimports, data files, and Info.plist settings.
# Do not use --windowed / --onefile here — the spec controls everything.
echo ""
echo "▶ Building $APP_NAME.app..."
uv run pyinstaller "$SPEC_FILE" \
    --noconfirm \
    --clean \
    --log-level WARN

# ── Verify build ─────────────────────────────────────────────────────────────
if [ ! -d "$APP" ]; then
    echo ""
    echo "❌ Build failed — $APP not found"
    echo "   Retry with full output:"
    echo "   uv run pyinstaller $SPEC_FILE --noconfirm --clean --log-level DEBUG"
    exit 1
fi

SIZE=$(du -sh "$APP" | cut -f1)

# ── Code signing ──────────────────────────────────────────────────────────────
echo ""
echo "▶ Signing bundle (ad-hoc)..."
codesign --force --deep --sign - "$APP"

# ── Remove quarantine ─────────────────────────────────────────────────────────
echo ""
echo "▶ Removing quarantine attributes..."
xattr -cr "$APP"

# ── DMG background ────────────────────────────────────────────────────────────
echo ""
echo "▶ Generating DMG background..."
mkdir -p "$ASSETS_DIR"

uv run python - <<EOF
from PIL import Image, ImageDraw, ImageFont
import pathlib

W, H = 600, 400
img  = Image.new("RGB", (W, H), (245, 246, 248))
draw = ImageDraw.Draw(img)
font = ImageFont.load_default()

draw.text((195, 40),  "Install $APP_NAME $VERSION", (30, 30, 30),  font=font)
draw.text((135, 330), "Drag the application to Applications", (90, 90, 90), font=font)

# Arrow
draw.line(   (260, 200, 340, 200), fill=(120, 120, 120), width=6)
draw.polygon([(340, 200), (320, 185), (320, 215)], fill=(120, 120, 120))

pathlib.Path("$ASSETS_DIR").mkdir(parents=True, exist_ok=True)
img.save("$ASSETS_DIR/background.png")
print("  background.png written")
EOF

# ── Create DMG ────────────────────────────────────────────────────────────────
echo ""
echo "▶ Creating DMG..."

if ! command -v create-dmg &>/dev/null; then
    echo "⚠️  create-dmg not found — skipping DMG creation."
    echo "   Install with: brew install create-dmg"
else
    create-dmg \
        --volname "$APP_NAME" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 120 \
        --icon "$APP_NAME.app" 150 200 \
        --hide-extension "$APP_NAME.app" \
        --app-drop-link 450 200 \
        --background "$ASSETS_DIR/background.png" \
        "$DMG" \
        "$APP"
fi

# ── Final report ──────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Build succeeded"
echo "  Bundle : $APP  ($SIZE)"
if [ -f "$DMG" ]; then
    echo "  DMG    : $DMG"
fi
echo ""
echo "  Test   : ./$APP/Contents/MacOS/$APP_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
