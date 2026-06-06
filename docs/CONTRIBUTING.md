# Contributing to MT5 AI/ML Trading Bot

Thank you for your interest in contributing! As an institutional-grade trading system, we maintain high standards for code quality, safety, and reliability. This project follows an enterprise-grade governance model to ensure every change is verified, auditable, and production-safe.

---

## 🏛️ Governance Model

We use a role-based governance model where specific leads oversee different domains. You can identify the required reviewers in [.github/CODEOWNERS](../.github/CODEOWNERS).

- **Jules01 (Core & Trading) — `@triqbit`:** Oversees core architecture, MT5/XAUUSD trading logic, and system performance.
- **Jules02 (Security & Quality) — `@xnessom`:** Manages security, validation, CI quality, and system observability.
- **Jules03 (Release & Reliability) — `@andonly1348`:** Oversees release reliability, enterprise delivery, and governance compliance.
- **Jules04 (Quant & Research) — `@saysgrok`:** Responsible for model architectures, adaptive intelligence, and research simulations.
- **Jules05 (Product & Integration) — `@yxynoty`:** Oversees product stewardship, integration governance, and feature portfolio.
- **Jules06 (Developer Experience) — `@qufuwan`:** Owns the safe contribution pathway, developer runtime, and technical credibility.

---

## 🚀 Contributor Workflow

### 1. Preparation
- **Fork and Clone:** Create your own fork and clone it locally.
- **Setup Environment:** Use Python 3.11+. Follow the [Setup Guide](../SETUP_GUIDE.md).
- **Consult the [Contribution Map](./CONTRIBUTION_MAP.md):** Identify if your change falls into a **Safe Zone** (docs, tests) or a **Sensitive Zone** (trading logic, models, core).

### ⚠️ Critical: History Management & Daily Resets
This repository operates under a high-frequency update model. Please read the following carefully:
- **Daily History Grafting:** The `main` branch is updated daily via monolithic "grafts" (total repository swaps). This means standard Git history is often unavailable on `main`.
- **Mandatory Rebase:** Because `main` resets daily, your feature branch **must** be rebased onto the latest `main` commit before submission. Use `git fetch origin main` and `git rebase origin/main`.
- **Environment Stability:** If `make bootstrap` fails, check `docs/status/PROJECT_HEALTH.md` for known dependency conflicts or transient environment issues.

#### 🛠️ Graft Survival Kit (CLI)
If your branch has diverged significantly or "lost its ancestor" due to a daily graft, use this sequence to resync:

```bash
# 1. Update your local main cache
git fetch origin main

# 2. Rebase your work onto the new graft
# If standard rebase fails, you may need to use --onto
git rebase origin/main

# 3. If you get "no common ancestry" errors:
# This happens when main is force-pushed with a new history graft.
git rebase --onto origin/main <old-base-commit> <your-branch-name>
```

### 2. Implementation
- **Branching Strategy:** We enforce a strict branching strategy to ensure traceability. All development must occur on branches prefixed by type:
  - `feature/`: New capabilities or enhancements (e.g., `feature/ppo-optim-v2`)
  - `bugfix/`: Fixes for identified issues (e.g., `bugfix/mt5-conn-leak`)
  - `hotfix/`: Emergency production patches directly against `main`
  - `docs/`: Documentation-only improvements
  - `refactor/`: Code reorganization without functional changes
- **Conventional Commits:** All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification (e.g., `feat:`, `fix:`, `docs:`, `chore:`, `security:`). This enables automated changelog generation and versioning.
- **Standards:** Adhere to [ENTERPRISE_STANDARDS.md](./ENTERPRISE_STANDARDS.md) for linting, typing, and documentation.

### 3. Pull Request Lifecycle
1.  **Draft PR:** Open a Draft PR early to get feedback on architectural direction.
2.  **Mandatory Checks:** Ensure your PR passes all automated CI gates (Lint, Type, Security, Tests).
3.  **Governance Template:** Complete the [.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md) in full.
4.  **Evidence:** Attach test logs, coverage reports, and backtest evidence.
5.  **Review Cycle:** At least one approval from a designated [CODEOWNER](../.github/CODEOWNERS) is required.
6.  **Multi-Signature Sign-off:** Changes to **Sensitive Zones** (Trading, Models, Core) require mandatory multi-signature approval from both the relevant domain lead and the Release/Governance lead (@andonly1348).
7.  **Merge:** Once all criteria are met, the branch is merged into `main` (or `develop` if applicable).

---

## 🛡️ Required PR Checks (Mandatory Quality Gates)

Every Pull Request must pass the following gates before merge:

1.  **CI Pipeline:** Must pass all automated checks in GitHub Actions.
2.  **Code Coverage:** Minimum **85%** statement coverage. New code must include unit tests.
3.  **Type Safety:** `mypy` must return zero errors for all modified files.
4.  **Linting:** `ruff check .` must return zero errors.
5.  **Security Scan:** `pip-audit` or `trivy` must show zero vulnerabilities in dependencies.
6.  **License Compliance:** All new dependencies must comply with [docs/LICENSE_COMPLIANCE.md](./LICENSE_COMPLIANCE.md).
7.  **Documentation:** Documentation in `docs/` must be updated to reflect any source code changes.

---

## 🧪 Testing & Governance Verification

We practice Test-Driven Development (TDD) where possible.
- **Unit Tests:** Mandatory for all new functions and classes.
- **Integration Tests:** Required for changes touching MT5 connectors or database schemas.
- **Resilience Tests:** Mandatory for risk-management logic.

Run the full suite and governance checks locally:
```bash
# Run tests with coverage
PYTHONPATH=. python3 -m pytest tests/ --cov=src --cov-report=term-missing

# Run governance vitals check
PYTHONPATH=. python3 -m pytest tests/test_governance_vitals.py --noconftest

# Run Atlas Governance Auditor
python3 scripts/atlas_audit.py

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
- [Enterprise Standards](./ENTERPRISE_STANDARDS.md)

---
*By contributing, you agree that your contributions will be licensed under the project's MIT License.*
