# Acceptance Criteria: Trade Logging & Database Integration

## Functional Acceptance Criteria
- **Behavior:**
  - Must record every trade (execution, SL/TP hit, manual close) in PostgreSQL.
  - Must log risk events (signal rejections) with detailed reasons.
  - Must support ACID compliance for all financial data records.
  - Must provide an audit trail for AI decision-making (store features/confidence with trade).
- **Edge Cases:**
  - Handle database connection timeouts or outages (implement local buffer).
  - Handle duplicate ticket IDs from MT5.
- **Inputs/Outputs:**
  - Input: Execution results and risk event data.
  - Output: Persisted records in `trades` and `risk_events` tables.

## Technical Acceptance
- **Test Coverage:**
  - Unit tests for SQLAlchemy models and repository layer.
  - Integration tests with a test database using Alembic migrations.
- **Performance:**
  - Database write latency < 10ms.
- **Error Handling:**
  - Automatic reconnection logic for SQLAlchemy.
- **Logging/Observability:**
  - Log DB connection status on startup.

## Operational Acceptance
- **Documentation:**
  - `DATABASE_STANDARDS.md` covering schema and indexing.
  - Backup and recovery procedures for the trading database.
- **Configuration:**
  - DB URL managed via `TradingConfig`.
- **Rollback:**
  - Standard Alembic migration rollback procedures.
- **Monitoring:**
  - Alert on database disk space and slow queries.

## Release Readiness
- **Deployment:**
  - Dependent on PostgreSQL 15+.
- **Backward Compatibility:**
  - Migrations must handle schema evolution without data loss.
- **Migration:**
  - Requires initial Alembic migration to create tables.
- **Stakeholder Sign-off:**
  - Requires sign-off from Data Architect.
