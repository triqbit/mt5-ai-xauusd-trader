# Contributing to MT5 AI/ML Trading Bot

To ensure the safety, reliability, and institutional grade of this trading system, all contributions must follow our established governance and workflow standards.

---

## 🌪️ Current Status & Turbulence

The repository is currently in a state of **High Turbulence** due to rapid automated development cycles.

-   **550+ Open PRs:** Most are "Stale (Pre-Big-Bang)" due to history grafts.
-   **CI Blockage:** CI is globally failing due to legacy linting errors in `migrations/`.
-   **History Grafting:** The `main` branch resets daily via monolithic repository swaps.

**Do not let this deter you.** We are actively reviewing PRs in **Safe Zones** (docs, tests, scripts).

---

## 📖 Essential Guides

Please refer to the following documents before opening a Pull Request:

1.  **[Contributing Guide](./docs/CONTRIBUTING.md):** Detailed workflow, branching strategy, and quality gates.
2.  **[Contribution Map](./docs/CONTRIBUTION_MAP.md):** Understanding "Safe Zones" vs. "Sensitive Zones" to pick your first task.
3.  **[Your First Real Contribution](./docs/FIRST_REAL_CONTRIBUTION.md):** A step-by-step tutorial for new contributors.
4.  **[Architecture Quick-Start](./docs/ARCHITECTURE_QUICK.md):** Technical overview of system components and maturity levels.

---

## 🚦 Quick Rules & "Safe Zones"

-   **Daily Resets:** The `main` branch resets daily. Always rebase your branch on the latest `main` before submitting.
-   **Safe Zones:** We encourage new contributors to start with `docs/`, `tests/`, or `scripts/`. These have a faster path to merge.
-   **Multi-Signature:** Changes to trading logic, models, or core infrastructure require multi-signature approval from domain leads.
-   **Quality Gates:** All PRs must pass automated linting, type-checking, security scans, and maintain ≥85% test coverage.

---

## 🛠️ Graft Survival Kit (Rebase Instructions)

Because `main` is force-pushed daily, use these commands to keep your branch synced:

```bash
# 1. Update your local main cache
git fetch origin main

# 2. Rebase your work onto the new graft
git rebase origin/main

# 3. If you get "no common ancestry" errors:
git rebase --onto origin/main <old-base-commit> <your-branch-name>
```

---
*This repository is maintained by a role-based governance team. See [CODEOWNERS](./.github/CODEOWNERS) for details.*
