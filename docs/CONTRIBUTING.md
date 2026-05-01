# Contributing to MT5 AI/ML Trading Bot

Thank you for your interest in contributing to the MT5 AI/ML Trading Bot project! This document provides guidance on our contribution workflow and standards.

## 🏛️ Governance Model

This project uses a **Code Owners** model to ensure high-quality reviews:
- **Trading Engine (`src/trading/`):** Requires approval from `@mt5-bot/trading-leads`.
- **AI/ML Models (`src/models/`):** Requires approval from `@mt5-bot/ml-engineers`.
- **Core Framework (`src/core/`):** Requires approval from `@mt5-bot/core-maintainers`.

## 🛠️ Development Workflow

1. **Fork & Clone:** Fork the repository and clone it locally.
2. **Create a Branch:** Use descriptive branch names (e.g., `feat/add-rsi-filter` or `fix/mt5-reconnect`).
3. **Set Up Environment:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-ci.txt  # For linting and tests
   pre-commit install
   ```
4. **Implement Changes:** Follow our [Coding Standards](#-coding-standards).
5. **Run Tests:**
   ```bash
   python -m pytest tests/
   ```
6. **Commit & Push:** Ensure all pre-commit hooks pass.
7. **Submit PR:** Fill out the [PULL_REQUEST_TEMPLATE](../.github/PULL_REQUEST_TEMPLATE.md) completely.

## 📏 Coding Standards

- **Formatting:** We use `black` for formatting and `isort` for import sorting.
- **Linting:** `ruff` and `flake8` (max-line-length: 100).
- **Type Checking:** All new code must have type hints and pass `mypy`.
- **Docstrings:** Use Google-style docstrings for all modules, classes, and functions.
- **Complexity:** Keep functions small and focused (SRP).

## 🧪 Testing Requirements

- **Unit Tests:** Mandatory for all new logic.
- **Integration Tests:** Required for MT5 connector or database changes.
- **Backtest Verification:** ML model changes must include backtest results.
- **Coverage:** We aim for >80% code coverage.

## 🛡️ Security Policy

- **No Secrets:** Never commit `.env` files, API keys, or broker credentials.
- **Input Validation:** Use Pydantic for all configuration and external data.
- **Audit Logs:** Ensure significant actions (trades, config changes) are logged to the audit trail.

## 📚 Documentation

- Update `README.md` if user-facing changes are made.
- Update internal guides in `docs/` for architectural changes.
- Add release notes to `CHANGELOG.md` following [Conventional Commits](https://www.conventionalcommits.org/).

## ⚖️ License

By contributing, you agree that your contributions will be licensed under the project's [MIT License](../LICENSE).
