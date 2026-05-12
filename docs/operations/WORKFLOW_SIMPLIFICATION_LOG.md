# ⚡ Workflow Simplification Log

This log identifies every point where the current repository workflow depends on manual waiting, judgment, or repetitive effort, and defines the automation required to eliminate human intervention while preserving enterprise safety.

---

### Friction: Setup and Installation (Environment Parity)
**Current state:** Manual step-by-step installation following `SETUP_GUIDE.md` (30-45 mins). Multi-step directory creation and manual dependency installation across different operating systems.
**Proposed automation:** `One-command workflows`. Enhance `make init` (mapped to `scripts/bootstrap.sh`) to perform idempotent environment setup: automated venv creation, OS-specific dependency resolution (ARM vs x86), and directory scaffolding (`data/`, `logs/`, `models/trained/`).
**Implementation owner:** Jules01
**Risk level:** Low
**Estimated time saved:** 30 minutes per new environment

### Friction: Configuration Validation (Runtime Connectivity)
**Current state:** Manual verification of `.env` correctness. `make validate-config` only checks for presence of keys in `.env.example`, not runtime connectivity or secret validity.
**Proposed automation:** `Acceptance contracts`. Implement `scripts/verify_connectivity.py` as a pre-flight requirement. It must verify MT5 server reachability, credential validity, and MetaAPI synchronization status before allowing the bot to enter a RUNNING state.
**Implementation owner:** Jules02
**Risk level:** Low
**Estimated time saved:** 15 minutes per configuration change

### Friction: Starting a Backtest (Data & Baseline Comparison)
**Current state:** Manual CLI parameter input and manual comparison of results against historical baselines.
**Proposed automation:** `One-command workflows`. Implement `make backtest-standard` that auto-archives results to `docs/research/backtests/` and automatically compares metrics (Sharpe, MaxDD) against a "Golden Metadata" baseline using `scripts/verify_backtest_audit.py`.
**Implementation owner:** Jules01
**Risk level:** Low
**Estimated time saved:** 20 minutes per backtest run

### Friction: Running in Demo/Paper Mode (Safety Gates)
**Current state:** Manual selection of account credentials. High risk of accidental live execution with demo parameters.
**Proposed automation:** `Acceptance contracts`. Implement a "Hardened Mode Gate" in `src/trading/mt5_connector.py`. The connector must query `account_info()` and verify the `trade_mode` (Demo vs Real) matches the `MODE` environment variable. If `MODE=demo` but the account is `REAL`, the bot must perform an emergency shutdown.
**Implementation owner:** Jules02
**Risk level:** Medium
**Estimated time saved:** 10 minutes per launch

### Friction: Reviewing Model Performance (Centralized Dashboard)
**Current state:** Fragmented review using `generate_research_report.py` and manual SQL queries.
**Proposed automation:** `Self-service dashboards`. Fully automate `make report` to aggregate `TradeLogger` P&L, `ExecutionAnalytics`, and `SignalExplainer` traces into a single interactive HTML report served via a lightweight internal web server (FastAPI).
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 30 minutes per review

### Friction: Deploying to Production (Smoke Testing & Promotion)
**Current state:** Manual checklist verification (`PREPROD_CHECKLIST.md`). Staging verification is performed manually.
**Proposed automation:** `Branch promotion logic`. Implement `.github/workflows/production-gate.yml` which requires 100% test pass, `make audit` pass, and successful execution of `scripts/smoke_test.py` in a staging environment before allowing a merge to `main`.
**Implementation owner:** Jules03
**Risk level:** High
**Estimated time saved:** 60 minutes per release

### Friction: Monitoring and Alerting (Actionable Control)
**Current state:** Manual polling of logs. Alerts via Telegram are informative but lack context for immediate action.
**Proposed automation:** `Self-service dashboards`. Implement "Interactive Alerts" in the Telegram Command Center (using `src/monitoring/telegram_gateway.py`), allowing operators to click callback buttons to "Halve Position Size" or "Kill Current Symbol" directly from the alert message.
**Implementation owner:** Jules02
**Risk level:** Medium
**Estimated time saved:** 45 minutes per day

### Friction: Incident Response (Flatten & Fence)
**Current state:** Manual terminal intervention required to close positions during high-stress incidents.
**Proposed automation:** `One-command workflows`. Implement `make emergency-stop` (mapped to `scripts/emergency_flatten.py`) that immediately sends a high-priority "Close All" command to the MT5 API, bypasses all execution filters, and logs the action to `src/core/audit_log.py` as an "Emergency Operator Intervention".
**Implementation owner:** Jules03
**Risk level:** High
**Estimated time saved:** 10 minutes of critical exposure time

### Friction: Post-Trade Analysis & Attribution (Narrative Tagging)
**Current state:** Manual correlation of trades to market conditions. Qualitative alpha discovery is a manual brainstorming session.
**Proposed automation:** `Self-service dashboards`. Automate the "Trade Narrative Memory" where every trade in `TradeLogger` is automatically joined with `RegimeDetector` output and `EventIntelligence` (macro) data at the moment of entry.
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 60 minutes per trading session

### Friction: Daily Operator Review (Intelligence Briefing)
**Current state:** Fragmented review of performance logs, health status, and security audit logs (20-30 mins).
**Proposed automation:** `Templates`. Standardize `make daily-summary` to generate a "Daily Intelligence Briefing" in Markdown. This template should pre-populate with realized P&L, system health status, anomalous audit events, and a "Strategic Recommendation" generated from `src/core/decision_support.py`.
**Implementation owner:** Jules05
**Risk level:** Low
**Estimated time saved:** 20 minutes per day

### Friction: Macro Intelligence Integration (Manual Data Sourcing)
**Current state:** Market regimes and macro events are manually monitored or updated via fragmented scripts.
**Proposed automation:** `One-command workflows`. Implement `make sync-macro` (mapped to `scripts/fetch_macro_data.py`) to automatically pull FRED and YFinance data into the local `data/` cache, updating `src/data/event_intelligence.py` for the trading loop.
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 15 minutes per session

### Friction: PR Triage and Backlog Management (Deterministic Merging)
**Current state:** High volume of PRs with complex history grafting. Manual triage is slow and error-prone.
**Proposed automation:** `Merge gates that replace manual review`. Implement `scripts/generate_triage_report.py` to auto-label PRs based on file impact and CI results. Jules05 will auto-approve and merge "Safe Surface" PRs that satisfy the `AUTO_MERGE_POLICY.md`.
**Implementation owner:** Jules05
**Risk level:** Medium
**Estimated time saved:** 120 minutes per day

### Friction: Governance & Audit Traceability (Disconnected Audit)
**Current state:** Frequent history grafting and disjointed commits make tracking the evolution of trading logic difficult.
**Proposed automation:** `Self-service dashboards`. Implement a "Governance Audit Tool" (`scripts/atlas_audit.py`) that generates a unified diff-report for critical files (`risk_manager.py`, `mt5_connector.py`) across the last 10 graft-points to preserve institutional memory.
**Implementation owner:** Jules05
**Risk level:** Medium
**Estimated time saved:** 30 minutes per audit

---
*Generated by Jules05 — Repository Anti-Friction Strategy.*
