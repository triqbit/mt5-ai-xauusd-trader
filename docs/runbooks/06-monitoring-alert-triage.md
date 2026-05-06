# Runbook 06: Monitoring Alert Triage

## Overview
This runbook defines the triage and response process for alerts received via the Telegram Bot or Prometheus monitoring. Severity levels are strictly aligned with `docs/SLO_TARGETS.md`.

## Alert Severity Levels

### P0: Critical / Immediate Risk to Capital
**Description:** Trading is halted, or there is an unmanaged risk to capital.
- **Example Alerts:** `🚨 CIRCUIT BREAKER TRIGGERED`, `Margin Call Warning`, `Unauthorized Trade Detected`.
- **Response Target:** < 5 minutes.
- **Resolution Target:** < 1 hour.
- **Primary Action:** Execute Runbook 03 (Circuit Breaker) or Runbook 02 (MT5 Connection).

### P1: High / Service Degraded
**Description:** Core functionality is failing or severely degraded.
- **Example Alerts:** `Broker Connection Lost`, `Database Corruption`, `System Health: FAILED`.
- **Response Target:** < 15 minutes.
- **Resolution Target:** < 4 hours.
- **Primary Action:** Diagnose using `scripts/doctor.py` and execute Runbook 04 (Database Recovery) or Runbook 05 (Rollback).

### P2: Medium / Degradation Detected
**Description:** System is operational but approaching limits or showing drift.
- **Example Alerts:** `Model Confidence Degradation`, `High Latency Detected`, `Max Positions Reached`.
- **Response Target:** < 2 hours.
- **Resolution Target:** < 24 hours.
- **Primary Action:** Review logs and performance metrics; consider model retraining or resource scaling.

### P3: Low / Informational
**Description:** Routine updates or non-blocking issues.
- **Example Alerts:** `Daily Summary`, `New Deployment Successful`, `Disk Usage > 70%`.
- **Response Target:** < 24 hours.
- **Resolution Target:** 1 Week.

## Triage Procedure

1. **Acknowledge:** Acknowledge receipt of the alert in the Telegram channel immediately.
2. **Classify:** Confirm the severity level (P0-P3) based on the criteria above.
3. **Analyze:** Run the triage reporting script to identify incident patterns:
   ```bash
   python scripts/generate_triage_report.py
   ```
4. **Respond:** Execute the corresponding runbook for the identified symptom.
5. **Update:** For P0/P1 alerts, provide status updates every 15-30 minutes until resolution.
6. **Verify:** Use `/health/readiness` to confirm the fix and system stability.

## Incident Reporting
For every P0/P1 incident, a **Blameless Post-Mortem** must be conducted to update the `RiskManager` logic or improve monitoring thresholds.

## Expected Outcomes
- Response times meet the targets defined in `docs/SLO_TARGETS.md`.
- Critical incidents are resolved with minimal capital impact.
- Incident data is captured for long-term reliability improvements.

## Verification Commands
- **Check Health API:** `curl http://localhost:8000/health/readiness`
- **Review Risk Events:** `sqlite3 trades.db "SELECT event_type, description, created_at FROM risk_events ORDER BY created_at DESC LIMIT 10;"`
- **Review Audit Logs:** `sqlite3 audit.db "SELECT action, details, created_at FROM audit_log ORDER BY created_at DESC LIMIT 10;"`
- **Prometheus Metrics:** `curl http://localhost:8000/metrics | grep trading_system_errors`

## Escalation Path
- **P0/P1:** Immediate notification to @andonly1348 and the On-Call Engineer.
- **P2:** File a bug report in the repository for the next development sprint.
- **P3:** Log as a technical debt item or minor task.
