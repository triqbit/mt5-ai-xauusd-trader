# Runbook 03: Circuit Breaker Triggered

## Overview
This runbook covers the response to risk engine halts triggered by the `RiskManager`. Circuit breakers are designed to stop trading when catastrophic conditions are met.

## 1. Trigger Conditions
A circuit breaker is triggered if:
- **Drawdown Limit**: Total account drawdown reaches 15%.
- **Daily Loss Limit**: Realized daily loss reaches the configured `MAX_DAILY_LOSS` (default 5%).
- **Manual Halt**: An emergency stop was triggered by an administrator.

## 2. Investigation Steps

### 2.1 Analyze Trigger Source
1. Check the `risk_events` table in the database to find the exact reason:
   ```sql
   SELECT * FROM risk_events WHERE event_type = 'CIRCUIT_BREAKER' ORDER BY created_at DESC LIMIT 1;
   ```
2. Review the logs leading up to the halt to see if a specific trade or market condition caused the breach.

### 2.2 Verify Account State
1. Log into the MT5 terminal and verify the current equity and open positions.
2. Ensure all positions are closed if the circuit breaker was a "Hard Stop" (Drawdown > 15%).

## 3. Recovery Procedures

### 3.1 Resetting Daily Loss Halt
Daily loss halts reset automatically at 00:00 UTC. To restart early (NOT RECOMMENDED):
1. Evaluate why the loss occurred.
2. If it was a system error (and not a trading strategy failure), you can manually reset the `DailyStats` in `RiskManager` by restarting the bot with a cleared state or a temporary configuration change.

### 3.2 Resetting Major Drawdown Halt
This requires manual intervention and strategy review.
1. **Strategy Review**: Analyze why the 15% drawdown was hit. Is the model drifting? Is there a bug in position sizing?
2. **Approval**: Obtain manager approval to resume trading.
3. **Restart**: Restart the bot. The `RiskManager` will recalculate the `peak_equity` upon startup based on the current balance, effectively resetting the drawdown calculation.

## 4. Escalation Path
- **P1 (Circuit Breaker Triggered)**: Trading is halted. Immediate notification to the Trading Lead and Risk Officer is required.

## 5. Verification Commands
```bash
# Check risk events in the trade database
sqlite3 trades.db "SELECT * FROM risk_events ORDER BY created_at DESC LIMIT 5;"

# Check bot status in logs
grep "CIRCUIT BREAKER" logs/trading_bot.log
```
