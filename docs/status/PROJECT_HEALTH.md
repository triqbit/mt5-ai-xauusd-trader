# 🩺 Technical Project Health Dashboard

This dashboard provides real-time visibility into the technical health, process integrity, and evidence status of the repository.

## 📊 Quick Status

| Metric | Status | Note |
| :--- | :--- | :--- |
| **CI Success Rate** | 🟢 95% | RC v1.1.0-rc5 verified and stable. |
| **Lint Debt** | 🟡 4,400+ Issues | Primarily un-sorted imports and unused variables in tests. |
| **Process Integrity** | 🔴 RED | Accelerated history grafting on `main` (25 consecutive days). |
| **Evidence Maturity** | 🟡 **Active Verification** | Verified subsystem maturity in [Evidence Scorecard](../audits/ENTERPRISE_EVIDENCE_SCORECARD.md). |

---

## 🏗️ Technical Health Details

### 🧪 CI & Testing
- **Latest Release Candidate:** v1.1.0-rc10 (Verified May 20)
- **Integration Pass Rate:** 🟢 80% (Verified May 21)
- **Primary Bottleneck:** API harmonization in Risk Manager modules.

### 🧹 Code Quality (Ruff)
- **Total Errors:** 4,400+
- **Key Areas:**
  - `tests/`: 3,400+ issues (Unused imports, unformatted blocks).
  - `src/`: 0 issues (100% clean core).
- **Strategy:** Core is 100% clean; test debt is deferred to avoid history noise.

### 📜 Process Integrity
- **Status:** 🔴 **CRITICAL**
- **Issue:** The repository uses monolithic history grafts for daily updates. This destroys Git ancestry and obscures granular logic changes.
- **Audit Requirement:** Manual line-by-line validation of `src/trading/` is mandatory for each graft.
- **Reference:** [Process Integrity Log](./PROCESS_INTEGRITY_LOG.md)

---

## 🔍 Evidence Inventory

| Evidence Artifact | Category | Status |
| :--- | :--- | :--- |
| [Enterprise Evidence Scorecard](../audits/ENTERPRISE_EVIDENCE_SCORECARD.md) | Compliance | ✅ Active |
| [Technical Evidence Index](../audits/README.md) | Navigator | ✅ Active |
| [Integration Test Results](../testing/INTEGRATION_TEST_RESULTS.md) | System Quality | ✅ Verified (2026-05-21) |
| [Walk-Forward Robustness](../audits/walkforward_verification_report.md) | Strategy Research | ⏳ Provisional |
| Architecture Quick-Start | System Map | ✅ Verified (2026-05-07) |

---

## 🏛️ Governance Context
This dashboard is maintained by **Jules06 (Technical Credibility & Evidence Surface Engine)** to provide a transparent view of technical debt and risk for institutional stakeholders.
