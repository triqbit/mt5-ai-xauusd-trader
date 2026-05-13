# Service Level Objectives (SLO) & Reliability Targets

This document defines the formal, measurable reliability standards for the MT5 AI/ML Trading Bot. These targets translate "Enterprise Quality" into specific, trackable objectives to ensure production trust, capital safety, and operational excellence.

## 1. Availability SLOs (System Uptime)

Uptime is defined as the percentage of time the system is operational and capable of executing trades during active market hours (XAUUSD: Monday 00:00 - Friday 23:59 Server Time).

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **System Uptime (Live Mode)** | **99.5%** | `/health/readiness` probe success rate (Prometheus: `system_component_health{component="liveness"}`). |
| **API Availability** | 99.9% | Percentage of 2xx/3xx responses from health/metrics endpoints. |
| **MT5 Connectivity** | 99.0% | Prometheus: `system_component_health{component="mt5"}` status during market hours. |

**Acceptable Downtime:** ~3.6 hours per 30-day rolling window during market hours.

## 2. CI/CD & Engineering SLOs

Ensuring the stability of the delivery pipeline and the quality of the codebase.

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **CI Pipeline Success Rate** | **95.0%** | Ratio of "Success" vs "Failure" in GitHub Actions `ci.yml` and `pre-deploy-validation.yml`. |
| **Test Coverage (Core)** | > 85% | Automated `pytest-cov` report (Gate 8 in `pre-deploy-validation.yml`). |
| **Security Scan Cleanliness** | 100% | Zero `CRITICAL` or `HIGH` vulnerabilities in Trivy/Gitleaks scans. |

## 3. Performance & Latency SLOs

Inference and execution latency are measured via `src/core/profiler.py` and exported to Prometheus.

| Metric | P50 | P95 | P99 | Measurement Method |
|--------|-----|-----|-----|-------------------|
| **Model Inference** | < 10ms | < 50ms | < 100ms | `trading_block_duration_seconds{block_label="inference"}` |
| **Risk Approval** | < 20ms | < 50ms | < 100ms | `trading_block_duration_seconds{block_label="risk_check"}` |
| **End-to-End Latency** | < 100ms | < 500ms | < 1.5s | `trading_execution_latency_seconds` |
| **Backtest Generation** | **< 5 min** | **< 8 min** | **< 12 min** | Audit Log: `action="backtest_completed"` (metadata: `duration_seconds`). |

## 4. Operational Responsiveness (Alert Triage)

Response expectations for the operations team, aligned with the [Monitoring Runbook](runbooks/06-monitoring-alert-triage.md).

| Severity | Target Response (ACK) | Target Resolution | Measurement Method |
|----------|-----------------------|-------------------|--------------------|
| **P0 (Critical)** | **< 5 mins** | < 1 hour | Time-to-Acknowledge (TTO) in Incident Tracker |
| **P1 (High)** | **< 15 mins** | < 4 hours | Time-to-Acknowledge (TTO) in Incident Tracker |
| **P2 (Medium)** | < 2 hours | < 24 hours | Time-to-Resolution (TTR) in Incident Tracker |
| **P3 (Low)** | < 24 hours | 1 Week | JIRA/Issue Age Tracking |

## 5. Incident Recovery (RTO/RPO)

Defined in the [Disaster Recovery Plan](DISASTER_RECOVERY.md).

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **Recovery Time Objective (RTO)** | **15 mins** | Time from incident detection to `system_restored` event in audit log (logged via `AuditLogger.log_system_restored`). |
| **Recovery Point Objective (RPO)** | **1 hour** | Maximum data age in the most recent valid database backup (verified via `scripts/backup_verify.sh` logs). |

## 6. Error Budget Framework (30-Day Rolling Window)

The Error Budget is the maximum allowable unreliability. If the budget is exhausted, a "Stability Freeze" is triggered.

| Component | SLO | Error Budget | "Acceptable" Failure / Month | Description |
|-----------|-----|--------------|-----------------------------|-------------|
| **Availability** | 99.5% | 0.5% | 216 Minutes (3.6 Hours) | Total downtime across all market hours (equiv. to ~14 incidents at 15m RTO). |
| **CI Stability** | 95.0% | 5.0% | 5 failures per 100 commits | Non-transient pipeline failures (excludes infrastructure flakiness). |
| **Trade Execution** | 99.9% | 0.1% | 1 failure per 1,000 signals | Technical execution failures (e.g., timeout, rejection due to code bug). |
| **Data Integrity** | 100% | 0.0% | **Zero** incidents | No unrecoverable data loss or permanent database corruption. |

### 6.1 Stability Freeze Protocol

If any error budget reaches **0% remaining** within a 30-day window:
1. **Immediate Feature Freeze**: All PRs containing new features or non-critical refactors are blocked.
2. **Reliability Sprint**: The next development cycle is dedicated 100% to addressing the root cause of the SLO breach.
3. **Mandatory Post-Mortem**: A blameless post-mortem must be conducted and documented in `docs/audits/`.

## 7. Governance & Reporting

- **Real-time Tracking**: SLO compliance is monitored via Grafana dashboards pulling from Prometheus.
- **Weekly Review**: Reliability metrics are reviewed every Monday to assess remaining error budgets.
- **Audit Trail**: Every SLO breach is logged as a `critical_event` in the `audit.db`.
- **Stakeholder Report**: A monthly reliability summary is generated using `scripts/generate_research_report.py` (Enterprise Section).
