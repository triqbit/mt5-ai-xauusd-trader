# Merge-Readiness Checklist

> [!IMPORTANT]
> **Critical Repository State Notice:** The `main` branch is currently operating under a history-grafting model. All merges must be carefully audited to ensure they do not accidentally overwrite or regress core logic from other active modules. **Mandatory rebase against commit `58a3d9de20ea747acf06a52981d8a0098a86d97f` is required for all PRs.**

Generated on: 2026-06-16 14:30:00 UTC

This checklist identifies top promising PRs for immediate review.

## 1. PR #1336: DX: improve developer onboarding and contribution experience
- **Short scope summary**: Safe Surface update improving documentation and CI dependency harmonization.
- **Domains touched**: docs, ci/deps
- **CI status**: unknown (Stale - Pre-Big-Bang)
- **Missing items**: Mandatory rebase against commit `58a3d9de20ea747acf06a52981d8a0098a86d97f`
- **Recommendation**: Candidate for review after rebase and CI success.

## 2. PR #1210: docs: 📘 Jules02: Documentation and schema governance — Unified decision schemas and tracing
- **Short scope summary**: Formalizes risk and execution decisions using structured Pydantic schemas and implements trace ID propagation.
- **Domains touched**: docs, core/schemas, trading
- **CI status**: unknown (Stale - Pre-Big-Bang)
- **Missing items**: Mandatory rebase against commit `58a3d9de20ea747acf06a52981d8a0098a86d97f`
- **Recommendation**: High-value governance improvement. Candidate for review after rebase.

## 3. PR #1300: 🧹 Jules05: Technical debt cleanup — architectural harmonization
- **Short scope summary**: Consolidates RiskEngine/RiskManager and relocates FeatureEngineer for better domain separation.
- **Domains touched**: refactor, core, trading
- **CI status**: unknown (Stale - Pre-Big-Bang)
- **Missing items**: Mandatory rebase against commit `58a3d9de20ea747acf06a52981d8a0098a86d97f`
- **Recommendation**: Core architectural cleanup. Candidate for review after rebase.

---
*Prepared by Jules06 (qufuwan) for Jules05 and human review.*
