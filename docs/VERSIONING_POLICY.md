# Versioning Policy

This document defines the semantic versioning policy and automated changelog standards for the MT5 AI/ML Trading Bot project.

## 1. Semantic Versioning (SemVer)

We follow [Semantic Versioning 2.0.0](https://semver.org/). Versions are expressed as `MAJOR.MINOR.PATCH`.

- **MAJOR**: Incompatible API changes, or fundamental shifts in trading logic/risk architecture that require manual intervention or migration.
- **MINOR**: New features added in a backwards-compatible manner (e.g., a new technical indicator, a new model architecture, or a new monitoring dashboard).
- **PATCH**: Backwards-compatible bug fixes, security patches, or documentation updates.

## 2. Conventional Commits

To enable automated changelog generation and version bumping, all commits to the `main` and `develop` branches MUST follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

`<type>[optional scope]: <description>`

### Supported Types:
- `feat`: A new feature (corresponds to a MINOR version bump).
- `fix`: A bug fix (corresponds to a PATCH version bump).
- `perf`: A code change that improves performance.
- `docs`: Documentation only changes.
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, etc).
- `refactor`: A code change that neither fixes a bug nor adds a feature.
- `test`: Adding missing tests or correcting existing tests.
- `chore`: Updating build tasks, package manager configs, etc.
- `ci`: Changes to CI configuration files and scripts.

### Breaking Changes:
Indicate a breaking change by adding a `!` after the type/scope or by adding `BREAKING CHANGE:` in the footer of the commit message. This triggers a MAJOR version bump.

## 3. Tagging Strategy

### Stable Releases
Stable releases are tagged on the `main` branch:
- Format: `vMAJOR.MINOR.PATCH` (e.g., `v1.2.0`)
- These represent production-ready code that has passed all CI/CD gates.

### Pre-releases
Pre-releases can be used for beta testing or integration validation:
- Format: `vMAJOR.MINOR.PATCH-<tag>.N` (e.g., `v1.2.0-rc.1`, `v1.2.0-alpha.5`)
- Pre-releases are typically tagged on the `develop` or feature branches.

## 4. Automated Workflow

1. **Changelog**: On every push to `main`, a GitHub Action automatically updates the `CHANGELOG.md` file based on the commits since the last release.
2. **Version Bump**: The `Release Orchestration` workflow handles the final versioning and tagging based on the provided input or commit history analysis.
3. **Drafting Releases**: The CI pipeline will automatically draft a GitHub Release with the generated changelog for final review by the Release Lead (Jules03).

## 5. Guidance for Version Bumping

| Change Type | Version Component | Example |
| :--- | :--- | :--- |
| Breaking Change | MAJOR | `1.5.2` -> `2.0.0` |
| New Feature | MINOR | `1.5.2` -> `1.6.0` |
| Bug Fix | PATCH | `1.5.2` -> `1.5.3` |
| Security Patch | PATCH | `1.5.3` -> `1.5.4` |
| Dependency Update | PATCH | `1.5.4` -> `1.5.5` |

---
**Policy Owner:** Jules03 (Release Reliability & Governance)
**Status:** Active
**Last Updated:** May 2024
