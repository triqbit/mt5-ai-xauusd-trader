# Workflow Simplification Log

This document maps repository workflow friction points and defines the automation strategy to eliminate manual intervention, judgment calls, and repetitive review effort. This is the authoritative roadmap for achieving operational autonomy.

---

## 🛠️ Operational Friction & Automation Map

### Friction: Setup and Installation
**Current state:** Manual step-by-step installation of Python dependencies and OS-level libraries (TA-Lib). Dependency conflicts often caught only after installation.
**Proposed automation:** **One-command workflow**: `make setup` command that performs:
1. OS detection and TA-Lib source compilation (if missing).
2. Environment shim validation (ensuring correct Python version and architecture).
3. Dependency conflict audit using `pip-compile` logic before installation.
**Implementation owner:** Jules01
**Risk level:** Low
**Estimated time saved:** 15 minutes per developer/environment setup.

### Friction: Configuration Validation
**Current state:** Manual `.env` creation from `.env.example`. Missing or invalid variables cause runtime crashes. Manual inspection of `main.py` output to confirm connectivity.
**Proposed automation:** **Acceptance Contract**: Mandatory `python main.py --check-config` gate.
1. Pydantic-based schema validation of all secrets and parameters.
2. Connectivity "dry-run" to MT5, Database, and Telegram API.
3. Integration into `.pre-commit-config.yaml` to prevent commits with broken local config templates.
**Implementation owner:** Jules02
**Risk level:** Low
**Estimated time saved:** 10 minutes per configuration change.

### Friction: Starting a Backtest
**Current state:** Multiple entry points; data ingestion requires manual CSV placement or MT5 export. Parameters are often hardcoded in research scripts.
**Proposed automation:** **One-command workflow**: `python main.py --mode backtest --config backtest_params.yaml`.
1. Automated data sync from MT5/S3 for the specified date range.
2. Parallelized execution using `vectorized_backtester`.
3. Auto-generation of an "Insights Report" (PDF) comparing results to the production baseline.
**Implementation owner:** Jules04
**Risk level:** Medium
**Estimated time saved:** 30 minutes per backtest run.

### Friction: Running in Demo/Paper Mode
**Current state:** Manual coordination of MT5 terminal settings and bot flags. Verification of "safe" execution relies on human observation of logs.
**Proposed automation:** **Branch Promotion Logic**: Automated "Demo-Gate" via `docker-compose --profile demo`.
1. Feature branches are deployed to a persistent Demo environment upon passing CI.
2. **Deterministic Gate**: Must complete 24 hours of error-free execution with at least 5 trades satisfying the "Signal Fidelity" contract before being eligible for Staging.
**Implementation owner:** Jules01
**Risk level:** Medium
**Estimated time saved:** 20 minutes per feature promotion.

### Friction: Reviewing Model Performance
**Current state:** Operators must tail logs or run manual SQL queries against `trades.db` to check P&L, Sharpe Ratio, or model confidence.
**Proposed automation:** **Self-service Dashboard**: Integrated TUI (via `rich`) and Web UI (via `streamlit`).
1. Real-time visualization of Equity Curve, Drawdown, and Regime Detection state.
2. Automated Slack/Telegram "Performance Pulse" every 4 hours.
3. Eliminates manual "How's the bot doing?" status requests.
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 15 minutes per review cycle.

### Friction: Deploying to Production
**Current state:** Manual execution of a 20+ point checklist. Requires judgment on whether "Staging looks good enough."
**Proposed automation:** **Deterministic Promotion**: GitHub Actions `release.yml` with Blue/Green deployment.
1. **Health Gate**: Automatic promotion from Staging to Production if the system maintains `HEALTHY` status for 48 hours without a single `CRITICAL` alert.
2. Rollback is triggered automatically if `MAX_DAILY_LOSS` is breached within the first 4 hours of deployment.
**Implementation owner:** Jules03
**Risk level:** High
**Estimated time saved:** 60 minutes per release.

### Friction: Monitoring and Alerting
**Current state:** Alerts are manually configured in Telegram. Thresholds are subjective and often lead to "alert fatigue" or missed events.
**Proposed automation:** **Merge Gate**: The CI pipeline (`.github/workflows/ci.yml`) will block any PR modifying `src/trading/` or `src/core/risk_engine.py` if it does not include an updated `alerts_threshold.json` or a corresponding test case for a new risk event.
**Implementation owner:** Jules02
**Risk level:** Medium
**Estimated time saved:** 45 minutes per new feature integration.

### Friction: Incident Response
**Current state:** Manual intervention via SSH or terminal. Requires human judgment to decide if a drawdown is "normal" or an "incident."
**Proposed automation:** **One-command workflow**: Automated Kill-switch and Telegram Remote Control.
1. Telegram commands `/panic`, `/halt`, `/status` provide instant mobile-first control.
2. **Circuit Breaker**: Logic in `RiskManager` that automatically enters `READ_ONLY` mode if the connection latency exceeds 500ms for 5 consecutive polls.
**Implementation owner:** Jules03
**Risk level:** High
**Estimated time saved:** 20 minutes per incident.

### Friction: Post-Trade Analysis
**Current state:** Manual export of trade logs to spreadsheets for "Why did we take this trade?" analysis.
**Proposed automation:** **Acceptance Contract**: Automated "Trade Attribution Report."
1. Every trade closing triggers a background task that calculates "Alpha Attribution" (Regime state, Model confidence, Sentiment score at entry).
2. Weekly "Journal PDF" is compiled automatically and sent to the core team, replacing manual journaling.
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 30 minutes per week.

### Friction: Daily Operator Review
**Current state:** Repetitive manual checks of system health, risk exposure, and market context before the trading day begins.
**Proposed automation:** **Decision Support Template**: "Pre-Trade Intelligence Briefing."
1. Sent via Telegram 15 minutes before market open.
2. Includes: System Health status, Current Market Regime (e.g., "Trending High Vol"), Risk Limit utilization, and "What-If" scenario warnings.
3. Reduces daily review to a single "Confirm/Acknowledge" button.
**Implementation owner:** Jules05
**Risk level:** Low
**Estimated time saved:** 20 minutes per day.

---

## 📜 Deterministic Acceptance Contracts

To replace manual "judgment calls," every PR must satisfy these objective contracts before Jules05 authorizes a merge:

1. **Safety Contract**: No PR shall increase `MAX_DAILY_LOSS` or `RISK_PER_TRADE` above system defaults without an attached `STRESS_TEST_REPORT` showing survival in 2008/2020-style volatility.
2. **Performance Contract**: AI model updates must demonstrate a >5% improvement in Sharpe Ratio OR a >10% reduction in Max Drawdown over a 5-year backtest vs. the current Production benchmark.
3. **Observability Contract**: Every new trading sub-module MUST implement the `HealthCheckInterface` and provide at least two custom Prometheus/TUI metrics.

## 🚀 Branch Promotion Strategy (Deterministic)

| From | To | Condition (Zero-Human Intervention) |
| :--- | :--- | :--- |
| `feature/*` | `develop` | CI Pass + Linter Pass + 80% Coverage. |
| `develop` | `demo` | Successful `make setup` in clean Docker env + 0 Critical Security Vulnerabilities. |
| `demo` | `staging` | 24h error-free execution + 5 successful trades + Signal Fidelity > 0.8. |
| `staging` | `main` (Prod) | 48h error-free execution + Health Gate "Green" + SLO Compliance > 99.9%. |
