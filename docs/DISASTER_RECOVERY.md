# Disaster Recovery Plan (DRP)

## 1. Overview
This document defines the practical disaster recovery procedures for the MT5 AI/ML Trading Bot, covering the database, logs, and critical operational data.

## 2. Recovery Objectives
- **Recovery Point Objective (RPO):** 1 Hour
  - Maximum acceptable data loss is 1 hour of trading activity.
- **Recovery Time Objective (RTO):** 15 Minutes
  - The system should be back online within 15 minutes of a disaster declaration.

## 3. Data Classification & Backup Strategy

### 3.1 SQLite Database (`trades.db`)
- **Backup Method:** Online snapshot using `.backup` command via `sqlite3`.
- **Frequency:**
  - **Full Backup:** Every 24 hours.
  - **Snapshots:** Every 1 hour.
- **Retention Policy:**
  - Hourly snapshots: 48 hours.
  - Daily backups: 30 days.
  - Weekly backups: 90 days.
  - Monthly backups: 1 year (Regulatory requirement).

### 3.2 Application Logs (`logs/`)
- **Archival Policy:**
  - Active logs rotated daily.
  - Compressed and moved to long-term storage after 7 days.
  - Retained for 90 days.

### 3.3 Performance Reports
- **Archival Policy:**
  - Exported to CSV/JSON monthly.
  - Indefinite retention in secure cloud storage for model training and auditing.

## 4. Automated Backup Verification
Every backup must undergo an automated verification process using `scripts/backup_verify.sh`:
1. **Integrity Check:** Run `PRAGMA integrity_check` on the database.
2. **Checksum Validation:** Generate and store SHA256 checksums for each backup file.
3. **Restoration Dry-run:** Periodically restore the backup to a temporary location and verify:
   - Table counts match expectations.
   - Latest 5 signals/trades are present.

## 5. Step-by-Step Restoration Procedure

### 5.1 Database Restoration
1. **Identify the latest valid backup** from the backup repository.
2. **Verify the checksum** of the backup file:
   ```bash
   sha256sum -c trades.db.YYYYMMDD_HHMM.bak.sha256
   ```
3. **Stop the trading bot** if it is still running:
   ```bash
   pkill -f main.py
   ```
4. **Restore the database file**:
   ```bash
   cp trades.db.YYYYMMDD_HHMM.bak trades.db
   ```
5. **Verify data integrity**:
   ```bash
   sqlite3 trades.db "PRAGMA integrity_check;"
   ```
6. **Confirm latest data**:
   ```bash
   sqlite3 trades.db "SELECT count(*) FROM trades;"
   ```

### 5.2 Log Recovery
1. Retrieve logs from archival storage if required for incident analysis.
2. Uncompress logs to the `logs/` directory.

## 6. Disaster Scenarios and Responses

| Scenario | Response Action |
| :--- | :--- |
| **Database Corruption** | Stop bot, restore from latest hourly snapshot, verify integrity. |
| **Disk Failure** | Provision new storage, restore latest daily backup, replay transaction logs (if any). |
| **Cloud Provider Outage** | Failover to secondary region/provider, restore latest off-site backup. |
| **Malicious Attack** | Isolate system, identify last known good backup, audit for unauthorized changes, restore. |

## 7. Plan Maintenance
- **Review Frequency:** Quarterly.
- **Drill Frequency:** Monthly restoration dry-runs (automated).
- **Owner:** Release Reliability & Governance (Jules03).
