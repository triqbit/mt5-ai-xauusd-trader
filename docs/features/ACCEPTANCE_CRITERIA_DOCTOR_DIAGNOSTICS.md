# Acceptance Criteria: Doctor Diagnostics Suite

## Functional Acceptance Criteria
- **Behavior:**
    - Perform a comprehensive system health check using `python main.py --doctor`.
    - Verify Python version (>= 3.12.13) and availability of critical system dependencies (MT5, TA-Lib, OpenSSL).
    - Validate presence and format of required `.env` variables without exposing secrets.
    - Check file system permissions for `logs/`, `data/`, and `models/`.
    - Verify connectivity to the MetaTrader 5 terminal and the SQLite/PostgreSQL database.
- **Edge Cases:**
    - Handle missing optional dependencies (e.g., `talib`) by providing installation instructions.
    - Detect "Zombie" MT5 processes or port conflicts that might block execution.
    - Handle read-only file systems or restricted permission environments.
- **Inputs/Outputs:**
    - **Inputs:** CLI flag `--doctor`.
    - **Outputs:** A scannable terminal report with `[PASS]`, `[WARN]`, or `[FAIL]` badges and clear remediation steps.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for each diagnostic check (Dependency check, Env check, Connection check).
    - Integration test ensuring the `--doctor` command returns a non-zero exit code if critical checks fail.
- **Performance:**
    - Total diagnostic execution time < 5 seconds.
- **Error Handling:**
    - Every `[FAIL]` must be accompanied by a specific error message and a suggested fix.
- **Observability:**
    - Diagnostic results should be logged to `logs/diagnostics.log` for remote troubleshooting.

## Operational Acceptance
- **Documentation:**
    - Updated "Troubleshooting" section in README.md linking to the doctor command.
    - Detailed runbook for interpreting and fixing common diagnostic failures.
- **Configuration:**
    - None (Diagnostic tool is autonomous).
- **Rollback:**
    - N/A (Non-trading component).
- **Monitoring:**
    - N/A.

## Release Readiness
- **Deployment:** Mandatory inclusion in all production and development releases.
- **Backward Compatibility:** No impact on existing trading logic.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Core Development Lead (Jules01) and Product Steward (Jules05).
