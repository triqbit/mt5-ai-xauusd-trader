# Disaster Recovery Plan (DRP)

## 1. Overview
This document outlines the disaster recovery procedures for the MT5 AI/ML Trading Bot, focusing on the preservation and restoration of the trading database (`trades.db`), operational logs, and critical performance data.

## 2. Recovery Objectives
- **Recovery Point Objective (RPO):** 1 hour (Maximum data loss allowed).
- **Recovery Time Objective (RTO):** 15 minutes (Maximum time to restore service after a disaster).

## 3. Data Classification and Retention
| Data Type | Importance | Primary Location | Backup Frequency | Retention (Local) | Archival (Off-site) |
|-----------|------------|------------------|------------------|-------------------|---------------------|
| Trading Database (`trades.db`) | Critical | Root Directory | Every 1 hour | 30 Days | 7 Years (Compliance) |
| Operational Logs | High | `logs/` | Every 1 hour | 30 Days | 90 Days |
| Performance Reports | High | `reports/` | Every 1 hour | 30 Days | 2 Years |
| Model Weights | Medium | `src/models/` | On change/Release | N/A | Infinite (Git/Registry) |
| Configuration (`.env`) | Critical | Root Directory | Manual | N/A | Secure Vault |

*Note: Retention periods are governed by the [Data Retention Policy](DATA_RETENTION_POLICY.md).*

## 4. Backup Strategy

### 4.1. Automated Backup Process
- **Tool:** `scripts/backup_verify.sh`
- **Schedule:** Recommended to run via cron every hour:
  ```cron
  0 * * * * /path/to/scripts/backup_verify.sh >> /var/log/mt5_backup.log 2>&1
  ```
- **Integrity Checks:**
  - **Checksums:** Every backup artifact generates a SHA256 checksum.
  - **Restoration Dry-run:** The script performs a `PRAGMA integrity_check` on the backup database file to ensure it is not corrupt.

### 4.2. Local Retention Enforcement
The `backup_verify.sh` script automatically prunes local backups older than 30 days to manage disk space.

## 5. Restoration Procedures

### 5.1. Database Restoration (Scenario: Data Corruption)
1. **Stop the bot:**
   ```bash
   kill $(pgrep -f "python main.py")
   ```
2. **Identify the latest healthy backup:**
   List backups in `backups/db/` and choose the most recent.
3. **Verify the checksum:**
   ```bash
   cd backups/db/
   sha256sum -c trades_YYYYMMDD_HHMMSS.db.sha256
   ```
4. **Restore the file:**
   ```bash
   cp trades_YYYYMMDD_HHMMSS.db ../../trades.db
   ```
5. **Post-Restoration Integrity Check:**
   ```bash
   sqlite3 trades.db "PRAGMA integrity_check;"
   ```
6. **Restart the bot.**

### 5.2. Log and Report Restoration
1. **Locate the archive:**
   Backups are stored in `backups/logs/` or `backups/reports/`.
2. **Extract the archive:**
   ```bash
   tar -xzf backups/logs/logs_YYYYMMDD_HHMMSS.tar.gz -C ./logs/
   ```

### 5.3. Complete System Loss
1. **Provision a new environment** (Docker/VPS).
2. **Clone the repository.**
3. **Restore `.env`** from secure storage (Secrets Manager/Vault).
4. **Restore latest `trades.db`** from off-site/cloud backup.
5. **Deploy:**
   ```bash
   docker-compose up -d
   ```

## 6. Verification and Drills
- **Continuous Verification:** The `scripts/backup_verify.sh` script provides immediate feedback on backup health.
- **Manual Restore Drill:** A full restoration drill must be conducted every quarter to ensure RTO/RPO targets are achievable.
- **Audit Logging:** Every successful backup and verification is logged for auditability.

## 7. Escalation
- **Primary:** Jules03 (Release Reliability & Governance)
- **Secondary:** Jules02 (Security & Hardening)
