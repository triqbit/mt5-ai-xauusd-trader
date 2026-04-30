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
- ✅ **Observability:** Observability and logging must meet project standards.
- ✅ **Architecture:** Changes must fit within existing architectural conventions.

## High-Risk Files (Auto-Merge Blocked)

Changes to the following files or patterns will automatically block auto-merge and require manual review by a lead engineer:

- `src/trading/executor.py` (and relevant execution logic like `src/trading/order_manager.py`)
- `src/core/risk_engine.py` (and `src/trading/risk_manager.py`)
- `src/trading/mt5_connector.py`
- `config/secrets.*` (and any file containing credentials or auth logic)
- `.github/workflows/deploy.*` (and `.github/workflows/ci.yml`)
- `Dockerfile` and other infrastructure-as-code files.
- `migrations/.*` (Database migrations)

## Escalation Procedure

Pull requests that trigger a block must be manually reviewed and merged. The following scenarios require **IMMEDIATE ESCALATION** to the Lead Architect or Product Owner:

- 🚨 Changes to live trading execution logic.
- 🚨 Modifications to risk parameters or position sizing.
- 🚨 Credential, secret, or auth surface changes.
- 🚨 Destructive database migrations.
- 🚨 Docker deployment or infrastructure control changes.
- 🚨 Changes to CI/CD workflows that affect deployment.

## Audit Log

Auto-merge decisions are recorded here for transparency and accountability.

| Date | PR # | Action | Reason | Result |
| :--- | :--- | :--- | :--- | :--- |
