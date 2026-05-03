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
- `main`: Production-ready stable code. No direct commits allowed.
- `develop`: Integration branch for new features.
- `feature/*`: New features.
- `fix/*`: Bug fixes.
- `docs/*`: Documentation updates.

## ⚖️ Pull Request Lifecycle

1.  **Preparation:** Ensure your branch is up to date with `develop`.
2.  **Implementation:** Follow the code quality and testing standards below.
3.  **Self-Review:** Perform a thorough self-review of your changes.
4.  **Submission:** Open a PR targeting `develop`. Fill out the [PR Template](../.github/PULL_REQUEST_TEMPLATE.md) completely.
5.  **Quality Gates:** Automated CI will run. All checks (Tests, Coverage, Security, Lint) MUST pass.
6.  **Review:** Tag the appropriate [CODEOWNERS](../.github/CODEOWNERS) based on the modules modified.
7.  **Address Feedback:** Respond to and implement requested changes.
8.  **Merge:** Once approved and gates pass, a maintainer will merge the PR.

## 🛡️ Quality Gates & Standards

Every Pull Request must pass the following mandatory gates:
1.  **CI Pipeline:** Must pass all automated tests and linting.
2.  **Code Coverage:** Minimum **85%** statement coverage (as defined in `EXCELLENCE_BLUEPRINT.md`). New code must be covered.
3.  **Security Scan:** No HIGH or CRITICAL vulnerabilities (verified via `pip-audit` and `Trivy`).
4.  **License Compliance:** All new dependencies must have approved licenses (MIT, Apache 2.0, BSD). See `docs/LICENSE_COMPLIANCE.md`.
5.  **Documentation:** Documentation must be updated in `docs/` or root `.md` files if source code is modified.
6.  **Type Safety:** `mypy` must pass with zero errors on the modified code.

## 📝 Coding Standards

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
- **Formatting:** Code must be formatted using Black standards (via `ruff format src/ main.py`).

## 🧪 Testing Requirements
- All new features MUST include unit tests in `tests/`.
- Risk-sensitive code (trading logic) must include integration tests or backtest evidence.
- Run tests locally:
  ```bash
  python -m pytest tests/ --cov=src --cov-report=term-missing
  ```

## 🛡️ Security First
If you find a security vulnerability, please **do NOT open a public issue**.
1.  Read the [SECURITY Policy](../SECURITY.md).
2.  Report via **GitHub Private Vulnerability Reporting** (preferred).
3.  Or use the **Security Report** issue template which is configured for private triage.

## 📖 Related Policies
- [Versioning Policy](./VERSIONING_POLICY.md)
- [Release Playbook](./RELEASE_PLAYBOOK.md)
- [SLO Targets](./SLO_TARGETS.md)

---
*By contributing, you agree that your contributions will be licensed under the project's MIT License.*
