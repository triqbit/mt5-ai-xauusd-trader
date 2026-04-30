# Service Level Objectives (SLO) & Reliability Targets

This document defines the measurable reliability standards for the MT5 AI/ML XAUUSD Trading Bot repository and runtime system. These objectives ensure "enterprise quality" is trackable and actionable.

## 1. System Uptime Targets

Uptime is defined as the system's availability to process market data and execute trades as per its configuration.

| Environment | Target Uptime | Monthly Error Budget (Downtime) |
|-------------|---------------|----------------------------------|
| **Live Trading** | 99.9% | 43.8 minutes |
| **Demo Trading** | 99.0% | 7.3 hours |

## 2. CI/CD Pipeline Performance

To ensure high code quality and stable releases, the automated validation pipelines must meet the following targets:

- **CI Success Rate:** 95% of commits on monitored branches (main, develop) must pass all automated checks (linting, tests, security scans) on the first run.
- **Pipeline Execution Time:**
    - Pull Request Validation: < 10 minutes
    - Full Pre-deployment Suite: < 20 minutes

## 3. Alert Response Time Expectations

Alerts are categorized by severity, with defined expectations for acknowledgement and resolution.

| Severity | Definition | Acknowledgement (MTTA) | Resolution (MTTR) |
|----------|------------|------------------------|-------------------|
| **P0** | Critical: Trading halted, system down | 5 minutes | 1 hour |
| **P1** | High: Performance degradation, partial loss | 15 minutes | 4 hours |
| **P2** | Medium: Non-critical feature failure | 1 hour | 24 hours |
| **P3** | Low: Minor UI/Log issues, inquiries | 4 hours | 3 business days |

## 4. Model Inference Latency

Inference latency is the time taken by the AI model to produce a prediction once a feature set is provided.

| Metric | Target Latency |
|--------|----------------|
| **P50 (Median)** | < 10ms |
| **P95** | < 50ms |
| **P99** | < 100ms |

## 5. Backtest Performance

Backtesting must be efficient to allow for rapid strategy iteration and validation.

- **Target Generation Time:** < 5 minutes for a standard 1-year historical data backtest on XAUUSD (M5 timeframe).
- **Throughput:** Capable of running 10 parallel backtests during optimization without exceeding system memory limits.

## 6. Disaster Recovery & Incident Targets

Recovery targets define the maximum acceptable data loss and downtime during a major incident.

- **Recovery Time Objective (RTO):** < 4 hours (Time to restore system functionality after a failure).
- **Recovery Point Objective (RPO):** < 1 hour (Maximum period for which data might be lost from the last successful backup).

## 7. Error Budget Framework

The error budget is the maximum amount of time the system can be failing without violating the SLO.

- **Monthly Budget (Live):** 43.8 minutes.
- **Consumption Policy:**
    - If > 50% of the budget is consumed in the first 2 weeks, feature development is paused to focus on stability.
    - If > 80% of the budget is consumed, an immediate "Stability Sprint" is triggered.
    - If 100% is consumed, all non-emergency changes are frozen until the next budget cycle.

## 8. Review Cycle

These targets are reviewed quarterly by the Release Reliability and Engineering teams to ensure they remain aligned with business needs and technical capabilities.
