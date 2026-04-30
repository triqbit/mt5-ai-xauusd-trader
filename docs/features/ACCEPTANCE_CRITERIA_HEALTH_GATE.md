# Acceptance Criteria: Startup Health Gate

## Functional Acceptance Criteria
- **Behavior:** Perform a comprehensive system check before starting the trading loop to ensure all dependencies and connections are ready.
- **Edge Cases:**
    - Block startup if the MT5 terminal is unreachable or login fails.
    - Block startup if required model weights are missing or corrupted.
    - Block startup if database connectivity is unavailable (in live mode).
- **Inputs/Outputs:**
    - **Inputs:** Configuration settings, environment variables, external connection status.
    - **Outputs:** Health Report (JSON) and exit code 0 (Success) or 1 (Failure).

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for each health check component (Connectivity, DB, FS, Models).
    - Integration test simulating a failed dependency to verify the bot does not start.
- **Performance:**
    - Total health check time < 5 seconds.
- **Error Handling:**
    - Provide clear, actionable error messages for every failure (e.g., "ERROR: MT5_PASSWORD not set").
- **Observability:**
    - Log health check results to both console and a `health.log` file.

## Operational Acceptance
- **Documentation:**
    - Runbook for troubleshooting common startup failures in `docs/runbooks/STARTUP_ERRORS.md`.
- **Configuration:**
    - Ability to skip non-critical health checks (e.g., `--skip-health-db` in demo mode).
- **Rollback:**
    - Revert health gate logic if it becomes a bottleneck for legitimate deployments.
- **Monitoring:**
    - Alert if a production instance fails its health gate more than 3 times in an hour.

## Release Readiness
- **Deployment:** Integrated into the `main.py` entrypoint.
- **Backward Compatibility:** Must support all existing configuration parameters.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Release Manager.
