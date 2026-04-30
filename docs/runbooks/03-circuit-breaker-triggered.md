# Runbook 03: Circuit Breaker Triggered

## Description
This runbook provides instructions for responding to risk engine halts triggered by circuit breakers or daily loss limits.

## Trigger Scenarios

### 1. Hard Circuit Breaker (15% Drawdown)
**Symptom:** Logs show `CIRCUIT BREAKER: drawdown=...% - trading halted`. Telegram alert sent.
**Step-by-step Instructions:**
1. **Immediate Action:** Verify all open positions are closed via MT5 Terminal or MetaAPI.
2. **Audit:** Review `trades` table in `trades.db` to identify the sequence of losing trades.
   ```sql
   SELECT * FROM trades ORDER BY created_at DESC LIMIT 20;
   ```
3. **Analyze:** Check if the losses were due to model failure, high volatility (slippage), or bug in execution.
4. **Remediation:** If a bug is found, fix and deploy. If model failure, retrain or adjust parameters.
5. **Recovery:** To resume trading, the peak equity must be reset or the account balance increased. **Note:** This requires manual intervention and approval from Risk Committee.

**Expected Outcome:** Trading remains halted until manual override.

### 2. Daily Loss Limit Hit
**Symptom:** Logs show `Daily loss limit hit: ...%`. Signal rejections with reason `Daily loss limit reached`.
**Step-by-step Instructions:**
1. Wait for the trading day to end.
2. Review intraday trades for anomalies.
3. The bot will automatically resume at the start of the next trading day when `reset_daily()` is called.
4. If immediate resumption is critical (and approved):
   - Restart the bot process (this will reset `DailyStats` in memory).

**Expected Outcome:** Bot resumes trading after 00:00 UTC or process restart.

## Escalation Path
1. Hard Circuit Breaker: MUST escalate to Trading Lead (Jules01) and Risk Manager (Jules03).
2. Unexpected Daily Loss: Escalate to Quant Strategist (Jules04) to review model performance.

## Verification Commands
```bash
# Check risk events in database
sqlite3 trades.db "SELECT * FROM risk_events WHERE event_type='CIRCUIT_BREAKER';"

# Check current drawdown in logs
grep "drawdown" logs/app.log | tail -n 5
```
