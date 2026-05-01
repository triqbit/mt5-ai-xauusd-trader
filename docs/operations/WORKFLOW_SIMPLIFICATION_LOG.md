# Workflow Simplification Log

This document maps repository workflow friction points and defines the automation strategy to eliminate manual intervention and repetitive review effort.

---

## 🛠️ Operational Friction & Automation Map

### Friction: Setup and Installation
**Current state:** Manual step-by-step installation of Python dependencies and OS-level libraries (TA-Lib).
**Proposed automation:** **One-command workflow**: `make setup` command that detects OS, installs TA-Lib from source if missing, and initializes the virtual environment.
**Implementation owner:** Jules01
**Risk level:** Low
**Estimated time saved:** 15 minutes per occurrence

### Friction: Configuration Validation
**Current state:** Manual `.env` creation; validation only happens at runtime, potentially leading to mid-session crashes.
**Proposed automation:** **Acceptance Contract**: Implement `python main.py --check-config` that validates all Pydantic models, connectivity, and DB credentials. Integrated into a pre-commit hook to block commits with invalid local configurations.
**Implementation owner:** Jules02
**Risk level:** Low
**Estimated time saved:** 5 minutes per occurrence

### Friction: Starting a Backtest
**Current state:** Inconsistent entry points (referenced in `main.py` but missing `scripts/backtest.py`).
**Proposed automation:** **One-command workflow**: Unified `python main.py --mode backtest` command that handles historical data ingestion (XAUUSD M1-D1), execution, and automated PDF report generation.
**Implementation owner:** Jules04
**Risk level:** Medium
**Estimated time saved:** 20 minutes per occurrence

### Friction: Running in Demo/Paper Mode
**Current state:** Manual coordination of MT5 terminal settings and bot flags.
**Proposed automation:** **Branch Promotion Logic**: Docker-compose profiles (`docker-compose --profile demo up`) combined with a deterministic rule: a feature branch is automatically promoted to `demo-integration` status after passing CI, where it must run for 24 hours error-free before being eligible for staging.
**Implementation owner:** Jules01
**Risk level:** Medium
**Estimated time saved:** 15 minutes per occurrence

### Friction: Reviewing Model Performance
**Current state:** Requires manual database queries or log tailing.
**Proposed automation:** **Self-service Dashboard**: A Streamlit-based interface (`/dashboard`) that auto-refreshes P&L, Sharpe, and model confidence metrics, eliminating manual status requests.
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 10 minutes per occurrence

### Friction: Deploying to Production
**Current state:** Manual execution of a 20+ point checklist in `DEPLOYMENT_GUIDE.md`.
**Proposed automation:** **Deterministic Promotion**: GitHub Actions "Release" workflow that automates Blue/Green deployment. Promotion from `staging` to `main` is automated if the Health Gate passes continuously for 48 hours in the staging environment.
**Implementation owner:** Jules03
**Risk level:** High
**Estimated time saved:** 45 minutes per occurrence

### Friction: Monitoring and Alerting
**Current state:** Manual Telegram setup and threshold configuration.
**Proposed automation:** **Merge Gate**: Automated provisioning of Prometheus alerts via environment variables. The CI pipeline will block PRs touching `src/trading/` if they do not include an update to the corresponding `alerts.yml` or monitoring metadata.
**Implementation owner:** Jules02
**Risk level:** Medium
**Estimated time saved:** 30 minutes per occurrence

### Friction: Incident Response
**Current state:** Manual kill-switch execution requiring SSH or terminal access.
**Proposed automation:** **One-command workflow**: Telegram-based bot commands (e.g., `/halt_all`, `/close_positions`) for rapid, mobile-first emergency intervention.
**Implementation owner:** Jules03
**Risk level:** High
**Estimated time saved:** 15 minutes per incident

### Friction: Post-Trade Analysis
**Current state:** Manual export of trade logs to spreadsheets for analysis.
**Proposed automation:** **Acceptance Contract**: Automated "Session Recap" generation - an HTML/PDF report generated automatically when the bot is stopped. Mandatory attribution scores (>0.7) for every trade must be present for the session to be marked as "Valid."
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 20 minutes per trade session

### Friction: Daily Operator Review
**Current state:** Repetitive manual checks of system health, risk exposure, and P&L.
**Proposed automation:** **Decision Support Template**: "Pre-Trade Intelligence Briefing" - a consolidated summary of system health and market regime sent to the operator 15 minutes before market open, reducing decision paralysis.
**Implementation owner:** Jules05
**Risk level:** Low
**Estimated time saved:** 15 minutes per day

---

## 📜 Deterministic Acceptance Contracts

To replace manual "judgment calls," every major feature must satisfy the following objective contracts before merging:

1. **Safety Contract**: No PR shall increase `MAX_DAILY_LOSS` or `RISK_PER_TRADE` above system defaults without a `STRESS_TEST_REPORT` attached.
2. **Performance Contract**: AI model updates must demonstrate a >5% improvement in Sharpe Ratio or a >10% reduction in Max Drawdown over a 3-year backtest vs. the current production baseline.
3. **Observability Contract**: Every new trading sub-module must implement the `HealthCheckInterface` and provide at least two custom Prometheus metrics.

## 🚀 Branch Promotion Strategy

| From | To | Condition (Deterministic) |
| :--- | :--- | :--- |
| `feature/*` | `develop` | CI Pass + 1 Approved Review |
| `develop` | `demo` | 0 Critical Bugs + Successful `make setup` in clean Docker env |
| `demo` | `staging` | 24h error-free execution + 5 successful trades |
| `staging` | `main` (Prod) | 48h error-free execution + Health Gate Green |
