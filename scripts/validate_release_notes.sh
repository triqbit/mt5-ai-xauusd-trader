#!/bin/bash
set -e

CHANGELOG="CHANGELOG.md"

echo "📝 Validating release notes..."

# 1. Check if CHANGELOG.md exists
if [ ! -f "$CHANGELOG" ]; then
    echo "❌ Error: $CHANGELOG not found!"
    exit 1
fi

# 2. Check if CHANGELOG.md is non-empty
if [ ! -s "$CHANGELOG" ]; then
    echo "❌ Error: $CHANGELOG is empty!"
    exit 1
fi

# 3. Get current version from pyproject.toml
# Extracting version from [project] section
VERSION=$(grep -m 1 "version =" pyproject.toml | cut -d '"' -f 2)

if [ -z "$VERSION" ]; then
    echo "❌ Error: Could not determine version from pyproject.toml"
    exit 1
fi

echo "  - Current version: $VERSION"

# 4. Check if version exists in CHANGELOG.md
if grep -q "$VERSION" "$CHANGELOG"; then
    echo "✅ Version $VERSION found in $CHANGELOG."
else
    echo "❌ Error: Version $VERSION not found in $CHANGELOG!"
    exit 1
fi

echo "✅ Release notes validation passed."
