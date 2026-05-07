# Runbook 03: Circuit Breaker Triggered
**Version:** 1.1 | **Last Updated:** 2026-05-07

## Overview
Critical response for when the `RiskManager` circuit breaker halts trading due to a 15% equity drawdown.

## Step-by-Step Instructions

### 1. Emergency Halt
- Stop the bot immediately: `docker stop mt5-trader`.
- Manually close or hedge risky positions in the MT5 Terminal/Mobile App.

### 2. Incident Analysis
- Run the incident report: `python scripts/generate_incident_report.py`.
- Query `risk_events` table for breach details.
- Check `audit_log` for the `risk_decision` that triggered the halt.

### 3. Reset (After Resolution)
- Address the root cause (e.g., model failure, extreme market event).
- Restart the bot: `docker start mt5-trader`.
- Monitor the first 5 trades closely.

## Expected Outcomes
- All open risk is neutralized.
- Circuit breaker state is cleared only after root cause analysis.
- Audit trail for the event is complete.

## Verification Commands
- `python scripts/generate_incident_report.py`
- `sqlite3 trades.db "SELECT * FROM risk_events WHERE event_type='CIRCUIT_BREAKER' ORDER BY created_at DESC LIMIT 1;"`

## Escalation Path
1. **Risk Breach:** Risk Lead (@maintainer-trading).
2. **Model Failure:** ML Lead (@maintainer-models).
3. **P0 Incident:** Business Owner (@andonly1348).
