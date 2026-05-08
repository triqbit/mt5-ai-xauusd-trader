# Runbook 04: Database Corruption Recovery
**Version:** 1.2 | **Last Updated:** 2026-05-08

## Overview
Procedures for recovering from SQLite corruption in `trades.db` or `audit.db`. This runbook leverages the built-in backup and verification framework defined in `docs/DISASTER_RECOVERY.md`.

## Step-by-Step Instructions

### 1. In-Place Repair (Minor Corruption)
If the database file is still accessible but returns `DatabaseError` or `MALFORMED`, attempt an in-place repair using the SQLite recovery tool:
```bash
# Example for trades.db
sqlite3 trades.db ".recover" | sqlite3 trades_recovered.db

# Check integrity of the recovered file
sqlite3 trades_recovered.db "PRAGMA integrity_check;"
```
- If `integrity_check` returns `ok`, swap the files:
  ```bash
  mv trades.db trades.db.corrupt
  mv trades_recovered.db trades.db
  ```

### 2. Backup Restoration (Major Corruption)
If in-place repair fails or the file is physically corrupted/missing:
1. **Stop the Bot:** `docker stop xauusd_trader`
2. **Locate Latest Healthy Backup:**
   ```bash
   ls -ltr backups/db/
   ```
3. **Verify Backup Integrity & Checksum:**
   Identify the latest `.db` and its corresponding `.sha256` file.
   ```bash
   cd backups/db/
   sha256sum -c trades_YYYYMMDD_HHMMSS.db.sha256
   ```
4. **Restore Database File:**
   ```bash
   cp trades_YYYYMMDD_HHMMSS.db ../../trades.db
   ```
5. **Verify Restored File:**
   ```bash
   sqlite3 ../../trades.db "PRAGMA integrity_check;"
   ```

### 3. Verification & Cleanup
- Run the system doctor to ensure the bot can connect to the restored database:
  ```bash
  python scripts/doctor.py
  ```
- Check the audit log to identify the last recorded transaction and ensure minimal data loss (RPO < 1h):
  ```bash
  sqlite3 audit.db "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 5;"
  ```
- Once verified, restart the bot: `docker start xauusd_trader`.

## Expected Outcomes
- Databases pass `PRAGMA integrity_check` with an `ok` result.
- The bot starts without `SQLAlchemy` or `DatabaseError` exceptions.
- Recent trade and audit data is preserved (Recovery Point Objective < 1 hour).

## Verification Commands
- `sqlite3 trades.db "PRAGMA integrity_check;"`
- `sqlite3 audit.db "PRAGMA integrity_check;"`
- `python scripts/doctor.py`
- `curl -s http://localhost:8000/health/readiness`

## Escalation Path
1. **DB Connection Failures:** DevOps Lead (@maintainer-quality).
2. **Significant Data Loss:** Release Reliability Engineer (Jules03).
3. **Data Integrity Audit:** Compliance Officer.
