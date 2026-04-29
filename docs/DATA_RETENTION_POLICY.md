# Data Retention Policy

## 1. Overview
This document defines the policies for how long operational data is kept and when it is purged within the MT5 AI/ML Trading Bot ecosystem. These policies ensure compliance with financial regulations while maintaining system performance and storage efficiency.

## 2. Retention Windows

| Data Type | Retention Period | Action After Expiry | Reason |
|-----------|------------------|---------------------|--------|
| Application Logs | 90 Days | Delete | Operational troubleshooting |
| Trade Records | 7 Years | Archive & Delete | Regulatory compliance |
| Model Signals | 1 Year | Delete | Model performance analysis |
| Risk Events | 2 Years | Delete | Audit trail & risk assessment |
| Performance Metrics| 1 Year | Archive & Delete | Long-term performance tracking |
| Backtest Results | 180 Days | Delete | Strategy development |

## 3. Archival Rules

### 3.1 Trade Records
Trade records must be preserved for 7 years to meet regulatory requirements. After 7 years, data may be permanently deleted unless a legal hold is in place. Trade data should be exported to a long-term storage format (e.g., CSV or Parquet) before being purged from the active database.

### 3.2 Performance Metrics
Performance snapshots are summarized annually. Detailed monthly metrics are archived to CSV format in the `archives/` directory before being purged from the primary database after 1 year.

### 3.3 Backtest Results
Backtest results are kept for 180 days to support ongoing strategy refinement. Results older than 180 days are deleted unless manually marked for preservation.

## 4. Automated Purging Schedule

The `scripts/data_cleanup.py` script is responsible for executing the purging logic. It should be scheduled to run weekly via a cron job or similar task scheduler.

- **Weekly Run**: Sunday at 00:00 UTC.
- **Log Rotation**: Handled by the system's logging configuration, but the cleanup script provides a fallback for non-rotated files.

## 5. Auditability vs. Storage Control

| Category | Preservation Requirement | Data Examples |
|----------|--------------------------|---------------|
| **Audit-Critical** | High (7+ Years) | Trade tickets, execution timestamps, prices, lot sizes. |
| **Operational** | Medium (1-2 Years) | Risk rejections, model confidence scores, signal timestamps. |
| **Transient** | Low (90 Days) | Debug logs, connection heartbeat logs, temporary cache data. |

## 6. Implementation

Automated cleanup is implemented in `scripts/data_cleanup.py`. This script:
1. Identifies records exceeding the retention window.
2. Archives necessary data to the `archives/` directory.
3. Performs safe deletion from the database.
4. Supports a `--dry-run` mode for verification.
