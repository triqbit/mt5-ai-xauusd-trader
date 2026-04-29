# Runbook 04: Database Corruption Recovery

## Description
This runbook provides steps to identify and recover from SQLite database corruption in the trade logging system.

## Failure Scenarios

### 1. SQLite Database Corruption
**Symptoms:** Logs show "sqlite3.DatabaseError: database disk image is malformed" or "OperationalError: (sqlite3.OperationalError) corrupt database".
**Cause:** Improper shutdowns, hardware failure, or filesystem issues.

**Steps to Recover:**

#### Option A: Integrity Check & Fix (Light Corruption)
1.  Stop the trading bot.
2.  Run the SQLite integrity check:
    ```bash
    sqlite3 trades.db "PRAGMA integrity_check;"
    ```
3.  If errors are found, attempt to recover by dumping to SQL and re-importing:
    ```bash
    sqlite3 trades.db ".dump" > dump.sql
    mv trades.db trades.db.bak
    sqlite3 trades.db < dump.sql
    ```
4.  Re-run the integrity check.

#### Option B: Restore from Backup (Heavy Corruption)
1.  Stop the trading bot.
2.  Locate the latest valid backup (e.g., `trades.db.bak` or automated backups if configured).
3.  Rename the corrupt database:
    ```bash
    mv trades.db trades.db_corrupt_$(date +%F)
    ```
4.  Copy the backup to `trades.db`:
    ```bash
    cp backups/trades_latest.db trades.db
    ```
5.  Verify the integrity of the restored database.

#### Option C: Database Recreation (Last Resort)
*Note: This will lose historical trade data.*
1.  Move the old database aside.
2.  Restart the bot. The `TradeLogger` will automatically recreate the schema on initialization.

---

## Escalation Path
- **Data Loss:** If critical trade history is lost, escalate to the Compliance/Audit lead (Jules03) for manual reconciliation with MT5 history.
- **Persistent Hardware Issues:** Escalate to Infrastructure support.

## Verification Commands
1. Check database integrity:
   ```bash
   sqlite3 trades.db "PRAGMA integrity_check;"
   ```
2. Verify table count and basic data presence:
   ```bash
   sqlite3 trades.db "SELECT count(*) FROM trades;"
   ```
