# 🎯 Jules05: Deterministic Merge Queue [2026-05-02]

This document serves as the authoritative source of truth for the integration state and merge priorities of the repository, managed by Jules05.

## 📊 Summary State
- **Merge-Ready**: 2
- **Fix-Required**: 5
- **Blocked**: 0
- **Risky (Escalated)**: 3
- **Superseded**: 0

---

## 🚀 Priority Merge Queue

| Order | Branch | Classification | Rationale | Next Action |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `origin/fix-ci-and-imports-10275903423945476535` (#370) | fix-required | Resolves critical CI blockers. Requires rebase after #469. | Rebase and merge to stabilize the build. |
| 2 | `origin/implement-model-stubs-11387061741357092186` (#375) | fix-required | Provides production-ready model stubs. Requires rebase after #469. | Rebase and merge. |
| 3 | `origin/feat/vectorized-backtester-engine-2507153487072586691` (#368) | fix-required | High-value vectorized backtesting engine. Requires rebase after #469. | Rebase and merge. |
| 4 | `origin/release/v1.1.0-2506536362439602818` (#373) | merge-ready | Assembles the v1.1.0 release candidate. | Finalize release composition. |
| 5 | `origin/feat/decision-support-system-5901454689429807923` (#468) | merge-ready | Implements institutional decision support system. Already integrated with main. | Merge. |

---

## 🛠️ Fix Required (Minor Quality Issues / Rebase Needed)

| Branch | Reason |
| :--- | :--- |
| `origin/jules-ci-mypy-hardening-4853801334882103621` (#359) | Requires rebase and resolution of new typing issues after #469. |
| `origin/jules02-cli-ux-improvement-869278649885808152` (#358) | Requires rebase to align with new CLI structure. |

---

## ⚠️ Escalation List (Requires Human Sign-off)

The following changes touch high-risk areas (trading logic, risk limits) and require manual review per the Jules05 Escalation Policy.

| Branch | Reason for Escalation | Impact Area |
| :--- | :--- | :--- |
| `origin/jules-execution-filter-impl-9884553851395903715` (#372) | Implements 8-layer execution filter. Touches core `main.py`. | Trading Execution / Risk |
| `origin/macro-event-intelligence-9573672987878901155` (#360) | Implements macroeconomic event intelligence affecting live trading loop. | Risk Engine / Live Loop |
| `remotes/origin/feature/decision-support-system-5565901309274814363` (#366) | Superseded by #468 but contains legacy UX logic for review. | Core Trading / UX |

---

## 📅 Stale / Superseded / Low-Priority

- 300+ stale PRs identified following #469 "Big Bang" merge. Targeted for pruning in next cycle.

---

*Last Updated: 2026-05-02 by Jules05*
