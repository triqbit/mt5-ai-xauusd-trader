#!/bin/bash
# MT5 AI/ML Trading Bot - Release Packaging Script
# This script standardizes the creation of a deployable release artifact.
# Author: Jules03 (Release Reliability & Governance)

set -e

# --- Configuration ---
PROJECT_ROOT=$(pwd)
PYPROJECT_FILE="pyproject.toml"
RELEASES_DIR="releases"
IMAGE_NAME="mt5-ai-xauusd-trader"

# Portable sha256 function
sha256_cmd() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$@"
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$@"
  else
    echo "Error: No sha256 checksum tool found." >&2
    exit 1
  fi
}

# --- 1. Version Extraction ---
if [ ! -f "$PYPROJECT_FILE" ]; then
    echo "Error: $PYPROJECT_FILE not found. Run this script from the project root."
    exit 1
fi

VERSION=$(grep '^version =' "$PYPROJECT_FILE" | cut -d '"' -f 2)
if [ -z "$VERSION" ]; then
    echo "Error: Could not extract version from $PYPROJECT_FILE."
    exit 1
fi

RELEASE_PATH="${RELEASES_DIR}/v${VERSION}"
echo "--------------------------------------------------------"
echo "Packaging Release v${VERSION}..."
echo "Target Path: ${RELEASE_PATH}"
echo "--------------------------------------------------------"

# --- 2. Directory Management ---
if [ -d "$RELEASE_PATH" ]; then
    echo "Warning: Release directory $RELEASE_PATH already exists. Re-creating..."
    rm -rf "$RELEASE_PATH"
fi
mkdir -p "$RELEASE_PATH"

# --- 3. Artifact Collection ---

# A. Docker Info
echo "Collecting Docker Information..."
cat <<EOF > "${RELEASE_PATH}/docker_info.json"
{
  "image": "${IMAGE_NAME}",
  "tag": "v${VERSION}",
  "build_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "vcs_ref": "$(git rev-parse HEAD 2>/dev/null || echo "unknown")"
}
EOF

# B. Environment Template
echo "Collecting Environment Template..."
if [ -f ".env.example" ]; then
    cp ".env.example" "${RELEASE_PATH}/"
else
    echo "Error: .env.example not found."
    exit 1
fi

# C. Database Migrations
echo "Collecting Database Migrations..."
if [ -d "migrations" ]; then
    cp -r migrations "${RELEASE_PATH}/"
else
    echo "Error: migrations directory not found."
    exit 1
fi

# D. Configuration Documentation
echo "Generating Configuration Reference..."
python3 scripts/generate_config_docs.py src/core/config.py "${RELEASE_PATH}/CONFIG_REFERENCE.md" "$VERSION"

# E. Release Notes
echo "Extracting Release Notes..."
if [ -f "CHANGELOG.md" ]; then
    # Improved extraction logic: find [Unreleased] section and stop at the next version header
    sed -n '/## \[Unreleased\]/,/## \[/p' CHANGELOG.md | sed '1d;$d' > "${RELEASE_PATH}/RELEASE_NOTES.md"
    if [ ! -s "${RELEASE_PATH}/RELEASE_NOTES.md" ]; then
         echo "Warning: RELEASE_NOTES.md is empty. Ensure [Unreleased] section in CHANGELOG.md is populated."
         echo "Development Build - No specific release notes." > "${RELEASE_PATH}/RELEASE_NOTES.md"
    fi
else
    echo "Error: CHANGELOG.md not found."
    exit 1
fi

# --- 4. Validation & Checksums ---

echo "Validating Artifact Completeness..."
MANDATORY_FILES=("docker_info.json" ".env.example" "CONFIG_REFERENCE.md" "RELEASE_NOTES.md" "migrations/env.py")

for file in "${MANDATORY_FILES[@]}"; do
    if [ ! -f "${RELEASE_PATH}/${file}" ]; then
        echo "Error: Mandatory file ${file} is missing from the artifact."
        exit 1
    fi
    if [ ! -s "${RELEASE_PATH}/${file}" ]; then
        echo "Error: Mandatory file ${file} is empty."
        exit 1
    fi
done

echo "Generating Checksum Manifest..."
(cd "${RELEASE_PATH}" && find . -type f ! -name "checksums.sha256" | while read -r f; do
    sha256_cmd "$f" >> "checksums.sha256"
done)

echo "--------------------------------------------------------"
echo "SUCCESS: Release v${VERSION} packaged successfully."
echo "Location: ${RELEASE_PATH}"
echo "--------------------------------------------------------"
sha256_cmd "${RELEASE_PATH}/checksums.sha256"
