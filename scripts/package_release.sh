#!/bin/bash
# ==============================================================================
# MT5 AI/ML Trading Bot - Release Packaging Script
# Usage: bash scripts/package_release.sh <version>
# ==============================================================================

set -e

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Error: Version argument required (e.g., 1.0.1)"
    exit 1
fi

RELEASE_DIR="releases/v$VERSION"
PACKAGE_NAME="release-v$VERSION.tar.gz"

echo "📦 Packaging Release v$VERSION..."

# 1. Clean and create release directory
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# 2. Collect artifacts
echo "  -> Collecting source code..."
tar -czf "$RELEASE_DIR/source.tar.gz" \
    --exclude=".git" \
    --exclude="tests" \
    --exclude="releases" \
    --exclude="__pycache__" \
    --exclude=".pytest_cache" \
    --exclude=".env" \
    .

echo "  -> Collecting documentation..."
cp -r docs "$RELEASE_DIR/"
cp README.md "$RELEASE_DIR/"
cp CHANGELOG.md "$RELEASE_DIR/" 2>/dev/null || touch "$RELEASE_DIR/CHANGELOG.md"

echo "  -> Collecting configuration templates..."
cp .env.example "$RELEASE_DIR/"
cp alembic.ini "$RELEASE_DIR/"

# 3. Generate Integrity Manifest
echo "  -> Generating SHA256 checksums..."
cd "$RELEASE_DIR"
find . -type f -not -name "CHECKSUMS.txt" -exec sha256sum {} + > CHECKSUMS.txt
cd ../..

# 4. Create final package
echo "  -> Creating final archive..."
tar -czf "$PACKAGE_NAME" -C "releases" "v$VERSION"

echo "✅ Release package created: $PACKAGE_NAME"
echo "📍 Location: $(pwd)/$PACKAGE_NAME"
sha256sum "$PACKAGE_NAME"
