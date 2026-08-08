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

1. **[Contributing Guide](./docs/CONTRIBUTING.md):** Detailed workflow, branching strategy, and quality gates.
2. **[Contribution Map](./docs/CONTRIBUTION_MAP.md):** Understanding "Safe Zones" vs. "Sensitive Zones" to pick your first task.
3. **[Your First Real Contribution](./docs/FIRST_REAL_CONTRIBUTION.md):** A step-by-step tutorial for new contributors.
4. **[Architecture Quick-Start](./docs/ARCHITECTURE_QUICK.md):** Technical overview of system components and maturity levels.

---

## 🚦 Quick Rules & "Safe Zones"

- **Keep Aligned:** Always rebase or synchronize your branch with the latest `main` commit before submitting.
- **Safe Zones:** We encourage new contributors to start with `docs/`, `tests/`, or `scripts/`. These have a faster path to merge.
- **Multi-Signature:** Changes to trading logic, models, or core infrastructure require multi-signature approval from domain leads.
- **Quality Gates:** All PRs must pass automated linting, type-checking, security scans, and maintain ≥85% test coverage.

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
