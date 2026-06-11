# Merge-Readiness Checklist

> [!IMPORTANT]
> **Critical Repository State Notice:** The `main` branch is currently operating under a history-grafting model. All merges must be carefully audited to ensure they do not accidentally overwrite or regress core logic from other active modules. **Mandatory rebase against commit `e61fc1d` is required for all PRs.**

> [!WARNING]
> **Global CI Blockage:** The 'Fast Validation' CI check is currently failing on `main` due to global formatting drift (120 files out of compliance with `ruff==0.4.3`). All PRs will fail CI until this baseline drift is addressed by a repository-wide reformat.

Generated on: 2026-06-11 14:30:00 UTC

This checklist identifies top promising PRs for immediate review.

## 1. PR #1336: DX: improve developer onboarding and contribution experience
- **Short scope summary**: Updates documentation and setup scripts to improve the developer experience and onboarding process.
- **Domains touched**: docs, infra/scripts
- **CI status**: unknown (Blocked by global formatting drift)
- **Missing items**: Mandatory rebase against commit `e61fc1d`
- **Recommendation**: Candidate for detailed review once rebased.

## 2. PR #1300: 🧹 Jules05: Technical debt cleanup — architectural harmonization
- **Short scope summary**: Core cleanup and architectural alignment across multiple modules to reduce technical debt.
- **Domains touched**: core architecture, refactor
- **CI status**: unknown (Blocked by global formatting drift)
- **Missing items**: Mandatory rebase against commit `e61fc1d`
- **Recommendation**: Candidate for review after rebase and validation.

## 3. PR #1210: docs: 📘 Jules02: Documentation and schema governance — Unified decision schemas and tracing
- **Short scope summary**: Unifies decision schemas and implements tracing for better documentation and schema governance.
- **Domains touched**: docs, schema governance
- **CI status**: unknown (Blocked by global formatting drift)
- **Missing items**: Mandatory rebase against commit `e61fc1d`
- **Recommendation**: Candidate for review once rebase is confirmed.

---
*Prepared by Jules06 (qufuwan) for Jules05 and human review.*
