# 🩺 Technical Project Health Dashboard

This dashboard provides real-time visibility into the technical health, process integrity, and evidence status of the repository.

## 📊 Quick Status

| Metric | Status | Note |
| :--- | :--- | :--- |
| **CI Success Rate** | 🟢 98.5% | 952/966 tests passing (Verified June 12, 2026). |
| **Lint Debt** | 🟡 139 Issues | 8 legacy errors in `migrations/` and 1 recent E741 in `scripts/`. |
| **Process Integrity** | 🔴 RED | Accelerated history grafting on `main` (51 consecutive days). |
| **Evidence Maturity** | 🟢 **Active Verification** | Verified subsystem maturity in [Evidence Scorecard](../audits/ENTERPRISE_EVIDENCE_SCORECARD.md). |

---

## 🏗️ Technical Health Details

### 🧪 CI & Testing
- **Latest Release Candidate:** v1.1.0-rc10 (Verified June 12, 2026)
- **Integration Pass Rate:** 🟢 98.5% (Verified June 12, 2026)
- **Primary Bottleneck:** API harmonization in Risk Manager modules.

### 🧹 Code Quality (Ruff)
- **Total Errors:** 139 (Excluding restricted domains)
- **Key Areas:**
  - `tests/`: 3,400+ issues (Unused imports, unformatted blocks) - *Deferred to avoid noise*.
  - `src/`: 0 issues (100% clean core).
  - `scripts/`: 1 issue (E741: Ambiguous variable name 'l' in `generate_triage_report.py`).
- **Strategy:** Core is 100% clean; script/migration debt is documented for escalation.

### 📜 Process Integrity
- **Status:** 🔴 **CRITICAL**
- **Issue:** The repository uses monolithic history grafts for daily updates. This destroys Git ancestry and obscures granular logic changes.
- **Current Node:** Commit `ec8edc2` (51st consecutive graft).
- **Audit Requirement:** Manual line-by-line validation of `src/trading/` is mandatory for each graft.
- **Reference:** [Process Integrity Log](./PROCESS_INTEGRITY_LOG.md)

---

## 🔍 Evidence Inventory

| Evidence Artifact | Category | Status |
| :--- | :--- | :--- |
| [Enterprise Evidence Scorecard](../audits/ENTERPRISE_EVIDENCE_SCORECARD.md) | Compliance | ✅ Active |
| [Technical Evidence Index](../audits/README.md) | Navigator | ✅ Active |
| [Integration Test Results](../testing/INTEGRATION_TEST_RESULTS.md) | System Quality | ✅ Verified (2026-06-12) |
| [Walk-Forward Robustness](../audits/walkforward_verification_report.md) | Strategy Research | ✅ Verified (2026-06-05) |
| Architecture Quick-Start | System Map | ✅ Verified (2026-06-05) |

---

## 🏛️ Governance Context
This dashboard is maintained by **Jules06 (Technical Credibility & Evidence Surface Engine)** to provide a transparent view of technical debt and risk for institutional stakeholders.
