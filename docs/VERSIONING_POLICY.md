# Versioning Policy

This document defines the versioning and changelog strategy for the MT5 AI/ML Trading Bot project.

## 1. Semantic Versioning (SemVer)

We strictly follow [Semantic Versioning 2.0.0](https://semver.org/). Versions are in the format `MAJOR.MINOR.PATCH`.

- **MAJOR**: Incompatible API changes, breaking changes in trading logic, or major architectural shifts.
- **MINOR**: Backward-compatible functionality additions, new trading indicators, or model enhancements.
- **PATCH**: Backward-compatible bug fixes, security patches, or documentation updates.

## 2. Version Bump Guidance

| Change Type | Version Component | Example |
| :--- | :--- | :--- |
| Breaking changes | MAJOR | `1.5.2` -> `2.0.0` |
| New features | MINOR | `1.5.2` -> `1.6.0` |
| Bug fixes / Refactor | PATCH | `1.5.2` -> `1.5.3` |

## 3. Pre-release vs. Stable Release

### Stable Releases
Stable releases are tagged on the `main` branch. They represent production-ready code that has passed all CI/CD gates and manual approvals.
Tag format: `vMAJOR.MINOR.PATCH` (e.g., `v1.0.0`)

### Pre-releases (Alpha/Beta/RC)
Pre-releases are used for testing new features before they are finalized.
Tag format: `vMAJOR.MINOR.PATCH-pre.X` (e.g., `v1.1.0-rc.1`)

## 4. Automated Changelog & Versioning

The project uses GitHub Actions to automate versioning and changelog generation.

### Conventional Commits
We encourage (but do not strictly enforce if using PR labels) the use of [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` for new features (MINOR bump)
- `fix:` for bug fixes (PATCH bump)
- `perf:`, `docs:`, `refactor:`, `style:`, `test:`, `chore:` (PATCH bump)
- `BREAKING CHANGE:` in footer or `!` after type (MAJOR bump)

### Pull Request Labels
The automation primarily uses PR labels to categorize changes and determine the next version bump:
- `release:major`: Triggers a MAJOR version bump.
- `release:minor` or `feature`: Triggers a MINOR version bump.
- `release:patch` or `fix` or `bug`: Triggers a PATCH version bump.

### Automated Workflow
1. When a PR is merged to `main`, the `changelog.yml` workflow is triggered.
2. It analyzes the PR labels or conventional commits.
3. It generates/updates `CHANGELOG.md`.
4. It creates a new GitHub Release and Git Tag.
5. It updates the version in `pyproject.toml` and `src/__init__.py`.

## 5. Enforcement

- All Pull Requests MUST have at least one appropriate label before merging.
- Merges to `main` without versioning labels will default to a PATCH bump if no other information is available.
- Direct pushes to `main` are restricted to ensure the automated workflow remains the source of truth for releases.
