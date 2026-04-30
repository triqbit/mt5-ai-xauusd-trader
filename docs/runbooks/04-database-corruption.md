# Runbook 04: Database Corruption Recovery

## Description
This runbook provides instructions for recovering from SQLite database corruption in `trades.db`.

## Recovery Procedures

### 1. Verification of Corruption
**Symptom:** Logs show `sqlite3.DatabaseError: database disk image is malformed` or SQLAlchemy `OperationalError`.
**Step-by-step Instructions:**
1. Run integrity check:
   ```bash
   sqlite3 trades.db "PRAGMA integrity_check;"
   ```
2. If it returns anything other than `ok`, the database is corrupt.

**Expected Outcome:** Integrity check identifies corruption.

### 2. Recovery using `.dump` (Best Effort)
**Step-by-step Instructions:**
1. Attempt to dump data to a SQL file, ignoring errors:
   ```bash
   sqlite3 trades.db ".dump" > dump.sql
   ```
2. Create a new database from the dump:
   ```bash
   mv trades.db trades.db.bak
   sqlite3 trades.db < dump.sql
   ```
3. Verify integrity of the new database:
   ```bash
   sqlite3 trades.db "PRAGMA integrity_check;"
   ```

**Expected Outcome:** `trades.db` is recreated with most data intact.

### 3. Recovery from Backup
**Step-by-step Instructions:**
1. Stop the trading bot process.
2. Locate the latest backup (e.g., in `backups/` directory if configured, or EBS snapshot).
3. Restore the backup file:
   ```bash
   cp backups/trades.db.latest trades.db
   ```
4. Restart the bot.

**Expected Outcome:** Bot resumes with data from the last backup.

## Prevention
1. Ensure the filesystem has enough space.
2. Use `WAL` mode for SQLite to improve concurrency and reliability.
3. Schedule regular backups (see `DEPLOYMENT_GUIDE.md`).

## Escalation Path
1. Recovery fails: Escalate to Platform Engineer (Jules03) or DBA.
2. Significant data loss (>1 hour): Notify Compliance/Audit.

## Verification Commands
```bash
# Check table counts after recovery
sqlite3 trades.db "SELECT count(*) FROM trades;"
sqlite3 trades.db "SELECT count(*) FROM model_signals;"
```
