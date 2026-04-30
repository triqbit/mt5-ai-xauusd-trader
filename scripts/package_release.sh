#!/bin/bash
# MT5 AI/ML Trading Bot - Release Packaging Script
# This script bundles all necessary components for a deployable artifact.

set -e

# 1. Validation
echo "[1/5] Validating environment and source..."

if [ ! -f "pyproject.toml" ]; then
    echo "Error: pyproject.toml not found. Run this script from the repo root."
    exit 1
fi

# Configuration
VERSION=$(grep -m 1 "version =" pyproject.toml | tr -d '"' | awk '{print $3}')
RELEASE_DIR="releases/v${VERSION}"
LOG_FILE="release_packaging.log"

echo "Starting release packaging for version ${VERSION}..." | tee "${LOG_FILE}"

if [ ! -f ".env.example" ]; then
    echo "Error: .env.example not found at root." | tee -a "${LOG_FILE}"
    exit 1
fi

# Check for required documentation
REQUIRED_DOCS=("docs/RELEASE_ARTIFACTS.md" "docs/CONFIG.md" "RELEASE_NOTES.md")
for doc in "${REQUIRED_DOCS[@]}"; do
    if [ ! -f "${doc}" ]; then
        echo "Error: Required documentation ${doc} is missing." | tee -a "${LOG_FILE}"
        exit 1
    fi
done

# Check for migrations
if [ ! -d "migrations" ] || [ -z "$(ls -A migrations/versions 2>/dev/null)" ]; then
    echo "Error: No database migrations found in migrations/versions. Release must include migrations." | tee -a "${LOG_FILE}"
    exit 1
fi

# 2. Build Docker Image
echo "[2/5] Building Docker image..." | tee -a "${LOG_FILE}"
IMAGE_TAG="trading-bot:${VERSION}"

if ! docker build -t "${IMAGE_TAG}" . | tee -a "${LOG_FILE}"; then
    echo "Error: Docker build failed. A valid release requires a successful Docker build." | tee -a "${LOG_FILE}"
    exit 1
fi
docker tag "${IMAGE_TAG}" "trading-bot:latest"

# 3. Collect Artifacts
echo "[3/5] Collecting artifacts into ${RELEASE_DIR}..." | tee -a "${LOG_FILE}"
mkdir -p "${RELEASE_DIR}"

# Copy configuration and docs
cp .env.example "${RELEASE_DIR}/"
cp docs/CONFIG.md "${RELEASE_DIR}/"
cp RELEASE_NOTES.md "${RELEASE_DIR}/"
cp docs/RELEASE_ARTIFACTS.md "${RELEASE_DIR}/"

# Copy migrations
mkdir -p "${RELEASE_DIR}/migrations"
cp -r migrations/* "${RELEASE_DIR}/migrations/"

# 4. Generate Checksum Manifest
echo "[4/5] Generating checksum manifest..." | tee -a "${LOG_FILE}"
# Use sha256sum or shasum -a 256 depending on what's available
SHA_CMD="sha256sum"
if ! command -v sha256sum &> /dev/null; then
    SHA_CMD="shasum -a 256"
fi

cd "${RELEASE_DIR}"
find . -type f ! -name "SHA256SUMS" -print0 | xargs -0 $SHA_CMD > SHA256SUMS
cd ../..

# 5. Final Verification
echo "[5/5] Verifying artifact completeness..." | tee -a "${LOG_FILE}"
MISSING_ARTIFACTS=0

REQUIRED_ARTIFACT_FILES=(
    ".env.example"
    "CONFIG.md"
    "RELEASE_NOTES.md"
    "RELEASE_ARTIFACTS.md"
    "SHA256SUMS"
)

for file in "${REQUIRED_ARTIFACT_FILES[@]}"; do
    if [ ! -f "${RELEASE_DIR}/${file}" ]; then
        echo "Error: Missing artifact file ${file} in ${RELEASE_DIR}" | tee -a "${LOG_FILE}"
        MISSING_ARTIFACTS=$((MISSING_ARTIFACTS + 1))
    fi
done

if [ ! -d "${RELEASE_DIR}/migrations" ]; then
    echo "Error: Migrations directory missing in ${RELEASE_DIR}" | tee -a "${LOG_FILE}"
    MISSING_ARTIFACTS=$((MISSING_ARTIFACTS + 1))
fi

if [ $MISSING_ARTIFACTS -eq 0 ]; then
    echo "--------------------------------------------------" | tee -a "${LOG_FILE}"
    echo "RELEASE v${VERSION} IS DEPLOYABLE" | tee -a "${LOG_FILE}"
    echo "Artifacts located in: ${RELEASE_DIR}" | tee -a "${LOG_FILE}"
    echo "Docker image: ${IMAGE_TAG}" | tee -a "${LOG_FILE}"
    echo "--------------------------------------------------" | tee -a "${LOG_FILE}"
else
    echo "Error: Release packaging failed validation." | tee -a "${LOG_FILE}"
    exit 1
fi
