# Runbook 06: Monitoring Alert Triage
**Version:** 1.1 | **Last Updated:** 2026-05-07

## Overview
Defined process for triaging Telegram/Prometheus alerts.

## Alert Severity Levels
- **P0:** Critical. Immediate risk to capital. (Action: < 5m)
- **P1:** High. Service failure/degradation. (Action: < 15m)
- **P2:** Medium. Efficiency/drift issues. (Action: < 2h)
- **P3:** Low. Info/Routine. (Action: < 24h)

## Step-by-Step Instructions

### 1. Initial Triage
- Acknowledge alert in Telegram.
- Run `python scripts/generate_incident_report.py` to see recent DB activity.

### 2. Escalation
- If P0/P1: Execute corresponding runbook (02, 03, 04, or 05).
- If P2: Create GitHub Issue and monitor.

## Expected Outcomes
- Response targets met.
- Root causes identified via `generate_incident_report.py`.
- Correct runbooks engaged based on symptoms.

## Verification Commands
- `python scripts/generate_incident_report.py`
- `curl http://localhost:8000/health/readiness`

## Escalation Path
1. **P0 Incident:** @andonly1348.
2. **On-Call:** Primary Trading On-Call.
