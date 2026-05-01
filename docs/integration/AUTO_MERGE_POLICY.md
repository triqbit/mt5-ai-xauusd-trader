# Auto-Merge Policy

This document defines the strict auto-merge policy for the MT5 AI/ML Trading Bot project. The goal is to eliminate 80% of manual approval friction while maintaining enterprise safety.

## Auto-Merge Criteria

Auto-merge is **ONLY** allowed when **ALL** of the following conditions are met:

- ✅ **CI Checks:** All required CI checks must pass (tests, lint, coverage ≥ 80%, security scan clean).
- ✅ **Approvals:** Required code owners have approved the pull request.
- ✅ **Conflicts:** No merge conflicts with the target branch.
- ✅ **Safety:** No high-risk files (as defined below) are touched.
- ✅ **Test Coverage:** Tests must be added or updated for any new functionality.
- ✅ **Documentation:** Documentation must be updated where required by the change.
- ✅ **Observability:** Observability and logging must meet project standards (standard `structlog`, no `print` statements, mandatory docstrings).
- ✅ **Architecture:** Changes must fit within existing architectural conventions (e.g., using `MT5Connector`, Pydantic models for config).

## High-Risk Files (Auto-Merge Blocked)

Changes to the following files or patterns will automatically block auto-merge and require manual review by a lead engineer:

- `src/trading/executor.py` (Live trading execution logic)
- `src/core/risk_engine.py` (Core risk calculation engine)
- `src/trading/order_manager.py` (Order execution and management)
- `src/trading/portfolio_manager.py` (Portfolio and state management)
- `src/trading/mt5_connector.py` (MT5 integration and connectivity)
- `src/trading/risk_manager.py` (Risk parameters and position sizing)
- `src/core/config.py` (System configuration and security defaults)
- `config/secrets.*` (Credentials, secrets, or auth surface changes)
- `.github/workflows/deploy.*` (Deployment control changes)
- `.github/workflows/ci.yml` (CI/CD workflows that affect deployment)
- `Dockerfile` (Infrastructure-as-code and container definitions)
- `migrations/.*` (Database migrations, especially destructive ones)

## Escalation Procedure

Pull requests that trigger a block must be manually reviewed and merged. The following scenarios require **IMMEDIATE ESCALATION** to the Lead Architect or Product Owner:

1. **Identification:** The `auto-merge-policy.yml` workflow will automatically block the PR and add the `escalated-risk` label.
2. **Notification:** A comment will be posted on the PR explaining the reason for the block.
3. **Review:** A Lead Engineer or Product Owner must perform a deep-dive review of the changes.
4. **Validation:** For high-risk changes, manual verification in a staging/demo environment is mandatory.
5. **Approval:** Two senior approvals are required for any change labeled `escalated-risk`.
6. **Merge:** The PR must be merged manually after all criteria are met.

## Audit Log

Auto-merge decisions are recorded here for transparency and accountability. This log is automatically updated by the `auto-merge-audit.yml` workflow upon PR closure for low-risk changes.

| Date | PR # | Action | Reason | Result |
| :--- | :--- | :--- | :--- | :--- |
| 2026-04-30 | #368 | Auto-Merged | Policy checks passed | [PR](https://github.com/triqbit/mt5-ai-xauusd-trader/pull/368) |
| 2026-04-29 | #365 | Auto-Merged | Policy checks passed | [PR](https://github.com/triqbit/mt5-ai-xauusd-trader/pull/365) |
