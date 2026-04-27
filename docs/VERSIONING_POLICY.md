# Versioning Policy

This document defines the versioning and release strategy for the MT5 AI/ML Trading Bot project.

## Semantic Versioning (SemVer)

The project adheres to [Semantic Versioning 2.0.0](https://semver.org/). Versions are expressed in the format `MAJOR.MINOR.PATCH`.

- **MAJOR** version when you make incompatible API changes or significant architectural shifts.
- **MINOR** version when you add functionality in a backwards-compatible manner, or introduce significant changes to trading logic.
- **PATCH** version when you make backwards-compatible bug fixes or minor configuration tweaks.

### Guidance for Version Bumping

| Change Type | Version Bump | Examples |
| :--- | :--- | :--- |
| **Breaking Change** | `MAJOR` | Removal of core configuration parameters, database schema changes that are not backwards compatible, or a complete rewrite of the trading engine. |
| **Feature / Logic Change** | `MINOR` | Adding a new technical indicator, introducing a new model ensemble method, adding a new risk management module, or significant performance optimizations. |
| **Bug Fix / Maintenance** | `PATCH` | Fixing a logic error in risk calculations, documentation updates, dependency security patches, or minor UI/Logging improvements. |

## Release Tagging Strategy

- **Stable Releases**: Tagged as `vMAJOR.MINOR.PATCH` (e.g., `v1.2.3`). These are ready for production use.
- **Pre-releases**: Tagged with a suffix like `vMAJOR.MINOR.PATCH-alpha.X` or `vMAJOR.MINOR.PATCH-beta.X`. These are for testing and staging only.

## Automation

We use `release-please-action` to automate versioning and changelog generation.

### Conventional Commits

Version bumps and changelog entries are driven by [Conventional Commits](https://www.conventionalcommits.org/).

- `fix:` triggers a **PATCH** bump.
- `feat:` triggers a **MINOR** bump.
- `feat!:` or `fix!:` (or `BREAKING CHANGE:` in the footer) triggers a **MAJOR** bump.

Other types (e.g., `docs:`, `chore:`, `refactor:`, `test:`) do not trigger a version bump by default but are included in the changelog.

### Automated Workflow

1.  When a PR is merged into the `main` branch, the `changelog.yml` workflow runs.
2.  It calculates the next version based on the commit history.
3.  It updates `CHANGELOG.md`, `pyproject.toml`, and `src/__init__.py`.
4.  It creates/updates a Release PR.
5.  Merging the Release PR will tag the repository and create a GitHub Release.
