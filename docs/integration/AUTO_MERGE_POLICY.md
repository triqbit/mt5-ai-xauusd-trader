# Auto-Merge Policy

This document defines the strict auto-merge policy for the MT5 AI/ML Trading Bot project. The goal is to eliminate 80% of manual approval friction while maintaining enterprise safety for a trading system.

## Auto-Merge Criteria

Auto-merge is **ONLY** allowed when **ALL** of the following conditions are met:

- ✅ **CI Checks Passing:** All required CI checks must pass (tests, lint, coverage ≥ 80%, security scan clean).
- ✅ **Required Approvals:** Required code owners have approved the pull request.
- ✅ **No Merge Conflicts:** No conflicts with the target branch.
- ✅ **Safety First:** No high-risk files (as defined below) are touched.
- ✅ **Test Coverage:** Tests must be added or updated for any new functionality.
- ✅ **Documentation:** Documentation must be updated where required by the change.
- ✅ **Observability Standards:** Logging must meet standards (standard `structlog`, no `print` statements in `src/`, mandatory docstrings).
- ✅ **Architectural Fit:** Changes must fit within existing architectural conventions.

## Block and Escalate Rules

Automatically **BLOCK** and **ESCALATE** if any of these are true:

- 🚨 **Changes to live trading execution logic:** Modification to `src/trading/executor.py` or files interacting with MT5 order placement.
- 🚨 **Modifications to risk parameters or position sizing:** Changes to `src/core/risk_engine.py`, `src/trading/risk_engine.py`, or `src/trading/risk_manager.py`.
- 🚨 **Credential, secret, or auth surface changes:** Any change to `config/secrets.*` or credential handling.
- 🚨 **Destructive database migrations:** Migrations in `migrations/` that alter historical trade data or schema.
- 🚨 **Docker deployment or infrastructure control changes:** Changes to `Dockerfile` or container orchestration.
- 🚨 **Changes to CI/CD workflows that affect deployment:** Modifications to `.github/workflows/deploy.*` or `ci.yml`.

## High-Risk File Patterns (Auto-Merge Prohibited)

The following patterns trigger an automatic block and escalation:

- `src/trading/executor.py`
- `src/core/risk_engine.py`
- `src/trading/risk_engine.py`
- `src/trading/risk_manager.py`
- `config/secrets.*`
- `.github/workflows/deploy.*`
- `.github/workflows/ci.yml`
- `Dockerfile`
- `migrations/.*`

## Escalation Procedure

1. **Identification:** The `auto-merge-policy.yml` workflow blocks the PR and adds the `escalated-risk` label.
2. **Notification:** A comment is posted on the PR explaining the policy violation and the need for manual review.
3. **Review:** A Lead Engineer or Product Owner must perform a deep-dive review of the escalated changes.
4. **Validation:** Manual verification in a staging environment is mandatory for escalated risks.
5. **Approval:** At least two senior approvals are required for any change labeled `escalated-risk`.

## Audit Log of Auto-Merge Decisions

This log tracks auto-merge decisions for transparency and compliance.

| Date | PR # | Action | Reason | Result |
| :--- | :--- | :--- | :--- | :--- |
| 2026-04-30 | #368 | Auto-Merged | Policy checks passed | [PR](https://github.com/triqbit/mt5-ai-xauusd-trader/pull/368) |
| 2026-04-29 | #365 | Auto-Merged | Policy checks passed | [PR](https://github.com/triqbit/mt5-ai-xauusd-trader/pull/365) |
