# Acceptance Criteria: Deterministic Migration Drift Detection

## Functional Acceptance Criteria
- **Behavior:**
    - Automatically detect any discrepancy between the current application state (SQLAlchemy models) and the database schema state (Alembic history).
    - Detect missing or inconsistent indices, foreign keys, and column constraints.
    - Specifically check for drift in high-risk tables: `positions`, `trades`, `risk_limits`, and `audit_log`.
- **Edge Cases:**
    - Handle differences in schema representation between SQLite (local dev) and PostgreSQL (production).
    - Ignore "unmanaged" tables or extensions specifically excluded in the configuration.
- **Inputs/Outputs:**
    - **Inputs:** Application models, Alembic migration scripts, target database connection.
    - **Outputs:** Detailed "Drift Report" in CI logs; exit code 1 if drift is detected.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the detection script logic.
    - Integration test in CI that intentionally introduces drift (e.g., adds a model column without a migration) and verifies failure.
- **Performance:**
    - Drift detection must complete in < 10 seconds per check.
- **Error Handling:**
    - Fail gracefully with a clear error message if the database is unreachable or migrations are corrupted.
- **Observability:**
    - Log the "Last Successful Drift Check" timestamp.
    - Export drift status (binary) to the health monitoring system.

## Operational Acceptance
- **Documentation:**
    - Runbook for resolving drift: `docs/runbooks/08-db-schema-remediation.md`.
    - Instructions for excluding tables or columns from the check.
- **Configuration:**
    - `DRIFT_CHECK_EXCLUSIONS`: List of tables/regexes to ignore.
- **Rollback:**
    - N/A (Verification utility).
- **Monitoring:**
    - Dashboard indicator for "Schema Integrity Status".

## Release Readiness
- **Deployment:** Mandatory CI gate for all Pull Requests affecting the `src/models/` or `migrations/` directories.
- **Backward Compatibility:** Must support all existing migration versions.
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Security & Quality Lead (Jules02).
