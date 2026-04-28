#!/bin/bash
# ==============================================================================
# MT5 AI/ML Trading Bot - Release Packaging Script
#
# Usage: ./scripts/package_release.sh <version> [docker_image_tag]
# ==============================================================================

set -e

VERSION=$1
DOCKER_TAG=${2:-"triqbit/mt5-trading-bot:$VERSION"}

if [ -z "$VERSION" ]; then
    echo "Error: Version argument is required (e.g., 1.0.0)"
    exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
RELEASE_DIR="$REPO_ROOT/releases/release-$VERSION"
ARTIFACT_NAME="release-v$VERSION.tar.gz"

echo "📦 Packaging release $VERSION..."

# 1. Prepare directory
mkdir -p "$RELEASE_DIR"
rm -rf "${RELEASE_DIR:?}/*"

# 2. Collect components
echo "  > Collecting components..."

# 2.1 Docker image reference
echo "$DOCKER_TAG" > "$RELEASE_DIR/DOCKER_IMAGE"

# 2.2 Environment template
cp "$REPO_ROOT/.env.example" "$RELEASE_DIR/"

# 2.3 Database migrations
if [ -d "$REPO_ROOT/migrations" ]; then
    cp -r "$REPO_ROOT/migrations" "$RELEASE_DIR/"
else
    echo "Warning: migrations directory not found!"
    mkdir -p "$RELEASE_DIR/migrations/versions"
    touch "$RELEASE_DIR/migrations/README"
fi

# 2.4 Configuration documentation
if [ -f "$REPO_ROOT/DEPLOYMENT_GUIDE.md" ]; then
    cp "$REPO_ROOT/DEPLOYMENT_GUIDE.md" "$RELEASE_DIR/CONFIG_GUIDE.md"
else
    echo "Configuration Guide" > "$RELEASE_DIR/CONFIG_GUIDE.md"
fi

# 2.5 Release Notes (Extract from CHANGELOG.md)
if [ -f "$REPO_ROOT/CHANGELOG.md" ]; then
    # Simple extraction logic for the specified version
    sed -n "/## \[$VERSION\]/,/## /p" "$REPO_ROOT/CHANGELOG.md" | sed '$d' > "$RELEASE_DIR/RELEASE_NOTES.md"
    if [ ! -s "$RELEASE_DIR/RELEASE_NOTES.md" ]; then
        echo "Warning: Could not extract release notes for $VERSION from CHANGELOG.md"
        echo "# Release $VERSION" > "$RELEASE_DIR/RELEASE_NOTES.md"
    fi
else
    echo "# Release $VERSION" > "$RELEASE_DIR/RELEASE_NOTES.md"
fi

# 3. Generate Checksum Manifest
echo "  > Generating checksum manifest..."
cd "$RELEASE_DIR"
find . -type f ! -name "MANIFEST.sha256" -print0 | xargs -0 sha256sum > MANIFEST.sha256
cd "$REPO_ROOT"

# 4. Create Artifact Archive
echo "  > Creating tarball..."
tar -czf "$ARTIFACT_NAME" -C "$REPO_ROOT/releases" "release-$VERSION"
mv "$ARTIFACT_NAME" "$REPO_ROOT/releases/"

# 5. Validation
echo "🔍 Validating artifact completeness..."

REQUIRED_FILES=("DOCKER_IMAGE" ".env.example" "migrations/env.py" "CONFIG_GUIDE.md" "RELEASE_NOTES.md" "MANIFEST.sha256")
MISSING=0

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -e "$RELEASE_DIR/$file" ]; then
        echo "❌ Missing mandatory component: $file"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -eq 0 ]; then
    echo "✅ Release artifact $VERSION successfully validated and packaged."
    echo "Location: $REPO_ROOT/releases/$ARTIFACT_NAME"
else
    echo "❌ Validation failed. $MISSING components missing."
    exit 1
fi
