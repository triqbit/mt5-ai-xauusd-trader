# 🩺 Technical Project Health Dashboard

This dashboard provides real-time visibility into the technical health, process integrity, and evidence status of the repository.

## 📊 Quick Status

| Metric | Status | Note |
| :--- | :--- | :--- |
| **CI Success Rate** | 🔴 BLOCKED | CI hard-blocked by 13 linting errors in `migrations/env.py` and `scripts/`. |
| **PR Backlog** | 🔴 561 Stale | 100% of open PRs are stale relative to the 115th history graft. |
| **Process Integrity** | 🔴 RED | Accelerated history grafting on `main` (115 consecutive nodes). |
| **Evidence Maturity** | 🟢 **Active Verification** | Verified subsystem maturity in [Evidence Scorecard](../audits/ENTERPRISE_EVIDENCE_SCORECARD.md). |

---

## 🏗️ Technical Health Details

### 🧪 CI & Testing
- **Status:** 🔴 **BLOCKED**
- **Issue:** Global CI blockage due to 13 persistent linting errors.
- **Integration Pass Rate:** 🟢 98.5% (Baseline verified June 12, 2026; subsequent merges bypass CI).

### 🧹 Code Quality (Ruff)
- **Total Errors:** 143+ (Excluding restricted domains)
- **Key Areas:**
  - `tests/`: 3,400+ issues (Unused imports, unformatted blocks) - *Deferred to avoid noise*.
  - `src/`: 0 issues (100% clean core).
  - `migrations/`: 6 legacy formatting errors.
  - `scripts/`: 7 persistent linting errors (F841, RUF059).
- **Strategy:** Core is 100% clean; resolving baseline lint errors is required to unblock CI.

### 📜 Process Integrity
- **Status:** 🔴 **CRITICAL**
- **Issue:** The repository uses monolithic history grafts for daily updates. This destroys Git ancestry and obscures granular logic changes.
- **Current Node:** Commit `57c8902b9b6caa2f60564582a513fc2f2f5ceffa` (115th consecutive graft).
- **Audit Requirement:** Manual line-by-line validation of `src/trading/` is mandatory for each graft.
- **Reference:** [Process Integrity Log](./PROCESS_INTEGRITY_LOG.md)

---

## 🔍 Evidence Inventory

| Evidence Artifact | Category | Status |
| :--- | :--- | :--- |
| [Enterprise Evidence Scorecard](../audits/ENTERPRISE_EVIDENCE_SCORECARD.md) | Compliance | ✅ Active |
| [Technical Evidence Index](../audits/README.md) | Navigator | ✅ Active |
| [Integration Test Results](../testing/INTEGRATION_TEST_RESULTS.md) | System Quality | ✅ Verified (2026-07-16) |
| [Walk-Forward Robustness](../audits/walkforward_verification_report.md) | Strategy Research | ✅ Verified (2026-07-16) |
| Architecture Quick-Start | System Map | ✅ Verified (2026-07-16) |

---

## 🏛️ Governance Context
This dashboard is maintained by **Jules06 (Technical Credibility & Evidence Surface Engine)** to provide a transparent view of technical debt and risk for institutional stakeholders.
