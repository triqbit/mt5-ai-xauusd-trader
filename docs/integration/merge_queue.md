# Jules05: Integration Merge Queue

**Date:** April 27, 2026
**Author:** Jules05 (Integration Governor)
**Status:** Active

## 🎯 Executive Summary
This document serves as the authoritative source of truth for the repository's integration state. All branch merges must follow the priority defined here. Risky changes affecting live trading or core risk logic are escalated for human approval.

---

## 🚦 Branch Classification

### ✅ Merge-Ready (High Priority)
*Foundational fixes and scaffolding that resolve current CI/CD failures and establish project structure.*

| Branch | Description | Next Action |
| :--- | :--- | :--- |
| `origin/fix-ci-and-imports-3046185923106439279` | Resolves CI failures, import errors, and `main.py` logic. Most comprehensive fix. | **Merge to main** |
| `origin/scaffold-enterprise-src-4481247120820447229` | Establishes enterprise directory structure and core modules. | **Merge after CI fix** |
| `origin/atlas-production-ready-logic-3183940976416666717` | Critical initialization fixes for `main.py` and `RiskManager`. | **Merge with Scaffolding** |
| `origin/feat/enterprise-governance-6323515867174033642` | Implements contribution governance and repository controls. | **Merge to main** |

### ⚠️ Risky (Escalated for Human Sign-off)
*Changes touching live trading execution, risk parameters, or security.*

| Branch | Description | Risk Factor |
| :--- | :--- | :--- |
| `origin/advanced-risk-management-9398696029163028749` | Implements advanced risk rules. | Modifies core risk logic. |
| `origin/feat/capital-allocator-2295387355869441054` | Institutional-grade capital allocation. | Affects position sizing and exposure. |
| `origin/feature/execution-filter-cascade-2680833654317939670` | 6-layer execution filter. | Directly gates trade execution. |
| `origin/shield/fix-unsafe-pytorch-load-1958796467089920034` | Security fix for model loading. | Touches binary artifact loading. |

### 🛠️ Fix-Required / Blocked
*Branches with failing checks or waiting for foundational dependencies.*

| Branch | Dependency | Next Action |
| :--- | :--- | :--- |
| `origin/feature/rl-evaluation-module-3083043083700434420` | `scaffold-enterprise-src` | Rebase after scaffolding merge. |
| `origin/feature/benchmarking-framework-12225164502670516368` | `scaffold-enterprise-src` | Rebase after scaffolding merge. |

### ⏩ Superseded
*Replaced by newer or more comprehensive work.*

| Branch | Superseded By | Reason |
| :--- | :--- | :--- |
| `origin/fix/ci-pipeline-and-imports-12481436982634906248-5092811707976827255` | `fix-ci-and-imports-3046...` | 3046 is more recent and covers more components. |
| `origin/fix-ci-and-imports-3453867646978336275` | `fix-ci-and-imports-3046...` | Older version of CI fix. |
| `origin/bolt-optimize-gym-env-obs-14044301027058587888` | `bolt-optimize-gym-env-obs-1267...` | Latest CI fix in 1267 version. |

### 💤 Strategically Low-Priority
*Technically valid but not contributing to current Phase 1 objectives.*

| Branch | Description | Current Status |
| :--- | :--- | :--- |
| `origin/palette/micro-ux-enhancements-6584088588365220719` | Session summary UI enhancements. | Hold until core trading logic is stable. |

### 🏚️ Stale / To-be-deleted
*Branches that are over 5 days old without recent activity, or are fragmented versions of integrated features. These are currently excluded from the active queue.*

| Category | Count | Action |
| :--- | :--- | :--- |
| Historical Fixes (`fix-*`, `fix/*`) | 10+ | Mark for deletion after CI fix merge. |
| Fragmented Features (`feat/*`, `feature/*`) | 60+ | Evaluate for cherry-picking or archive. |
| Temporary Refactors (`docker-*`, `bolt-*`) | 15+ | Superseded by latest CI/Docker work. |
| Governance/Docs Snapshots | 10+ | Archive once standards are merged to main. |

---

## 📅 Merge Queue Order

1. **`fix-ci-and-imports-3046185923106439279`** (Priority: CRITICAL)
2. **`scaffold-enterprise-src-4481247120820447229`** (Priority: HIGH)
3. **`atlas-production-ready-logic-3183940976416666717`** (Priority: HIGH)
4. **`feat/enterprise-governance-6323515867174033642`** (Priority: MEDIUM)
5. **`setup-versioning-automation-6242588021629564226`** (Priority: MEDIUM)

---

## 🚨 Escalation List (Human Action Required)

The following PRs require manual review by a Human Senior Developer or Risk Officer before Jules05 can approve integration:

1. **Risk Management Overhaul:** `origin/advanced-risk-management-9398696029163028749`
2. **Execution Logic Change:** `origin/feature/execution-filter-cascade-2680833654317939670`
3. **Capital Allocation Logic:** `origin/feat/capital-allocator-2295387355869441054`
4. **Security Hardening (Model Load):** `origin/shield/fix-unsafe-pytorch-load-1958796467089920034`

---

## 🔄 Governance Rules (Jules05)
- **No Direct Push to Main:** All changes must go through this queue.
- **CI Dependency:** No merge-ready branch will be integrated until CI is green.
- **Risk Gate:** Any branch touching `src/trading` or `src/core/risk_manager.py` is automatically classified as `risky`.
