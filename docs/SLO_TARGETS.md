# Service Level Objectives (SLO) & Reliability Targets

This document defines the measurable reliability standards and performance targets for the MT5 AI/ML Trading Bot. These metrics turn "enterprise quality" into trackable objectives for production readiness.

## 1. System Availability (Uptime)

Uptime is defined as the system's ability to process signals and manage active trades in `live` mode.

| Mode | Target Availability | Allowed Downtime (Monthly) |
| :--- | :--- | :--- |
| **Live Trading** | 99.9% | ~43.8 Minutes |
| **Demo Trading** | 99.0% | ~7.3 Hours |
| **Backtesting Engine** | 95.0% | ~36.5 Hours |

**Measurement:** Percentage of successful heartbeats sent to the monitoring system per 5-minute interval.

## 2. CI/CD Pipeline Performance

The CI pipeline must remain stable to ensure rapid delivery of fixes and features.

| Metric | Target |
| :--- | :--- |
| **Pipeline Success Rate** | 95% of commits to `main` must pass all checks |
| **Deployment Success Rate** | 99% of production deployments succeed or auto-rollback |
| **PR Validation Time** | < 15 Minutes (Linting, Testing, Security) |

## 3. Performance & Latency Targets

Latency is critical for gold (XAUUSD) trading where price movements are rapid.

### 3.1 Model Inference Latency
Measured from the time the feature vector is ready to the generation of the consensus signal.

| Percentile | Target Latency |
| :--- | :--- |
| **P50 (Median)** | < 10 ms |
| **P95** | < 50 ms |
| **P99** | < 100 ms |

### 3.2 Execution & Backtesting
| Metric | Target |
| :--- | :--- |
| **Order Execution Latency** | < 100 ms (Signal to MT5 Order Send) |
| **Backtest Generation Time** | < 5 Minutes (1-year historical data, standard features) |
| **Feature Engineering Latency** | < 50 ms (Raw data to feature vector) |

## 4. Incident Response & Recovery

Defined by Severity Levels as specified in `MONITORING_ALERTING.md`.

| Severity | Response Time (Acknowledge) | Resolution Target |
| :--- | :--- | :--- |
| **P1 (Critical)** | < 5 Minutes | < 2 Hours |
| **P2 (High)** | < 30 Minutes | < 8 Hours |
| **P3 (Medium)** | < 2 Hours | < 3 Business Days |
| **P4 (Low)** | < 24 Hours | Best Effort |

### 4.1 Disaster Recovery (DR)
| Metric | Target | Description |
| :--- | :--- | :--- |
| **RTO (Recovery Time Objective)** | < 4 Hours | Time to restore full system operation after a total failure. |
| **RPO (Recovery Point Objective)** | < 1 Hour | Maximum acceptable data loss (transactional/audit logs). |

## 5. Error Budget Framework

The error budget is the maximum amount of time the system can be unreliable before we stop feature development and focus solely on reliability.

### 5.1 Monthly Budget (99.9% Target)
- **Total Budget:** 43.8 Minutes / Month.
- **Consumption:**
  - Unplanned outages (MT5 disconnects, server crashes).
  - Failed deployments resulting in downtime.
  - Critical bugs that halt trading operations.

### 5.2 Policy Actions
- **Budget > 20% remaining:** Normal operations; feature development continues.
- **Budget < 20% remaining:** Warning; stability-focused tasks prioritized in the next sprint.
- **Budget Exhausted (0%):** Freeze all non-emergency features; task force assigned to root-cause analysis and system hardening.

## 6. Review & Evolution

These targets are reviewed quarterly by the Release Reliability & Governance lead (Jules03) to ensure they remain realistic and aligned with trading performance goals.
