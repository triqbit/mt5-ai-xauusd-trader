# Runbook 03: Circuit Breaker Triggered

## Overview
The `RiskManager` implements a global circuit breaker that halts all trading if the account equity drawdown reaches or exceeds 15% from its peak. This is a critical safety mechanism to prevent catastrophic capital loss.

## Symptoms
- Telegram Alert: `🚨 CIRCUIT BREAKER: drawdown=XX.X% - trading halted` (P0 - Critical)
- Logs: `CIRCUIT BREAKER: drawdown=0.15 - trading halted`
- New signals are rejected with reason: `Circuit breaker active`
- Health Check: `/health/readiness` reports `RiskManager: DEGRADED`.

## Immediate Response (P0 Protocol)

### 1. Stop Trading Engine
Shut down the bot immediately to prevent any further automated activity while investigating.
```bash
docker stop mt5-trader
```

### 2. Secure Open Positions
1. Log in to the MT5 terminal (Desktop or Mobile).
2. Review all open positions for the account.
3. Manually close any positions if they are contributing to further drawdown beyond the 15% limit.

## Investigation

### 1. Identify the Trigger Event
Query the `risk_events` table in the database to find the timestamp and specific drawdown value that triggered the breaker:
```bash
sqlite3 trades.db "SELECT * FROM risk_events WHERE event_type='CIRCUIT_BREAKER' ORDER BY created_at DESC LIMIT 1;"
```

### 2. Analyze Recent Trades
Review the most recent trades that led to the drawdown:
```bash
sqlite3 trades.db "SELECT * FROM trades ORDER BY created_at DESC LIMIT 10;"
```
- Was it a single large loss or a series of losses?
- Did the stop-loss levels fail to execute?
- Is there a discrepancy between the bot's calculated equity and the broker's balance?

### 3. Check for Model Drift
Review the `PerformanceMetric` snapshots:
```bash
sqlite3 trades.db "SELECT * FROM performance_metrics ORDER BY created_at DESC LIMIT 5;"
```

## Reset Procedure

**WARNING:** The circuit breaker must NOT be reset until the root cause of the drawdown is fully understood and a mitigation plan is in place.

### 1. Manual Reset
The circuit breaker state is maintained in-memory by the `RiskManager`. Restarting the application will re-initialize the `peak_equity` to the current account balance, effectively resetting the breaker.

1. Ensure the root cause is addressed.
2. Restart the bot:
   ```bash
   docker start mt5-trader
   ```

### 2. Post-Reset Audit
Verify that the reset is logged in the `risk_events` table (manually logged by the operator or automatically on startup):
```bash
sqlite3 trades.db "SELECT * FROM risk_events ORDER BY created_at DESC LIMIT 1;"
```

## Expected Outcomes
- Circuit breaker state is cleared and the bot is ready to accept new signals.
- Peak equity is reset to the current account level.
- Audit trail contains a record of the trigger event and the subsequent investigation/reset.

## Verification Commands
- **Check Readiness:** `curl http://localhost:8000/health/readiness`
- **Verify Risk Logs:** `sqlite3 trades.db "SELECT event_type, created_at FROM risk_events WHERE created_at > datetime('now', '-1 hour');"`
- **Monitor Logs:** `tail -f logs/trading_bot.log | grep "RiskManager"`

## Escalation Path
1. **Level 1:** Risk Manager (@maintainer-trading).
2. **Level 2:** Core Strategy Developer (@maintainer-models).
3. **Level 3:** Portfolio Manager / Business Owner.
