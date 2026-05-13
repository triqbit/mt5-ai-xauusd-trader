#!/bin/bash
# MT5 AI/ML Trading Bot - Standardized Release Packaging Script
# Standardizes the creation and validation of deployable release artifacts.
# Author: Jules03 (Release Reliability & Governance)

set -e

# --- Configuration ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYPROJECT_FILE="pyproject.toml"
RELEASES_DIR="releases"
IMAGE_NAME="triqbit/mt5-ai-xauusd-trader"

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

# --- 1. Version Management ---
if [ -n "$VERSION" ]; then
    VERSION=${VERSION#v}
    echo "Using version from environment: $VERSION"
else
    if [ ! -f "$PYPROJECT_FILE" ]; then
        echo "Error: $PYPROJECT_FILE not found."
        exit 1
    fi
    VERSION=$(grep '^version =' "$PYPROJECT_FILE" | cut -d '"' -f 2)
fi

RELEASE_PATH="${RELEASES_DIR}/v${VERSION}"
echo "--------------------------------------------------------"
echo "Standardizing Release v${VERSION}..."
echo "Target: ${RELEASE_PATH}"
echo "--------------------------------------------------------"

# --- 2. Prerequisite & Validation Gates ---
echo "Executing Mandatory Validation Gates..."

# Gate 1: Version Sync
python3 scripts/verify_version_sync.py

# Gate 1.1: Atlas Governance Audit
python3 scripts/atlas_audit.py

# Gate 2: Environment Template Integrity
python3 scripts/validate_env.py

# Gate 3: Migration Safety
python3 scripts/verify_migrations.py

# Gate 4: Dependency Harmonization
python3 scripts/verify_dependencies.py

# Gate 5: Release Notes Verification
python3 scripts/check_release_notes.py

# --- 3. Artifact Collection ---
if [ -d "$RELEASE_PATH" ]; then
    echo "Cleaning existing release directory..."
    rm -rf "$RELEASE_PATH"
fi
mkdir -p "$RELEASE_PATH"

# Component A: Docker Image
DOCKER_AVAILABLE="false"
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "   [+] Component: Docker Image (image.tar.gz)"
    # Build or check for existing image
    if ! docker image inspect "${IMAGE_NAME}:v${VERSION}" >/dev/null 2>&1; then
        if [ "$SKIP_DOCKER_BUILD" = "true" ]; then
            echo "   [!] SKIP_DOCKER_BUILD=true. Image not found locally and build skipped."
        else
            echo "Building Docker Image..."
            if docker build -t "${IMAGE_NAME}:v${VERSION}" .; then
                 docker save "${IMAGE_NAME}:v${VERSION}" | gzip > "${RELEASE_PATH}/image.tar.gz"
                 DOCKER_AVAILABLE="true"
                 IMAGE_TAG="v${VERSION}"
            fi
        fi
    else
        echo "   [*] Using existing local image: ${IMAGE_NAME}:v${VERSION}"
        docker save "${IMAGE_NAME}:v${VERSION}" | gzip > "${RELEASE_PATH}/image.tar.gz"
        DOCKER_AVAILABLE="true"
        IMAGE_TAG="v${VERSION}"
    fi
fi

if [ "$DOCKER_AVAILABLE" = "false" ]; then
    if [ "$ALLOW_MOCK_ARTIFACTS" = "true" ]; then
        echo "   [!] WARNING: Creating mock image.tar.gz (NO_DOCKER_MODE)"
        echo "Mock Docker Image for v${VERSION}" | gzip > "${RELEASE_PATH}/image.tar.gz"
        IMAGE_TAG="mock-v${VERSION}"
    else
        echo "Error: Docker unavailable or build failed and ALLOW_MOCK_ARTIFACTS=false."
        exit 1
    fi
fi

# Component B: Docker Metadata
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

# Component C: Environment Template
echo "   [+] Component: Environment Template (.env.example)"
cp ".env.example" "${RELEASE_PATH}/"

# Component D: Database Migrations
echo "   [+] Component: Database Migrations (migrations/)"
mkdir -p "${RELEASE_PATH}/migrations"
cp -r migrations/* "${RELEASE_PATH}/migrations/"
find "${RELEASE_PATH}/migrations" -name "__pycache__" -type d -exec rm -rf {} +

# Component E: Configuration Reference
echo "   [+] Component: Configuration Reference (CONFIG_REFERENCE.md)"
python3 scripts/generate_config_docs.py src/core/config.py "${RELEASE_PATH}/CONFIG_REFERENCE.md" "$VERSION"

# Component F: Release Notes
echo "   [+] Component: Release Notes (RELEASE_NOTES.md)"
if grep -q "## \[${VERSION}\]" CHANGELOG.md; then
    awk "/## \[${VERSION}\]/{flag=1;next} /^## \[/{flag=0} flag" CHANGELOG.md > "${RELEASE_PATH}/RELEASE_NOTES.md"
else
    awk "/## \[Unreleased\]/{flag=1;next} /^## \[/{flag=0} flag" CHANGELOG.md > "${RELEASE_PATH}/RELEASE_NOTES.md"
fi
if [ ! -s "${RELEASE_PATH}/RELEASE_NOTES.md" ]; then
    echo "Release notes fallback." > "${RELEASE_PATH}/RELEASE_NOTES.md"
fi

# Component G: Research Reports (Optional in packaging, mandatory in workflow)
# This section handles research_*.md/html
echo "   [+] Component: Research Reports (optional collect)"
REPORT_FILES=("research_audit_report.md" "research_verification_report.md" "research_audit_report.html" "research_verification_report.html")
for r in "${REPORT_FILES[@]}"; do
    if [ -f "$r" ]; then
        cp "$r" "${RELEASE_PATH}/"
    fi
done

# --- 4. Verification & Integrity ---
echo "Finalizing Artifact with Checksum Manifest..."

# Verify all mandatory files exist and are non-empty
MANDATORY_FILES=("image.tar.gz" "docker_info.json" ".env.example" "CONFIG_REFERENCE.md" "RELEASE_NOTES.md")
for f in "${MANDATORY_FILES[@]}"; do
    if [ ! -s "${RELEASE_PATH}/$f" ]; then
        echo "Error: Mandatory file $f is missing or empty."
        exit 1
    fi
done

# Verify mandatory directories
if [ ! -d "${RELEASE_PATH}/migrations" ] || [ -z "$(ls -A "${RELEASE_PATH}/migrations")" ]; then
    echo "Error: Mandatory directory migrations/ is missing or empty."
    exit 1
fi

# Generate SHA256 checksums
pushd "${RELEASE_PATH}" > /dev/null
# Ensure clean manifest
rm -f "checksums.sha256"
find . -type f ! -name "checksums.sha256" | sort | while read -r f; do
    sha256_cmd "$f" >> "checksums.sha256"
done
# Self-verify
sha256_cmd -c checksums.sha256 > /dev/null
popd > /dev/null

echo "--------------------------------------------------------"
echo "SUCCESS: Standardized Release v${VERSION} Ready."
echo "Location: ${RELEASE_PATH}"
echo "--------------------------------------------------------"
sha256_cmd "${RELEASE_PATH}/checksums.sha256"
