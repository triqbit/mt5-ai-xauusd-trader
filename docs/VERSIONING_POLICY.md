# Versioning Policy

This document defines the semantic versioning policy, automated changelog standards, and release tagging strategies for the MT5 AI/ML Trading Bot project.

## 1. Semantic Versioning (SemVer)

We strictly follow [Semantic Versioning 2.0.0](https://semver.org/). Versions are expressed as `MAJOR.MINOR.PATCH`.

- **MAJOR**: Incompatible API changes, fundamental shifts in trading logic, or major risk architecture modifications that require manual intervention or data migration.
- **MINOR**: New features added in a backwards-compatible manner (e.g., a new technical indicator, a new model architecture, or a new monitoring dashboard).
- **PATCH**: Backwards-compatible bug fixes, security patches, or documentation updates.

## 2. Conventional Commits

To enable automated changelog generation and version bumping, all commits to the `main` branch MUST follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

`<type>[optional scope]: <description>`

### Supported Types:
- `feat`: A new feature (corresponds to a **MINOR** version bump).
- `fix`: A bug fix (corresponds to a **PATCH** version bump).
- `perf`: A code change that improves performance (corresponds to a **PATCH** version bump).
- `docs`: Documentation only changes (corresponds to a **PATCH** version bump).
- `refactor`: A code change that neither fixes a bug nor adds a feature (corresponds to a **PATCH** version bump).
- `style`, `test`, `chore`, `ci`: Internal changes that usually do not trigger a version bump unless they are part of a larger release.

### Breaking Changes:
Indicate a breaking change by adding a `!` after the type/scope or by adding `BREAKING CHANGE:` in the footer of the commit message. This triggers a **MAJOR** version bump.

## 3. Tagging & Release Strategy

### Stable Releases
- **Branch**: `main`
- **Tag Format**: `vMAJOR.MINOR.PATCH` (e.g., `v1.2.0`)
- **Requirement**: Must pass all CI/CD gates, including security scans and pre-production checklists.

### Pre-releases
- **Tag Format**: `vMAJOR.MINOR.PATCH-<tag>.N` (e.g., `v1.2.0-rc.1`, `v1.2.0-alpha.5`)
- **Use Case**: Beta testing, integration validation, or release candidates.
- **Automation**: Pre-releases can be triggered manually via the `Release Orchestration` workflow.

## 4. Automated Workflow

1. **Automated Changelog**: Every push to `main` triggers the `changelog.yml` workflow, which appends new conventional commits to the `CHANGELOG.md` file under the `[Unreleased]` section.
2. **Version Bump Automation**: The `Release Orchestration` (`release.yml`) workflow:
   - Calculates the next version based on commit history (using `github-tag-action`).
   - Updates `pyproject.toml` and `src/__init__.py`.
   - Creates a new Git tag and GitHub Release.
3. **Manual Override**: The release version can be manually specified during workflow dispatch if needed.

## 5. Guidance for Version Bumping

| Change Type | Version Component | Example Commit |
| :--- | :--- | :--- |
| **Breaking Change** | MAJOR | `feat!: overhaul execution engine` |
| **Breaking Change** | MAJOR | `fix: API BREAKING CHANGE: ...` |
| **New Feature** | MINOR | `feat: add PPO reinforcement learning agent` |
| **Bug Fix** | PATCH | `fix: resolve race condition in order execution` |
| **Performance** | PATCH | `perf: optimize vectorized feature extraction` |
| **Security** | PATCH | `fix: update vulnerable dependency` |
| **Documentation** | PATCH | `docs: update disaster recovery runbook` |

---
**Policy Owner:** Jules03 (Release Reliability & Governance)
**Status:** Active
