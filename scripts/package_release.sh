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

# Check for Docker
if ! command -v docker >/dev/null 2>&1; then
    if [ "$ALLOW_MOCK_ARTIFACTS" = "true" ]; then
        echo "Warning: docker command not found, but ALLOW_MOCK_ARTIFACTS=true."
        echo "The 'image.tar.gz' component will be a placeholder for local verification."
        DOCKER_AVAILABLE="false"
    else
        echo "Error: docker command not found. Docker is required for production release packaging."
        echo "If you are testing the packaging script locally without Docker, use ALLOW_MOCK_ARTIFACTS=true."
        exit 1
    fi
else
    if ! docker info >/dev/null 2>&1; then
        if [ "$ALLOW_MOCK_ARTIFACTS" = "true" ]; then
            echo "Warning: Docker daemon not accessible, but ALLOW_MOCK_ARTIFACTS=true."
            DOCKER_AVAILABLE="false"
        else
            echo "Error: Docker daemon is not running or accessible."
            echo "If you are testing the packaging script locally without Docker, use ALLOW_MOCK_ARTIFACTS=true."
            exit 1
        fi
    else
        DOCKER_AVAILABLE="true"
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
echo "Verifying version synchronization..."
python3 scripts/verify_version_sync.py

echo "Verifying dependencies harmonization..."
python3 scripts/verify_dependencies.py

# --- 4. Directory Management ---
if [ -d "$RELEASE_PATH" ]; then
    echo "Warning: Release directory $RELEASE_PATH already exists. Re-creating..."
    rm -rf "$RELEASE_PATH"
fi
mkdir -p "$RELEASE_PATH"

# --- 5. Artifact Collection ---

# A. Docker Image (Save)
if [ "$DOCKER_AVAILABLE" = "false" ]; then
    if [ "$ALLOW_MOCK_ARTIFACTS" = "true" ]; then
        echo "   [!] WARNING: Creating mock image.tar.gz (NO_DOCKER_MODE)"
        echo "Mock Docker Image for v${VERSION}" | gzip > "${RELEASE_PATH}/image.tar.gz"
        IMAGE_TAG="mock-v${VERSION}"
    else
        echo "Error: Docker unavailable and ALLOW_MOCK_ARTIFACTS is not true. Cannot create artifact."
        exit 1
    fi
else
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
fi

# B. Docker Info (Metadata)
echo "   [+] Component: Docker Metadata (docker_info.json)"
cat <<EOF > "${RELEASE_PATH}/docker_info.json"
{
  "image": "${IMAGE_NAME}",
  "tag": "${IMAGE_TAG}",
  "build_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "vcs_ref": "$(git rev-parse HEAD 2>/dev/null || echo "unknown")",
  "docker_available": ${DOCKER_AVAILABLE}
}
EOF

# Validate JSON
if command -v python3 >/dev/null 2>&1; then
    python3 -c "import json; json.load(open('${RELEASE_PATH}/docker_info.json'))"
    if [ $? -ne 0 ]; then
        echo "Error: Invalid docker_info.json generated"
        exit 1
    fi
fi

# C. Environment Template
echo "   [+] Component: Environment Template (.env.example)"
cp ".env.example" "${RELEASE_PATH}/"

# D. Database Migrations
echo "   [+] Component: Database Migrations (migrations/)"
if [ ! -d "migrations" ]; then
    echo "Error: migrations directory not found."
    exit 1
fi
mkdir -p "${RELEASE_PATH}/migrations"
cp -r migrations/* "${RELEASE_PATH}/migrations/"
find "${RELEASE_PATH}/migrations" -name "__pycache__" -type d -exec rm -rf {} +

# Verify at least some migration content exists
if [ ! -d "${RELEASE_PATH}/migrations/versions" ] || [ -z "$(ls -A "${RELEASE_PATH}/migrations/versions" 2>/dev/null)" ]; then
    echo "Warning: No migration versions found in migrations/versions/"
fi

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

# Pre-validation of component existence before manifest generation
echo "Pre-manifest Validation..."
# Comprehensive list of all files that MUST be in the artifact
ARTIFACT_COMPONENTS=(
    "image.tar.gz"
    "docker_info.json"
    ".env.example"
    "CONFIG_REFERENCE.md"
    "RELEASE_NOTES.md"
    "migrations/env.py"
    "migrations/script.py.mako"
)

for comp in "${ARTIFACT_COMPONENTS[@]}"; do
    if [ ! -f "${RELEASE_PATH}/${comp}" ]; then
        echo "Error: Missing critical component ${comp}"
        exit 1
    fi
    if [ ! -s "${RELEASE_PATH}/${comp}" ]; then
        echo "Error: Critical component ${comp} is empty."
        exit 1
    fi
done

echo "Generating Checksum Manifest..."
# Clear existing manifest if any
rm -f "${RELEASE_PATH}/checksums.sha256"

# We avoid subshells for manifest generation to ensure error propagation
# We use a temporary file to store the checksums before moving it to the final location
TEMP_MANIFEST=$(mktemp)
# Change to the release path to get relative paths in the manifest
pushd "${RELEASE_PATH}" > /dev/null
# Use find to list files and loop over them
while IFS= read -r f; do
    # Skip the manifest itself and pycache
    [[ "$f" == "./checksums.sha256" ]] && continue
    [[ "$f" == *"__pycache__"* ]] && continue

    # Ensure file is readable
    if [ ! -r "$f" ]; then
        echo "Error: File $f is not readable."
        exit 1
    fi

    # Run sha256_cmd and append to temp manifest
    # We must ensure the command itself succeeded
    if ! sha256_cmd "$f" >> "$TEMP_MANIFEST"; then
        echo "Error: Failed to generate checksum for $f"
        exit 1
    fi
done < <(find . -type f | sort)
popd > /dev/null

mv "$TEMP_MANIFEST" "${RELEASE_PATH}/checksums.sha256"

# Verify manifest itself
echo "Verifying Checksum Manifest integrity..."
pushd "${RELEASE_PATH}" > /dev/null
if ! sha256_cmd -c checksums.sha256 > /dev/null; then
    echo "Error: Checksum verification failed! Artifact is corrupted."
    exit 1
fi
popd > /dev/null

echo "--------------------------------------------------------"
echo "SUCCESS: Release v${VERSION} packaged successfully."
echo "Location: ${RELEASE_PATH}"
echo "--------------------------------------------------------"
sha256_cmd "${RELEASE_PATH}/checksums.sha256"
