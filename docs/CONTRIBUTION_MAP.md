# 🗺️ Contribution Map

This map defines the "Safe Zones" and "Sensitive Zones" of the MT5 AI/ML Trading Bot repository to help contributors find the best starting point and understand the review expectations for different areas.

## 🚦 System at a Glance

| Zone | Path | Risk Level | Review Requirement | Evidence Required |
| :--- | :--- | :--- | :--- | :--- |
| **Safe Zone** | `docs/`, `tests/`, `scripts/` | 🟢 Low | Standard Peer Review | Unit Tests / Doc Lint |
| **Utility Zone** | `src/utils/`, `src/analytics/` | 🟡 Medium | Domain Expert Review | Integration Tests |
| **Sensitive Zone** | `src/trading/`, `src/models/`, `src/core/` | 🔴 High | Lead + Multi-Signature | Backtests + Stress Tests |

---

## 🌪️ Turbulence Response FAQ

The repository is currently in a state of **High Turbulence** due to rapid automated development cycles. Here is how to navigate as a contributor:

### 1. Why are there 550+ open PRs?
Most open PRs are **"Stale (Pre-Big-Bang)"**. They were created against previous repository history grafts and are currently pending bulk closure or manual rebase. **Do not let this deter you.** Focus on "Safe Surface" candidates identified in the latest [PR Triage Report](./status/PR_TRIAGE_DAILY.md).

### 2. Why is CI blocked?
CI is currently failing globally due to legacy linting errors in `migrations/` that were integrated during a history graft. **Safe contributions (docs, tests, scripts) are still encouraged.** Maintainers will manually verify your PR if it stays within a **Safe Zone**.

### 3. How do I know if my PR is safe to merge?
Check the [Merge-Ready Checklist](./status/MERGE_READY_CHECKLIST.md). If your PR is listed there, it has been flagged as a priority for alignment and review.

---

## 🟢 Safe Zones (Recommended for First PRs)

These areas are perfect for new contributors to get familiar with the project and provide immediate value with minimal risk to trading operations.

### 1. Documentation (`docs/`)
- **Improvement Areas:** Clarity, typos, missing diagrams, or adding new guides (e.g., specific cloud deployment steps).
- **Goal:** Make the system easier to understand and run for the next engineer.

### 2. Testing (`tests/`)
- **Improvement Areas:** Increasing coverage for `src/utils/`, adding edge-case unit tests, or performance benchmarks.
- **Goal:** Strengthen the system's reliability without changing production logic.

### 3. Developer Experience (`scripts/`, `Makefile`)
- **Improvement Areas:** Improving `make doctor` checks, `bootstrap.sh` robustness, or adding new CLI helpers for developers.
- **Goal:** Reduce the "Time to First Success" for new developers.

---

## 🟡 Utility & Analytics Zones

These areas require a deeper understanding of the system's data structures but do not directly influence live trading decisions.

### 1. Utilities (`src/utils/`)
- **Improvement Areas:** Optimization of generic helpers, logging improvements, or date/time formatting.

### 2. Analytics (`src/analytics/`)
- **Improvement Areas:** Post-trade analysis reports, visualization of backtest results, or journal mining logic.

---

## 🔴 Sensitive Zones (High-Stake Areas)

Changes to these directories affect the core financial and operational safety of the bot. Contributions here require extensive evidence (backtests, stress tests) and mandatory lead review.

### 1. Trading Logic (`src/trading/`)
- **Modules:** `mt5_connector.py`, `risk_manager.py`, `execution_filter.py`.
- **Constraint:** Do NOT modify without explicit coordination with Jules01/Jules03.

### 2. Model Architectures (`src/models/`)
- **Modules:** `dynamic_ensemble.py`, `ppo_agent.py`, `regime_detector.py`.
- **Constraint:** Changes must be backed by quantitative research and Jules04 approval.

### 3. Core Engine (`src/core/`)
- **Modules:** `config.py`, `health.py`, `constants.py`.
- **Constraint:** Affects system-wide invariants and startup safety.

---

## 🛠️ How to Pick Your First Task

1.  **Read [Your First Real Contribution](./FIRST_REAL_CONTRIBUTION.md):** Follow our step-by-step guide to making a low-risk, high-impact first contribution.
2.  **Filter PRs by Label:** Use GitHub's label filters to find existing work in Safe Zones for inspiration or collaboration:
    - `is:pr is:open label:docs`: Documentation improvements.
    - `is:pr is:open label:test`: Testing and coverage enhancements.
    - `is:pr is:open label:chore`: Maintenance and developer experience tasks.
3.  **Run `make doctor`:** If any check fails on your system, improving that check or the documentation around it is a great first contribution.
4.  **Check `docs/status/PR_TRIAGE_DAILY.md`:** Look for PRs categorized as **"Safe Surface"**. This report is updated daily and is the best source for finding approved first-task candidates.
5.  **Audit `tests/`:** Find a module with low coverage (check `make test` output) and add missing unit tests.

---
*This map is maintained by Jules06 (qufuwan). If you are unsure where your change fits, please open a discussion or tag a maintainer.*
