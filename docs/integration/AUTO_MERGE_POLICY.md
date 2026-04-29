# Auto-Merge Policy

This document defines the strict auto-merge policy for the `mt5-ai-xauusd-trader` repository. The goal is to eliminate 80% of manual approval friction while maintaining enterprise safety for a trading system.

## ✅ Auto-Merge Criteria

Auto-merge is **ONLY** allowed when **ALL** the following conditions are met:

1.  **CI Checks:** All required CI checks must pass (tests, lint, coverage ≥80%, security scan clean).
2.  **Approvals:** Required code owners have approved the pull request.
3.  **No Conflicts:** The pull request has no merge conflicts with the base branch.
4.  **Low Risk:** No high-risk files (as defined below) are touched.
5.  **Tests:** Tests must be added or updated for any new functionality.
6.  **Documentation:** Documentation must be updated where required.
7.  **Observability:** Logging and observability must meet the system's enterprise standards.
8.  **Architecture:** The changes must fit within existing architectural conventions.

## 🚨 Blocking & Escalation (High-Risk)

Auto-merge is strictly **BLOCKED** and requires manual human review/escalation if any of the following are true:

*   **Live Trading Logic:** Changes to `src/trading/executor.py` or any core trading execution logic.
*   **Risk Parameters:** Modifications to risk parameters, position sizing, or `src/core/risk_engine.py`.
*   **Security/Auth:** Changes to `config/secrets.*`, credential handling, or the authentication surface.
*   **Infrastructure/CI:** Changes to `.github/workflows/deploy.*`, Docker deployment controls, or CI/CD workflows affecting deployment.
*   **Database:** Destructive database migrations.

### High-Risk File Patterns

The following patterns are monitored and will trigger an automatic block of auto-merge:

- `src/trading/executor.py`
- `src/core/risk_engine.py`
- `src/trading/risk_manager.py`
- `config/secrets.*`
- `.github/workflows/deploy.*`
- `Dockerfile`
- `migrations/`

## 📈 Escalation Procedure

1.  If a PR is blocked by the auto-merge policy, the `auto-merge-policy` workflow will fail with a descriptive error.
2.  The PR author must request a manual review from the relevant lane lead (Jules01-Jules04) or a human operator.
3.  Risk-related changes **MUST** be approved by the Risk Lead (Jules02) or a human administrator.

## 📝 Audit Log

| Date | PR # | Author | Decision | Reason |
| :--- | :--- | :--- | :--- | :--- |
| 2026-04-29 | N/A | Jules05 | Policy Established | Initial policy creation |
