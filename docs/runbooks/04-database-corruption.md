# Runbook 04: Database Corruption Recovery

## Overview
This runbook provides procedures for recovering from SQLite database corruption in the `trades.db` file used for logging and risk management.

## 1. Failure Identification
Database corruption may manifest as:
- `sqlalchemy.exc.DatabaseError` with "database disk image is malformed".
- Bot failing to start with "unable to open database file".
- Queries returning inconsistent results or errors.

## 2. Recovery Procedures

### 2.1 Attempt SQLite Recovery
If the database file is still readable but malformed:
1. **Stop the Bot**: Ensure no processes are writing to the DB.
2. **Backup**: `cp trades.db trades.db.bak`
3. **Run Recovery**:
   ```bash
   sqlite3 trades.db ".recover" | sqlite3 trades_recovered.db
   ```
4. **Swap**: `mv trades_recovered.db trades.db`
5. **Restart Bot**: Verify it can read historical trades.

### 2.2 Rebuild from Broker History
If recovery fails and the DB is lost:
1. **Delete Corrupt DB**: `rm trades.db`
2. **Initialize New DB**: Start the bot; it will recreate the schema.
3. **Manual Reconciliation**: The bot will fetch current open positions from MT5. However, historical trade data in the DB will be missing.
4. **Optional**: Use a script to fetch trade history from MT5 and backfill the `trades` table.

## 3. Prevention
- Ensure the filesystem is not full.
- Avoid running the bot on network-mounted drives (NFS/SMB) which are prone to SQLite locking issues.
- Maintain periodic backups of `trades.db`.

## 4. Escalation Path
- **P2 (DB Corruption)**: Impacts reporting and intraday risk tracking. Should be resolved before the next trading session.

## 5. Verification Commands
```bash
# Check database integrity
sqlite3 trades.db "PRAGMA integrity_check;"

# List last 5 trades to verify data access
sqlite3 trades.db "SELECT id, ticket, symbol, status FROM trades ORDER BY id DESC LIMIT 5;"
```
