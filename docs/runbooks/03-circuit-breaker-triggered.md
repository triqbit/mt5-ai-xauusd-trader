# Runbook 03: Circuit Breaker Triggered

## Overview
The `RiskManager` implements a global circuit breaker that halts all trading if the account equity drawdown reaches or exceeds 15% from its peak. This runbook covers the response and reset procedure.

## Symptoms
- Telegram Alert: `CIRCUIT BREAKER: drawdown=XX.X% - trading halted` (P0 - Critical)
- Logs: `CIRCUIT BREAKER: drawdown=0.15 - trading halted`
- New signals are rejected with reason: `Circuit breaker active`

## Immediate Response

### 1. Stop Trading Engine
Shut down the bot to prevent any further automated activity while investigating.
```bash
docker stop mt5-trader
```

### 2. Secure Open Positions
1. Log in to the MT5 terminal (desktop or mobile).
2. Review all open positions.
3. Manually close positions if necessary to prevent further loss beyond the 15% limit.

## Investigation

### 1. Analyze Recent Trades
- Review `trades.db` or the trade logs in the database.
- Identify if the losses were due to a series of normal losing trades or a "black swan" event.
- Check for execution issues (high slippage, stale prices).

### 2. Verify Model Performance
- Check for model drift in the operations dashboard.
- Ensure the algorithm is still performing within expected parameters.

## Reset Procedure

**Note:** The circuit breaker should NOT be reset until the root cause of the drawdown is understood and mitigated.

### 1. Clear State
The circuit breaker is stateful within the running process. To reset:
1. Ensure the root cause is addressed.
2. Restart the bot process. This will re-initialize the `RiskManager` with current equity as the new peak (unless persistence logic is modified).
   ```bash
   docker start mt5-trader
   ```

### 2. Manual Reset (If persistence is implemented)
If the peak equity is persisted in the database:
1. Update the `peak_equity` value in the database to the current equity.
2. Restart the bot.

## Verification
1. Check logs for: `RiskManager initialised`.
2. Monitor first few trades in `demo` mode if possible before resuming `live` trading.

## Escalation Path
1. **Level 1:** Risk Manager / Quantitative Lead.
2. **Level 2:** Core Strategy Developer.
3. **Level 3:** Portfolio Manager.
