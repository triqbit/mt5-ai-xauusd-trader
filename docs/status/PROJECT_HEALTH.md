# 🩺 Technical Project Health Dashboard

This dashboard provides real-time visibility into the technical health, process integrity, and evidence status of the repository.

## 📊 Quick Status

| Metric | Status | Note |
| :--- | :--- | :--- |
| **CI Success Rate** | 🔴 BLOCKED | Blocked by dependency conflict in `requirements-ci.txt`. |
| **Lint Debt** | 🟡 138 Issues | 8 legacy errors in `migrations/`; script debt resolved. |
| **Process Integrity** | 🔴 RED | Accelerated history grafting on `main` (51 consecutive days). |
| **Evidence Maturity** | 🟢 **Active Verification** | Verified subsystem maturity in [Evidence Scorecard](../audits/ENTERPRISE_EVIDENCE_SCORECARD.md). |

---

## 🏗️ Technical Health Details

### 🧪 CI & Testing
- **Latest Release Candidate:** v1.1.0-rc10 (Verified June 12, 2026)
- **Integration Pass Rate:** 🔴 **BLOCKED** (June 13, 2026)
- **Primary Bottleneck:** Dependency conflict between `metaapi-cloud-sdk` and `python-socketio`.
- **Status:** Fast Validation passes; Dependency Safety fails.

### 🧹 Code Quality (Ruff)
- **Total Errors:** 138 (Excluding restricted domains)
- **Key Areas:**
  - `tests/`: 3,400+ issues (Unused imports, unformatted blocks) - *Deferred to avoid noise*.
  - `src/`: 0 issues (100% clean core).
  - `scripts/`: 0 issues (100% clean automation).
- **Strategy:** Core and automation are 100% clean; migration debt is documented for escalation.

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
