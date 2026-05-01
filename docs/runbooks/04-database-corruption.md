# Runbook 04: Database Corruption Recovery

## Overview
The bot uses SQLite (`trades.db`) for operational logging. This runbook covers recovery from database corruption or loss.

## Symptoms
- Logs: `sqlite3.DatabaseError: database disk image is malformed`
- Bot fails to start with database-related errors.
- Migration failures via Alembic.

## Recovery Procedures

### 1. Attempt SQLite Repair
Try to recover data from the corrupted file:
```bash
sqlite3 trades.db ".recover" | sqlite3 trades_recovered.db
mv trades.db trades.db.bak
mv trades_recovered.db trades.db
```

### 2. Restore from Backup
If repair fails, restore the most recent backup:
1. Locate backup in `backups/` directory (if configured).
2. Copy the backup to the root directory as `trades.db`.
   ```bash
   cp backups/trades_20240501.db ./trades.db
   ```

### 3. Re-initialize Database (Data Loss Acceptable)
If no backup exists and repair fails:
1. Delete the corrupted file:
   ```bash
   rm trades.db
   ```
2. Run migrations to recreate the schema:
   ```bash
   alembic upgrade head
   ```

## Verification
1. Run a database integrity check:
   ```bash
   sqlite3 trades.db "PRAGMA integrity_check;"
   ```
2. Check logs for successful trade logging.
3. Verify migration status:
   ```bash
   alembic current
   ```

## Prevention
- Ensure the disk is not full (`df -h`).
- Avoid hard-killing the bot process (use `SIGTERM`).
- Implement automated daily backups of `trades.db`.

## Escalation Path
1. **Level 1:** Database Administrator / DevOps.
2. **Level 2:** Jules03 (Release Reliability).
