# Versioning Policy

## 📌 Overview
This project follows [Semantic Versioning 2.0.0 (SemVer)](https://semver.org/) for its release strategy. This policy ensures predictable releases and maintains compatibility across the enterprise trading infrastructure.

## 🔢 Version Format
Versions are expressed as `MAJOR.MINOR.PATCH`:
- **MAJOR**: Incompatible API changes, significant architectural shifts, or breaking changes in the trading logic/execution engine.
- **MINOR**: Backward-compatible functionality additions, such as new indicators, trading strategies, or configuration options.
- **PATCH**: Backward-compatible bug fixes, security patches, or documentation updates.

## 🚀 Version Increment Guidelines

### Increment MAJOR when:
1. Breaking changes are introduced to the core trading engine (`src/trading/`).
2. Database schema migrations that are not backward compatible.
3. Major dependency upgrades that require code refactoring (e.g., migrating from DRL v2 to v3).
4. Removing deprecated features or APIs.

### Increment MINOR when:
1. Adding a new AI/ML model architecture in `src/models/`.
2. Implementing new market indicators or feature engineering techniques.
3. Adding support for new symbols or asset classes.
4. Introducing new configuration settings that don't break existing setups.

### Increment PATCH when:
1. Fixing bugs in the execution filter or risk management logic.
2. Updating dependencies for security (CVE fixes).
3. Improving documentation or internal logging.
4. Performance optimizations that do not change external behavior.

## 🧪 Pre-release Strategy
Before a stable release, the project may use pre-release tags to allow for testing:
- **Alpha (`-alpha.X`)**: Internal testing, feature-incomplete.
- **Beta (`-beta.X`)**: Feature-complete, open for wider testing and bug reports.
- **Release Candidate (`-rc.X`)**: Final validation phase before the stable release.

Example: `1.1.0-rc.1`

## 🛠 Automation & Conventional Commits
To facilitate automated changelog generation and version bumping, this project enforces [Conventional Commits](https://www.conventionalcommits.org/):

- `fix:` -> Triggers a **PATCH** bump.
- `feat:` -> Triggers a **MINOR** bump.
- `perf:`, `refactor:`, `docs:`, `style:`, `test:`, `build:`, `ci:` -> Usually no bump or **PATCH** bump.
- `BREAKING CHANGE:` (or `!` in the header) -> Triggers a **MAJOR** bump.

## 📋 Release Checklist
Every release must pass the following checks:
1. CI Pipeline (Tests, Linting, Security Scans) is green.
2. `CHANGELOG.md` is updated (automatically or manually).
3. Version is updated in `pyproject.toml` and `src/__init__.py`.
4. Git tag is created and pushed.
