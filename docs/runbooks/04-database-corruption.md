# Runbook 04: Database Corruption Recovery
**Version:** 1.1 | **Last Updated:** 2026-05-07

## Overview
Procedures for recovering from SQLite corruption in `trades.db` or `audit.db`.

## Step-by-Step Instructions

### 1. In-Place Repair
- Try `sqlite3 dbname.db ".recover" | sqlite3 dbname_new.db`.
- Check integrity: `sqlite3 dbname_new.db "PRAGMA integrity_check;"`.
- Swap new for old.

### 2. Backup Restoration
- Locate latest backup: `ls -ltr backups/db/`.
- Verify checksum: `sha256sum -c <backup>.sha256`.
- Restore: `cp backups/db/<backup>.db ./trades.db`.

## Expected Outcomes
- Databases pass `PRAGMA integrity_check`.
- Bot starts without `DatabaseError`.
- Recent trade and audit data is preserved (RPO < 1h).

## Verification Commands
- `sqlite3 trades.db "PRAGMA integrity_check;"`
- `sqlite3 audit.db "PRAGMA integrity_check;"`
- `python scripts/doctor.py`

## Escalation Path
1. **DB Failures:** DevOps Lead (@maintainer-quality).
2. **Data Loss:** Release Reliability Engineer (Jules03).
