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

### 1. Contribution Lifecycle
We follow a structured lifecycle for all changes to ensure maximum reliability:

1.  **Issue Identification:** Every contribution must start with an issue (Bug, Feature, or Security).
2.  **Triage:** A maintainer will triage the issue and assign a priority (P0-P3).
3.  **Branching:** Create a branch from `main` using the appropriate prefix:
    - `feature/`: New capabilities or enhancements (e.g., `feature/ppo-optim-v2`)
    - `bugfix/`: Fixes for identified issues (e.g., `bugfix/mt5-conn-leak`)
    - `hotfix/`: Emergency production patches
    - `docs/`: Documentation-only improvements
    - `refactor/`: Code reorganization without functional changes
4.  **Implementation:** Develop your changes, adhering to [ENTERPRISE_STANDARDS.md](./ENTERPRISE_STANDARDS.md).
5.  **Pull Request:** Open a PR using the [.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md).
6.  **Review & Multi-Signature:**
    - Changes to **Sensitive Zones** (Trading, Models, Core) require **multi-signature approval** from both the domain lead and the Release/Governance lead (@andonly1348).
7.  **Merge:** Once all checks pass and approvals are received, the PR is merged into `main`.

### 2. Implementation Standards
- **Conventional Commits:** All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.
- **Testing:** We practice Test-Driven Development (TDD). New code MUST have corresponding tests.
- **Type Safety:** All Python code must be fully type-hinted and pass `mypy`.

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
- Follow the [SECURITY.md](../SECURITY.md).
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
