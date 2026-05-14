# Acceptance Criteria: Automated Branch Promotion Logic

## Functional Acceptance Criteria
- **Behavior:**
    - Implement an automated workflow (`.github/workflows/production-gate.yml`) that governs the promotion of code from `staging` (or PR) to `main`.
    - Mandatory "Golden Metadata" baseline comparison: New backtest results must be compared against a historical baseline; any significant degradation in Sharpe or MaxDD must block promotion.
    - Automated execution of the full test suite, including unit, integration, and governance tests.
    - Integration of a mandatory smoke test in a staging environment before final promotion.
- **Edge Cases:**
    - Handle scenarios where the "Golden Metadata" baseline is missing (default to strict mode).
    - Gracefully handle CI runner timeouts or infrastructure failures during promotion.
    - Prevent concurrent promotion workflows for the same target branch.
- **Inputs/Outputs:**
    - **Inputs:** PR merge request to `main`, current backtest metrics, historical baseline metadata.
    - **Outputs:** Automated approval or rejection of the promotion, detailed promotion log, and updated baseline (if successful).

## Technical Acceptance
- **Test Coverage:**
    - 100% pass rate for all existing tests is a hard requirement for promotion.
    - Integration tests for the promotion script itself (e.g., `scripts/verify_backtest_audit.py`).
- **Performance:**
    - Promotion workflow (excluding standard CI tests) should complete in < 5 minutes.
- **Error Handling:**
    - Provide clear, actionable reasons for promotion rejection (e.g., "Sharpe ratio degradation of 15% detected").
- **Observability:**
    - Log every promotion attempt, including the diff of performance metrics, to the system audit log.

## Operational Acceptance
- **Documentation:**
    - Document the promotion logic and "Golden Metadata" update process in `docs/operations/BRANCH_PROMOTION.md`.
    - Provide instructions for manually overriding the promotion gate in emergencies.
- **Configuration:**
    - Configurable thresholds for metric degradation (e.g., `MAX_SHARPE_DEGRADATION=0.05`).
- **Rollback:**
    - Automated rollback of the promotion if the post-promotion smoke test fails.
- **Monitoring:**
    - Track promotion success/failure rates and reasons in a centralized dashboard.

## Release Readiness
- **Deployment:** Integral for CI/CD pipeline automation and stability.
- **Backward Compatibility:** Must support legacy backtest result formats for baseline comparison.
- **Migration:** Initial generation of the "Golden Metadata" baseline from the current stable release.
- **Sign-off:** Requires approval from the Release Reliability Lead (Jules03) and Product Steward (Jules05).
