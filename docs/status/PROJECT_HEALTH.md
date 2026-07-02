# 🩺 Technical Project Health Dashboard

This dashboard provides real-time visibility into the technical health, process integrity, and evidence status of the repository.

## 📊 Quick Status

| Metric | Status | Note |
| :--- | :--- | :--- |
| **CI Success Rate** | 🔴 BLOCKED | CI hard-blocked by 6 linting errors in `migrations/env.py`. |
| **PR Backlog** | 🔴 557 Stale | 100% of open PRs are stale relative to the 85th history graft. |
| **Process Integrity** | 🔴 RED | Accelerated history grafting on `main` (85 consecutive nodes). |
| **Evidence Maturity** | 🟢 **Active Verification** | Verified subsystem maturity in [Evidence Scorecard](../audits/ENTERPRISE_EVIDENCE_SCORECARD.md). |

---

## 🏗️ Technical Health Details

### 🧪 CI & Testing
- **Status:** 🔴 **BLOCKED**
- **Issue:** Global CI blockage due to 6 linting errors in `migrations/env.py`.
- **Integration Pass Rate:** 🟢 98.5% (Baseline verified June 12, 2026; subsequent merges bypass CI).

### 🧹 Code Quality (Ruff)
- **Total Errors:** 136+ (Excluding restricted domains)
- **Key Areas:**
  - `tests/`: 3,400+ issues (Unused imports, unformatted blocks) - *Deferred to avoid noise*.
  - `src/`: 0 issues (100% clean core).
  - `migrations/`: 6 legacy formatting errors.
- **Strategy:** Core is 100% clean; resolving `migrations/` lint errors is required to unblock CI.

### 📜 Process Integrity
- **Status:** 🔴 **CRITICAL**
- **Issue:** The repository uses monolithic history grafts for daily updates. This destroys Git ancestry and obscures granular logic changes.
- **Current Node:** Commit `b482f3d` (85th consecutive graft).
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
