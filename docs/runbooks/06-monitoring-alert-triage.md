# Runbook 06: Monitoring Alert Triage

## Overview
This runbook defines the triage process for alerts received via Telegram or other monitoring channels.

## Alert Severity Levels

### P0: Critical / Immediate Action Required
**Description:** Trading is halted, or there is an immediate risk to capital.
- **Example Alerts:** `CIRCUIT BREAKER`, `Margin Call Alert`, `System Crash`, `Unauthorized Access`.
- **Response Time:** < 5 minutes.
- **Action:** Shut down the bot, secure positions, and escalate immediately.

### P1: Error / Action Needed within 15 Minutes
**Description:** Trading is severely degraded or failing on a specific symbol.
- **Example Alerts:** `Broker Connection Lost`, `Order Failure Rate High`, `Database Corruption`.
- **Response Time:** 15 minutes.
- **Action:** Diagnose connection or database issues using relevant runbooks.

### P2: Warning / Action Needed within 1 Hour
**Description:** System is operational but degraded or approaching limits.
- **Example Alerts:** `High Memory Usage`, `Model Drift Detected`, `Max Positions Reached`.
- **Response Time:** 1 hour.
- **Action:** Investigate resource usage or model performance; plan for scaling or retraining.

### P3: Info / Status Update
**Description:** General system health or operational logs.
- **Example Alerts:** `Daily Summary`, `System Health: OK`, `New Model Deployed`.
- **Response Time:** No immediate action.
- **Action:** Review during daily/weekly checks.

## Triage Procedure

1. **Acknowledge:** Mark the alert as acknowledged in the monitoring channel.
2. **Verify:** Check the operations dashboard to confirm the alert is not a false positive.
3. **Classify:** Confirm the severity (P0-P3).
4. **Respond:** Execute the corresponding runbook:
   - P0 -> Runbook 03 (Circuit Breaker)
   - P1 -> Runbook 02 (Connection) or 04 (Database)
5. **Communicate:** Update stakeholders if P0 or P1.
6. **Resolve:** Once the issue is fixed, verify via dashboards and close the alert.

## Verification
- Dashboard metrics return to normal ranges.
- Telegram alert: `RESOLVED: [Alert Name]`.

## Escalation Path
- **P0/P1:** Notify on-call engineer and team lead.
- **P2:** Log Jira ticket for next business day.
