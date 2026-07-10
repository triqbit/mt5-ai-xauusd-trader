# 🩺 Technical Project Health Dashboard

This dashboard provides real-time visibility into the technical health, process integrity, and evidence status of the repository.

## 📊 Quick Status

| Metric | Status | Note |
| :--- | :--- | :--- |
| **CI Success Rate** | 🔴 BLOCKED | CI hard-blocked by 122 formatting issues and pre-existing lint debt. |
| **PR Backlog** | 🔴 559 Stale | 100% of open PRs are stale relative to the 100th history graft. |
| **Process Integrity** | 🔴 RED | Accelerated history grafting on `main` (100 consecutive nodes). |
| **Evidence Maturity** | 🟢 **Active Verification** | Verified subsystem maturity in [Evidence Scorecard](../audits/ENTERPRISE_EVIDENCE_SCORECARD.md). |

---

## 🏗️ Technical Health Details

### 🧪 CI & Testing
- **Status:** 🔴 **BLOCKED**
- **Issue:** Global CI blockage due to 122 formatting errors and 6-8 linting errors in `migrations/env.py`.
- **Integration Pass Rate:** 🟢 98.5% (Baseline verified June 12, 2026; subsequent merges bypass CI).

### 🧹 Code Quality (Ruff)
- **Total Errors:** 130+ (Formatting and pre-existing lint debt)
- **Key Areas:**
  - `tests/`: Extensive formatting drift - *Restricted zone*.
  - `src/`: Extensive formatting drift - *Restricted zone*.
  - `migrations/`: 6-8 persistent linting errors.
- **Strategy:** Resolving global formatting debt requires Lead Engineer intervention to unblock CI.

### 📜 Process Integrity
- **Status:** 🔴 **CRITICAL**
- **Issue:** The repository uses monolithic history grafts for daily updates. This destroys Git ancestry and obscures granular logic changes.
- **Current Node:** Commit `87dd18e` (100th consecutive graft).
- **Audit Requirement:** Manual line-by-line validation of `src/trading/` is mandatory for each graft.
- **Reference:** [Process Integrity Log](./PROCESS_INTEGRITY_LOG.md)

---

## 🔍 Evidence Inventory

| Evidence Artifact | Category | Status |
| :--- | :--- | :--- |
| [Enterprise Evidence Scorecard](../audits/ENTERPRISE_EVIDENCE_SCORECARD.md) | Compliance | ✅ Active |
| [Technical Evidence Index](../audits/README.md) | Navigator | ✅ Active |
| [Integration Test Results](../testing/INTEGRATION_TEST_RESULTS.md) | System Quality | ✅ Verified (2026-06-25) |
| [Walk-Forward Robustness](../audits/walkforward_verification_report.md) | Strategy Research | ✅ Verified (2026-06-25) |
| Architecture Quick-Start | System Map | ✅ Verified (2026-06-25) |

---

## 🏛️ Governance Context
This dashboard is maintained by **Jules06 (Technical Credibility & Evidence Surface Engine)** to provide a transparent view of technical debt and risk for institutional stakeholders.
