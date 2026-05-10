# Runbook 03: Circuit Breaker Triggered
**Version:** 1.4.0 | **Last Updated:** 2024-06-01

## Overview
Critical response procedure for when the automated `RiskManager` circuit breaker halts trading due to safety breaches (e.g., 15% equity drawdown, extreme spread, or model calibration failure).

## Step-by-Step Instructions

### 1. Emergency Containment
- **IMMEDIATE ACTION:** Verify the bot has stopped placing new orders.
- Stop the container to prevent any automated activity during triage:
  ```bash
  docker stop xauusd_trader
  ```
- **Manual Intervention:** Open the MT5 Terminal or Mobile App and manually close or hedge any remaining open positions that pose a risk to capital.

### 2. Incident Analysis & Triage
- Generate an automated incident report to understand the breach:
  ```bash
  export DATABASE_URL="sqlite:///trades.db"
  export AUDIT_DATABASE_URL="sqlite:///audit.db"
  python scripts/generate_incident_report.py
  ```
- Review the `risk_events` table for specific breach details:
  ```bash
  sqlite3 trades.db "SELECT * FROM risk_events ORDER BY created_at DESC LIMIT 5;"
  ```
- Check `audit_log` for the `risk_decision` that preceded the halt:
  ```bash
  sqlite3 audit.db "SELECT * FROM audit_log WHERE action LIKE '%risk%' ORDER BY created_at DESC LIMIT 10;"
  ```
- **Common Trigger Causes:**
  - **Equity Drawdown:** Cumulative losses exceeded the daily/weekly/monthly threshold defined in `docs/SLO_TARGETS.md` or `src/core/config.py`.
  - **Spread Alert:** Market liquidity vanished, triggering a safety halt.
  - **Model Drift:** Model accuracy dropped below 0.50 or calibration error exceeded 0.25.

### 3. Resolution & Root Cause
- Address the underlying cause identified in Step 2.
- If it was a market-wide "Flash Crash", wait for volatility to stabilize.
- If it was a model failure, involve the ML Lead (@maintainer-models).
- **DO NOT** restart the bot until a clear root cause is identified and documented.

### 4. System Reset
- Once authorized to resume, restart the bot:
  ```bash
  docker start xauusd_trader
  ```
- Monitor the `logs/` directory and the Prometheus `/metrics` endpoint closely for the first 5 trades.
- Verify the `circuit_breaker_status` metric is reset to `0.0` (Healthy):
  ```bash
  curl -s http://localhost:8000/metrics | grep circuit_breaker
  ```

## Expected Outcomes
- All open risk is neutralized immediately.
- A detailed incident report is generated and archived.
- Circuit breaker state is cleared only after formal root cause analysis and stakeholder approval.

## Escalation Path
1. **Risk Breach/Limits:** Risk Lead (@maintainer-trading).
2. **Model Performance/Drift:** ML Lead (@maintainer-models).
3. **P0 Financial Incident:** Business Owner (@andonly1348).

## Verification Commands
- `python scripts/generate_incident_report.py`
- `sqlite3 trades.db "SELECT event_type, reason, created_at FROM risk_events WHERE event_type='CIRCUIT_BREAKER' ORDER BY created_at DESC LIMIT 1;"`
- `curl -s http://localhost:8000/metrics | grep circuit_breaker`
