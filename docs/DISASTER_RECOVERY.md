# Disaster Recovery Plan

This document outlines the disaster recovery (DR) strategy for the MT5 AI/ML Trading Bot, ensuring the availability, integrity, and recoverability of critical operational data.

## 1. Objectives

- **Recovery Point Objective (RPO)**: 1 hour
  - Maximum acceptable data loss during a disaster is 1 hour of operational data.
- **Recovery Time Objective (RTO)**: 30 minutes
  - The system should be restored and operational within 30 minutes of a declared disaster.

## 2. Critical Data Assets

| Data Asset | Type | Primary Location | Importance |
| :--- | :--- | :--- | :--- |
| **Trading Database** | SQLite (`trades.db`) | Project Root | Critical (Audit/Compliance) |
| **Application Logs** | File (`logs/*.log`) | `/logs` | High (Troubleshooting) |
| **Model Artifacts** | Binary (`models/`) | `/models` | High (Execution) |
| **Configuration** | Environment (`.env`) | Project Root | Critical (Connectivity) |

## 3. Backup Strategy

### 3.1 Backup Schedule

| Asset | Frequency | Method |
| :--- | :--- | :--- |
| `trades.db` | Hourly | SQLite Online Backup / Snapshot |
| `trades.db` | Daily | Full Compressed Export |
| Application Logs | Daily | Log Rotation and Archival |
| Configuration | On Change | Secure Secret Store / Encrypted Backup |

### 3.2 Data Retention Policy

In alignment with enterprise standards:
- **Application Logs**: 90 days
- **Model Signals**: 1 year
- **Backtest Results**: 2 years
- **Trade Records**: 7 years (Regulatory requirement)
- **Risk Events**: 7 years
- **Performance Metrics**: 7 years

### 3.3 Archival Policy
- Data exceeding the active retention window but within the regulatory window will be moved to long-term cold storage (e.g., AWS S3 Glacier).
- Performance reports and trade logs are archived monthly into compressed `.tar.gz` packages with SHA256 manifests.

## 4. Backup Integrity & Verification

To ensure backups are functional, the following automated checks are performed:
1. **Physical Integrity**: `PRAGMA integrity_check;` executed on every SQLite backup.
2. **Checksum Validation**: SHA256 hashes generated for every backup artifact.
3. **Restoration Dry-run**: Daily automated restoration of the latest backup to a temporary instance to verify data accessibility.

## 5. Recovery Procedures

### 5.1 Database Restoration

1. **Stop the Trading Bot**:
   ```bash
   pkill -f main.py
   ```

2. **Locate the Latest Healthy Backup**:
   ```bash
   ls -lt backups/trades_*.db.gz | head -n 1
   ```

3. **Restore the Database**:
   ```bash
   gunzip -c backups/trades_YYYYMMDD_HHMMSS.db.gz > trades.db
   ```

4. **Verify Integrity**:
   ```bash
   sqlite3 trades.db "PRAGMA integrity_check;"
   ```

5. **Restart the Bot**:
   ```bash
   python main.py --mode [mode]
   ```

### 5.2 Emergency Failover (MetaAPI)

If the primary MT5 terminal is unreachable:
1. Ensure `USE_METAAPI=true` is set in `.env`.
2. Provide valid `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID`.
3. Restart the bot; the `MT5Connector` will automatically switch to the cloud failover path.

## 6. Incident Response

1. **Detection**: Monitoring alerts trigger on database corruption or connection loss.
2. **Analysis**: Check `logs/error.log` to identify the failure root cause.
3. **Recovery**: Follow the procedures in Section 5.
4. **Verification**: Confirm connectivity via `python scripts/validate_env.py` and check the health dashboard.
5. **Post-Mortem**: Document the incident, recovery steps, and preventive measures.
