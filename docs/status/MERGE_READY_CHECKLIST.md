# Merge-Readiness Checklist

> [!IMPORTANT]
> **Critical Repository State Notice:** The `main` branch is currently operating under a history-grafting model. All merges must be carefully audited to ensure they do not accidentally overwrite or regress core logic from other active modules.

Generated on: 2026-05-06 18:30:00 UTC

This checklist identifies top promising PRs for immediate review, helping Jules05 and human reviewers process candidates efficiently.

## 1. PR #746: resolve all CI failures, security vulnerabilities, and import errors
- **Scope**: Critical fix resolving CI failures and patching security vulnerabilities in FastAPI/Starlette.
- **Domains touched**: `CI/CD`, `Security`, `Infrastructure`.
- **CI Status**: Candidate for immediate merge to restore stability.
- **Key Changes**:
    - Bumped `starlette` (0.49.1) and `fastapi` (0.136.1).
    - Fixed Ruff violations (RUF022, RUF046).
    - Resolved imports in `src/analytics/` and `src/monitoring/`.
- **Missing Items**: None identified.
- **Recommendation**: High-priority candidate for review; critical for restoring CI pipeline health.

## 2. PR #712: 🗺️ Atlas: [release-readiness improvement] Startup Validation Layer
- **Scope**: Implements a robust startup validation layer to prevent misconfigured live trading.
- **Domains touched**: `Core`, `Production Readiness`, `Risk`.
- **CI Status**: Merge-ready per Jules05 priority queue.
- **Key Changes**:
    - Enhanced MT5 credential and SYMBOL/TIMEFRAME integrity checks.
    - Placeholder detection for Redis and SQLite warning in LIVE mode.
    - Added comprehensive unit tests in `tests/test_config_validator.py`.
- **Missing Items**: None identified.
- **Recommendation**: Ready for detailed review; essential for safe production deployments.

## 3. PR #740: Enhance RareEventSimulator for Institutional Black-Swan Research
- **Scope**: Enhances research capabilities by standardizing Black-Swan metrics and improving simulation realism.
- **Domains touched**: `Research`, `Analytics`.
- **CI Status**: Merge-ready per Jules05 priority queue.
- **Key Changes**:
    - Standardized `peak_impact_pct` calculation.
    - Added realistic spread widening and volume surges to FLASH_CRASH scenarios.
    - Improved `FeatureEngineer` compatibility tests.
- **Missing Items**: None identified.
- **Recommendation**: Ready for detailed review; improves institutional-grade stress testing.

---
*Prepared by Jules06 (qufuwan) for Jules05 and human review.*
