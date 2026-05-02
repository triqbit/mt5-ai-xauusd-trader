# Service Level Objectives (SLO) & Reliability Targets

This document defines the measurable reliability standards for the MT5 AI/ML Trading Bot repository and runtime system. These targets represent "Enterprise Quality" translated into trackable objectives.

## 1. Availability SLOs (Uptime)

Uptime is measured during active market hours (XAUUSD: Monday 00:00 - Friday 23:59 Server Time).

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **System Uptime (Live Mode)** | 99.5% | `/health/readiness` probe success rate via uptime monitor. |
| **API Availability** | 99.9% | Percentage of successful 200 OK responses on the FastAPI router. |
| **MT5 Connectivity** | 99.0% | Percentage of time `MT5Connector.is_initialized` is True during market hours. |

**Acceptable Downtime:** ~3.6 hours per 30-day rolling window.

## 2. CI/CD & Development SLOs

Ensuring high engineering standards and stable delivery pipelines.

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **CI Pipeline Success Rate** | 95.0% | Percentage of GitHub Action runs on `main` and `develop` that finish with "Success". |
| **Test Coverage (Core)** | > 80% | `pytest-cov` statement coverage on `src/core/` and `src/trading/`. |
| **Static Analysis Compliance** | 100% | Zero critical/high issues from `flake8`, `mypy`, and `bandit` in PRs. |

## 3. Performance & Latency SLOs

Measured via `src/core/profiler.py` and exported to Prometheus.

| Metric | P50 | P95 | P99 | Measurement Method |
|--------|-----|-----|-----|-------------------|
| **Model Inference** | < 100ms | < 250ms | < 500ms | Time from feature vector input to PPO/Ensemble output. |
| **Risk Approval** | < 50ms | < 150ms | < 300ms | Time to pass through the 6-layer `RiskManager` cascade. |
| **End-to-End Latency** | < 500ms | < 1.5s | < 3s | Market Event -> Inference -> Risk -> MT5 Order Execution. |
| **Backtest Generation** | < 5 min | < 8 min | < 12 min | Time to execute 1-year XAUUSD backtest (1M candles). |

## 4. Operational Reliability & Alerting

Response expectations for the Jules-led operations team.

| Severity | Target Response | Target Resolution | Description |
|----------|-----------------|-------------------|-------------|
| **P0 (Critical)** | < 5 mins | < 1 hour | Trading halted, connection lost, or critical balance mismatch. |
| **P1 (High)** | < 15 mins | < 4 hours | Degraded performance, model drift, or partial service failure. |
| **P2 (Medium)** | < 2 hours | < 24 hours | Non-blocking bugs, UI/monitoring issues, or disk warnings. |
| **P3 (Low)** | < 24 hours | 1 Week | Documentation updates, minor refactors, or feature requests. |

## 5. Incident Recovery (RTO/RPO)

Defined in [Disaster Recovery Plan](DISASTER_RECOVERY.md).

| Metric | Target | Description |
|--------|--------|-------------|
| **Recovery Time (RTO)** | 15 mins | Maximum time to restore service after a system/process failure. |
| **Recovery Point (RPO)** | 1 hour | Maximum data loss allowed (governed by hourly database backups). |

## 6. Error Budget Framework (30-Day Rolling Window)

The error budget is the acceptable amount of failure. Exceeding these triggers a "Stability Freeze" where feature work stops to address technical debt.

| Component | Error Budget | "Acceptable" Failures per Month (approx) |
|-----------|--------------|-----------------------------------------|
| **Availability** | 0.5% (3.6h) | ~3-4 hours of cumulative outage. |
| **CI Stability** | 5% | ~5 failed builds per 100 commits to protected branches. |
| **Trade Execution** | 0.1% | 1 failed order per 1,000 approved signals. |
| **Model Accuracy** | 5% Drift | Max 5% deviation from expected confidence thresholds. |
| **Data Integrity** | 0% | Zero unrecoverable data corruption events. |

## 7. Monitoring & Governance
- **Automation:** Compliance is tracked via Prometheus metrics (`trading_latency_ms`, `health_check_status`).
- **Reporting:** Weekly reliability reports generated from Prometheus/Grafana.
- **Audit:** Any SLO breach requires a Blameless Post-Mortem and an update to the [Risk Manager](../src/trading/risk_manager.py) or [Circuit Breaker](../src/core/monitor.py) logic if applicable.
