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
| **Test Coverage (Core)** | > 85% | `pytest-cov` statement coverage on `src/core/` and `src/trading/`. |
| **Static Analysis Compliance** | 100% | Zero critical/high issues from `ruff`, `mypy`, and `bandit` in PRs. |

## 3. Performance & Latency SLOs

Measured via `src/core/profiler.py` and exported to Prometheus.

| Metric | P50 | P95 | P99 | Measurement Method |
|--------|-----|-----|-----|-------------------|
| **Model Inference** | < 10ms | < 50ms | < 100ms | Time from feature vector input to PPO/Ensemble output. |
| **Risk Approval** | < 20ms | < 50ms | < 100ms | Time to pass through the 6-layer `RiskManager` cascade. |
| **End-to-End Latency** | < 100ms | < 500ms | < 1.5s | Market Event -> Inference -> Risk -> MT5 Order Execution. |
| **Backtest Generation** | < 5 min | < 8 min | < 12 min | Time to execute 1-year XAUUSD backtest (1M candles). |

## 4. Operational Reliability & Alerting

Response expectations for the Jules-led operations team, aligned with `docs/runbooks/06-monitoring-alert-triage.md`.

| Severity | Target Response | Target Resolution | Description |
|----------|-----------------|-------------------|-------------|
| **P0 (Critical)** | < 5 mins | < 1 hour | Trading halted, circuit breaker triggered, or critical balance mismatch. |
| **P1 (High)** | < 15 mins | < 4 hours | Degraded performance, broker connection lost, or database corruption. |
| **P2 (Medium)** | < 2 hours | < 24 hours | Non-blocking bugs, model drift detected, or high latency warnings. |
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
| **Availability** | 0.5% (3.6h) | ~3.6 hours of cumulative outage during market hours. |
| **CI Stability** | 5% | ~5 failed builds per 100 commits to protected branches. |
| **Trade Execution** | 0.1% | 1 failed order per 1,000 approved signals. |
| **Model Accuracy** | 5% Drift | Max 5% deviation from expected confidence thresholds. |
| **Data Integrity** | 0% | Zero unrecoverable data corruption events. |

### 6.1 Error Budget Calculation Formulas

| Metric | Formula |
|--------|---------|
| **Availability Budget** | `(Market Minutes * Error Budget %) / 100` |
| **CI Stability Budget** | `(Total Protected Commits * Error Budget %) / 100` |
| **Trade Execution Budget** | `(Total Approved Signals * Error Budget %) / 100` |

**Example (Availability):**
- Market minutes per month: ~20 days * 24h * 60m = 28,800 minutes.
- Error Budget (0.5%): `28,800 * 0.005 = 144 minutes` (~2.4 hours).
- If downtime exceeds 144 minutes in a rolling 30-day window, the budget is exhausted.

**Example (Trade Execution):**
- Total approved signals: 500 trades/month.
- Error Budget (0.1%): `500 * 0.001 = 0.5 trades` (Round down to 0).
- Effectively, zero execution failures are permitted for a 500-trade volume to stay within budget.

### 6.2 Stability Freeze Protocol
If any error budget is exhausted (reaches 0% remaining) within a 30-day window:
1. **Feature Freeze**: No new features or non-critical refactors allowed.
2. **Mandatory Reliability Sprint**: Next development cycle focused solely on SLO remediation.
3. **Post-Mortem Review**: Mandatory review with @andonly1348 to adjust risk limits or monitoring thresholds.

## 7. Monitoring & Governance
- **Automation:** Compliance is tracked via Prometheus metrics (`trading_latency_ms`, `health_check_status`).
- **Reporting:** Weekly reliability reports generated from Prometheus/Grafana.
- **Audit:** Any SLO breach requires a Blameless Post-Mortem and an update to the [Risk Manager](../src/trading/risk_manager.py) or [Circuit Breaker](../src/core/monitor.py) logic if applicable.
