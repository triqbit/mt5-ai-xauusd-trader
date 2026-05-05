# Runbook 03: Circuit Breaker Triggered

## Overview
The `RiskManager` implements a global circuit breaker that halts all trading if the account equity drawdown reaches or exceeds **15%** from its peak. This is a critical safety mechanism to prevent catastrophic capital loss.

## Symptoms
- **Telegram Alert:** `🚨 CIRCUIT BREAKER: drawdown=XX.X% - trading halted` (P0 - Critical)
- **Logs:** `CIRCUIT BREAKER: drawdown=0.15 - trading halted`
- **Signal Rejection:** New signals are rejected with reason: `Circuit breaker active`.
- **Health Check:** `/health/readiness` reports `RiskManager: DEGRADED`.

## Immediate Response (P0 Protocol)

### 1. Stop Trading Engine
Shut down the bot immediately to prevent any further automated activity during investigation.
```bash
docker stop mt5-trader
```

### 2. Secure Open Positions
1. Log in to the MT5 terminal (Desktop, Web, or Mobile).
2. Review all open positions.
3. **Manual Exit:** Close any positions that are contributing to the drawdown or pose further risk.

## Investigation

### 1. Identify the Trigger Event
Query the `risk_events` table in the audit database to find the timestamp and specific drawdown value:
```bash
sqlite3 trades.db "SELECT event_type, description, created_at FROM risk_events WHERE event_type='CIRCUIT_BREAKER' ORDER BY created_at DESC LIMIT 1;"
```

### 2. Analyze Recent Trade Performance
Review the trades leading up to the breach to identify patterns or failures:
```bash
sqlite3 trades.db "SELECT ticket, symbol, direction, entry_price, exit_price, pnl, created_at FROM trades ORDER BY created_at DESC LIMIT 10;"
```
- Did multiple trades hit Stop Loss (SL) simultaneously?
- Was there a failure in SL execution (slippage)?
- Is there a discrepancy between the bot's equity calculation and the broker's balance?

### 3. Check for Model/Strategy Drift
Review `performance_metrics` snapshots:
```bash
sqlite3 trades.db "SELECT * FROM performance_metrics ORDER BY created_at DESC LIMIT 5;"
```

## Reset Procedure

**WARNING:** Do NOT reset the circuit breaker until the root cause is fully understood and documented.

### 1. Manual Reset
The circuit breaker state is in-memory. Restarting the application re-initializes the `peak_equity` to the current balance.

1. Ensure all critical issues are addressed.
2. Restart the bot:
   ```bash
   docker start mt5-trader
   ```

### 2. Audit the Reset
Confirm that the system has resumed in a healthy state:
```bash
sqlite3 trades.db "SELECT event_type, description, created_at FROM risk_events ORDER BY created_at DESC LIMIT 5;"
```

## Expected Outcomes
- Circuit breaker is cleared and the bot is ready to accept new signals.
- `peak_equity` is reset to the current account level.
- A full audit trail of the trigger event and resolution exists in `risk_events`.

## Verification Commands
- **Check Readiness:** `curl http://localhost:8000/health/readiness`
- **Verify Audit Logs:** `sqlite3 trades.db "SELECT event_type, created_at FROM risk_events WHERE created_at > datetime('now', '-1 hour');"`
- **Monitor Risk Logs:** `docker logs mt5-trader | grep "RiskManager"`

## Escalation Path
1. **Level 1:** Risk Lead (@maintainer-trading).
2. **Level 2:** ML/Quant Lead (@maintainer-models).
3. **Level 3:** Business Owner (@andonly1348).
