# Disaster Recovery Plan

This document outlines the disaster recovery (DR) procedures for the MT5 AI/ML Trading Bot, covering the database, logs, and critical operational data.

## 1. Objectives

- **Recovery Point Objective (RPO)**: < 1 hour. We aim to lose no more than 1 hour of trading data in the event of a failure.
- **Recovery Time Objective (RTO)**: < 4 hours. We aim to restore full system functionality within 4 hours of a disaster declaration.

## 2. Backup Strategy

### 2.1 SQLite Database
The primary trade database (`trades.db`) uses SQLite.

- **Full Backup**: Daily at 00:00 UTC.
- **Incremental/Frequent Backup**: Every 6 hours (06:00, 12:00, 18:00 UTC).
- **Method**: Use `sqlite3` online backup API via `scripts/backup_verify.sh` to ensure zero downtime.
- **Integrity**: Every backup is followed by a verification step (restoration dry-run and checksum generation).

### 2.2 Application Logs
- **Frequency**: Continuous logging to file.
- **Rotation**: Daily log rotation.
- **Backup**: Logs are bundled into a `.tar.gz` archive during each backup run.

### 2.3 Critical Configuration
- `.env` files and certificates should be backed up whenever changed.
- Note: Secrets should be stored in a secure vault; the backup contains the vault references or encrypted blobs.

## 3. Retention Policy

| Data Type | Daily Backups | Weekly Backups | Monthly Backups | Archival |
|-----------|---------------|----------------|-----------------|----------|
| SQLite DB | 30 Days       | 90 Days        | 1 Year          | 7 Years  |
| Trade Logs| 30 Days       | 90 Days        | 1 Year          | 7 Years  |
| Reports   | 30 Days       | 90 Days        | 1 Year          | 7 Years  |

- **Rotation**: The `backup_verify.sh` script automatically removes local backups older than 30 days.
- **Archival**: After 30 days, backups should be moved to long-term cold storage (e.g., AWS S3 Glacier) to meet the 7-year regulatory requirement.

## 4. Automated Verification

Backups are only considered valid if they pass the verification process. This is automated via `scripts/backup_verify.sh`.

1. **Restoration Dry-run**: The database backup is restored to a temporary location.
2. **Integrity Check**: `PRAGMA integrity_check;` is run on the restored SQLite database.
3. **Data Validation**: A simple query is executed to ensure records are accessible.
4. **Compression**: Database and logs are compressed (`.gz`, `.tar.gz`).
5. **Checksum**: A SHA256 sum is generated for every *compressed* backup artifact.

## 5. Restoration Procedures

### 5.1 Restoring the Database

1. **Stop the Trading Bot**:
   ```bash
   # Example if using systemd
   sudo systemctl stop mt5-trader
   ```

2. **Locate the Latest Valid Backup**:
   Check the backup directory (default: `backups/`) for the most recent `backup_*.db.gz` file.

3. **Verify Checksum**:
   ```bash
   # Use the generated .sha256 file
   sha256sum -c backup_YYYYMMDD_HHMMSS.db.gz.sha256
   ```

4. **Restore the File**:
   ```bash
   gunzip -c backups/backup_YYYYMMDD_HHMMSS.db.gz > trades.db
   ```

5. **Verify Integrity**:
   ```bash
   sqlite3 trades.db "PRAGMA integrity_check;"
   ```

6. **Restart the Bot**:
   ```bash
   sudo systemctl start mt5-trader
   ```

### 5.2 Restoring Logs
Logs can be extracted from the backup archives:
```bash
# Verify checksum first
sha256sum -c backup_YYYYMMDD_HHMMSS_logs.tar.gz.sha256

# Extract to the logs directory
mkdir -p logs/
tar -xzf backups/backup_YYYYMMDD_HHMMSS_logs.tar.gz -C logs/
```

## 6. Disaster Scenarios

| Scenario | Recovery Action |
|----------|-----------------|
| Database Corruption | Restore from latest 6-hour incremental backup. |
| Host Failure | Provision new host, clone repo, restore `.env` and latest DB backup. |
| Data Center Outage | Deploy to secondary region using latest off-site backups. |

---
**Last Updated**: January 2026
**Owner**: Jules03 (Release Reliability & Governance)
