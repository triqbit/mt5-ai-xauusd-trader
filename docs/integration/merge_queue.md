# 🎯 Jules05: Deterministic Merge Queue [2026-05-23]

This document serves as the authoritative source of truth for the integration state and merge priorities of the repository, managed by Jules05.

## 📊 Summary State
- **Merge-Ready**: 0 (Waiting for base harmonization)
- **Fix-Required**: 548+ (Divergent branches/roots)
- **Blocked**: All feature branches (until Harmonization #1372 is merged)
- **Risky (Escalated)**: 36+ (Trading logic, Risk parameters, Security, Model Inference)
- **Superseded/Stale**: 547+ (Pre-May 22 "Big Bang")

---

## 🚀 Priority Merge Queue

| Order | PR # | Branch | Classification | Rationale | Next Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | #1372 | `Jules05-resolve-cross-agent-conflict-13854965436455603502` | risky (escalated) | **SYSTEM BASE:** Cross-agent conflict resolution. Harmonizes Risk API and Model interfaces. Required to fix history root. | **ESCALATE:** Human review required for Risk API changes. |
| 1 | #1395 | `jules05-auto-merge-policy-update-14778474038957274841` | risky (escalated) | **GOVERNANCE:** Auto-merge policy update. Touches CI/CD safety gates. | **ESCALATE:** Human review required for policy changes. |
| 2 | #1369 | `jules02-security-hardening-model-signatures-17851897229134920353` | risky (escalated) | **SECURITY:** HMAC-SHA256 signature verification for models. Protects against supply chain attacks. | **ESCALATE:** Human review required for security surface changes. |
| 3 | #1384 | `security/model-integrity-guard-13330429797659203878` | risky (escalated) | **SECURITY:** HMAC-SHA256 model integrity guard. Hardens model loading path. | **ESCALATE:** Human review required for security surface changes. |
| 4 | #1386 | `jules02-cli-ux-improvements-8438108481486765359` | risky (escalated) | **UX/CORE:** Configurable polling and setup wizard enhancements. Touches core loop control. | **ESCALATE:** Expert review for core loop changes. |
| 5 | #1389 | `jules02/unified-schemas-5643005943939164146` | risky (escalated) | **SCHEMA:** Unified decision funnel schemas. Touches core data models. | **ESCALATE:** Review for schema consistency. |
| 6 | #1371 | `jules02/risk-reconciliation-8990552146312303501` | blocked | **RESILIENCE:** Synthetic test scenarios for risk reconciliation. Depends on #1372. | Rebase on #1372 after it merges. |
| 7 | #1365 | `feat/rare-event-simulator-enhancements-10851597428787068158` | risky (escalated) | **INTELLIGENCE:** Enhances rare event simulator with stochastic paths. Touches research simulation. | **ESCALATE:** Review for research logic changes. |

---

## 🛠️ Fix Required (Architectural Divergence)

The following PRs are currently classified as Fix Required because they are **DISCONNECTED ROOTS**. They do not share a common history with the harmonized base. Merging them will cause catastrophic repo state.

| PR # | Branch | Reason | Next Action |
| :--- | :--- | :--- | :--- |
| #1350 | `feat-jules-decision-funnel-unification-v2-13333372400311877230` | **CORE:** Unification of model interfaces. Divergent root. | Jules02 to rebase on #1372. |
| #1351 | `feat/confidence-calibration-engine-16069901825976839716` | **INTELLIGENCE:** Modifies main inference logic. Divergent root. | Jules04 to rebase on #1372. |
| #1349 | `feature/regime-detector-institutional-4989658781633186276` | **INTELLIGENCE:** Institutional regime logic. Divergent root. | Jules04 to rebase on #1372. |

---

## ⚠️ Escalation List (Requires Human Sign-off)

Per `docs/integration/AUTO_MERGE_POLICY.md`, the following changes must be manually reviewed by a human lead.

| PR # | Branch | Reason for Escalation | Impact Area |
| :--- | :--- | :--- | :--- |
| #1372 | `Jules05-resolve-cross-agent-conflict-13854965436455603502` | **CORE:** Final Risk API Harmonization. Modifies `RiskManager`. | Trading Execution |
| #1395 | `jules05-auto-merge-policy-update-14778474038957274841` | **GOVERNANCE:** Auto-merge policy modification. | CI/CD Safety |
| #1369 | `jules02-security-hardening-model-signatures-17851897229134920353` | **SECURITY:** New HMAC verification layer for model loading. | Security Surface |
| #1384 | `security/model-integrity-guard-13330429797659203878` | **SECURITY:** New HMAC integrity guard for model files. | Security Surface |
| #1386 | `jules02-cli-ux-improvements-8438108481486765359` | **UX/CORE:** Modifies core loop polling and setup wizard. | Execution Control |

---

## 📅 Stale / Superseded / Low-Priority

- **Superseded:** All PRs targeting `main` opened before 2026-05-22 that do not include the "Big Bang" root.
- **Low-Priority:** Stale UX enhancements (e.g., #1281) until core stability is restored.

---

## 🚨 Critical Process Alert
**Status:** 🔴 CRITICAL FRAGMENTATION
**Warning:** The `main` branch still lacks the harmonized Risk API. "Risk API Drift" is the primary blocker for autonomous trading.
**Directive:** Priority 0 (#1372) MUST be the focus of all coordination until merged.

---
*Last Updated: 2026-05-23 by Jules05*
