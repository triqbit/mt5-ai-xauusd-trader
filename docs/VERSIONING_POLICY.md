# Versioning Policy

This document defines the semantic versioning policy, automated changelog standards, and release tagging strategies for the MT5 AI/ML Trading Bot project.

## 1. Semantic Versioning (SemVer)

We strictly follow [Semantic Versioning 2.0.0](https://semver.org/). Versions are expressed as `MAJOR.MINOR.PATCH`.

### MAJOR (X.0.0)
Incremented when making incompatible API changes or fundamental shifts that require operator intervention. For this trading bot, this includes:
- **Breaking Risk Architecture**: Changes to how risk is calculated or enforced that could lead to unexpected exposure if not reviewed.
- **Incompatible Database Migrations**: Schema changes that cannot be automatically rolled back or that break existing data structures.
- **Core Strategy Overhaul**: Fundamental changes to the execution engine or signal processing logic that fundamentally change the bot's behavior.
- **Configuration Breaking Changes**: Removal or renaming of mandatory environment variables.

### MINOR (0.X.0)
Incremented when adding functionality in a backwards-compatible manner. Examples:
- **New Features**: Adding a new technical indicator, a new ML model architecture, or a new monitoring dashboard.
- **Non-breaking Risk Enhancements**: Adding new optional risk filters or tightening existing ones without breaking the execution flow.
- **Performance Improvements**: Significant optimizations that do not change external behavior.
- **Database Additions**: New tables or columns that do not affect existing queries.

### PATCH (0.0.X)
Incremented for backwards-compatible bug fixes. Examples:
- **Bug Fixes**: Resolving race conditions, fixing off-by-one errors in calculations, or correcting logging issues.
- **Security Patches**: Updating vulnerable dependencies.
- **Documentation Updates**: Improving runbooks, READMEs, or inline comments.
- **Refactoring**: Internal code cleanup with no change in functionality.

## 2. Conventional Commits

To enable automated changelog generation and version bumping, all commits to the `main` branch MUST follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

`<type>[optional scope]: <description>`

### Supported Types:
- `feat`: A new feature (corresponds to a **MINOR** version bump).
- `fix`: A bug fix (corresponds to a **PATCH** version bump).
- `security`: A security fix (corresponds to a **PATCH** version bump).
- `perf`: A code change that improves performance (corresponds to a **PATCH** version bump).
- `docs`: Documentation only changes (corresponds to a **PATCH** version bump).
- `refactor`: A code change that neither fixes a bug nor adds a feature (corresponds to a **PATCH** version bump).
- `style`, `test`, `chore`, `ci`: Internal changes that usually do not trigger a version bump unless they are part of a larger release.

### Breaking Changes:
Indicate a breaking change by adding a `!` after the type/scope or by adding `BREAKING CHANGE:` in the footer of the commit message. This triggers a **MAJOR** version bump.
*Example*: `feat!: overhaul risk management engine`

## 3. Pull Request Labels
PR labels can be used to override or supplement automation. This is particularly useful when a PR contains multiple commit types but should trigger a specific version increment.

- `release:major`: Forces a **MAJOR** version bump regardless of commit types.
- `release:minor`: Forces a **MINOR** version bump.
- `release:patch`: Forces a **PATCH** version bump.

If multiple labels are applied, the highest increment takes precedence (`major` > `minor` > `patch`).

## 4. Tagging & Release Strategy

### Stable Releases
- **Branch**: `main`
- **Tag Format**: `vMAJOR.MINOR.PATCH` (e.g., `v1.2.0`)
- **Requirement**: Must pass all CI/CD gates, including security scans, 85% test coverage, and pre-production checklists.

### Pre-releases (Release Candidates)
- **Tag Format**: `vMAJOR.MINOR.PATCH-rc.N` (e.g., `v1.1.0-rc.5`)
- **Use Case**: Final validation before a stable release.
- **Automation**: Triggered manually via the `Release Orchestration` workflow.

### Alpha/Beta Releases
- **Tag Format**: `vMAJOR.MINOR.PATCH-alpha.N` or `vMAJOR.MINOR.PATCH-beta.N`
- **Use Case**: Early testing of experimental features.

## 5. Automated Workflow

1. **Automated Changelog**: Every push to `main` triggers the `changelog.yml` workflow, which appends new conventional commits to the `CHANGELOG.md` file under the `[Unreleased]` section.
2. **Commit Validation**: Every Pull Request is checked by the `commit-check.yml` workflow to ensure it meets Conventional Commit standards.
3. **Version Bump Automation**: The `Release Orchestration` (`release.yml`) workflow:
   - Calculates the next version based on commit history (or uses provided input).
   - Updates `pyproject.toml` and `src/__init__.py`.
   - Transitions `[Unreleased]` content in `CHANGELOG.md` to a new versioned header.
   - Creates a new Git tag and GitHub Release.

## 6. Guidance for Version Bumping

| Change Type | Version Component | Example Commit |
| :--- | :--- | :--- |
| **Breaking Change** | MAJOR | `feat!: remove legacy risk manager` |
| **New Strategy** | MINOR | `feat: add trend-following ensemble model` |
| **Bug Fix** | PATCH | `fix: correct ATR calculation window` |
| **Dependency Update** | PATCH | `chore(deps): bump ruff to 0.4.3` |

## 7. Versioning Decision Matrix

| IF THE CHANGE... | THEN BUMP... | EXAMPLE |
| :--- | :--- | :--- |
| Changes a mandatory `.env` variable name | **MAJOR** | `feat!: rename MT5_SERVER to MT5_HOST` |
| Changes the risk calculation engine logic | **MAJOR** | `feat!: new drawdown calculation algorithm` |
| Adds a new Technical Indicator | **MINOR** | `feat: add Ichimoku Cloud support` |
| Adds a new command-line flag | **MINOR** | `feat: add --dry-run to backtester` |
| Fixes a calculation error in RSI | **PATCH** | `fix: correct RSI smoothing period` |
| Updates the README with new instructions | **PATCH** | `docs: add deployment troubleshooting section` |
| Optimizes a loop in feature engineering | **PATCH** | `perf: vectorize moving average calculation` |

---
**Policy Owner:** Jules03 (Release Reliability & Governance)
**Status:** Active
**Last Updated:** 2024-06-10
