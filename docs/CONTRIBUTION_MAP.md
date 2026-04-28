# Contribution Map

This document provides a guide to the repository structure, categorizing areas into **Safe Zones** (lower risk, ideal for new contributors) and **Sensitive Zones** (critical components requiring extra care and maintainer oversight).

## 🗺️ Codebase Overview

| Path | Description | Category | Owner (Role) |
| :--- | :--- | :--- | :--- |
| `tests/` | Unit and integration tests | **Safe Zone** | Jules02 |
| `docs/` | Project documentation | **Safe Zone** | All Jules |
| `src/core/` | Configuration & foundation | **Neutral** | Jules01 |
| `src/environment/`| ML Gym environments | **Neutral** | Jules04 |
| `src/models/` | AI/ML Architectures | **Sensitive** | Jules04 / Jules01 |
| `src/trading/` | Execution & Risk Engines | **Sensitive** | Jules01 / Jules02 |
| `scripts/` | Tooling & Setup scripts | **Safe Zone** | Jules06 |

---

## ✅ Safe Zones (High Contribution Accessibility)

These areas are ideal for first-time contributors or those looking to improve system robustness without touching core trading logic.

### 1. `tests/`
- **What to contribute**: Better coverage, edge case testing, performance benchmarks, or fixing flaky tests.
- **Why**: Improves system reliability without affecting production behavior.
- **Owner**: Jules02 (Security, Quality, Validation & Observability).

### 2. `docs/`
- **What to contribute**: Clarifying architecture, improving setup guides, fixing typos, or adding examples.
- **Why**: Enhances developer experience and project credibility.
- **Owner**: Jules06 (Developer Experience & Contributor Trust).

### 3. `scripts/`
- **What to contribute**: Improving `bootstrap.sh`, adding diagnostic tools, or enhancing CLI ergonomics.
- **Why**: Simplifies the first-run experience for other developers.
- **Owner**: Jules06 (Developer Experience).

---

## ⚠️ Sensitive Zones (High Impact, Handle with Care)

Changes in these areas require deep domain knowledge and will undergo rigorous review by specialized maintainers.

### 1. `src/trading/`
- **Focus**: MT5 SDK connectors, order execution, and risk engines.
- **Risk**: Direct financial impact. A bug here can lead to unintended trades or loss of capital.
- **Reviewers**: Jules01 (Core implementation) & Jules02 (Validation).

### 2. `src/models/`
- **Focus**: PPO, Dreamer V3, LSTM, and ensemble logic.
- **Risk**: Strategy degradation. Suboptimal changes can lead to poor performance or "broken" AI logic.
- **Reviewers**: Jules04 (Quant Research) & Jules01 (Core implementation).

### 3. `src/core/`
- **Focus**: Global configuration, Pydantic settings, and system-wide defaults.
- **Risk**: Cross-system instability. Changes here affect every other module.
- **Reviewers**: Jules01 (Core architecture).

---

## 🛠️ Contribution Workflow for Sensitive Areas

If you wish to contribute to a **Sensitive Zone**:
1. **Open an Issue**: Discuss the proposed change with the maintainers first.
2. **Provide Evidence**: Show backtest results, performance metrics, or formal proof of the improvement.
3. **Draft PR**: Submit as a Draft PR for early feedback before final review.

---

## 🚦 PR Governance (Jules05)

All PRs are governed by **Jules05** (Product Stewardship & Integration Governance), who ensures that the change aligns with the project's long-term roadmap and architecture coherence.

---

*Not sure where to start? Check out [FIRST_REAL_CONTRIBUTION.md](./FIRST_REAL_CONTRIBUTION.md) (coming soon) or look for issues labeled `good-first-issue`.*
