# Runbook 04: Database Corruption Recovery

## Overview
The bot uses SQLite for trade logging and performance tracking. While robust, SQLite can suffer from corruption due to filesystem errors or improper shutdowns.

## Diagnosis

### Symptoms
- Logs: `sqlalchemy.exc.DatabaseError: (sqlite3.DatabaseError) database disk image is malformed`
- Application crashes on startup during `TradeLogger` initialization.
- Query failures on specific tables.

### Integrity Check
Run the SQLite integrity check:
```bash
sqlite3 trades.db "PRAGMA integrity_check;"
```
If anything other than `ok` is returned, the database is corrupted.

## Recovery Steps

### 1. Attempt Repair (SQLite Recovery)
Try to recover as much data as possible using the `.recover` command:
```bash
sqlite3 trades.db ".recover" | sqlite3 trades_fixed.db
mv trades.db trades.db.corrupt
mv trades_fixed.db trades.db
```

### 2. Restore from Backup
If repair fails, restore the most recent backup from the `backups/` directory (if configured) or the cloud storage.
```bash
# Example from local backups
cp backups/trades_db_20260120_0000.bak trades.db
```

### 3. Reinitialize and Re-sync (Last Resort)
If no backups are available:
1.  Delete the corrupted database: `rm trades.db`
2.  Start the bot; it will recreate the schema automatically.
3.  **Manual Re-sync:** Manually populate the `trades` table with open positions from the MT5 terminal to ensure the `RiskManager` has correct state.

## Verification
1.  **Check Integrity:**
    ```bash
    sqlite3 trades.db "PRAGMA integrity_check;"
    ```
2.  **Verify Schema:**
    ```bash
    alembic current
    ```
    If Alembic is used for migrations, ensure it reports the expected version.
3.  **App Launch:** Start the bot and check for `TradeLogger` initialization logs.

## Escalation Path
1.  **Level 1:** DevOps/Infrastructure for disk/filesystem health checks.
2.  **Level 2:** Database Lead (@andonly1348) for manual data recovery.

## Preventive Measures
- Ensure `DATABASE_STANDARDS.md` regarding backups is followed.
- Use WAL (Write-Ahead Logging) mode for SQLite to reduce corruption risk:
  `sqlite3 trades.db "PRAGMA journal_mode=WAL;"`
