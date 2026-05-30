# 🩺 Technical Project Health Dashboard

This dashboard provides real-time visibility into the technical health, process integrity, and evidence status of the repository.

## 📊 Quick Status

| Metric | Status | Note |
| :--- | :--- | :--- |
| **CI Success Rate** | 🟢 98.5% | 952/966 tests passing (Verified June 5, 2026). |
| **Lint Debt** | 🟢 33 Issues | Core and scripts are 100% clean; minimal debt in tests. |
| **Process Integrity** | 🔴 RED | Accelerated history grafting on `main` (35 consecutive days). |
| **Evidence Maturity** | 🟢 **Active Verification** | Verified subsystem maturity in [Evidence Scorecard](../audits/ENTERPRISE_EVIDENCE_SCORECARD.md). |

---

## 🏗️ Technical Health Details

### 🧪 CI & Testing
- **Latest Release Candidate:** v1.1.0-rc10 (Verified June 5, 2026)
- **Integration Pass Rate:** 🟢 98.5% (Verified June 5, 2026)
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
| [Integration Test Results](../testing/INTEGRATION_TEST_RESULTS.md) | System Quality | ✅ Verified (2026-06-05) |
| [Walk-Forward Robustness](../audits/walkforward_verification_report.md) | Strategy Research | ✅ Verified (2026-06-05) |
| Architecture Quick-Start | System Map | ✅ Verified (2026-06-05) |

---

## 🏛️ Governance Context
This dashboard is maintained by **Jules06 (Technical Credibility & Evidence Surface Engine)** to provide a transparent view of technical debt and risk for institutional stakeholders.
