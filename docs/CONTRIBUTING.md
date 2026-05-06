# Contributing to MT5 AI/ML Trading Bot

Thank you for your interest in contributing! As an institutional-grade trading system, we maintain high standards for code quality, safety, and reliability. This project follows an enterprise-grade governance model to ensure every change is verified, auditable, and production-safe.

---

## 🏛️ Governance Model

We use a role-based governance model where specific leads oversee different domains. You can identify the required reviewers in [.github/CODEOWNERS](../.github/CODEOWNERS).

- **Jules01 (Trading Lead) — `@maintainer-trading`:** Oversees MT5 connectors, risk engines, and execution logic.
- **Jules02 (Security & CI Lead) — `@xnessom`:** Manages dependency security, CI/CD hardening, and Docker infrastructure.
- **Jules03 (Release & Governance Lead) — `@andonly1348`:** Final sign-off on releases, production readiness, and governance policy.
- **Jules04 (ML/Quant Lead) — `@maintainer-models`:** Responsible for model architectures, feature engineering, and research.
- **Jules05 (Product Lead) — `@andonly1348`:** Oversees product strategy, business logic, and enterprise delivery.
- **Jules06 (Quality Lead) — `@maintainer-quality`:** Ensures testing rigour, code standards, and observability compliance.

---

## 🚀 Contributor Workflow

### 1. Preparation
- **Fork and Clone:** Create your own fork and clone it locally.
- **Setup Environment:** Use Python 3.11+. Follow the [Setup Guide](../SETUP_GUIDE.md).
- **Consult the [Contribution Map](./CONTRIBUTION_MAP.md):** Identify if your change falls into a **Safe Zone** (docs, tests) or a **Sensitive Zone** (trading logic, models).

### 2. Implementation
- **Branching Strategy:** Use descriptive branch names prefixed by type:
  - `feature/` for new features (e.g., `feature/ppo-optim-v2`)
  - `bugfix/` for bug fixes (e.g., `bugfix/mt5-conn-leak`)
  - `hotfix/` for emergency production fixes
  - `docs/` for documentation-only changes
- **Conventional Commits:** We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification (e.g., `feat:`, `fix:`, `docs:`, `chore:`).
- **Standards:** Adhere to [ENTERPRISE_STANDARDS.md](../ENTERPRISE_STANDARDS.md) for linting, typing, and documentation.
- **Quality Gates:** Your code must pass all local quality gates before submission.

### 3. Pull Request Submission & Lifecycle
- **Target Branch:** All PRs should target the `develop` branch unless they are critical hotfixes for `main`.
- **Draft PRs:** Open a Draft PR early to get feedback on architectural direction.
- **Complete the PR Template:** Use the [.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md) and fill out every section, including the **Rollback Strategy**.
- **Evidence:** Attach test logs, coverage reports, and backtest evidence (if applicable).
- **Review Cycle:** At least one approval from a designated [CODEOWNER](../.github/CODEOWNERS) is required. Changes to **Sensitive Zones** require multi-signature approval from at least two leads (typically the domain lead and Jules03).
- **Merge Criteria:** Once all CI gates pass and approval is received, Jules03 or the module lead will merge the PR.

---

## 🛡️ Mandatory Quality Gates

Every Pull Request must pass the following gates to be eligible for merge:

1.  **CI Pipeline:** Must pass all automated checks in GitHub Actions.
2.  **Code Coverage:** Minimum **85%** statement coverage. New code must include tests.
3.  **Type Safety:** `mypy` must return zero errors for all modified files.
4.  **Linting:** `ruff check .` must return zero errors.
5.  **Security Scan:** `pip-audit` must show zero vulnerabilities in dependencies.
6.  **License Compliance:** All new dependencies must comply with [docs/LICENSE_COMPLIANCE.md](./LICENSE_COMPLIANCE.md).
7.  **Documentation:** Documentation in `docs/` must be updated to reflect any source code changes.

---

## 🧪 Testing Requirements

We practice Test-Driven Development (TDD) where possible.
- **Unit Tests:** Mandatory for all new functions and classes.
- **Integration Tests:** Required for changes touching MT5 connectors or database schemas.
- **Resilience Tests:** Mandatory for risk-management logic.

Run the full suite locally:
```bash
# Run tests with coverage
python3 -m pytest tests/ --cov=src --cov-report=term-missing

# Run environment diagnostics
python3 scripts/doctor.py
```

---

## 🛡️ Security First

If you discover a security vulnerability, please **do NOT open a public issue**.
- Follow the [Security Policy](../SECURITY.md).
- Report via **GitHub Private Vulnerability Reporting**.
- For critical issues, contact the leads listed in `SECURITY.md`.

---

## 📖 Additional Resources
- [Versioning Policy](./VERSIONING_POLICY.md)
- [Release Playbook](./RELEASE_PLAYBOOK.md)
- [SLO Targets](./SLO_TARGETS.md)
- [Architecture Quick-Start](./ARCHITECTURE_QUICK.md)

---
*By contributing, you agree that your contributions will be licensed under the project's MIT License.*
