# Merge-Readiness Checklist

Generated on: 2026-05-03

This checklist identifies top promising PRs for immediate review.

## ⚠️ Critical Repository State Notice
The `main` branch has recently undergone monolithic history grafting (last observed commit `c0885cd`). Most open PRs, including the candidates below, are currently in a state that would cause significant code regressions (deletion of thousands of lines of recently integrated institutional logic) if merged without a full rebase onto the latest `main`.

## 1. PR #550: Refactor Docker environment and enable multi-arch CI support
- **Scope Summary**: Updates Docker infrastructure for multi-stage builds and multi-platform (linux/amd64, linux/arm64) support.
- **Domains Touched**: Infra, Docker, CI/CD.
- **CI Status**: Unknown (Pending/Stale).
- **Missing Items**: Requires a full rebase onto `main`. Currently shows deletion of ~200 files integrated into `main`.
- **Recommendation**: **Needs rebase** — High risk of regression. Once rebased, it is a high-value infra improvement.

## 2. PR #548: 🤖 Jules05: Auto-merge policy update
- **Scope Summary**: Refines the automated merge policy and merge queue documentation.
- **Domains Touched**: Governance, Documentation, GitHub Actions.
- **CI Status**: Unknown (Pending/Stale).
- **Missing Items**: Requires a full rebase. Current diff indicates a reset of many `docs/` and `src/` files to an older state.
- **Recommendation**: **Needs rebase** — Safe once rebased as it primarily touches non-trading logic.

## 3. PR #532: ⚡ Bolt: Vectorize row access in Benchmark Adapters
- **Scope Summary**: Performance optimization for benchmark adapters by vectorizing row access.
- **Domains Touched**: Research, Analytics, Performance.
- **CI Status**: Unknown (Pending/Stale).
- **Missing Items**: Requires a full rebase.
- **Recommendation**: **High-risk — needs domain expert review** and rebase. Touches research benchmarking logic.

## 4. PR #539: Institutional Feature Engineering Pipeline with MTF and TA-Lib Integration
- **Scope Summary**: Enhances the feature engineering pipeline with Multi-Timeframe and TA-Lib support.
- **Domains Touched**: Core, Research, Feature Engineering.
- **CI Status**: Pending.
- **Missing Items**: Requires a full rebase.
- **Recommendation**: **Needs rebase** — Promising core advancement but currently out of sync with `main`.

---
*Prepared by Jules06 (qufuwan) for Jules05 and human review.*
