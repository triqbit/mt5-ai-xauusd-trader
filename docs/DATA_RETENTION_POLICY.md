# Data Retention Policy

## 1. Overview
This document defines the policies for how long operational data is kept and when it is purged within the MT5 AI/ML Trading Bot system. These policies ensure compliance with regulatory requirements while maintaining system performance and storage efficiency.

## 2. Retention Windows

| Data Type | Retention Period | Action After Period |
|-----------|------------------|---------------------|
| Application Logs (`logs/*.log`) | 90 Days | Permanent Deletion |
| Trade Records (`trades` table) | 7 Years | Permanent Deletion (Regulatory Compliance) |
| Model Signals (`model_signals` table) | 1 Year | Permanent Deletion |
| Risk Events (`risk_events` table) | 2 Years | Permanent Deletion |
| Performance Metrics | 1 Year | Archive to CSV/Parquet, then delete from DB |
| Backtest Results | 180 Days | Permanent Deletion |
| Market Data (OHLCV) | 5 Years | Move to Cold Storage |

## 3. Preservation vs. Rotation

### 3.1 Preservation for Auditability
The following data is preserved to ensure a complete audit trail of trading activity:
- **Trade Records**: Execution details, tickets, symbols, and PnL.
- **Audit Logs**: (If implemented) Changes to system configuration or manual overrides.
- **Risk Events**: Circuit breaker triggers and rejection reasons.

### 3.2 Rotation for Storage Control
The following data is rotated frequently to prevent disk space exhaustion:
- **Debug Logs**: Highly verbose logs are kept for a shorter window (90 days).
- **Model Signals**: High-frequency signal data that did not result in trades.
- **Temporary Backtest Artifacts**: Large CSVs or plots generated during model training/backtesting.

## 4. Archival Rules

### 4.1 Performance Metrics
Performance metrics (`performance_metrics` table) are valuable for long-term strategy analysis.
- Data older than **1 year** will be exported to a structured format (e.g., JSON or Parquet) and stored in the `archives/` directory or cloud storage.
- After successful archival, records are purged from the live database.

### 4.2 Backtest Results
Backtest results can consume significant space.
- Results are kept for **180 days** to allow for comparison between model iterations.
- Results associated with "Production" model versions may be flagged for indefinite retention until the model is decommissioned.

## 5. Automated Purging Schedule
An automated cleanup script (`scripts/data_cleanup.py`) is scheduled to run:
- **Frequency**: Weekly (every Sunday at 00:00 UTC).
- **Process**:
    1. Scan `logs/` directory for files older than 90 days.
    2. Scan database tables for records exceeding their retention window.
    3. Export/Archive data where required by section 4.
    4. Perform safe deletion of expired records.

## 6. Compliance and Legal Hold
In the event of a legal or regulatory inquiry, a "Legal Hold" may be placed on specific datasets, suspending the automated purging for those records until the hold is lifted by an authorized officer.
