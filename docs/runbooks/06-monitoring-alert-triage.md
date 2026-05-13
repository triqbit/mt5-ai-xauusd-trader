# Runbook 06: Monitoring Alert Triage
**Version:** 1.1.0-rc8 | **Last Updated:** 2024-06-12

## Overview
Defined process for triaging alerts from Telegram and Prometheus/Grafana. This ensures that the most critical events (P0/P1) are addressed with priority to minimize capital risk.

## Alert Severity Levels

| Severity | Definition | Target Response (ACK) | Target Resolution |
|---|---|---|---|
| **P0** | **Critical:** Immediate risk to capital (e.g., Circuit Breaker, Large Drawdown, DB Corruption). | < 5 Minutes | < 1 Hour |
| **P1** | **High:** Service failure/degradation (e.g., MT5 Disconnected, API 503, Health Check Failed). | < 15 Minutes | < 4 Hours |
| **P2** | **Medium:** Efficiency or drift issues (e.g., High Spread, Model Accuracy Drop, Disk Space 80%). | < 2 Hours | < 24 Hours |
| **P3** | **Low:** Informational or Routine (e.g., Daily performance summary, Minor linting warning). | < 24 Hours | 1 Week |

## Step-by-Step Instructions

### 1. Initial Triage & Acknowledgement
1. **Acknowledge:** As soon as an alert is received on Telegram, reply with "ACK" or the "👀" emoji to signal that an operator is investigating.
2. **Context Gathering:** Run the automated triage/incident tools:
   ```bash
   # Generate a report of the last 24 hours of activity
   export DATABASE_URL="sqlite:///trades.db"
   export AUDIT_DATABASE_URL="sqlite:///audit.db"
   python scripts/generate_incident_report.py
   ```
3. **Dashboard Review:** Open the Grafana dashboard to check P50/P95/P99 latencies and system resource utilization.

### 2. Action & Escalation
- **If P0:**
  - Engage **Runbook 03 (Circuit Breaker)** or **Runbook 04 (Database Corruption)** immediately.
  - Halt trading if the bot has not already done so.
  - Call the Business Owner (@andonly1348).
- **If P1:**
  - Engage **Runbook 02 (MT5 Connection Outage)** or **Runbook 05 (Rollback)** if a recent release caused the issue.
  - Check `docker logs xauusd_trader --tail 200`.
- **If P2:**
  - Create a GitHub Issue with the alert details and the output of `generate_incident_report.py`.
  - Monitor for escalation to P1.
- **If P3:**
  - Review during standard business hours.

### 3. Resolution & Closure
1. Once the issue is resolved, verify the system health:
   ```bash
   curl -f http://localhost:8000/health/readiness
   python scripts/doctor.py
   python scripts/smoke_test.py
   ```
2. Post a brief "Resolved" message in the Telegram channel with the root cause (e.g., "Resolved: MetaAPI Cloud outage restored by provider").

## Expected Outcomes
- Response targets (TTO) are consistently met per `docs/SLO_TARGETS.md`.
- Root causes are identified using standardized scripts and tools.
- Correct specialized runbooks are engaged based on alert symptoms.
- No P0 alert remains unacknowledged for more than 5 minutes.
- No P1 alert remains unacknowledged for more than 15 minutes.

## Escalation Path
1. **P0 Financial/Capital Incident:** Business Owner (@andonly1348).
2. **P1 Service Outage:** Release Reliability Engineer (Jules03).
3. **P2/P3 Operational:** Primary On-Call Engineer.

## Verification Commands
```bash
python scripts/generate_incident_report.py
python scripts/doctor.py
python scripts/smoke_test.py
```
