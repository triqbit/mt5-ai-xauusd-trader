# Workflow Simplification Log

This document maps repository workflow friction points and defines the automation strategy to eliminate manual intervention.

---

### Friction: Setup and Installation
**Current state:** Manual step-by-step installation of Python dependencies and OS-level libraries (TA-Lib).
**Proposed automation:** `make setup` command or a specialized `setup.sh` that detects OS, installs TA-Lib from source if missing, and initializes the virtual environment.
**Implementation owner:** Jules01
**Risk level:** Low
**Estimated time saved:** 15 minutes per occurrence

### Friction: Configuration Validation
**Current state:** Manual `.env` creation; validation only happens at runtime, potentially leading to mid-session crashes.
**Proposed automation:** Implement `python main.py --check-config` that validates all Pydantic models, connectivity to MT5/MetaAPI, and DB credentials without starting the trading loop.
**Implementation owner:** Jules02
**Risk level:** Low
**Estimated time saved:** 5 minutes per occurrence

### Friction: Starting a Backtest
**Current state:** Inconsistent entry points (referenced in `main.py` but missing `scripts/backtest.py`).
**Proposed automation:** Unified `python main.py --mode backtest` command that handles historical data ingestion (XAUUSD M1-D1), execution, and automated PDF report generation.
**Implementation owner:** Jules04
**Risk level:** Medium
**Estimated time saved:** 20 minutes per occurrence

### Friction: Running in Demo/Paper Mode
**Current state:** Manual coordination of MT5 terminal settings and bot flags.
**Proposed automation:** Docker-compose profiles (`docker-compose --profile demo up`) that spin up a containerized MT5 environment (via Wine) and the bot in a single command.
**Implementation owner:** Jules01
**Risk level:** Medium
**Estimated time saved:** 15 minutes per occurrence

### Friction: Reviewing Model Performance
**Current state:** Requires manual database queries or log tailing.
**Proposed automation:** A Streamlit-based self-service dashboard (`/dashboard`) that auto-refreshes P&L, Sharpe, and model confidence metrics.
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 10 minutes per occurrence

### Friction: Deploying to Production
**Current state:** Manual execution of a 20+ point checklist in `DEPLOYMENT_GUIDE.md`.
**Proposed automation:** GitHub Actions "Release" workflow that automates the Blue/Green deployment to Kubernetes after passing the mandatory "Health Gate."
**Implementation owner:** Jules03
**Risk level:** High
**Estimated time saved:** 45 minutes per occurrence

### Friction: Monitoring and Alerting
**Current state:** Manual Telegram setup and threshold configuration.
**Proposed automation:** Auto-provisioning of Prometheus alerts and Telegram webhooks via environment variables, ensuring every deployment is "monitored-by-default."
**Implementation owner:** Jules02
**Risk level:** Medium
**Estimated time saved:** 30 minutes per occurrence

### Friction: Incident Response
**Current state:** Manual kill-switch execution requiring SSH or terminal access.
**Proposed automation:** Telegram-based bot commands (e.g., `/halt_all`, `/close_positions`) for rapid, mobile-first emergency intervention.
**Implementation owner:** Jules03
**Risk level:** High
**Estimated time saved:** 15 minutes per incident

### Friction: Post-Trade Analysis
**Current state:** Manual export of trade logs to spreadsheets for analysis.
**Proposed automation:** Automated "Session Recap" generation - an HTML/PDF report generated automatically when the bot is stopped or at the end of the trading day.
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 20 minutes per trade session

### Friction: Daily Operator Review
**Current state:** Repetitive manual checks of system health, risk exposure, and P&L.
**Proposed automation:** "Pre-Trade Intelligence Briefing" - a consolidated summary of system health and market regime sent to the operator 15 minutes before market open.
**Implementation owner:** Jules05
**Risk level:** Low
**Estimated time saved:** 15 minutes per day
