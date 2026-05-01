# Service Level Objectives (SLO) & Reliability Targets

This document defines the measurable reliability standards for the MT5 AI/ML Trading Bot repository and runtime system.

## 1. Availability SLOs

| Metric | Target | Description |
|--------|--------|-------------|
| **System Uptime (Live Mode)** | 99.5% | Percentage of time the bot is active and connected during market hours. |
| **API Availability** | 99.9% | Availability of the health check and monitoring endpoints. |
| **MT5 Connectivity** | 99.0% | Percentage of time the connection to the broker terminal is active. |

## 2. Reliability SLOs

| Metric | Target | Description |
|--------|--------|-------------|
| **CI Pipeline Success Rate** | 95.0% | Percentage of commits to `main` and `develop` that pass all CI checks. |
| **Order Execution Success** | 99.9% | Percentage of approved signals that result in a successfully placed order (excluding broker rejections). |
| **Database Integrity** | 100% | Zero instances of unrecoverable data corruption in `trades.db`. |

## 3. Latency SLOs

| Metric | P50 | P95 | P99 |
|--------|-----|-----|-----|
| **Model Inference** | < 100ms | < 250ms | < 500ms |
| **Risk Approval Latency** | < 50ms | < 150ms | < 300ms |
| **End-to-End Execution** | < 500ms | < 1.5s | < 3s |

*End-to-end execution covers Signal -> Inference -> Risk Approval -> MT5 Order.*

## 4. Operational & Performance SLOs

| Metric | Target | Description |
|--------|--------|-------------|
| **Backtest Generation Time** | < 5 mins | Time to run a standard 1-year backtest on XAUUSD. |
| **Startup Time** | < 30s | Time from process launch to first health check passing. |
| **Log Retention** | 90 days | Availability of historical operational logs. |

## 5. Incident Response & Recovery (from [DRP](DISASTER_RECOVERY.md))

| Metric | Target | Description |
|--------|--------|-------------|
| **Alert Response (P0)** | < 5 mins | Initial triage for critical/trading-halted events. |
| **Alert Response (P1)** | < 15 mins | Initial triage for degraded service or connection loss. |
| **Recovery Time (RTO)** | 15 mins | Maximum time to restore service after a disaster. |
| **Recovery Point (RPO)** | 1 hour | Maximum data loss allowed in the event of failure. |

## 6. Error Budget Framework

The error budget represents the acceptable amount of failure over a 30-day rolling window.

| Component | Budget (30 Days) | Action on Exhaustion |
|-----------|------------------|----------------------|
| **Downtime** | ~3.6 hours | Halt new feature releases; prioritize stability. |
| **CI Failures** | 5% of builds | Audit CI pipeline and test stability. |
| **Trade Failures** | 0.1% of trades | Audit MT5 Connector and Risk Manager logic. |
| **Inference Latency** | 1% > 500ms | Optimize model architecture or hardware allocation. |

## 7. Monitoring & Reporting
- SLO compliance is tracked via the `HealthChecker` and `Monitor` classes.
- Monthly reliability reviews are conducted to adjust targets based on production performance.
- Breaching an SLO triggers an automatic P2 alert for investigation.
