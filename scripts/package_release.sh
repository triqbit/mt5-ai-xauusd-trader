#!/bin/bash
# MT5 AI/ML Trading Bot - Release Packaging Script
# usage: ./scripts/package_release.sh <version>

set -e

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Error: Version argument is required (e.g., 1.0.0)"
    exit 1
fi

RELEASE_NAME="release-v$VERSION"
STAGING_DIR="tmp_release_$VERSION"
IMAGE_TAG="mt5-ai-trader:$VERSION"

echo ">>> Packaging release $VERSION..."

# 1. Create staging directory
mkdir -p "$STAGING_DIR"

# 2. Build Docker image
echo ">>> Building Docker image: $IMAGE_TAG"
docker build -t "$IMAGE_TAG" .

# 3. Save Docker image to tarball
echo ">>> Saving Docker image to tarball..."
docker save "$IMAGE_TAG" -o "$STAGING_DIR/image.tar"

# 4. Collect other components
echo ">>> Collecting components..."
cp .env.example "$STAGING_DIR/"
cp CHANGELOG.md "$STAGING_DIR/"
cp docs/CONFIGURATION.md "$STAGING_DIR/"
cp -r migrations/ "$STAGING_DIR/"

# 5. Generate Checksum Manifest
echo ">>> Generating checksum manifest..."
(cd "$STAGING_DIR" && find . -type f -not -name "checksums.sha256" -print0 | xargs -0 sha256sum > checksums.sha256)

# 6. Verify completeness
echo ">>> Verifying artifact completeness..."
REQUIRED_FILES=("image.tar" ".env.example" "CHANGELOG.md" "CONFIGURATION.md" "checksums.sha256")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$STAGING_DIR/$file" ]; then
        echo "Error: Missing mandatory file: $file"
        exit 1
    fi
done

if [ ! -d "$STAGING_DIR/migrations" ]; then
    echo "Error: Missing migrations directory"
    exit 1
fi

# 7. Create final archive
echo ">>> Creating final archive: $RELEASE_NAME.tar.gz"
tar -czf "$RELEASE_NAME.tar.gz" -C "$STAGING_DIR" .

# 8. Cleanup
echo ">>> Cleaning up staging directory..."
rm -rf "$STAGING_DIR"

echo ">>> SUCCESS: Release artifact created: $RELEASE_NAME.tar.gz"
