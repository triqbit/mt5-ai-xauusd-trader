# 🎯 Jules05: Deterministic Merge Queue [2026-05-15]

This document serves as the authoritative source of truth for the integration state and merge priorities of the repository, managed by Jules05.

## 📊 Summary State
- **Merge-Ready**: 1
- **Fix-Required**: 15+ (Divergent branches)
- **Blocked**: 0
- **Risky (Escalated)**: 12
- **Superseded/Stale**: 495+

---

## 🚀 Priority Merge Queue

| Order | PR # | Branch | Classification | Rationale | Next Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | #1187 | `tech-debt-cleanup-16405513240068772382` | merge-ready | **BASE:** Big Bang Harmonization. Resolves architectural drift and implements 8-layer safety cascade. Must merge before any other PRs. | Merge to main. |
| 2 | #1112 | `observability-resilience-metrics-6812208704950725445` | fix-required | **SAFE SURFACE:** High diagnostic value but stale (Pre-Big-Bang). | Rebase on tech-debt-cleanup. |
| 3 | #1136 | `jules05-product-coherence-improvements-6139647032211712134` | fix-required | **COHERENCE:** Systematic cleanup but stale (Pre-Big-Bang). | Rebase on tech-debt-cleanup. |
| 4 | #1210 | `jules02-unified-schemas-8823223411712761998` | fix-required | **GOVERNANCE:** Unified decision schemas. Stale (Pre-Big-Bang). | Rebase on tech-debt-cleanup. |

---

## 🛠️ Fix Required (Architectural Divergence)

The following PRs are currently classified as Fix Required because they are stale relative to the Big Bang commit (`e23adfa`). Merging them as-is would destroy the harmonized architecture.

| PR # | Branch | Reason | Next Action |
| :--- | :--- | :--- | :--- |
| #1227 | `jules02-db-reconciliation-6133725546972143180` | **STALE:** New work but lacks Big Bang base. | Jules02 to rebase. |
| #1223 | `feat/stress-lab-severity-tracking-15885290868617108463` | **STALE:** New work but lacks Big Bang base. | Jules04 to rebase. |
| #1222 | `feat/macro-event-intelligence-10701451590615114884` | **STALE:** New work but lacks Big Bang base. | Jules04 to rebase. |
| #1215 | `jules02-regime-adaptive-safety-hardening-4357052007584945700` | **STALE:** New work but lacks Big Bang base. | Jules02 to rebase. |
| #1212 | `resilience-recovery-path-7031444098850161571` | **STALE:** New work but lacks Big Bang base. | Jules02 to rebase. |
| #1207 | `feat/capital-allocator-institutional-7216075788528344685` | **STALE:** Pre-Big-Bang. | Jules04 to rebase. |
| #1159 | `integration-test-coverage-risk-cascade-6731118668585697452` | **STALE:** Pre-Big-Bang. | Jules02 to rebase. |
| #1157 | `jules-ci-quality-fix-2377864910779478693` | **STALE:** Pre-Big-Bang. | Jules02 to rebase. |

---

## ⚠️ Escalation List (Requires Human Sign-off)

The following changes touch high-risk areas and require manual review per the Jules05 Escalation Policy.

| PR # | Branch | Reason for Escalation | Impact Area |
| :--- | :--- | :--- | :--- |
| #1227 | `jules02-db-reconciliation-...` | **DB:** Touches `migrations/`. | Database |
| #1215 | `jules02-regime-adaptive-...` | **RISK:** Touches `RiskManager`. | Risk Management |
| #1207 | `feat/capital-allocator-...` | **RISK:** Touches `capital_allocator.py`. | Risk Management |
| #1212 | `resilience-recovery-path-...` | **DB/CORE:** Touches DB retries and state recovery. | Core/Resilience |
| #1222 | `feat/macro-event-intelligence-...` | **TRADING:** Touches signal filtering and intelligence. | Trading Logic |

---

## 📅 Stale / Superseded / Low-Priority

- **Action Required:** Bulk close 495 stale PRs/branches dated before 2026-05-14.
- **Superseded:** All PRs pre-dating the Big Bang (2026-05-14) that have not been rebased.

---

## 🚨 Critical Process Alert
**Integration Status:** Transitioning to Release Candidate v1.1.0-rc10.
**Warning:** Severe divergence detected. `main` must be aligned with the Big Bang commit (`e23adfa`) immediately.
**Requirement:** All agents must rebase active work on the harmonized base after #1187 is merged.

---
*Last Updated: 2026-05-15 by Jules05*
