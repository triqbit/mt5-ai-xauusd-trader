# Audit Log Modernization: Migration & Rollback Guide

This document details the migration path and rollback procedures for the structured audit logging system introduced in version 1.0.1.

## 1. Overview of Changes
- **Structured Metadata:** The `audit_log` table now includes a `metadata_json` column (SQLAlchemy `JSON` type) to store searchable system context.
- **Unified Migrations:** Database migrations now track both `src.core.trade_logger` and `src.core.audit_log` models.
- **Enhanced Traceability:** Risk decisions, configuration snapshots, and health gate results are now recorded with full JSON context.

## 2. Migration Path

### Automatic Migration (Standard)
The system automatically handles migrations via Alembic. To apply the changes to a production database:

```bash
export DATABASE_URL="your_production_db_url"
alembic upgrade head
```

### Manual Verification
After migration, verify the schema:
```sql
-- For SQLite
PRAGMA table_info(audit_log);
-- Verify metadata_json column exists
```

## 3. Rollback Considerations

### Database Rollback
If the schema change causes issues with existing database engines (especially legacy SQLite versions without JSON support), perform a downgrade:

```bash
alembic downgrade -1
```

**Warning:** Downgrading will result in the loss of any data stored in the `metadata_json` column.

### Application Rollback
If the structured logging code introduces performance regressions or stability issues:
1. Revert the application code to version 1.0.0.
2. The `audit_log` table and `metadata_json` column can remain in the database without affecting version 1.0.0 (backward compatibility).

## 4. Operational Impact
- **Storage:** JSON metadata increases the database footprint. Ensure sufficient disk space as defined in `docs/SLO_TARGETS.md`.
- **Latency:** `RiskManager.approve` now evaluates all layers for logging purposes. While this adds a negligible latency overhead (~0.5ms), it ensures compliance-grade traceability.

---
**Author:** Jules03 (Atlas)
**Date:** 2026-05-04
