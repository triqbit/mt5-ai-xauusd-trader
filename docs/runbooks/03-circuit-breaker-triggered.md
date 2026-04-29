# Runbook 03: Circuit Breaker Triggered

## Description
This runbook outlines the response procedure when the Risk Manager triggers a circuit breaker or daily loss limit, halting all trading activities to protect capital.

## Failure Scenarios

### 1. 15% Maximum Drawdown Halt (Global Circuit Breaker)
**Symptoms:** Logs show "CIRCUIT BREAKER: drawdown=... - trading halted". Telegram alert: "CRITICAL: Circuit Breaker Triggered!".
**Cause:** The account equity has dropped 15% or more from its peak.

**Steps to Respond:**
1.  **Immediate Action:** Verify that the bot has stopped placing new orders.
2.  **Analyze Positions:** Manually check MT5 for any open positions. The bot may have halted, but open trades might still be active. Decide whether to manually close them based on current market conditions.
3.  **Root Cause Analysis:** Investigate why the drawdown occurred:
    - Market anomaly or "black swan" event.
    - Model failure or logic error.
    - Connectivity/slippage issues.
4.  **Reporting:** Document the event in the trade logs and report to stakeholders.
5.  **Resumption:** Do **not** restart the bot immediately. Adjust model parameters, risk limits, or strategy before resuming. Resumption requires manual intervention and configuration update.

**Expected Outcome:** Trading is halted until manual intervention and strategy adjustment.

---

### 2. Daily Loss Limit Hit
**Symptoms:** Logs show "Daily loss limit hit". Signals are rejected with reason "Daily loss limit reached".
**Cause:** Realized losses for the current day have exceeded the `MAX_DAILY_LOSS` (default 5%) defined in the config.

**Steps to Respond:**
1.  The Risk Manager will automatically reject all new signals for the remainder of the trading day.
2.  Review the trades that led to the daily loss.
3.  Wait for the next trading day for the `reset_daily()` function to automatically re-enable trading.
4.  If the loss limit is hit frequently, consider lowering `RISK_PER_TRADE`.

**Expected Outcome:** Trading resumes automatically after the daily reset.

---

## Escalation Path
- **Circuit Breaker Triggered:** Escalate immediately to the Portfolio Manager (Jules05) and Quant Researcher (Jules04).
- **Strategy Failure:** Escalate to Jules04 for model retraining or logic review.

## Verification Commands
1. Check risk events in the database:
   ```bash
   # Using sqlite3 to check risk_events table
   sqlite3 trades.db "SELECT * FROM risk_events WHERE event_type='CIRCUIT_BREAKER' OR event_type='SIGNAL_REJECTED' ORDER BY created_at DESC LIMIT 5;"
   ```
2. Check bot logs for rejection reasons:
   ```bash
   grep "Signal REJECTED" logs/trading.log
   ```
