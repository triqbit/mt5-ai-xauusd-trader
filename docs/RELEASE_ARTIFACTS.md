# Release Artifact Standards

This document defines the requirements for a valid, deployable release artifact for the MT5 AI/ML Trading Bot.

## Artifact Components

A standard release artifact must be a compressed archive (`.tar.gz`) containing the following components:

1.  **Docker Image**: A tagged Docker image saved as a tarball (`image.tar`). This ensures environment consistency and reproducibility.
2.  **Environment Template**: A `.env.example` file documenting all required and optional environment variables.
3.  **Database Migrations**: The `migrations/` directory containing all Alembic scripts required to bring the database schema to the correct version.
4.  **Configuration Documentation**: `docs/CONFIGURATION.md` providing detailed explanations of settings.
5.  **Release Notes**: `CHANGELOG.md` documenting the changes included in the release.
6.  **Checksum Manifest**: A `checksums.sha256` file containing SHA256 hashes of all files within the archive to ensure integrity.

## Validation Criteria

An artifact is considered valid and deployable ONLY if:

*   The `scripts/package_release.sh` completes without errors.
*   All mandatory components listed above are present in the archive.
*   The Docker image can be loaded and started successfully.
*   The checksums in the manifest match the files in the artifact.
*   The `CHANGELOG.md` contains an entry for the current version.

## Packaging Process

The packaging is automated via the `scripts/package_release.sh` script.

```bash
./scripts/package_release.sh <version>
```

Example:
```bash
./scripts/package_release.sh 1.0.0
```

This will generate a `release-v1.0.0.tar.gz` file in the root directory.
