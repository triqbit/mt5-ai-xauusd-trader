# Contributing to MT5 AI/ML Trading Bot

Thank you for your interest in contributing! As an institutional-grade trading system, we maintain high standards for code quality, safety, and reliability.

## 🏛️ Governance Model
- **Core Maintainer:** @andonly1348 (Jules03) - Final sign-off on all releases and core changes.
- **Trading Lead:** Responsible for MT5 connectors and risk engines.
- **ML Lead:** Responsible for model architectures and training pipelines.

## 🚀 Getting Started

### 1. Fork and Clone
```bash
git clone https://github.com/your-username/mt5-ai-xauusd-trader.git
cd mt5-ai-xauusd-trader
```

### 2. Local Environment Setup
We recommend using Python 3.11+.
```bash
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install -r requirements-ci.txt
```

### 3. Branching Strategy
- `main`: Production-ready stable code.
- `develop`: Integration branch for new features.
- `feature/*`: New features.
- `fix/*`: Bug fixes.
- `docs/*`: Documentation updates.

## 📝 Contribution Standards

### Conventional Commits
We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat`: A new feature (MINOR bump).
- `fix`: A bug fix (PATCH bump).
- `docs`: Documentation changes.
- `refactor`: Code change that neither fixes a bug nor adds a feature.
- `test`: Adding or correcting tests.
- `BREAKING CHANGE`: Add `!` after type/scope (MAJOR bump).

### Code Quality
- **Linting:** We use [Ruff](https://github.com/astral-sh/ruff). Run `ruff check .` before committing.
- **Typing:** Type hints are mandatory. Run `mypy src/ --ignore-missing-imports`.
- **Formatting:** Code must be formatted using Black standards (via Ruff).

## 🧪 Testing Requirements
- All new features MUST include unit tests.
- Code coverage must not drop below **80%**.
- Run tests locally:
  ```bash
  python -m pytest tests/
  ```

## ⚖️ Pull Request Process
1. Ensure your branch is up to date with `develop`.
2. Fill out the [PR Template](.github/PULL_REQUEST_TEMPLATE.md) completely.
3. PRs require at least one approval from a designated [CODEOWNER](.github/CODEOWNERS).
4. CI pipeline must pass (tests, security scan, linting).
5. If changing trading logic, provide backtest results or verification evidence.

## 🛡️ Security
If you find a security vulnerability, please do NOT open a public issue. Refer to the Security Report process in our issue templates.

---
*By contributing, you agree that your contributions will be licensed under the project's MIT License.*
