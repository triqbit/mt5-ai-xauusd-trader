# Runbook 06: Monitoring Alert Triage

## Overview
This runbook provides a guide for triaging Telegram alerts and other monitoring notifications by severity.

## 1. Severity Levels

| Severity | Description | Response Time | Action |
| :--- | :--- | :--- | :--- |
| **P1 - CRITICAL** | Trading halted, connection lost, or heavy loss. | < 5 Minutes | Immediate intervention. |
| **P2 - HIGH** | Order rejections, high latency, or disk space low. | < 30 Minutes | Investigate and resolve. |
| **P3 - MEDIUM** | Model confidence low, minor linter issues in CI. | Next Business Day | Review and plan fix. |
| **P4 - INFO** | Trade executed, daily summary, bot heartbeat. | N/A | Log for audit. |

## 2. Common Alerts and Triage Actions

### 2.1 [P1] CIRCUIT_BREAKER_TRIGGERED
- **Cause**: Drawdown > 15% or Daily Loss > 5%.
- **Action**: Follow **Runbook 03**. Notify stakeholders immediately.

### 2.2 [P1] BROKER_CONNECTION_LOST
- **Cause**: MT5 terminal down or network issue.
- **Action**: Follow **Runbook 02**. Check host internet and MT5 status.

### 2.3 [P2] ORDER_REJECTED
- **Cause**: Rejection by broker (insufficient funds, invalid price) or `RiskManager`.
- **Action**: Check logs for "Order rejected" or "Signal REJECTED". Check account balance and margin.

### 2.4 [P2] HIGH_LATENCY
- **Cause**: Network delay to broker > 1s or slow model inference.
- **Action**: Check CPU/Memory usage on the host. Check network stability.

### 2.5 [P3] DATA_GAP_DETECTED
- **Cause**: Missing OHLCV bars from the data feed.
- **Action**: The bot usually retries. If persistent, check symbol availability in MT5 Market Watch.

## 3. Telegram Triage Protocol
1. **Acknowledge**: React to the message or reply "Investigating" to notify the team.
2. **Diagnose**: Use `tail -f logs/trading_bot.log` to see the live error stream.
3. **Resolve**: Follow the specific runbook or escalate if the root cause is unknown.

## 4. Verification
- Verify the alert has cleared (e.g., "Connection Restored" message).
- Check the dashboard (Grafana/Streamlit) for healthy metrics.
