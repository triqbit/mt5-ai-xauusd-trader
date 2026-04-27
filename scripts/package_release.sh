#!/bin/bash
# ==============================================================================
# MT5 AI/ML Trading Bot - Release Packaging Script
# Packages and validates a deployable artifact.
# Usage: ./scripts/package_release.sh <version>
# ==============================================================================

set -e

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Error: Version tag is required (e.g., v1.0.0)"
    exit 1
fi

# Validation: Version format (vX.Y.Z)
if [[ ! $VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must follow semantic versioning format (e.g., v1.0.0)"
    exit 1
fi

RELEASE_DIR="release/$VERSION"
echo "📦 Packaging release $VERSION into $RELEASE_DIR..."

# Create release directory
mkdir -p "$RELEASE_DIR"

# 1. Docker Image Reference
# In a real CI environment, this would be the actual image tag.
# For now, we simulate this by creating the file.
IMAGE_TAG="mt5-bot:$VERSION"
echo "$IMAGE_TAG" > "$RELEASE_DIR/DOCKER_IMAGE"

# 2. Environment Template
if [ ! -f ".env.example" ]; then
    echo "Error: .env.example not found!"
    exit 1
fi
cp ".env.example" "$RELEASE_DIR/"

# 3. Database Migrations
if [ ! -d "migrations" ]; then
    echo "Error: migrations/ directory not found!"
    exit 1
fi
cp -r migrations "$RELEASE_DIR/"

# 4. Configuration Documentation
mkdir -p "$RELEASE_DIR/docs"
cp docs/*.md "$RELEASE_DIR/docs/"
cp README.md "$RELEASE_DIR/"

# 5. Release Notes
# If CHANGELOG.md exists, extract the latest entry, otherwise create a stub.
if [ -f "CHANGELOG.md" ]; then
    # Simple extraction logic (first section until next H2 or end of file)
    sed -n "/## \[$VERSION\]/,/## \[/p" CHANGELOG.md | sed '$d' > "$RELEASE_DIR/RELEASE_NOTES.md"
fi

if [ ! -s "$RELEASE_DIR/RELEASE_NOTES.md" ]; then
    echo "# Release Notes - $VERSION" > "$RELEASE_DIR/RELEASE_NOTES.md"
    echo "Automated release for version $VERSION." >> "$RELEASE_DIR/RELEASE_NOTES.md"
fi

# 6. Checksum Manifest
echo "🔍 Generating checksum manifest..."
(
    cd "$RELEASE_DIR"
    find . -type f ! -name "CHECKSUM.sha256" -print0 | xargs -0 sha256sum > "CHECKSUM.sha256"
)

# --- Final Validation ---
echo "✅ Validating artifact completeness..."

MANDATORY_FILES=(
    "DOCKER_IMAGE"
    ".env.example"
    "RELEASE_NOTES.md"
    "CHECKSUM.sha256"
)

MANDATORY_DIRS=(
    "migrations"
    "docs"
)

for file in "${MANDATORY_FILES[@]}"; do
    if [ ! -f "$RELEASE_DIR/$file" ]; then
        echo "❌ Validation failed: Missing mandatory file $file"
        exit 1
    fi
done

for dir in "${MANDATORY_DIRS[@]}"; do
    if [ ! -d "$RELEASE_DIR/$dir" ]; then
        echo "❌ Validation failed: Missing mandatory directory $dir"
        exit 1
    fi
done

echo "🎉 Release $VERSION packaged and validated successfully!"
echo "Location: $RELEASE_DIR"
