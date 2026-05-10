# Enterprise Standards for MT5 AI/ML Trading Bot

This document outlines the engineering standards and quality expectations for all contributions to the repository.

## 1. Code Quality & Standards

### A. Linting & Formatting
We use `ruff` for linting and formatting. All code must pass `ruff check .` and `ruff format .`.

### B. Type Safety
We use `mypy` for static type checking. All source code in `src/` must be fully type-hinted.

### C. Documentation
- Use Google-style docstrings for all public classes and functions.
- Maintain up-to-date documentation in the `docs/` directory.

## 2. Testing Standards
- **Unit Tests:** Required for all new logic.
- **Integration Tests:** Required for MT5 and Database interactions.
- **Coverage:** Minimum 85% statement coverage is mandated for all PRs.
- **TDD:** We encourage Test-Driven Development for core trading and risk logic.

## 3. Git & Workflow
- **Branching:** Use `feature/`, `bugfix/`, `hotfix/`, or `docs/` prefixes.
- **Commits:** Follow Conventional Commits (e.g., `feat:`, `fix:`, `chore:`).
- **PRs:** Must complete the PR template and pass all CI gates.

## 4. Security
- Never commit secrets or `.env` files.
- Report vulnerabilities privately according to `SECURITY.md`.
- Use `pip-audit` to check for dependency vulnerabilities.

## 5. Performance
- Minimize latency in the trading loop.
- Use efficient data structures for high-frequency market data handling.
