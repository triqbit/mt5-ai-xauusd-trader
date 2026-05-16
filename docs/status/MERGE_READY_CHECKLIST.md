# Merge-Readiness Checklist

> [!IMPORTANT]
> **Critical Repository State Notice:** The `main` branch is currently operating under a history-grafting model. All merges must be carefully audited to ensure they do not accidentally overwrite or regress core logic from other active modules.

Generated on: 2026-05-16 13:10:03 UTC

This checklist identifies top promising PRs for immediate review.

## 1. PR #1245: 🛡️ Jules02: Risk control and drift monitoring — Veto power and schema unification
- **Short scope summary**: Medium Risk update implementing '🛡️ Jules02: Risk control and drift monitoring — Veto power and schema unification'
- **Domains touched**: AI models, core architecture, core trading, tests
- **CI status**: pending
- **Missing items**: docs
- **Qualitative Assessment**: Standardizes risk schemas and introduces veto power, critical for preventing drift-induced rogue trades.
- **Recommendation**: Needs CI success before merge

## 2. PR #1257: Implement Institutional-Grade Capital Allocator
- **Short scope summary**: High Risk update implementing 'Implement Institutional-Grade Capital Allocator'
- **Domains touched**: core architecture, core trading, docs, tests
- **CI status**: pending
- **Missing items**: None identified
- **Qualitative Assessment**: Core infrastructure update for position sizing; requires careful validation of capital protection logic and domain expert sign-off.
- **Recommendation**: High-risk — needs domain expert review

## 3. PR #1256: 📡 Jules02: Observability improvement — Decision funnel and technical metrics
- **Short scope summary**: High Risk update implementing '📡 Jules02: Observability improvement — Decision funnel and technical metrics'
- **Domains touched**: core architecture, core trading, other, tests
- **CI status**: pending
- **Missing items**: docs
- **Qualitative Assessment**: Enhances decision funnel visibility, providing better transparency into trade rejections and technical performance.
- **Recommendation**: High-risk — needs domain expert review

---
*Prepared by Jules06 (qufuwan) for Jules05 and human review.*
