# Operational Runbooks
**Version:** 1.1 | **Last Updated:** 2026-05-07

This directory contains enterprise-grade operational runbooks for the MT5 AI/ML Trading Bot. These documents provide standardized procedures for responding to common failure scenarios, ensuring production safety, auditability, and rapid recovery.

## Runbook Index

| ID | Runbook | Description |
|---|---|---|
| 01 | [CI Failure Recovery](./01-ci-failure-recovery.md) | Recovering from failing GitHub Actions (linting, tests, security). |
| 02 | [MT5 Connection Outage](./02-mt5-connection-outage.md) | Handling MT5 Terminal or MetaAPI cloud gateway connectivity failures. |
| 03 | [Circuit Breaker Triggered](./03-circuit-breaker-triggered.md) | Responding to automated risk engine halts due to drawdown. |
| 04 | [Database Corruption](./04-database-corruption.md) | Recovering from SQLite corruption in `trades.db` or `audit.db`. |
| 05 | [Failed Deployment Rollback](./05-failed-deployment-rollback.md) | Standard procedure for reverting bad releases (Docker/Migrations). |
| 06 | [Monitoring Alert Triage](./06-monitoring-alert-triage.md) | Triaging Telegram/Prometheus alerts by severity (P0-P3). |
| 07 | [Secret Rotation Procedure](./07-secret-rotation-procedure.md) | Rotating MT5, MetaAPI, and Telegram credentials safely. |

## Standard Operating Principles

1. **Safety First:** Capital preservation is our primary mission. When in doubt, halt trading.
2. **Audit Everything:** Every manual intervention and recovery action must be traceable in the audit logs.
3. **Verify Before Resuming:** Always use `scripts/doctor.py` and `/health/readiness` to verify system state before resuming automated trading.
4. **No Manual Overrides:** Critical risk limits (Circuit Breakers) should not be overridden without executive approval and a documented post-mortem.

## Support & Escalation

Refer to the individual runbooks for specific escalation paths. For global platform issues, contact the Release Reliability Engineer (Jules03).
