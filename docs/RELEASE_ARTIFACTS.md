# Release Artifacts Standard

This document defines what constitutes a valid, deployable artifact for the MT5 AI/ML Trading Bot. All production releases must adhere to this standard to ensure consistency, security, and traceability.

## 📦 Artifact Components

A valid release artifact is a directory or archive named `release/<version>/` containing the following components:

### 1. Docker Image Reference
- **File:** `DOCKER_IMAGE`
- **Content:** The full tag of the Docker image pushed to the registry (e.g., `mt5-bot:v1.2.3`).
- **Purpose:** Identifies the exact immutable container image to be deployed.

### 2. Environment Template
- **File:** `.env.example`
- **Purpose:** A template for required environment variables. It must include all configurable parameters defined in `src/core/config.py`.

### 3. Database Migrations
- **Directory:** `migrations/`
- **Purpose:** Contains all Alembic migration scripts required to bring the database schema to the version matching the release.

### 4. Configuration Documentation
- **Directory:** `docs/`
- **Purpose:** Includes all relevant documentation (README, DEPLOYMENT_GUIDE, etc.) to ensure operators have the necessary information for deployment and maintenance.

### 5. Release Notes
- **File:** `RELEASE_NOTES.md`
- **Purpose:** A summary of changes, including new features, bug fixes, and breaking changes for the specific version.

### 6. Checksum Manifest
- **File:** `CHECKSUM.sha256`
- **Purpose:** A manifest containing SHA256 hashes for all files in the artifact (excluding the manifest itself). This ensures artifact integrity.

## ✅ Validation Process

The `scripts/package_release.sh` script automates the creation and validation of these artifacts. A release is only marked as "deployable" if:

1. All mandatory files and directories are present.
2. The version tag follows Semantic Versioning (vX.Y.Z).
3. The checksum manifest is successfully generated and covers all included files.
4. (Optional) CI/CD pipeline has passed for the corresponding tag.

## 🚀 Deployment Workflow

1. **Package:** Run `scripts/package_release.sh <version>`.
2. **Verify:** Confirm the contents of `release/<version>/`.
3. **Deploy:** Use the `DOCKER_IMAGE` tag and `.env.example` to configure the production environment.
4. **Migrate:** Apply database migrations using `alembic upgrade head`.
