# 🎯 Jules05: Deterministic Merge Queue [2026-05-19]

This document serves as the authoritative source of truth for the integration state and merge priorities of the repository, managed by Jules05.

## 📊 Summary State
- **Merge-Ready**: 1 (System Core Harmonization)
- **Fix-Required**: 900+ (Divergent branches/roots)
- **Blocked**: All feature branches (until Harmonization is merged)
- **Risky (Escalated)**: 25 (Trading logic, Risk parameters, Secrets, Model Inference)
- **Superseded/Stale**: 500+ (Pre-May 15 work)

---

## 🚀 Priority Merge Queue

| Order | PR # | Branch | Classification | Rationale | Next Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | #1352 | `jules06-integrity-audit-2026-05-19-16239906442830812977` | merged | **AUDIT:** Documentation only. Merged into main (ea16529). | [None] |
| 1 | #1280 | `jules05-coherence-improvements-345411350074474294` | merge-ready | **SYSTEM BASE:** Final Architectural Harmonization. Restores 8-layer Risk cascade and FE relocation missing from main. Verified healthy. | Merge to main to fix history root. |
| 2 | #1281 | `ux-improvements-ergonomics-dashboard-12183713617457102929` | fix-required | **OPERATIONAL:** High-value UX and dashboard. Divergent root. | Rebase on #1 |
| 3 | #1289 | `jules02/db-reliability-reconciliation-5838315454598989615` | fix-required | **RESILIENCE:** Database state reconciliation. Divergent root. | Rebase on #1 |
| 4 | #1350 | `feat-jules-decision-funnel-unification-v2-13333372400311877230` | risky | **CORE:** Massive unification of model interfaces and trading paths. Divergent root. | Rebase on #1 and escalate. |

---

## 🛠️ Fix Required (Architectural Divergence)

The following PRs are currently classified as Fix Required because they are **DISCONNECTED ROOTS**. They do not share a common history with the harmonized base. Merging them will cause catastrophic repo state.

| PR # | Branch | Reason | Next Action |
| :--- | :--- | :--- | :--- |
| #1351 | `feat/confidence-calibration-engine-16069901825976839716` | **INTELLIGENCE:** Modifies main inference logic. | Jules04 to rebase on #1. |
| #1349 | `feature/regime-detector-institutional-4989658781633186276` | **INTELLIGENCE:** Institutional regime logic. | Jules04 to rebase on #1. |
| #1348 | `feature/institutional-reporting-enhancements-9053398351766023886` | **STRATEGY:** Research reporting UX. | Jules04 to rebase on #1. |
| #1332 | `origin/feat/decision-support-enhancements-11601613281179904091` | **INTELLIGENCE:** Enhancements to DSS. | Jules04 to rebase on #1. |

---

## ⚠️ Escalation List (Requires Human Sign-off)

Per `docs/integration/AUTO_MERGE_POLICY.md`, the following changes must be manually reviewed by a human lead.

| PR # | Branch | Reason for Escalation | Impact Area |
| :--- | :--- | :--- | :--- |
| #1350 | `feat-jules-decision-funnel-unification-v2-13333372400311877230` | **CORE:** Rewrites model prediction and risk execution paths. | Trading Execution |
| #1351 | `feat/confidence-calibration-engine-16069901825976839716` | **MODEL:** Injects calibration logic into live inference. | Signal Generation |
| #1257 | `feat/institutional-capital-allocator-699780167318509855` | **RISK:** Overhaul of capital management logic. | Risk Management |
| #1280 | `jules05-coherence-improvements-345411350074474294` | **SYSTEM:** Large-scale structural refactor. | Architecture |

---

## 📅 Stale / Superseded / Low-Priority

- **Superseded:** `jules-security-hardening-5694445454706320221` (Appears to destructively delete core regime detector files without justification).
- **Strategically Low-Priority:** `origin/jules06-integrity-audit-*` (Necessary for records, but secondary to system stability).
- **Bulk Closure Pending:** 500+ PRs opened before 2026-04-15 that are not active or rebased on the Big Bang root (`e23adfa`).

---

## 🚨 Critical Process Alert
**Status:** 🔴 CRITICAL FRAGMENTATION
**Warning:** The `main` branch still lacks the harmonized Risk API and Feature Engineering structure.
**Directive:** ALL AGENTS must stop creating new feature branches until PR #1280 is merged and history is stabilized.

---
*Last Updated: 2026-05-19 by Jules05*
