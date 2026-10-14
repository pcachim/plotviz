#!/usr/bin/env bash
# Publish a new plotviz release.
#
# Usage: ./publish_release.sh <version>      e.g. ./publish_release.sh 2026.06.3
#
# Updates __version__ in src/plotviz/config/_version.py, commits it, pushes,
# then creates and pushes the tag v<version>, which triggers the
# GitHub Actions release workflow (.github/workflows/release.yml).
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VERSION_FILE="src/plotviz/config/_version.py"
BRANCH="main"

CURRENT=$(sed -n 's/^__version__ = "\([^"]*\)".*/\1/p' "$VERSION_FILE")
echo "Current version: $CURRENT"

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
    read -r -p "New version: " VERSION
fi
VERSION="${VERSION#v}"

if [[ ! "$VERSION" =~ ^[0-9]+(\.[0-9]+)*(-[A-Za-z0-9.]+)?$ ]]; then
    echo "❌ Invalid version: '$VERSION'" >&2
    exit 1
fi
if [[ "$VERSION" == "$CURRENT" ]]; then
    echo "❌ Version is already $CURRENT" >&2
    exit 1
fi
TAG="v$VERSION"
if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    echo "❌ Tag $TAG already exists" >&2
    exit 1
fi
if [[ "$(git rev-parse --abbrev-ref HEAD)" != "$BRANCH" ]]; then
    echo "❌ Not on branch $BRANCH" >&2
    exit 1
fi

# Warn about other uncommitted changes (only the version file is committed).
OTHER=$(git status --porcelain | grep -v " $VERSION_FILE\$" || true)
if [[ -n "$OTHER" ]]; then
    echo "⚠️  Uncommitted changes that will NOT be part of this release commit:"
    echo "$OTHER"
fi

read -r -p "Release $CURRENT → $VERSION (tag $TAG)? [y/N] " ANSWER
[[ "$ANSWER" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }

sed -i.bak "s/^__version__ = \"[^\"]*\"/__version__ = \"$VERSION\"/" "$VERSION_FILE"
rm -f "$VERSION_FILE.bak"

git add "$VERSION_FILE"
git commit -m "chore: bump version to $VERSION"
git push origin "$BRANCH"
git tag "$TAG"
git push origin "$TAG"

echo "✅ Pushed $TAG — follow the build in the repository's Actions tab."
