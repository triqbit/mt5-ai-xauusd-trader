# Auto-Merge Policy

This document defines the strict auto-merge policy for the MT5 AI/ML Trading Bot project. The goal is to eliminate 80% of manual approval friction while maintaining enterprise safety.

## Auto-Merge Criteria

Auto-merge is **ONLY** allowed when **ALL** of the following conditions are met:

- ✅ **CI Checks:** All required CI checks must pass (tests, lint, coverage ≥ 80%, security scan clean).
- ✅ **Approvals:** Required code owners have approved the pull request.
- ✅ **No Merge Conflicts:** No conflicts with the target branch.
- ✅ **Safety:** No high-risk files (as defined below) are touched.
- ✅ **Test Coverage:** Tests must be added or updated for any new functionality (mandatory if `src/` or `main.py` is touched).
- ✅ **Documentation:** Documentation must be updated where required by the change (mandatory if `src/` or `main.py` is touched).
- ✅ **Observability:** Observability and logging must meet project standards (standard `structlog`, no plain `print()` statements in `src/`).
- ✅ **Architecture:** Changes must fit within existing architectural conventions.

## Block and Escalate Rules

Automatically **BLOCK** and **ESCALATE** if any of these are true:

- 🚨 **Changes to live trading execution logic:** Modification to `src/trading/executor.py`, `src/trading/mt5_connector.py`, or files interacting with MT5 order placement.
- 🚨 **Modifications to risk parameters or position sizing:** Changes to `src/core/risk_engine.py`, `src/trading/risk_engine.py`, `src/trading/risk_manager.py`, `src/trading/audited_risk_manager.py`, `src/trading/capital_allocator.py`, or `src/trading/execution_filter.py`.
- 🚨 **Credential, secret, or auth surface changes:** Any change to `config/secrets.*`, `.env.*`, or `src/core/config.py`.
- 🚨 **Destructive database migrations:** Migrations in `migrations/` that alter historical trade data or schema.
- 🚨 **Docker deployment or infrastructure control changes:** Changes to `Dockerfile`, `docker-compose.yml`, or `.github/workflows/deploy.*`.
- 🚨 **Changes to CI/CD workflows that affect deployment or quality gates:** Modifications to `.github/workflows/ci.yml`.

## High-Risk Files (Auto-Merge Prohibited)

The following patterns trigger an automatic block and escalation:

### Trading & Risk
- `src/trading/executor.py`
- `src/trading/mt5_connector.py`
- `src/core/risk_engine.py`
- `src/trading/risk_engine.py`
- `src/trading/risk_manager.py`
- `src/trading/audited_risk_manager.py`
- `src/trading/capital_allocator.py`
- `src/trading/execution_filter.py`

### Security & Auth
- `config/secrets.*`
- `.env.*`
- `src/core/config.py`

### Infrastructure & CI/CD
- `Dockerfile`
- `docker-compose.yml`
- `.github/workflows/deploy.*`
- `.github/workflows/ci.yml`
- `migrations/.*`

## Escalation Procedure

1. **Identification:** The `auto-merge-policy.yml` workflow blocks the PR and adds the `escalated-risk` label.
2. **Notification:** A comment is posted explaining the specific policy violation and category.
3. **Review:** A Lead Engineer or Product Owner must perform a deep-dive review.
4. **Validation:** Manual verification in a staging environment is mandatory for execution or risk logic changes.
5. **Approval:** Two senior approvals are required for any change labeled `escalated-risk`.

## Audit Log of Auto-Merge Decisions

| Date | PR # | Action | Reason | Result |
| :--- | :--- | :--- | :--- | :--- |
| 2026-05-13 | N/A | Policy Update | Jules05: Strict auto-merge enforcement (Refined high-risk patterns & categories) | [System Change] |
| 2026-05-08 | N/A | Policy Update | Jules05: Strict auto-merge enforcement (including docker-compose and ci.yml) | [System Change] |
| 2026-05-07 | N/A | Policy Update | Jules05: Strict auto-merge enforcement implemented | [System Change] |
| 2026-04-30 | #368 | Auto-Merged | Policy checks passed | [PR](https://github.com/triqbit/mt5-ai-xauusd-trader/pull/368) |
| 2026-04-29 | #365 | Auto-Merged | Policy checks passed | [PR](https://github.com/triqbit/mt5-ai-xauusd-trader/pull/365) |
