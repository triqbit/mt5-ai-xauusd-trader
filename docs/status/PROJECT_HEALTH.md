# 🩺 Technical Project Health Dashboard

This dashboard provides real-time visibility into the technical health, process integrity, and evidence status of the repository.

## 📊 Quick Status

| Metric | Status | Note |
| :--- | :--- | :--- |
| **CI Success Rate** | 🟡 99% | 931/940 tests passing; 9 regressions in RiskManager and Reporting. |
| **Lint Debt** | 🟡 4,400+ Issues | 61 critical ruff errors detected in latest graft. |
| **Process Integrity** | 🔴 RED | 20 days of history destruction; untracked artifacts cleaned. |
| **Evidence Maturity** | 🟡 Emerging | 1 verified audit; 5 upcoming enterprise scorecards. |

---

## 🏗️ Technical Health Details

### 🧪 CI & Testing
- **Latest Release Candidate:** v1.1.0-rc5
- **Test Results (2026-05-18):** 931 passed, 9 failed.
- **Regressions:** `RiskManager` interface mismatch and `python-socketio` dependency synchronization failure (5.14.0 vs 5.11.1).
- **Primary Bottleneck:** Interface drift between core logic and harmonized tests following monolithic grafts.

### 🧹 Code Quality (Ruff)
- **Total Errors:** 4,400+
- **Key Areas:**
  - `tests/`: 3,400+ issues (Unused imports, unformatted blocks).
  - `src/`: 0 issues (100% clean core).
  - `scripts/`: 800+ issues.
- **Strategy:** Automated fixes for formatting are blocked by history integrity concerns.

### 📜 Process Integrity
- **Status:** 🔴 **CRITICAL**
- **Issue:** The repository uses monolithic history grafts for daily updates. This destroys Git ancestry and obscures granular logic changes in trading and risk modules. Twentieth consecutive day of history destruction recorded on 2026-05-18, with PR #1331 executing the latest system-wide swap.
- **Audit Requirement:** Manual line-by-line validation of `src/trading/` is mandatory for each graft.
- **Reference:** [Process Integrity Log](./PROCESS_INTEGRITY_LOG.md)

---

## 🔍 Evidence Inventory

| Evidence Artifact | Category | Status |
| :--- | :--- | :--- |
| [Walk-Forward Robustness](../audits/walkforward_verification_report.md) | Strategy Research | ⏳ Provisional (In Review) |
| Architecture Quick-Start | System Map | ✅ Verified (2026-05-07) |
| Enterprise Scorecard | Compliance | ⏳ Upcoming |
| ADR Audit Report | Governance | ⏳ Upcoming |

---

## 🏛️ Governance Context
This dashboard is maintained by **Jules06 (Technical Credibility & Evidence Surface Engine)** to provide a transparent view of technical debt and risk for institutional stakeholders.
