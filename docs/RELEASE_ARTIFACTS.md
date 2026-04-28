# Release Artifact Standards

This document defines the mandatory components and structure of a valid deployable artifact for the MT5 AI/ML Trading Bot.

## 1. Core Components

Every release must be packaged into a single compressed archive (e.g., `release-vX.Y.Z.tar.gz`) containing:

### 1.1 Docker Image Reference
- **File:** `DOCKER_IMAGE`
- **Content:** The full tag of the verified Docker image (e.g., `triqbit/mt5-trading-bot:1.0.0`).
- **Requirement:** The image must have passed all CI/CD gates.

### 1.2 Environment Template
- **File:** `.env.example`
- **Content:** A complete list of required and optional environment variables with descriptions.
- **Requirement:** Must match the current version of `src/core/config.py`.

### 1.3 Database Migrations
- **Directory:** `migrations/`
- **Content:** All Alembic migration scripts required to reach the current schema version.
- **Requirement:** Must include a `versions/` subdirectory.

### 1.4 Configuration Documentation
- **File:** `CONFIG_GUIDE.md` (or link to current online docs)
- **Content:** Detailed explanation of trading parameters and risk limits.

### 1.5 Release Notes
- **File:** `RELEASE_NOTES.md`
- **Content:** Markdown file containing:
  - Version number
  - Summary of changes
  - Breaking changes
  - Migration instructions

### 1.6 Checksum Manifest
- **File:** `MANIFEST.sha256`
- **Content:** SHA256 hashes of all files included in the artifact.
- **Requirement:** Generated at the time of packaging.

## 2. Validation Criteria

An artifact is considered "deployable" only if:
1. All 6 core components are present.
2. The `MANIFEST.sha256` is valid (all files match their hashes).
3. The Docker image is accessible in the registry.
4. Database migrations have been verified as reversible.

## 3. Packaging Process

Release artifacts are generated using the `scripts/package_release.sh` script, which automates collection, hashing, and validation.
