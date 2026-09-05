# Contributing to MT5 AI/ML Trading Bot

To ensure the safety, reliability, and institutional grade of this trading system, all contributions must follow our established governance and workflow standards.

---

## 🟢 Repository Status & Health

Our repository maintains high-quality standards and a clean, linear contribution path.

- **CI Success Rate:** 🟢 **PASSING** (All formatting, linting, and tests pass cleanly).
- **Linear History:** 🟢 **STABLE** (The `main` branch maintains a fully linear, intact Git history for perfect auditability).
- **PR Alignment:** Always keep your branch synchronized with the latest `main` commit.

We actively encourage and review Pull Requests in **Safe Zones** (docs, tests, scripts) to help onboard new developers smoothly.

---

## 📖 Essential Guides

Please refer to the following documents before opening a Pull Request:

1. **[Contribution Map](./docs/CONTRIBUTION_MAP.md):** Safe Zones vs. Sensitive Zones directory matrix.
2. **[Your First Real Contribution](./docs/FIRST_REAL_CONTRIBUTION.md):** Step-by-step tutorial for new contributors.
3. **[Architecture Quick-Start](./docs/ARCHITECTURE_QUICK.md):** Technical overview of system components and maturity levels.
4. **[Enterprise Standards](./docs/ENTERPRISE_STANDARDS.md):** Enterprise coding and quality standards.

---

## 🚦 System Safe Zones & Review Matrix

To help contributors start safely, system paths are categorized into clear review risk tiers:

| Zone | Path | Risk Level | Review Requirement | Recommended First Contribution |
| :--- | :--- | :--- | :--- | :--- |
| **Safe Zone** | `docs/`, `tests/`, `scripts/`, `Makefile` | 🟢 Low | Standard Peer Review | Yes (Documentation, Unit Tests, Developer Scripts) |
| **Utility Zone** | `src/utils/`, `src/analytics/` | 🟡 Medium | Domain Lead Review | Secondary (Helpers, Telemetry, Analytics reports) |
| **Sensitive Zone** | `src/trading/`, `src/models/`, `src/core/` | 🔴 High | Lead + Multi-Signature | No (Core Execution, Models, Risk Engine) |

---

## 🚦 Quick Rules & Guidelines

- **Keep Aligned:** Always rebase or synchronize your branch with the latest `main` commit before submitting (`make resync`).
- **PR Title & Branch Rules:** CI enforces semantic PR titles (`docs:`, `chore:`, `test:`, `fix:`, `feat:`, `perf:`, `style:`, `refactor:`, `ci:`). **Do NOT use `DX:` prefix in PR titles or commits.**
- **Safe Zone Focus:** New contributors are strongly advised to start in `docs/`, `tests/`, or `scripts/` for a fast, friction-free path to merge.
- **Multi-Signature:** Changes to Sensitive Zones (`src/trading/`, `src/models/`, `src/core/`) require multi-signature approval from domain leads.
- **Quality Gates:** All PRs must pass automated linting, type-checking, security scans, and maintain high test coverage.

---

## 🛠️ Synchronization Kit

To keep your feature branch seamlessly updated with the latest `main` commit, use this command:

```bash
# Automated sync with the latest main
make resync
```

If you ever need to perform a manual rebase:
```bash
git fetch origin main
git rebase origin/main
```

---
*This repository is maintained by a role-based governance team. See [CODEOWNERS](./.github/CODEOWNERS) for details.*
