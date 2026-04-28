# Contributing to MT5 AI/ML Trading Bot

First off, thank you for considering contributing to the MT5 AI/ML Trading Bot! It's people like you who make this a great tool for the quantitative finance community.

This project is an enterprise-grade trading system. To maintain safety and reliability, we have established clear pathways for contribution.

## 🗺️ Contribution Map

Before you start, please review our [Contribution Map](./docs/CONTRIBUTION_MAP.md) to understand the "Safe Zones" and "Sensitive Zones" of the codebase.

## 🚀 Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/mt5-ai-xauusd-trader.git
   cd mt5-ai-xauusd-trader
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-ci.txt
   ```
4. **Set up pre-commit hooks**:
   ```bash
   pre-commit install
   ```

## 🌿 Branching Strategy

We use descriptive branch names to keep our workflow organized. Please name your branch based on the type of change:

- `feat/your-feature-name` for new features.
- `fix/your-fix-name` for bug fixes.
- `docs/your-doc-improvement` for documentation changes.
- `refactor/your-refactor-name` for code refactoring.
- `test/your-test-name` for adding or improving tests.

## 🛠️ Development Workflow

1. **Create a new branch** from `main` (or `develop` if applicable).
2. **Make your changes**. Ensure you follow the [Enterprise Standards](./ENTERPRISE_STANDARDS.md).
3. **Write or update tests** for your changes.
4. **Run tests and linting**:
   ```bash
   pytest tests/
   ruff check .
   ruff format --check .
   ```
5. **Commit your changes** with a clear and descriptive commit message.

## 📤 Pull Request Process

1. **Push your branch** to your fork.
2. **Submit a Pull Request** to the `main` branch of the original repository.
3. **PR Template Requirements**:
   - **Problem**: Describe the issue you are solving.
   - **Solution**: Describe the changes you made.
   - **Impact**: Describe the expected outcome.
   - **Validation**: List the tests you ran and their results.
4. **CI Pipeline**: All PRs must pass the CI pipeline (Linting, Security Audit, Tests) before being reviewed.

## 🛡️ Safety Boundaries

Do NOT modify:
- Core trading execution or strategy logic.
- Risk or position sizing behavior.
- Secrets, credentials, or authentication handling.
- Production deployment pipelines or release orchestration.

If your proposed change needs to touch these areas, please open an issue first to discuss it with the core maintainers.

## 🤝 Code of Conduct

By participating in this project, you agree to abide by our standards of professional and respectful conduct.

---

*Happy Trading!*
