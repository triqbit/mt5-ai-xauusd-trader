# Runbook 04: Database Corruption Recovery
**Version:** 1.1.0-rc8 | **Last Updated:** 2024-06-12

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
- **Audit Manual Action:**
  ```bash
  sqlite3 audit.db "INSERT INTO audit_log (actor, action, details, created_at) VALUES ('operator', 'operator_db_repair_attempt', 'Attempted in-place repair of trades.db', datetime('now'));"
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
- **Audit Manual Action:** Record the restoration:
  ```bash
  sqlite3 ../../audit.db "INSERT INTO audit_log (actor, action, details, created_at) VALUES ('operator', 'operator_db_restoration', 'Restored trades.db from backup trades_YYYYMMDD_HHMMSS.db', datetime('now'));"
  ```

### 3. Proactive Verification
Run the backup verification script to ensure all existing backups are healthy:
```bash
bash scripts/backup_verify.sh
```
- Review `logs/backup.log` for any failures.

### 4. Verification & Cleanup
- Run the system doctor to ensure the bot can connect to the restored database:
  ```bash
  python scripts/doctor.py
  ```
- Check the audit log to identify the last recorded transaction and ensure minimal data loss (RPO < 1h):
  ```bash
  sqlite3 audit.db "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 5;"
  ```
- Once verified, restart the bot: `docker start xauusd_trader`.
- **Audit Manual Action:**
  ```bash
  sqlite3 audit.db "INSERT INTO audit_log (actor, action, details, created_at) VALUES ('operator', 'operator_db_incident_resolved', 'Database corruption resolved and service resumed', datetime('now'));"
  ```

## Expected Outcomes
- Databases pass `PRAGMA integrity_check` with an `ok` result.
- The bot starts without `SQLAlchemy` or `DatabaseError` exceptions.
- Recent trade and audit data is preserved (Recovery Point Objective < 1 hour).

## Escalation Path
1. **DB Connection Failures:** DevOps Lead (@maintainer-quality).
2. **Significant Data Loss:** Release Reliability Engineer (Jules03).
3. **Data Integrity Audit:** Compliance Officer.

## Verification Commands
```bash
sqlite3 trades.db "PRAGMA integrity_check;"
sqlite3 audit.db "PRAGMA integrity_check;"
bash scripts/backup_verify.sh
python scripts/doctor.py
```
