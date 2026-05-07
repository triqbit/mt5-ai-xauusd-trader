# Acceptance Criteria: Unified Database Reliability

## Functional Acceptance Criteria
- **Behavior:**
    - Implement unified schema management using Alembic for both PostgreSQL and SQLite.
    - Enforce connection pooling (SQLAlchemy `QueuePool`) to prevent "Too many connections" errors.
    - Automate database migrations during the startup sequence.
    - Enforce foreign key constraints and indices for all primary trading tables.
- **Edge Cases:**
    - Handle migration failures with an automatic rollback.
    - Correctly manage "WAL mode" for SQLite to support concurrent reads/writes.
- **Inputs/Outputs:**
    - **Inputs:** `DATABASE_URL` environment variable.
    - **Outputs:** Initialized and migrated database schema, active connection pool.

## Technical Acceptance
- **Test Coverage:**
    - Integration tests for migration `up` and `down` paths.
    - Stress tests for concurrent database writes (simulating high-frequency signals).
- **Performance:**
    - Connection acquisition latency < 10ms.
    - Database write latency < 50ms for P95.
- **Error Handling:**
    - Catch and log database connection retries.
    - Fail startup if the database schema is out of sync with the application code.
- **Observability:**
    - Export "Connection Pool Status" metrics to Prometheus.

## Operational Acceptance
- **Documentation:**
    - Updated `DATABASE_STANDARDS.md` with the connection pooling and migration policy.
- **Configuration:**
    - `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` settings.
- **Rollback:**
    - Runbook for manual database restoration from backups.
- **Monitoring:**
    - Alert on "Database Migration Failure" or "Connection Pool Exhaustion".

## Release Readiness
- **Deployment:** Part of the Core Infrastructure hardening.
- **Backward Compatibility:** Must support legacy SQLite `trades.db` files until migration is complete.
- **Migration:** All existing data must be migrated to the new schema format.
- **Sign-off:** Requires approval from the Security & Quality Lead (Jules02).
