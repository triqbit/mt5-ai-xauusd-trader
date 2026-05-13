# Disaster Recovery Plan (DRP)

**Version:** 1.1.0
**Last Updated:** 2024-06-15
**Status:** PROD-READY

## 1. Overview
This document outlines the disaster recovery procedures for the MT5 AI/ML Trading Bot, focusing on the preservation and restoration of the trading database (`trades.db`), operational logs, and critical performance data. This plan is designed to ensure business continuity and regulatory compliance in the event of system failure, data corruption, or site-level disasters.

## 2. Recovery Objectives

The following targets are established for system recovery to ensure business continuity:

| Metric | Target | Description |
| :--- | :--- | :--- |
| **Recovery Point Objective (RPO)** | **1 Hour** | Maximum acceptable data loss duration. |
| **Recovery Time Objective (RTO)** | **15 Minutes** | Maximum time to restore services after disaster declaration. |

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

### 4.1 Trade Logs and Audit Trails
To ensure regulatory compliance and long-term traceability, long-term archival is managed by `scripts/data_cleanup.py`:
- **Annual Export**: Every year, all records from `trades` and `audit_log` tables older than 1 year are exported to compressed CSV format.
- **Immutable Storage**: These exports are moved to WORM (Write Once, Read Many) storage for a minimum of 7 years.
- **Checksum Manifest**: Each export is accompanied by a SHA256 checksum manifest to ensure immutability.

### 4.2 Performance Reports
- **Monthly Roll-up**: Performance snapshots in `reports/` are rolled up into monthly archives (`.tar.gz`).
- **Retention**: Local retention is 30 days; off-site archival is maintained for 2 years to support multi-year trend analysis.

### 4.3 Off-site Synchronization
- **Daily Sync**: The `backups/` directory is synchronized to secure off-site storage (e.g., AWS S3 with Glacier Instant Retrieval) every 24 hours.
- **Verification**: Integrity of off-site archives is verified quarterly by performing a test restoration of a random archive.

## 5. Backup Strategy

### 5.1. Automated Backup Process
The primary tool for backups is `scripts/backup_verify.sh`. It should be scheduled to run every hour via cron:
```cron
0 * * * * /path/to/scripts/backup_verify.sh >> /var/log/mt5_backup.log 2>&1
```

### 5.2. Backup Integrity Checks
The automated script performs the following checks for every backup:
1. **SQLite Integrity Check**: Runs `PRAGMA integrity_check;` on the backup file.
2. **Schema Validation**: Attempts to query critical tables to ensure the backup is functional.
3. **Checksum Generation**: Creates a `.sha256` manifest for each artifact.
4. **Archive Verification**: Tests the integrity of compressed log and report archives using `tar -tf`.

### 5.3 Restore Test (Automated Dry-run)
The `scripts/backup_verify.sh` script performs a mandatory "Restore Test" for every database backup:
1. **Structural Verification**: `PRAGMA integrity_check` ensures the SQLite file is not corrupt.
2. **Schema Validation**: Explicitly verifies the presence of all required tables (see below).
3. **Data Access Test**: Performs a count query on primary tables to ensure the data is readable.

### 5.4 Database Schema Reference
For manual verification, ensure the following tables are present in the restored databases:

**Trading Database (`trades.db`):**
- `trades`: Primary trade execution records.
- `model_signals`: AI/ML model predictions and confidence scores.
- `risk_events`: Rejections and circuit breaker activations.
- `performance_metrics`: Periodic performance snapshots (Sharpe, DD, etc.).
- `blocked_signal_analysis`: Opportunity cost analytics for rejected signals.
- `execution_qualities`: High-precision execution analytics and slippage.

**Audit Database (`audit.db`):**
- `audit_log`: System actions, configuration changes, and operator events.

## 6. Restoration Procedures

### 6.1. Database Restoration (Scenario: Data Corruption)
1. **Stop the Bot**:
   ```bash
   # Ensure all trading processes are terminated
   pkill -f "python main.py" || true
   ```
2. **Identify Latest Healthy Backup**:
   ```bash
   # List available backups for both trades and audit databases
   ls -ltr backups/db/
   ```
3. **Verify Checksum**:
   ```bash
   # Verify the integrity of the backup file before restoration
   cd backups/db/
   sha256sum -c trades_YYYYMMDD_HHMMSS.db.sha256
   sha256sum -c audit_YYYYMMDD_HHMMSS.db.sha256
   ```
4. **Restore Database Files**:
   ```bash
   # Restore the database files to the application root
   cp trades_YYYYMMDD_HHMMSS.db ../../trades.db
   cp audit_YYYYMMDD_HHMMSS.db ../../audit.db
   cd ../..
   ```
5. **Verify Restoration**:
   ```bash
   # Run integrity checks on the restored databases
   sqlite3 trades.db "PRAGMA integrity_check;"
   sqlite3 audit.db "PRAGMA integrity_check;"

   # Verify data presence and schema
   sqlite3 trades.db ".tables"
   sqlite3 trades.db "SELECT count(*) FROM trades;"
   sqlite3 trades.db "SELECT count(*) FROM model_signals;"
   sqlite3 audit.db "SELECT count(*) FROM audit_log;"
   ```

### 6.2. Log and Report Restoration
1. **Locate and Verify Archive**:
   ```bash
   # Verify the tarball integrity
   tar -tzf backups/logs/logs_YYYYMMDD_HHMMSS.tar.gz > /dev/null
   tar -tzf backups/reports/reports_YYYYMMDD_HHMMSS.tar.gz > /dev/null
   ```
2. **Extract Archive**:
   ```bash
   # Extract to the respective directories
   mkdir -p logs reports
   tar -xzf backups/logs/logs_YYYYMMDD_HHMMSS.tar.gz -C ./logs/
   tar -xzf backups/reports/reports_YYYYMMDD_HHMMSS.tar.gz -C ./reports/
   ```
3. **Verify Restoration**:
   ```bash
   # Confirm files are present
   ls -R logs/
   ls -R reports/
   ```

### 6.3 Model Weight Restoration
1. **Source**: Model weights are managed via Git LFS or a model registry.
2. **Restore**:
   ```bash
   # Ensure models/trained directory exists
   mkdir -p models/trained
   # Pull latest weights if using Git LFS
   git lfs pull
   # Or copy from a known backup location
   cp /path/to/backup/ensemble_latest.pt models/trained/
   ```
3. **Verify**:
   ```bash
   # Confirm model file exists and has correct size
   ls -lh models/trained/ensemble_latest.pt
   ```

### 6.4. Complete System Loss
1. Provision a new environment.
2. Clone the repository and install dependencies.
3. Restore `.env` from secure storage.
4. Restore latest `trades.db` and `audit.db` from off-site backup.
5. Verify health: `python3 scripts/doctor.py`.
6. Restart services: `docker-compose up -d`.

## 7. Crisis Management & Escalation
In the event of a major disaster (e.g., total data loss, persistent corruption):
1. **Incident Declaration**: Immediately log the incident in the audit trail (if available) or external incident tracker.
2. **Execution Halt**: Use the emergency stop if any trading processes are still active.
3. **Escalation Path**:
   - **Primary**: Jules03 (Release Reliability & Governance) - `@andonly1348`
   - **Secondary**: Jules02 (Security & CI Lead) - `@xnessom`
4. **Post-Mortem**: A mandatory post-mortem must be conducted within 48 hours of recovery, documented in `docs/audits/INCIDENT_YYYYMMDD.md`.

## 8. Disaster Recovery Drills
To ensure the effectiveness of this plan, the following drills are mandated:
- **Quarterly Full Restore**: Once every quarter, the latest backup must be restored to a non-production environment and verified for full functionality.
- **Drill Documentation**: Results of the drill, including any issues found and corrective actions taken, must be logged in `docs/audits/DR_DRILL_YYYY_QX.md`.
