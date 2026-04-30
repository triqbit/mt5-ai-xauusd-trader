# Contributing to MT5 AI/ML Trading Bot

Thank you for your interest in contributing to our project! To maintain high standards of reliability and production safety, we follow a structured contribution process.

## Contribution Workflow

### 1. Branching Strategy
- **main**: Production-ready code. Only merged from `develop` via release PRs.
- **develop**: Integration branch for new features and fixes.
- **feature/**: New features (e.g., `feature/new-indicator`).
- **fix/**: Bug fixes (e.g., `fix/connection-timeout`).
- **docs/**: Documentation-only changes.

### 2. Commit Conventions
We follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat: ...` for new features.
- `fix: ...` for bug fixes.
- `docs: ...` for documentation.
- `refactor: ...` for code refactoring.
- `test: ...` for adding/updating tests.

### 3. Pull Request Process
1. **Fork the repository** and create your branch from `develop`.
2. **Implement changes** and add/update tests.
3. **Verify locally**:
   - Run tests: `python -m pytest tests/`
   - Check linting: `ruff check .`
4. **Submit a Pull Request** to the `develop` branch.
5. **Fill out the PR template** checklist completely.
6. **Code Review**: At least one approval from a designated code owner is required.

## Required PR Checks
Before a PR can be merged, it must pass the following gates:
- **Unit & Integration Tests**: All tests in `tests/` must pass.
- **Test Coverage**: New code should aim for >80% coverage.
- **Linting & Style**: No linting errors (enforced via CI).
- **Security Audit**: No hardcoded secrets or vulnerable dependencies.
- **Documentation**: All new features must be documented in `docs/` and have docstrings.

## Code Ownership
Certain modules require approval from specific maintainers:
- `src/core/`: @andonly1348
- `src/trading/`: @maintainer-trading
- `src/models/`: @maintainer-models

## Coding Standards
- Use Python 3.10+ type hints.
- Follow Google-style docstrings.
- Adhere to the Enterprise Standards defined in `ENTERPRISE_STANDARDS.md`.

## Reporting Issues
- Use the provided issue templates for [Bugs](.github/ISSUE_TEMPLATE/bug_report.yml), [Features](.github/ISSUE_TEMPLATE/feature_request.yml), and [Security](.github/ISSUE_TEMPLATE/security_report.yml).

Thank you for helping us build a more reliable trading system!
