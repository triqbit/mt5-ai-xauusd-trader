# Runbook 06: Monitoring Alert Triage

## Overview
This runbook provides a framework for triaging and responding to alerts sent by the `Monitor` via Telegram.

## Alert Severity Levels

| Severity | Prefix | Description | Response Time |
| :--- | :--- | :--- | :--- |
| **P0 (Critical)** | `🚨 CRITICAL:` | System-halting event (Circuit breaker, MT5 Outage). | Immediate (< 5m) |
| **P1 (Error)** | `❌ ERROR:` | Failure to execute a specific trade or log data. | < 15m |
| **P2 (Warning)** | `⚠️ WARNING:` | Degraded performance (Confidence degradation, Daily loss limit). | < 1h |
| **P3 (Info)** | `📅 INFO:` / `📅 Daily` | Routine status updates and summaries. | No immediate action |

## Triage Procedures

### 1. P0 (Critical) Alerts
**Example:** `🚨 CRITICAL: Circuit Breaker Triggered!`
1.  **Acknowledge:** Post in the Telegram chat "Acknowledged, investigating".
2.  **Refer to Runbook:** Follow [Runbook 02 (Outage)](02-mt5-connection-outage.md) or [Runbook 03 (Circuit Breaker)](03-circuit-breaker-triggered.md).
3.  **Status Update:** Provide updates every 15 minutes until resolved.

### 2. P1 (Error) Alerts
**Example:** `❌ ERROR: Trade Execution Failed for XAUUSD`
1.  **Analyze Log:** Check `trading.log` for the MT5 error code (e.g., 10013 - Invalid volume).
2.  **Manual Check:** Verify the state of the account and the position in MT5 Terminal.
3.  **Fix:** Correct configuration or handle the edge case in code.

### 3. P2 (Warning) Alerts
**Example:** `⚠️ WARNING: Model Confidence Degradation`
1.  **Monitor:** Observe if the degradation persists over multiple candles.
2.  **Analyze:** Use the Forensic Analysis steps in [Runbook 03](03-circuit-breaker-triggered.md) to evaluate model performance.
3.  **Tune:** If necessary, adjust `confidence_threshold` in `config.py`.

### 4. P3 (Info) Alerts
**Example:** `📅 Daily Summary - 2026-01-20`
1.  **Review:** Cross-reference the net P&L with the broker's daily report.
2.  **Archive:** Ensure the data is correctly persisted in the `performance_metrics` table.

## Escalation Path
- **P0/P1:** Alert the on-call rotation immediately.
- **P2:** Discuss during the next daily stand-up/sync.
- **P3:** No escalation required.

## Verification
- Alert is marked as "RESOLVED" in the monitoring dashboard (if applicable).
- Root cause identified and documented in the incident log.
