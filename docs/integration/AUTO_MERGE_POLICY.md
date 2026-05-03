# Auto-Merge Policy

This document defines the strict auto-merge policy for the MT5 AI/ML Trading Bot project. The goal is to eliminate 80% of manual approval friction while maintaining enterprise safety.

## Auto-Merge Criteria

Auto-merge is **ONLY** allowed when **ALL** of the following conditions are met:

- ✅ **CI Checks:** All required CI checks must pass (tests, lint, coverage ≥ 80%, security scan clean).
- ✅ **Approvals:** Required code owners have approved the pull request.
- ✅ **No Merge Conflicts:** No conflicts with the target branch.
- ✅ **Safety:** No high-risk files (as defined below) are touched.
- ✅ **Test Coverage:** Tests must be added or updated for any new functionality.
- ✅ **Documentation:** Documentation must be updated where required by the change.
- ✅ **Observability:** Observability and logging must meet project standards (standard `structlog`, no `print` statements, mandatory docstrings).
- ✅ **Architecture:** Changes must fit within existing architectural conventions.

## Block and Escalate Rules

Automatically **BLOCK** and **ESCALATE** if any of these are true:

- 🚨 **Changes to live trading execution logic:** Modification to `src/trading/executor.py`, `src/trading/mt5_connector.py`, or `src/trading/order_manager.py`.
- 🚨 **Modifications to risk parameters or position sizing:** Changes to `src/core/risk_engine.py`, `src/trading/risk_manager.py`, or `src/trading/portfolio_manager.py`.
- 🚨 **Credential, secret, or auth surface changes:** Any change to `config/secrets.*`, `src/core/config.py`, or credential handling.
- 🚨 **Destructive database migrations:** Migrations in `migrations/` that alter historical trade data or schema.
- 🚨 **Docker deployment or infrastructure control changes:** Changes to `Dockerfile` or `docker-compose.yml`.
- 🚨 **Changes to CI/CD workflows that affect deployment:** Modifications to `.github/workflows/deploy.*` or `ci.yml`.

## High-Risk Files (Auto-Merge Prohibited)

The following patterns trigger an automatic block and escalation:

- `src/trading/executor.py`
- `src/trading/mt5_connector.py`
- `src/trading/order_manager.py`
- `src/core/risk_engine.py`
- `src/trading/risk_manager.py`
- `src/trading/portfolio_manager.py`
- `src/core/config.py`
- `config/secrets.*`
- `.github/workflows/deploy.*`
- `.github/workflows/ci.yml`
- `Dockerfile`
- `docker-compose.yml`
- `migrations/.*`

## Escalation Procedure

1. **Identification:** The `auto-merge-policy.yml` workflow blocks the PR and adds the `escalated-risk` label.
2. **Notification:** A comment is posted explaining the policy violation.
    - *Exemption:* Jules05 policy updates are exempt from self-blocking to allow for maintenance.
3. **Review:** A Lead Engineer or Product Owner must perform a deep-dive review.
4. **Validation:** Manual verification in a staging environment is mandatory.
5. **Approval:** Two senior approvals are required for any change labeled `escalated-risk`.

## Audit Log of Auto-Merge Decisions

This log is automatically maintained by the system.

| Date | PR # | Action | Reason | Result |
| :--- | :--- | :--- | :--- | :--- |
| 2026-05-03 | N/A | Updated | Strict auto-merge policy enforcement | [Jules05] |
| 2026-04-30 | #368 | Auto-Merged | Policy checks passed | [PR](https://github.com/triqbit/mt5-ai-xauusd-trader/pull/368) |
| 2026-04-29 | #365 | Auto-Merged | Policy checks passed | [PR](https://github.com/triqbit/mt5-ai-xauusd-trader/pull/365) |
