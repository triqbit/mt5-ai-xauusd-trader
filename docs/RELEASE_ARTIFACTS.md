# Release Artifacts Standard

This document defines what constitutes a valid deployable artifact for the MT5 AI/ML XAUUSD Trading Bot. All production releases must adhere to this standard to ensure consistency, auditability, and reliability.

## 1. Artifact Components

A valid release artifact consists of the following components:

### 1.1 Docker Image
- **Description**: A fully built Docker image containing the application and all its dependencies.
- **Requirement**: Must be tagged with a semantic version (e.g., `v1.0.0`) and the `latest` tag for the current stable release.
- **Verification**: `docker inspect` should show correct labels and versioning.

### 1.2 Environment Variable Template (`.env.example`)
- **Description**: A template file containing all required environment variables with placeholder values.
- **Requirement**: Must be kept in sync with `src/core/config.py`.
- **Location**: Root directory of the release package.

### 1.3 Database Migration Files
- **Description**: All SQLAlchemy/Alembic migration scripts required to bring the database schema to the release version.
- **Requirement**: Migrations must be reversible (include both `upgrade` and `downgrade` logic).
- **Location**: `migrations/versions/`

### 1.4 Configuration Documentation (`docs/CONFIG.md`)
- **Description**: Detailed documentation of all configuration parameters, their types, default values, and impact on the system.
- **Requirement**: Must explain risk limits and safety thresholds.

### 1.5 Release Notes (`RELEASE_NOTES.md`)
- **Description**: Markdown file detailing the changes in this version.
- **Contents**:
  - Version number and release date.
  - New features.
  - Bug fixes.
  - Breaking changes.
  - Security updates.
  - Contributor credits.

### 1.6 Checksum Manifest (`SHA256SUMS`)
- **Description**: A file containing SHA256 hashes of all files included in the release package.
- **Requirement**: Generated at the time of packaging to ensure artifact integrity.

## 2. Packaging Process

The release artifact is packaged using the `scripts/package_release.sh` script. This script performs the following steps:

1.  **Validation**: Checks that all source files are present and tests pass.
2.  **Build**: Builds the Docker image.
3.  **Collection**: Gathers all required files into a `releases/vX.Y.Z/` directory.
4.  **Manifest Generation**: Generates the SHA256 checksums for all collected files.
5.  **Final Verification**: Verifies the completeness of the package against this standard.

## 3. Validation Criteria

A release is marked as **DEPLOYABLE** only if:
- [ ] All CI/CD checks (linting, tests, coverage) have passed.
- [ ] The Docker image builds successfully without warnings.
- [ ] The `.env.example` file contains all fields defined in the Pydantic config.
- [ ] Database migrations are reversible and tested.
- [ ] The checksum manifest matches the actual files in the package.
- [ ] Release notes are present and follow the standard format.
