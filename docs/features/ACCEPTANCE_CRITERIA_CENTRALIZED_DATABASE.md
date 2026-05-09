# Acceptance Criteria: Centralized Database Architecture

## Functional Acceptance Criteria
- **Behavior:**
    - Transition from fragmented local SQLite databases to a unified, centralized PostgreSQL instance.
    - Support multi-account and multi-instance data aggregation in a single schema.
    - Implement row-level security (RLS) or tenant-id filtering if multiple bot instances share the same database.
    - Provide a centralized migration management system (Alembic).
- **Edge Cases:**
    - Handle network latency to the remote database without impacting trading performance (asynchronous persistence).
    - Provide a local "Fallback Cache" in case the centralized database is unreachable.
- **Inputs/Outputs:**
    - **Inputs:** `DATABASE_URL` environment variable.
    - **Outputs:** Centralized data repository for all system telemetry and history.

## Technical Acceptance
- **Test Coverage:**
    - Integration tests against a live PostgreSQL instance (using Testcontainers or a dedicated test DB).
    - Tests for the "Fallback Cache" and subsequent reconciliation logic.
- **Performance:**
    - Database write latency (async) must not impact the trading loop pulse.
- **Error Handling:**
    - Automatic reconnection logic with exponential backoff.
- **Observability:**
    - Centralized dashboard (Grafana) pointing to the PostgreSQL instance.

## Operational Acceptance
- **Documentation:**
    - Database migration guide.
    - Backup and Restore runbook.
- **Configuration:**
    - `DATABASE_URL`: Connection string.
    - `DB_FALLBACK_PATH`: Local path for SQLite cache.
- **Rollback:**
    - Ability to revert back to local SQLite if the centralized infrastructure fails (requires data export).
- **Monitoring:**
    - Alert on "Persistence Lag" (time between event and DB confirmation).

## Release Readiness
- **Deployment:** Requires PostgreSQL infrastructure availability.
- **Backward Compatibility:** Must support the existing SQLAlchemy models.
- **Migration:** Automated migration script to move data from legacy SQLite files to PostgreSQL.
- **Sign-off:** Requires approval from the Release Reliability Lead (Jules03).
