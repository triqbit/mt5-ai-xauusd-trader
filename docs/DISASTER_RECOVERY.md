# Disaster Recovery Plan (DRP)

This document outlines the disaster recovery procedures for the MT5 AI/ML Trading Bot, focusing on database, logs, and critical operational data.

## 1. Objectives

*   **Recovery Point Objective (RPO):** 1 hour (Maximum allowable data loss)
*   **Recovery Time Objective (RTO):** 30 minutes (Target time to restore service)

## 2. Backup Strategy

### 2.1 SQLite Database (`trades.db`)
The SQLite database contains all trade logs, model signals, risk events, and performance metrics.

*   **Schedule:** Hourly incremental backups (snapshots).
*   **Method:** `sqlite3 .backup` command to ensure consistency even if the database is in use.
*   **Retention Policy:**
    *   **Hourly:** Keep for 24 hours.
    *   **Daily:** Keep for 30 days.
    *   **Monthly:** Keep for 12 months.

### 2.2 Operational Logs & Performance Reports
Includes `logs/` directory and any exported CSV/JSON performance summaries.

*   **Schedule:** Daily.
*   **Method:** Compressed tarball (`tar.gz`).
*   **Archival Policy:** Move to long-term cold storage (e.g., AWS S3 Glacier, external drive) after 90 days. Keep archives for 3 years for compliance and audit purposes.

### 2.3 Critical Configuration
Includes `.env` and `pyproject.toml`.

*   **Schedule:** On change.
*   **Method:** Version control (Git) for config templates; secure secret manager for actual secrets.

## 3. Backup Verification

Automated verification is performed by `scripts/backup_verify.sh` after every backup.

*   **Integrity Check:** Run `PRAGMA integrity_check;` on the backup file.
*   **Checksums:** Generate SHA256 checksums for every backup artifact.
*   **Restoration Dry-run:** Periodically (automated daily) restore the backup to a temporary environment and verify the row count of the `trades` table.

## 4. Restoration Procedures

In the event of data loss or corruption, follow these steps:

### Step 1: Stop the Trading Bot
Ensure no active processes are writing to the database.
```bash
pkill -f "python main.py"
```

### Step 2: Locate the Latest Valid Backup
Identify the most recent backup file and its checksum.
```bash
ls -lt backups/db/
cat backups/db/trades_backup_latest.sqlite.sha256
```

### Step 3: Verify Backup Integrity
```bash
sha256sum -c backups/db/trades_backup_latest.sqlite.sha256
sqlite3 backups/db/trades_backup_latest.sqlite "PRAGMA integrity_check;"
```

### Step 4: Restore the Database
Replace the corrupted `trades.db` with the backup.
```bash
mv trades.db trades.db.corrupted_$(date +%Y%m%d)
cp backups/db/trades_backup_latest.sqlite trades.db
```

### Step 5: Verification
Check that the database is readable and contains expected data.
```bash
sqlite3 trades.db "SELECT COUNT(*) FROM trades;"
```

### Step 6: Restart the Bot
```bash
python main.py --mode demo --algo ensemble
```

## 5. Roles and Responsibilities

*   **System Administrator:** Responsible for maintaining the backup infrastructure and ensuring the automated script runs successfully.
*   **Compliance Officer:** Responsible for periodic audits of the backup retention and archival policy.
