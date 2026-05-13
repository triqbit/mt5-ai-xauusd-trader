# Runbook 03: Circuit Breaker Triggered
**Version:** 1.1.0-rc8 | **Last Updated:** 2024-06-12

## Overview
Procedures for responding to automatic trading halts caused by risk limit breaches or system instability.

## Step-by-Step Instructions

### 1. Identify the Trigger
Review the Telegram alert or audit log to determine why the circuit breaker tripped:
```bash
# Check audit log for circuit_breaker_triggered event
sqlite3 audit.db "SELECT * FROM audit_log WHERE action IN ('circuit_breaker_triggered', 'operator_circuit_breaker_triggered') ORDER BY created_at DESC LIMIT 1;"
```
Triggers include:
- `MAX_DRAWDOWN` (30%)
- `MAX_DAILY_LOSS` (5%)
- `MT5_CONNECTION_LOST` (>300s)
- `MODEL_ACCURACY_CRITICAL` (<50%)

### 2. Capital Preservation
1. **Verify Open Positions:** Check if any positions are still open.
2. **Force Close (If Necessary):** If the bot failed to close positions during the halt, close them manually via the MT5 mobile app or desktop terminal.

### 3. Investigation
1. Run the system doctor: `python scripts/doctor.py`.
2. Review the `DecisionSupportSystem` cockpit for recent signal quality.
3. If the trigger was `MAX_DRAWDOWN`, perform a post-mortem on recent trades.

### 4. Reset & Resume
1. Fix the underlying issue (e.g., restore internet, retrain model).
2. **Manual Reset:** Circuit breakers typically reset at 00:00 UTC. To override and resume earlier:
   ```bash
   # Caution: Only perform if the risk is understood and mitigated
   docker restart xauusd_trader
   ```

## Expected Outcomes
- Trading is successfully halted to prevent further loss.
- Audit trail captures the trigger reason and state.
- Normal operation is restored only after operator verification.

## Escalation Path
1. **Large Scale Drawdown:** Risk Lead (@andonly1348).
2. **Rogue Bot Behavior:** Jules03 (Governance).

## Verification Commands
```bash
curl -s http://localhost:8000/health/readiness
```
