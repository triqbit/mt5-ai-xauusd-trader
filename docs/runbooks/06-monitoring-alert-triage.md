# Runbook 06: Monitoring Alert Triage

## Description
This runbook provides a framework for triaging and responding to alerts sent by the bot's monitoring system via Telegram.

## Alert Severity Levels

| Severity | Alert Type | Description | Response Time |
| :--- | :--- | :--- | :--- |
| **CRITICAL** | Circuit Breaker Triggered | Trading halted due to major drawdown (15%+). | Immediate (< 5 mins) |
| **WARNING** | Confidence Degradation | Model confidence fell below the threshold (default 0.6). | Next Business Hour |
| **WARNING** | Daily Loss Limit | Trading paused for the day due to loss limit. | Same Day |
| **INFO** | Daily Summary | Regular update on P&L and trade count. | Review Weekly |

---

## Triage Steps

### 1. CRITICAL: Circuit Breaker Triggered
1.  Verify the halt in logs.
2.  Follow [Runbook 03: Circuit Breaker Triggered](./03-circuit-breaker-triggered.md).
3.  Notify the Portfolio Manager (Jules05).

### 2. WARNING: Confidence Degradation
1.  Check recent signals in the `model_signals` table.
2.  Analyze if market conditions have shifted (high volatility, low liquidity).
3.  If confidence remains low for > 4 hours, consider pausing the bot or switching to a more conservative `mode`.
4.  Consult the Quant Researcher (Jules04) for potential retraining.

### 3. WARNING: Daily Loss Limit
1.  Verify that all trades leading to the loss were executed correctly (no slippage/error).
2.  No immediate action required as the bot auto-halts, but review strategy parameters.
3.  Ensure the bot resumes correctly the next day.

### 4. INFO: Daily Summary
1.  Compare the bot's reported P&L with the MT5 account history.
2.  Update the performance tracking spreadsheet/dashboard.

---

## Escalation Path
- **Critical Alerts:** Portfolio Manager (Jules05).
- **Confidence/Model Issues:** Quant Researcher (Jules04).
- **Monitoring Tooling Issues:** Observability Lead (Jules02).

## Verification Commands
1. Check last 5 alerts in the Telegram chat.
2. Query the database for recent model signals:
   ```bash
   sqlite3 trades.db "SELECT algorithm, confidence, timestamp FROM model_signals ORDER BY timestamp DESC LIMIT 5;"
   ```
