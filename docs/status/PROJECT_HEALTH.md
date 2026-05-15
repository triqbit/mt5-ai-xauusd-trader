# 🩺 Technical Project Health Dashboard

This dashboard provides real-time visibility into the technical health, process integrity, and evidence status of the repository.

## 📊 Quick Status

| Metric | Status | Note |
| :--- | :--- | :--- |
| **CI Success Rate** | 🟢 95% | RC v1.1.0-rc5 verified and stable. |
| **Lint Debt** | 🟡 342 Issues | Primarily un-sorted imports and unused variables in tests. |
| **Process Integrity** | 🔴 RED | Accelerated history grafting on `main` (16 consecutive days). |
| **Evidence Maturity** | 🟡 Emerging | 1 verified audit; 5 upcoming enterprise scorecards. |

---

## 🏗️ Technical Health Details

### 🧪 CI & Testing
- **Latest Release Candidate:** v1.1.0-rc5
- **Test Coverage Target:** >80% (Current: Maintaining coverage above threshold)
- **Primary Bottleneck:** Environment stability (dependency conflicts in `requirements-linux.txt`).

### 🧹 Code Quality (Ruff)
- **Total Errors:** 342
- **Key Areas:**
  - `tests/`: 310+ issues (Unused imports, unformatted blocks).
  - `src/`: <30 issues (High quality in core logic).
- **Strategy:** Automated fixes for formatting are blocked by history integrity concerns.

### 📜 Process Integrity
- **Status:** 🔴 **CRITICAL**
- **Issue:** The repository uses monolithic history grafts for daily updates. This destroys Git ancestry and obscures granular logic changes in trading and risk modules. Sixteenth consecutive day of history destruction recorded on 2026-05-15, with multiple system-wide swaps per day.
- **Audit Requirement:** Manual line-by-line validation of `src/trading/` is mandatory for each graft.
- **Reference:** [Process Integrity Log](./PROCESS_INTEGRITY_LOG.md)

---

## 🔍 Evidence Inventory

| Evidence Artifact | Category | Status |
| :--- | :--- | :--- |
| [Walk-Forward Robustness](../audits/walkforward_verification_report.md) | Strategy Research | ✅ Verified (2026-05-08) |
| Architecture Quick-Start | System Map | ✅ Verified (2026-05-07) |
| Enterprise Scorecard | Compliance | ⏳ Upcoming |
| ADR Audit Report | Governance | ⏳ Upcoming |

---

## 🏛️ Governance Context
This dashboard is maintained by **Jules06 (Technical Credibility & Evidence Surface Engine)** to provide a transparent view of technical debt and risk for institutional stakeholders.
