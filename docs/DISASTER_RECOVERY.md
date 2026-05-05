# Disaster Recovery Plan (DRP)

## 1. Overview
This document outlines the disaster recovery procedures for the MT5 AI/ML Trading Bot, focusing on the preservation and restoration of the trading database (`trades.db`), operational logs, and critical performance data. This plan is designed to ensure business continuity and regulatory compliance in the event of system failure, data corruption, or site-level disasters.

## 2. Recovery Objectives
- **Recovery Point Objective (RPO):** 1 hour (Maximum data loss allowed).
- **Recovery Time Objective (RTO):** 15 minutes (Maximum time to restore service after a disaster).

## 3. Data Classification and Retention
The following table summarizes the backup and retention strategy for all critical system components, aligned with the [Data Retention Policy](DATA_RETENTION_POLICY.md).

| Data Type | Importance | Primary Location | Backup Frequency | Retention (Local) | Archival (Off-site) |
|-----------|------------|------------------|------------------|-------------------|---------------------|
| Trading Database (`trades.db`) | Critical | Root Directory | Every 1 hour | 30 Days | 7 Years (Compliance) |
| Audit Database (`audit.db`) | Critical | Root Directory | Every 1 hour | 30 Days | 7 Years (Compliance) |
| Operational Logs | High | `logs/` | Every 1 hour | 30 Days | 90 Days |
| Performance Reports | High | `reports/` | Every 1 hour | 30 Days | 2 Years |
| Model Weights | Medium | `src/models/` | On change/Release | N/A | Infinite (Git/Registry) |
| Configuration (`.env`) | Critical | Root Directory | Manual | N/A | Secure Vault |

*Note: All backups must be encrypted at rest in off-site storage.*

## 4. Archival Policy
To ensure long-term data durability and compliance:
- **Daily Off-site Sync**: Backups from the local `backups/` directory are synchronized to secure off-site storage (e.g., AWS S3 with Glacier Instant Retrieval) daily.
- **Compliance Archival**: Trade records and audit logs are exported to compressed Parquet/CSV format annually and stored in Immutable Storage for 7 years.
- **Archival Integrity**: Off-site archives must have their SHA256 checksums verified quarterly against the original backup records.

## 5. Backup Strategy

### 5.1. Automated Backup Process
The primary tool for backups is `scripts/backup_verify.sh`. It should be scheduled to run every hour via cron:
```cron
0 * * * * /path/to/scripts/backup_verify.sh >> /var/log/mt5_backup.log 2>&1
```

### 5.2. Backup Integrity Checks
The automated script performs the following checks for every backup:
1. **SQLite Integrity Check**: Runs `PRAGMA integrity_check;` on the backup file.
2. **Schema Validation**: Attempts to query critical tables (e.g., `trades`, `audit_log`) to ensure the backup is functional.
3. **Checksum Generation**: Creates a `.sha256` manifest for each artifact.
4. **Archive Verification**: Tests the integrity of compressed log and report archives using `tar -tf`.

## 6. Restoration Procedures

### 6.1. Database Restoration (Scenario: Data Corruption)
1. **Stop the Bot**:
   ```bash
   kill $(pgrep -f "python main.py") 2>/dev/null || true
   ```
2. **Identify Latest Healthy Backup**:
   ```bash
   ls -lh backups/db/
   ```
3. **Verify Checksum**:
   ```bash
   cd backups/db/
   sha256sum -c trades_YYYYMMDD_HHMMSS.db.sha256
   ```
4. **Restore Database File**:
   ```bash
   cp trades_YYYYMMDD_HHMMSS.db ../../trades.db
   cd ../..
   ```
5. **Verify Restoration**:
   ```bash
   sqlite3 trades.db "PRAGMA integrity_check;"
   sqlite3 trades.db "SELECT count(*) FROM trades;"
   ```

### 6.2. Log and Report Restoration
1. **Locate and Verify Archive**:
   ```bash
   tar -tzf backups/logs/logs_YYYYMMDD_HHMMSS.tar.gz > /dev/null
   ```
2. **Extract Archive**:
   ```bash
   tar -xzf backups/logs/logs_YYYYMMDD_HHMMSS.tar.gz -C ./logs/
   ```

### 6.3. Complete System Loss
1. Provision a new environment.
2. Clone the repository and install dependencies.
3. Restore `.env` from secure storage.
4. Restore latest `trades.db` and `audit.db` from off-site backup.
5. Verify health: `python3 scripts/doctor.py`.
6. Restart services: `docker-compose up -d`.

## 7. Disaster Recovery Drills
To ensure the effectiveness of this plan, the following drills are mandated:
- **Quarterly Full Restore**: Once every quarter, the latest backup must be restored to a non-production environment and verified for full functionality.
- **Drill Documentation**: Results of the drill, including any issues found and corrective actions taken, must be logged in `docs/audits/DR_DRILL_YYYY_QX.md`.

## 8. Escalation Path
1. **Primary**: Jules03 (Release Reliability & Governance) - `@andonly1348`
2. **Secondary**: Jules02 (Security & CI Lead) - `@xnessom`
