# Auto-Merge Policy

This document defines the automated merge policy for the MT5 AI/ML Trading Bot project. The goal is to eliminate 80% of manual approval friction while maintaining enterprise safety for a trading system.

## ✅ Auto-Merge Criteria

Auto-merge is **ONLY** allowed when **ALL** of the following conditions are met:

1.  **CI Checks:** All required CI checks must pass (tests, linting, coverage ≥ 80%, security scan clean).
2.  **Approvals:** Required code owners have approved the pull request.
3.  **Conflicts:** No merge conflicts exist with the base branch.
4.  **No High-Risk Files:** No high-risk files (as defined below) have been modified.
5.  **Testing:** Tests must be added or updated for any new functionality.
6.  **Documentation:** Documentation must be updated where required.
7.  **Observability:** Observability and logging must meet project standards.
8.  **Architecture:** The change must fit existing architectural conventions.

## 🚨 Blocking and Escalation Criteria

Auto-merge is **STRICTLY PROHIBITED** and manual review/escalation is required if any of the following are true:

*   **Trading Logic:** Changes to live trading execution logic.
*   **Risk Parameters:** Modifications to risk parameters or position sizing.
*   **Secrets/Auth:** Credential, secret, or authentication surface changes.
*   **Database:** Destructive database migrations.
*   **Infrastructure:** Docker deployment or infrastructure control changes.
*   **CI/CD:** Changes to CI/CD workflows that affect deployment.

### High-Risk File Patterns

Modifications to the following files or patterns will automatically block auto-merge:

- `src/trading/executor.py`
- `src/core/risk_engine.py`
- `config/secrets.*`
- `.github/workflows/deploy.*`

## 📈 Escalation Procedure

If a pull request is blocked from auto-merging due to one of the criteria above:

1.  The `auto-merge-policy` workflow will fail.
2.  The author must request a manual review from the primary maintainers/code owners.
3.  A minimum of two senior maintainers must approve the change after a thorough review of the high-risk implications.
4.  For live trading or risk parameter changes, a sign-off from the Lead Quant/Risk Officer is mandatory.

## 📝 Audit Log

| Date | PR # | Decision | Reason |
| :--- | :--- | :--- | :--- |
| 2024-05-22 | N/A | Policy Created | Initial implementation of the auto-merge policy. |
