# Contributing to MT5 AI/ML Trading Bot

Thank you for your interest in contributing! As an institutional-grade trading system, we maintain high standards for code quality, safety, and reliability.

## 🏛️ Governance Model
- **Core Maintainer:** @andonly1348 (Jules03) - Final sign-off on all releases and core changes.
- **Trading Lead:** @maintainer-trading - Responsible for MT5 connectors, risk engines, and analytics.
- **ML Lead:** @maintainer-models - Responsible for model architectures, environment, and research.
- **Quality Lead:** @maintainer-quality - Global oversight of standards, utilities, and CI/CD.

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

### 3. Find Your Path
Before you start coding, consult the [**Contribution Map**](./CONTRIBUTION_MAP.md) to identify the **Safe Zones** (low risk, fast review) vs. **Sensitive Zones** (high risk, mandatory lead review). This will help you choose a task that matches your expertise and current project needs.

### 4. Branching Strategy
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

### Code Quality & Formatting
- **Linting:** We use [Ruff](https://github.com/astral-sh/ruff). Run `ruff check .` before committing.
- **Typing:** Type hints are mandatory. Run `mypy src/ --ignore-missing-imports`.
- **Formatting:** Code must be formatted using Black standards (via Ruff).

## 🛡️ Quality Gates
Every Pull Request must pass the following mandatory gates:
1. **CI Pipeline:** Must pass all automated tests and linting.
2. **Code Coverage:** Minimum **80%** statement coverage. New code must be covered.
3. **Security Scan:** No HIGH or CRITICAL vulnerabilities (verified via Trivy/Bandit).
4. **License Compliance:** All new dependencies must have approved licenses (MIT, Apache 2.0, BSD).
5. **Documentation:** Documentation must be updated in `docs/` or root `.md` files if source code is modified.

## 🧪 Testing Requirements
- All new features MUST include unit tests.
- Risk-sensitive code (trading logic) must include integration tests or backtest evidence.
- Run tests locally:
  ```bash
  python -m pytest tests/ --cov=src --cov-report=term-missing
  ```

## ⚖️ Pull Request Process
0. **Check the Map:** Ensure your PR aligns with the [Contribution Map](./CONTRIBUTION_MAP.md) for its respective zone.
1. Ensure your branch is up to date with `develop`.
2. Fill out the [PR Template](.github/PULL_REQUEST_TEMPLATE.md) completely.
3. PRs require at least one approval from a designated [CODEOWNER](.github/CODEOWNERS).
4. For changes to `src/trading/` or `src/core/`, explicit approval from @andonly1348 or the respective Lead is required.
5. All mandatory Quality Gates must be green.

## 🛡️ Security
If you find a security vulnerability, please do NOT open a public issue. Use the Security Report template or contact the maintainers privately at security@example.com.

---
*By contributing, you agree that your contributions will be licensed under the project's MIT License.*
