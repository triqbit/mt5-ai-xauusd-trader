#!/bin/bash
# MT5 AI/ML Trading Bot - Release Packaging Script
# This script standardizes the creation of a deployable release artifact.
# Author: Jules03 (Release Reliability & Governance)

set -e

# --- Configuration ---
# Identify project root relative to script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYPROJECT_FILE="pyproject.toml"
RELEASES_DIR="releases"
IMAGE_NAME="mt5-ai-xauusd-trader"

cd "$PROJECT_ROOT"

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
    echo "Error: $PYPROJECT_FILE not found. Ensure you are in the project root."
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

# --- 2. Mandatory Validation Gates ---
echo "Running Pre-Packaging Validation Gates..."

echo "Checking environment template..."
python3 scripts/validate_env.py

echo "Verifying database migrations..."
python3 scripts/verify_migrations.py

echo "Validating release notes in CHANGELOG.md..."
python3 scripts/check_release_notes.py

# --- 3. Directory Management ---
if [ -d "$RELEASE_PATH" ]; then
    echo "Warning: Release directory $RELEASE_PATH already exists. Re-creating..."
    rm -rf "$RELEASE_PATH"
fi
mkdir -p "$RELEASE_PATH"

# --- 4. Artifact Collection ---

# A. Docker Image (Build and Save)
echo "Building Docker Image..."
# We use --load if using buildx, or just build for standard docker.
# Added a check if buildx is being used.
if docker buildx version >/dev/null 2>&1; then
    docker buildx build --load -t "${IMAGE_NAME}:v${VERSION}" .
else
    docker build -t "${IMAGE_NAME}:v${VERSION}" .
fi

echo "Exporting Docker Image to tarball..."
docker save "${IMAGE_NAME}:v${VERSION}" | gzip > "${RELEASE_PATH}/image.tar.gz"

# B. Docker Info (Metadata)
echo "Collecting Docker Information..."
cat <<EOF > "${RELEASE_PATH}/docker_info.json"
{
  "image": "${IMAGE_NAME}",
  "tag": "v${VERSION}",
  "build_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "vcs_ref": "$(git rev-parse HEAD 2>/dev/null || echo "unknown")"
}
EOF

# C. Environment Template
echo "Collecting Environment Template..."
cp ".env.example" "${RELEASE_PATH}/"

# D. Database Migrations
echo "Collecting Database Migrations..."
cp -r migrations "${RELEASE_PATH}/"

# E. Configuration Documentation
echo "Generating Configuration Reference..."
python3 scripts/generate_config_docs.py src/core/config.py "${RELEASE_PATH}/CONFIG_REFERENCE.md" "$VERSION"

# F. Release Notes
echo "Extracting Release Notes..."
# Improved extraction logic: find [Unreleased] section and stop at the next version header
sed -n '/## \[Unreleased\]/,/## \[/p' CHANGELOG.md | sed '1d;$d' > "${RELEASE_PATH}/RELEASE_NOTES.md"

if [ ! -s "${RELEASE_PATH}/RELEASE_NOTES.md" ] || [ "$(grep -c "[a-zA-Z]" "${RELEASE_PATH}/RELEASE_NOTES.md")" -eq 0 ]; then
     echo "Warning: RELEASE_NOTES.md is empty or only contains whitespace. Using fallback."
     echo "Development Build - No specific release notes for v${VERSION}." > "${RELEASE_PATH}/RELEASE_NOTES.md"
fi

# --- 5. Validation & Checksums ---

echo "Generating Checksum Manifest..."
(cd "${RELEASE_PATH}" && find . -type f ! -name "checksums.sha256" | sort | while read -r f; do
    sha256_cmd "$f" >> "checksums.sha256"
done)

echo "Validating Artifact Completeness..."
MANDATORY_FILES=("image.tar.gz" "docker_info.json" ".env.example" "CONFIG_REFERENCE.md" "RELEASE_NOTES.md" "checksums.sha256" "migrations/env.py")

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

# Verify manifest itself
echo "Verifying Checksum Manifest integrity..."
(cd "${RELEASE_PATH}" && sha256_cmd -c checksums.sha256 > /dev/null)

echo "--------------------------------------------------------"
echo "SUCCESS: Release v${VERSION} packaged successfully."
echo "Location: ${RELEASE_PATH}"
echo "--------------------------------------------------------"
sha256_cmd "${RELEASE_PATH}/checksums.sha256"
