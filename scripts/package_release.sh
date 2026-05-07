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
# Logic: If VERSION is provided, use it. If it starts with 'v', strip it to get the raw semantic version.
if [ -n "$VERSION" ]; then
    VERSION=${VERSION#v}
    echo "Using version from environment: $VERSION"
else
    if [ ! -f "$PYPROJECT_FILE" ]; then
        echo "Error: $PYPROJECT_FILE not found. Ensure you are in the project root."
        exit 1
    fi

    VERSION=$(grep '^version =' "$PYPROJECT_FILE" | cut -d '"' -f 2)
    if [ -z "$VERSION" ]; then
        echo "Error: Could not extract version from $PYPROJECT_FILE."
        exit 1
    fi
fi

RELEASE_PATH="${RELEASES_DIR}/v${VERSION}"
echo "--------------------------------------------------------"
echo "Packaging Release v${VERSION}..."
echo "Target Path: ${RELEASE_PATH}"
echo "--------------------------------------------------------"

# --- 2. Prerequisite Checks ---
echo "Running Prerequisite Checks..."

# Check for required Python packages
REQUIRED_PKGS=("alembic" "sqlalchemy" "pydantic" "pydantic_settings")
for pkg in "${REQUIRED_PKGS[@]}"; do
    if ! python3 -c "import $pkg" >/dev/null 2>&1; then
        echo "Error: Python package '$pkg' is not installed."
        echo "Please install it using: pip install $pkg"
        exit 1
    fi
done

# Check for Docker if build is not skipped
if [ "$SKIP_DOCKER_BUILD" != "true" ]; then
    if ! command -v docker >/dev/null 2>&1; then
        echo "Error: docker command not found."
        exit 1
    fi
    if ! docker info >/dev/null 2>&1; then
        echo "Error: Docker daemon is not running or accessible."
        exit 1
    fi
fi

# --- 3. Mandatory Validation Gates ---
echo "Running Pre-Packaging Validation Gates..."

echo "Checking environment template..."
python3 scripts/validate_env.py

echo "Verifying database migrations..."
python3 scripts/verify_migrations.py

echo "Validating release notes in CHANGELOG.md..."
python3 scripts/check_release_notes.py

# --- 4. Directory Management ---
if [ -d "$RELEASE_PATH" ]; then
    echo "Warning: Release directory $RELEASE_PATH already exists. Re-creating..."
    rm -rf "$RELEASE_PATH"
fi
mkdir -p "$RELEASE_PATH"

# --- 5. Artifact Collection ---

# A. Docker Image (Save)
if [ "$SKIP_DOCKER_BUILD" = "true" ]; then
    echo "SKIP_DOCKER_BUILD is true. Skipping Docker build and using existing image."
    if docker image inspect "${IMAGE_NAME}:v${VERSION}" >/dev/null 2>&1; then
        IMAGE_TAG="v${VERSION}"
    elif docker image inspect "${IMAGE_NAME}:${VERSION}" >/dev/null 2>&1; then
        IMAGE_TAG="${VERSION}"
    else
        echo "Error: SKIP_DOCKER_BUILD is true but no image found for ${IMAGE_NAME}:v${VERSION} or ${IMAGE_NAME}:${VERSION}."
        exit 1
    fi
else
    # Check if the image already exists (either as vX.X.X or raw version)
    if docker image inspect "${IMAGE_NAME}:v${VERSION}" >/dev/null 2>&1; then
        echo "Docker Image ${IMAGE_NAME}:v${VERSION} already exists. Skipping build..."
        IMAGE_TAG="v${VERSION}"
    elif docker image inspect "${IMAGE_NAME}:${VERSION}" >/dev/null 2>&1; then
        echo "Docker Image ${IMAGE_NAME}:${VERSION} exists. Skipping build..."
        IMAGE_TAG="${VERSION}"
    elif [ -n "$GITHUB_SHA" ] && docker image inspect "${IMAGE_NAME}:${GITHUB_SHA}" >/dev/null 2>&1; then
        echo "Docker Image for SHA ${GITHUB_SHA} exists. Tagging as v${VERSION} and using..."
        docker tag "${IMAGE_NAME}:${GITHUB_SHA}" "${IMAGE_NAME}:v${VERSION}"
        IMAGE_TAG="v${VERSION}"
    else
        echo "Building Docker Image..."
        if docker buildx version >/dev/null 2>&1; then
            docker buildx build --load -t "${IMAGE_NAME}:v${VERSION}" .
        else
            docker build -t "${IMAGE_NAME}:v${VERSION}" .
        fi
        IMAGE_TAG="v${VERSION}"
    fi
fi

echo "Exporting Docker Image ${IMAGE_NAME}:${IMAGE_TAG} to tarball..."
docker save "${IMAGE_NAME}:${IMAGE_TAG}" | gzip > "${RELEASE_PATH}/image.tar.gz"

# B. Docker Info (Metadata)
echo "   [+] Component: Docker Metadata (docker_info.json)"
cat <<EOF > "${RELEASE_PATH}/docker_info.json"
{
  "image": "${IMAGE_NAME}",
  "tag": "${IMAGE_TAG}",
  "build_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "vcs_ref": "$(git rev-parse HEAD 2>/dev/null || echo "unknown")"
}
EOF

# C. Environment Template
echo "   [+] Component: Environment Template (.env.example)"
cp ".env.example" "${RELEASE_PATH}/"

# D. Database Migrations
echo "   [+] Component: Database Migrations (migrations/)"
cp -r migrations "${RELEASE_PATH}/"

# E. Configuration Documentation
echo "   [+] Component: Configuration Reference (CONFIG_REFERENCE.md)"
python3 scripts/generate_config_docs.py src/core/config.py "${RELEASE_PATH}/CONFIG_REFERENCE.md" "$VERSION"

# F. Release Notes
echo "   [+] Component: Release Notes (RELEASE_NOTES.md)"
# Robust extraction logic using awk: extract text between target header and next header
if grep -q "## \[${VERSION}\]" CHANGELOG.md; then
    awk "/## \[${VERSION}\]/{flag=1;next} /^## \[/{flag=0} flag" CHANGELOG.md > "${RELEASE_PATH}/RELEASE_NOTES.md"
else
    awk "/## \[Unreleased\]/{flag=1;next} /^## \[/{flag=0} flag" CHANGELOG.md > "${RELEASE_PATH}/RELEASE_NOTES.md"
fi

if [ ! -s "${RELEASE_PATH}/RELEASE_NOTES.md" ] || [ "$(grep -c "[a-zA-Z]" "${RELEASE_PATH}/RELEASE_NOTES.md")" -eq 0 ]; then
     echo "Warning: RELEASE_NOTES.md is empty or only contains whitespace. Using fallback."
     echo "Development Build - No specific release notes for v${VERSION}." > "${RELEASE_PATH}/RELEASE_NOTES.md"
fi

# --- 6. Validation & Checksums ---

echo "Generating Checksum Manifest..."
# Clear existing manifest if any
rm -f "${RELEASE_PATH}/checksums.sha256"
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
