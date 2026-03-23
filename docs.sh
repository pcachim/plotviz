#!/usr/bin/env bash
# docs.sh — plotviz documentation helper
#
# Usage:
#   ./docs.sh serve     # live-reload local preview at http://127.0.0.1:8000
#   ./docs.sh deploy    # build and push versioned docs to GitHub Pages
#   ./docs.sh build     # build static site into site/ (no deploy)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Read version from the single source of truth ─────────────────────────────
VERSION=$(uv run python -c \
  "import sys; sys.path.insert(0,'src/plotviz'); \
   from config._version import __version__; print(__version__)")

CMD="${1:-}"

case "$CMD" in

  # ── serve ──────────────────────────────────────────────────────────────────
  serve)
    echo "▶ Starting live-reload docs server for plotviz $VERSION"
    echo "  Open http://127.0.0.1:8001 in your browser (Ctrl+C to stop)"
    echo ""
    uv run mkdocs serve --dev-addr 127.0.0.1:8001
    ;;

  # ── build ──────────────────────────────────────────────────────────────────
  build)
    echo "▶ Building static docs for plotviz $VERSION ..."
    uv run mkdocs build --clean
    echo "  Done — output in site/"
    ;;

  # ── deploy ─────────────────────────────────────────────────────────────────
  deploy)
    echo "▶ Deploying docs for plotviz $VERSION to GitHub Pages ..."

    # Require a clean git working tree so the deployed docs match the source
    if ! git diff --quiet HEAD; then
      echo "[ERROR] Uncommitted changes detected."
      echo "        Commit or stash your changes before deploying."
      exit 1
    fi

    # Ensure git identity is set (needed by mike)
    if ! git config user.email > /dev/null 2>&1; then
      echo "[ERROR] git user.email is not set."
      echo "        Run: git config --global user.email 'you@example.com'"
      exit 1
    fi

    # Deploy this version and tag it as 'latest'
    uv run mike deploy --push --update-aliases "$VERSION" latest
    uv run mike set-default --push latest

    echo ""
    echo "  Deployed $VERSION (alias: latest)"
    echo "  GitHub Pages will update in a few seconds."
    ;;

  # ── unknown ────────────────────────────────────────────────────────────────
  *)
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  serve     Live-reload local preview at http://127.0.0.1:8000"
    echo "  build     Build static site into site/"
    echo "  deploy    Push versioned docs to GitHub Pages"
    exit 1
    ;;

esac
