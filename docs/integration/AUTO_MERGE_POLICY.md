# Auto-Merge Policy

This document defines the strict auto-merge policy for the `mt5-ai-xauusd-trader` repository. The goal is to eliminate 80% of manual approval friction while maintaining enterprise safety.

## 1. Auto-Merge Criteria

Auto-merge is **ONLY** allowed when **ALL** the following conditions are met:

- ✅ **CI Checks Passing**: All required CI checks must pass (tests, lint, coverage ≥ 80%, security scan clean).
- ✅ **Approvals**: Required code owners have approved the changes.
- ✅ **No Conflicts**: No merge conflicts with the target branch.
- ✅ **Low Risk**: No high-risk files (see list below) have been touched.
- ✅ **Tested**: Tests must be added or updated for any new functionality.
- ✅ **Documented**: Documentation must be updated where required.
- ✅ **Observability**: Changes must meet logging and observability standards.
- ✅ **Architecture**: Change must fit existing architectural conventions.

## 2. High-Risk File Patterns

Any modification to files matching these patterns **BLOCKS** auto-merge and requires manual review:

- `src/trading/executor.py` (Core execution logic)
- `src/core/risk_engine.py` (Risk parameters and position sizing)
- `src/trading/risk_manager.py` (Trading risk management)
- `config/secrets.*` (Credentials and secrets)
- `.github/workflows/deploy.*` (Deployment workflows)
- `Dockerfile` and infrastructure-related files
- Database migrations affecting existing schemas

## 3. Escalation Procedure

If any of the following are true, the PR must be **BLOCKED** and **ESCALATED** to human reviewers:

- 🚨 Changes to live trading execution logic.
- 🚨 Modifications to risk parameters or position sizing.
- 🚨 Credential, secret, or auth surface changes.
- 🚨 Destructive database migrations.
- 🚨 Docker deployment or infrastructure control changes.
- 🚨 Changes to CI/CD workflows that affect deployment.

## 4. Audit Log of Auto-Merge Decisions

| Date | PR # | Action | Reason |
|------|------|--------|--------|
| 2024-05-22 | N/A | Policy Created | Initial implementation of Jules05 auto-merge policy. |
