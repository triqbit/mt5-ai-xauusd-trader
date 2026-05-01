# Disaster Recovery Plan (DRP)

## 1. Overview
This document outlines the disaster recovery procedures for the MT5 AI/ML Trading Bot, focusing on the preservation and restoration of the trading database (`trades.db`), operational logs, and critical performance data.

## 2. Recovery Objectives
- **Recovery Point Objective (RPO):** 1 hour (Maximum data loss allowed).
- **Recovery Time Objective (RTO):** 15 minutes (Maximum time to restore service after a disaster).

## 3. Data Classification
| Data Type | Importance | Primary Location | Backup Frequency |
|-----------|------------|------------------|------------------|
| Trading Database (`trades.db`) | Critical | Root Directory | Every 1 hour |
| Operational Logs | High | `logs/` | Daily Archival |
| Model Weights | Medium | `models/trained/` | On change/Release |
| Configuration (`.env`) | Critical | Root Directory | Manual (Secure Vault) |

## 4. Backup Strategy
### 4.1. SQLite Database
- **Tool:** `scripts/backup_verify.sh`
- **Schedule:** Automated cron job (every hour).
- **Retention:**
  - Standard retention: 30 days (Automated pruning).
- **Integrity:** Every backup includes a SHA256 checksum and a restoration dry-run verification.

### 4.2. Logs and Performance Reports
- **Tool:** Standard `tar` compression.
- **Schedule:** Daily at 00:00 UTC.
- **Archival Policy:**
  - Active logs: 7 days.
  - Archived logs: 90 days in local `backups/logs/`.
  - Long-term storage: Move to off-site/cloud storage after 90 days.

## 5. Restoration Procedures

### 5.1. Database Restoration (Scenario: Data Corruption)
1. Stop the bot: `kill $(pgrep -f "python main.py")`
2. Identify the latest healthy backup in `backups/`.
3. Verify the checksum:
   ```bash
   sha256sum -c trades_YYYYMMDD_HHMM.db.sha256
   ```
4. Restore the file:
   ```bash
   cp backups/trades_YYYYMMDD_HHMM.db ./trades.db
   ```
5. Run integrity check:
   ```bash
   sqlite3 trades.db "PRAGMA integrity_check;"
   ```
6. Restart the bot.

### 5.2. Complete System Loss
1. Provision a new environment (Docker/VPS).
2. Clone the repository.
3. Restore `.env` from secure storage.
4. Restore latest `trades.db` from off-site backup.
5. Deploy using `docker-compose up -d` or manual setup.

## 6. Verification and Testing
- **Automated Verification:** The `scripts/backup_verify.sh` script performs a restoration dry-run on every backup.
- **Manual Drill:** Conduct a full restoration drill every quarter.

## 7. Escalation
- **Primary:** Jules03 (Release Reliability)
- **Secondary:** Jules02 (Security & Hardening)
