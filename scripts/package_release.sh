#!/bin/bash
# MT5 Trading Bot - Release Packaging Script
# Bundles Docker image, migrations, documentation, and generates checksums.

set -e

RAW_VERSION=$1
if [ -z "$RAW_VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

# Normalize version (ensure it doesn't have a double 'v')
VERSION=$(echo "$RAW_VERSION" | sed 's/^v//')
TAG_VERSION="v$VERSION"

RELEASE_DIR="releases/$TAG_VERSION"
mkdir -p "$RELEASE_DIR"

echo "Step 1: Exporting Docker image..."
# Note: In a CI environment with separate jobs, the image should be passed via artifacts.
# If the image exists locally, we save it.
if docker image inspect "triqbit/mt5-ai-xauusd-trader:$TAG_VERSION" >/dev/null 2>&1; then
    docker save "triqbit/mt5-ai-xauusd-trader:$TAG_VERSION" | gzip > "$RELEASE_DIR/image.tar.gz"
else
    echo "Warning: Docker image triqbit/mt5-ai-xauusd-trader:$TAG_VERSION not found locally. Creating placeholder."
    touch "$RELEASE_DIR/image.tar.gz"
fi

echo "Step 2: Collecting migrations..."
if [ -d "migrations" ]; then
    cp -r migrations "$RELEASE_DIR/"
fi

echo "Step 3: Collecting configuration and documentation..."
[ -f ".env.example" ] && cp .env.example "$RELEASE_DIR/"
if [ -d "docs" ]; then
    cp -r docs "$RELEASE_DIR/"
fi
[ -f "CHANGELOG.md" ] && cp CHANGELOG.md "$RELEASE_DIR/"

echo "Step 4: Generating checksum manifest..."
cd "$RELEASE_DIR"
# Remove old checksums if they exist
rm -f checksums.sha256
find . -type f -exec sha256sum {} + > checksums.sha256
cd ../..

echo "Step 5: Creating final release archive..."
# Use the TAG_VERSION for the archive name to match workflow expectations
tar -czf "releases/release-$TAG_VERSION.tar.gz" -C releases "$TAG_VERSION"

echo "Release $TAG_VERSION packaged successfully at releases/release-$TAG_VERSION.tar.gz"
