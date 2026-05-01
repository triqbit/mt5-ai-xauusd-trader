# Release Artifact Standards

This document defines what constitutes a valid, deployable artifact for the MT5 AI/ML Trading Bot. Standardizing these artifacts ensures consistency, traceability, and safety across all environments.

## 1. Mandatory Artifact Components

Every release package must include the following components:

| Component | File/Format | Description |
| :--- | :--- | :--- |
| **Docker Information** | `docker_info.json` | Contains the Docker image name, tag, and SHA256 digest. |
| **Environment Template** | `.env.example` | The authoritative template for environment variables required by the version. |
| **Database Migrations** | `migrations/` | All Alembic migration files required to bring the database schema up to date. |
| **Configuration Docs** | `CONFIG_REFERENCE.md` | Auto-generated documentation of all configuration fields and their constraints. |
| **Release Notes** | `RELEASE_NOTES.md` | Version-specific changes extracted from `CHANGELOG.md`. |
| **Checksum Manifest** | `checksums.sha256` | SHA256 hashes of all files in the artifact package for integrity verification. |

## 2. Artifact Structure

The packaging process generates a directory structure as follows:

```text
releases/v<VERSION>/
├── docker_info.json
├── .env.example
├── CONFIG_REFERENCE.md
├── RELEASE_NOTES.md
├── checksums.sha256
└── migrations/
    ├── env.py
    ├── script.py.mako
    └── versions/
        └── *.py
```

## 3. Verification Process

The `scripts/package_release.sh` script enforces the following validation rules before marking an artifact as valid:

1.  **Completeness**: All mandatory files listed in Section 1 must exist.
2.  **Integrity**: The `checksums.sha256` file must match the actual file contents.
3.  **Non-Empty**: All generated text and JSON files must contain valid data (non-zero size).
4.  **Version Consistency**: The version in the artifact path must match the version in `pyproject.toml`.

## 4. Consumption and Deployment

To deploy a release artifact:

1.  Download the specific versioned directory from the artifact repository.
2.  Verify the checksums: `sha256sum -c checksums.sha256` (or `shasum -a 256`).
3.  Apply the Docker image tag specified in `docker_info.json` to the target environment.
4.  Update the environment variables based on `.env.example`.
5.  Run migrations:
    - In a containerized environment: The migrations are usually included in the Docker image. Run `docker run --rm <image> alembic upgrade head`.
    - In a local environment: Ensure the `src/` directory is present in your `PYTHONPATH` before running `alembic upgrade head`.

---
**Standard Owner:** Jules03 (Release Reliability & Governance)
**Last Updated:** May 2024
