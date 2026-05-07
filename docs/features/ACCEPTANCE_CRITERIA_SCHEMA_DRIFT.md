# Acceptance Criteria: CI Schema Drift Detection

## Functional Acceptance Criteria
- **Behavior:**
    - Automatically detect inconsistencies between the application's SQLAlchemy models and the actual database schema.
    - Compare Alembic's `current` head with the migration history.
    - Verify that all foreign keys, indices, and constraints defined in code are present in the database.
- **Edge Cases:**
    - Correctly handle differences between SQLite (local dev) and PostgreSQL (production) schema representations.
    - Ignore "unmanaged" tables or extensions (e.g., PostGIS) if configured.
- **Inputs/Outputs:**
    - **Inputs:** SQLAlchemy models, Alembic migration history, active DB connection.
    - **Outputs:** Pass/Fail status in CI, detailed "Drift Report" if inconsistencies are found.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the drift detection script (`scripts/check_schema_drift.py`).
    - Integration test verifying that a missing index triggers a CI failure.
- **Performance:**
    - Drift check must complete in < 10 seconds.
- **Error Handling:**
    - Fail gracefully if the database is unreachable, with a clear error message.
- **Observability:**
    - Log "Schema Drift Check PASSED/FAILED" to the CI logs.

## Operational Acceptance
- **Documentation:**
    - Runbook for resolving schema drift (`docs/runbooks/08-db-schema-remediation.md`).
- **Configuration:**
    - Ability to exclude specific tables from the drift check.
- **Rollback:**
    - N/A (Infrastructure check).
- **Monitoring:**
    - Alert on "Schema Drift Detected in Production" via the health system.

## Release Readiness
- **Deployment:** Part of the CI/CD Quality Gate.
- **Backward Compatibility:** N/A.
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Security & Quality Lead (Jules02).
