# Operational Runbooks
**Version:** 1.1.0-rc8 | **Last Updated:** 2024-06-12

This directory contains enterprise-grade operational runbooks for the MT5 AI/ML Trading Bot. These documents provide standardized procedures for responding to common failure scenarios, ensuring production safety, auditability, and rapid recovery.

## Runbook Index

| ID | Runbook | Description |
|---|---|---|
| 01 | [CI Failure Recovery](./01-ci-failure-recovery.md) | Procedures for recovering from failing GitHub Actions (Lint, Tests, Security). |
| 02 | [MT5 Connection Outage](./02-mt5-connection-outage.md) | Handling MT5 Terminal or MetaAPI cloud gateway connectivity failures. |
| 03 | [Circuit Breaker Triggered](./03-circuit-breaker-triggered.md) | Responding to automated risk engine halts due to safety/drawdown breaches. |
| 04 | [Database Corruption](./04-database-corruption.md) | Recovering from SQLite corruption in `trades.db` or `audit.db` using backups. |
| 05 | [Failed Deployment Rollback](./05-failed-deployment-rollback.md) | Standard procedure for reverting bad releases (Docker images & migrations). |
| 06 | [Monitoring Alert Triage](./06-monitoring-alert-triage.md) | Triaging Telegram/Prometheus alerts by severity (P0-P3) and impact. |
| 07 | [Secret Rotation Procedure](./07-secret-rotation-procedure.md) | Rotating MT5, MetaAPI, and Telegram credentials safely and securely. |

## Standard Operating Principles

1. **Safety First:** Capital preservation is our primary mission. When in doubt, halt trading and engage Runbook 03.
2. **Audit Everything:** Every manual intervention and recovery action must be traceable. Restarts and config changes are automatically logged.
3. **Verify Before Resuming:** Always use `scripts/doctor.py`, `scripts/smoke_test.py`, and `/health/readiness` to verify system state before resuming automated trading.
4. **No Manual Overrides:** Critical risk limits (Circuit Breakers) should not be bypassed without executive approval and a documented post-mortem.
5. **RPO/RTO Enforcement:** All recovery actions should aim for a 1-hour Recovery Point Objective (RPO) and a 15-minute Recovery Time Objective (RTO).
6. **Automation-Led Response:** Prioritize the use of standardized diagnostic and recovery scripts (`scripts/doctor.py`, `scripts/backup_verify.sh`, `scripts/generate_incident_report.py`) to reduce human error.

## Support & Escalation

Refer to the individual runbooks for specific escalation paths. For global platform issues or release-blocking failures, contact the Release Reliability Engineer (Jules03).
