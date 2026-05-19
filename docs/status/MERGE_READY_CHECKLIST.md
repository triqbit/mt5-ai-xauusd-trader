# Merge-Readiness Checklist

> [!IMPORTANT]
> **Critical Repository State Notice:** The `main` branch is currently operating under a history-grafting model. All merges must be carefully audited to ensure they do not accidentally overwrite or regress core logic from other active modules.

Generated on: 2026-05-19 18:00:00 UTC

This checklist identifies top promising PRs for immediate review.

## 1. PR #1351: Institutional Research Reporting Enhancements
- **Short scope summary**: Enhances the research reporting framework by improving Pydantic model validation for performance metrics and adding more granular analytics to generated reports.
- **Domains touched**: analytics, docs, research, tests
- **CI status**: pending
- **Missing items**: documentation for new reporting fields
- **Recommendation**: Ready for detailed review once CI passes; focus on the impact on existing report formats.

## 2. PR #1349: 📘 Jules02: Documentation and schema governance — Decision funnel unification
- **Short scope summary**: Unifies decision-making schemas across models and trading filters, establishing a consistent "decision funnel" for better traceability and observability.
- **Domains touched**: AI models, core architecture, core trading, database, tests
- **CI status**: pending
- **Missing items**: full regression suite for schema changes
- **Recommendation**: High-risk infrastructure change; requires domain expert review of `src/core/` and `src/trading/` to ensure schema compatibility.

## 3. PR #1353: Daily PR Intake & Risk Triage Dashboard [2026-05-19]
- **Short scope summary**: Updates the daily triage dashboard and aligns the "Big Bang" logic with the latest monolithic history graft (PR #1350).
- **Domains touched**: docs, infra/scripts
- **CI status**: pending
- **Missing items**: None identified
- **Recommendation**: Operational update; candidate for review to maintain process visibility after the recent system-wide swap.

---
*Prepared by Jules06 (qufuwan) for Jules05 and human review.*
