# Runbook 03: Circuit Breaker Triggered

## Overview
The `RiskManager` implements a global circuit breaker that halts all trading when account equity drawdown reaches or exceeds 15% from its peak. This runbook details the response required when this safety mechanism is activated.

## Immediate Response (T+0)

### 1. Confirm Trading Halt
- Verify the bot has stopped generating new orders.
- Telegram Alert: `🚨 CRITICAL: Circuit Breaker Triggered! Drawdown: XX.X%`
- Check logs for `CIRCUIT BREAKER: drawdown=... - trading halted`.

### 2. Manual Position Audit
1.  Open the MT5 Terminal.
2.  Review all open positions.
3.  **Mandatory Action:** Close all open positions manually if the bot has failed to do so automatically.
4.  Cancel all pending orders.

## Forensic Analysis (T+1h)

### 1. Identify Root Cause
- **Market Volatility:** Was there a flash crash or extreme "black swan" event?
- **Model Failure:** Did the AI model generate high-confidence signals that were consistently wrong?
- **Bug:** Was there a bug in the SL/TP execution or position sizing?
- **Data Issue:** Did the bot receive corrupted market data?

### 2. Review Risk Events
Query the database for risk events preceding the halt:
```sql
SELECT * FROM risk_events ORDER BY created_at DESC LIMIT 50;
```

### 3. Review Recent Trades
```sql
SELECT * FROM trades WHERE status = 'CLOSED' ORDER BY updated_at DESC LIMIT 10;
```

## Reset Procedure (T+24h+)

**DO NOT RESET WITHOUT A FORMAL INCIDENT POST-MORTEM.**

1.  **Resolve Root Cause:** Patch code, adjust model parameters, or update risk limits.
2.  **Backtest:** Run a full backtest to ensure the fix would have prevented the drawdown.
3.  **Manual Reset:**
    The circuit breaker is state-based. To reset, the `peak_equity` in the `RiskManager` must be updated or the bot restarted after the account has been replenished or the drawdown calculation adjusted.
    *Note: In the current implementation, restarting the bot resets the peak equity to the current balance, effectively resetting the drawdown calculation.*

## Escalation Path
1.  **Level 1:** On-call Trader (@maintainer-trading) for immediate position closure.
2.  **Level 2:** Quant Lead (@jules04 or @maintainer-models) for model forensic analysis.
3.  **Level 3:** Release Lead (@andonly1348) for approval to resume production trading.

## Verification
- Log message after restart: `RiskManager initialised | balance=...`
- Telegram message: `INFO: Trading resumed after circuit breaker reset` (if manual alert sent).
