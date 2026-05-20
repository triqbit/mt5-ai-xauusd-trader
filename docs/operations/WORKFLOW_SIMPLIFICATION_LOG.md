# ⚡ Workflow Simplification Log

This log identifies every point where the current repository workflow depends on manual waiting, judgment, or repetitive effort, and defines the automation required to eliminate human intervention while preserving enterprise safety.

---

### 1. Friction: Setup and Installation
**Current state:** Manual step-by-step installation following `SETUP_GUIDE.md` (30-45 mins). Frequent failures during TA-Lib C-library compilation and OS-specific dependency resolution.
**Proposed automation:** `One-command workflows`. Implement a `Dockerfile` and `docker-compose.yml` for a standardized "Development Container" that pre-installs all C-dependencies. Enhance `make init` to detect the environment and offer a containerized setup, eliminating "it works on my machine" friction.
**Implementation owner:** Jules01
**Risk level:** Low
**Estimated time saved:** 45 minutes per new environment

### 2. Friction: Configuration Validation
**Current state:** Manual verification of `.env` correctness. `make validate-config` only checks for presence of keys, not runtime connectivity or credential validity.
**Proposed automation:** `Acceptance contracts`. Implement `scripts/verify_connectivity.py` (integrated into `make validate-config`) as a pre-flight requirement. It must verify MT5 server reachability, credential validity, and MetaAPI synchronization status before allowing the bot to enter a RUNNING state.
**Implementation owner:** Jules02
**Risk level:** Low
**Estimated time saved:** 15 minutes per configuration change

### 3. Friction: Starting a Backtest
**Current state:** Manual CLI parameter input and manual comparison of results against historical baselines. Results are often lost in terminal scrollback.
**Proposed automation:** `One-command workflows`. Implement `make backtest-standard` that auto-archives results to `docs/research/backtests/` and automatically compares metrics (Sharpe, MaxDD) against a "Golden Metadata" baseline using `scripts/verify_backtest_audit.py`.
**Implementation owner:** Jules01
**Risk level:** Low
**Estimated time saved:** 20 minutes per backtest run

### 4. Friction: Running in Demo/Paper Mode
**Current state:** Manual selection of account credentials. High risk of accidental live execution with demo parameters if the wrong `.env` is loaded.
**Proposed automation:** `Acceptance contracts`. Implement a "Hardened Mode Gate" in `src/trading/mt5_connector.py`. The connector must query `account_info()` and verify the `trade_mode` (Demo vs Real) matches the `MODE` environment variable. If `MODE=demo` but the account is `REAL`, the bot must perform an emergency shutdown.
**Implementation owner:** Jules02
**Risk level:** Medium
**Estimated time saved:** 10 minutes per launch

### 5. Friction: Reviewing Model Performance
**Current state:** Fragmented review using `generate_research_report.py` and manual SQL queries. No unified view of signal attribution.
**Proposed automation:** `Self-service dashboards`. Fully automate `make report` to aggregate `TradeLogger` P&L, `ExecutionAnalytics`, and `SignalExplainer` traces into a single interactive HTML report served via a lightweight internal web server (FastAPI) at `localhost:8050`.
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 30 minutes per review

### 6. Friction: Deploying to Production
**Current state:** Manual checklist verification (`PREPROD_CHECKLIST.md`). Staging verification is performed manually by running the bot and watching logs.
**Proposed automation:** `Branch promotion logic`. Implement `.github/workflows/production-gate.yml` which requires 100% test pass, `make audit` pass, and successful execution of `scripts/smoke_test.py` (connecting to a dedicated Staging account) before allowing a merge to `main`.
**Implementation owner:** Jules03
**Risk level:** High
**Estimated time saved:** 60 minutes per release

### 7. Friction: Monitoring and Alerting
**Current state:** Manual polling of logs. Alerts via Telegram are informative but lack context for immediate action (e.g., "Drawdown alert" requires finding a laptop to stop the bot).
**Proposed automation:** `Self-service dashboards`. Implement "Interactive Alerts" in the Telegram Command Center (using `src/monitoring/telegram_gateway.py`), allowing operators to click callback buttons to "Halve Position Size", "Tighten Stops", or "Kill Current Symbol" directly from the alert message.
**Implementation owner:** Jules02
**Risk level:** Medium
**Estimated time saved:** 45 minutes per day

### 8. Friction: Incident Response
**Current state:** Manual terminal intervention required to close positions during high-stress incidents. Relies on the operator remembering the correct CLI flags.
**Proposed automation:** `One-command workflows`. Implement `make emergency-stop` (mapped to `scripts/emergency_flatten.py`) that immediately sends a high-priority "Close All" command to the MT5 API, bypasses all execution filters, and fences the account from further trading.
**Implementation owner:** Jules03
**Risk level:** High
**Estimated time saved:** 10 minutes of critical exposure time

### 9. Friction: Post-trade Analysis
**Current state:** Manual correlation of trades to market conditions. Qualitative alpha discovery is a manual brainstorming session.
**Proposed automation:** `Self-service dashboards`. Automate the "Trade Narrative Memory" where every trade in `TradeLogger` is automatically joined with `RegimeDetector` output and `EventIntelligence` (macro) data at the moment of entry, providing a "Post-Mortem" report for every trade.
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 60 minutes per trading session

### 10. Friction: Daily Operator Review
**Current state:** Fragmented review of performance logs, health status, and security audit logs (20-30 mins).
**Proposed automation:** `Templates`. Standardize `make daily-summary` to generate a "Daily Intelligence Briefing" in Markdown. This template should pre-populate with realized P&L, system health status, anomalous audit events, and a "Strategic Recommendation" generated from `src/core/decision_support.py`.
**Implementation owner:** Jules05
**Risk level:** Low
**Estimated time saved:** 20 minutes per day

### 11. Friction: History Harmonization (Disconnected Root Crisis)
**Current state:** Manual execution of `git replace` or complex cherry-picking to resolve non-ancestral history across feature branches.
**Proposed automation:** `Merge gates`. Implement a `scripts/verify_history_integrity.py` CI check that validates the presence of the global root commit (`e23adfa`) in the PR's lineage. Block merges that would further fragment the repository history.
**Implementation owner:** Jules05
**Risk level:** High
**Estimated time saved:** 120 minutes per merge conflict session

### 12. Friction: Risk Management API Alignment
**Current state:** Manual verification of `validate_signal()` signature across different branches. Drift often discovered only during integration testing.
**Proposed automation:** `Acceptance contracts`. Implement an "API Compatibility Test" in CI that uses `inspect` to verify that `RiskManager` implements the harmonized 8-layer signature before allowing merge.
**Implementation owner:** Jules05
**Risk level:** Medium
**Estimated time saved:** 45 minutes per integration session

### 13. Friction: PR Triage and Review
**Current state:** Manual labeling and categorization of PRs. High-risk changes (e.g., trading logic) are often buried under low-risk documentation updates, leading to review fatigue.
**Proposed automation:** `Merge gates`. Implement `.github/workflows/auto-merge-policy.yml` that automatically labels PRs based on file diffs (e.g., `Risk: High` for `src/trading/`). Block auto-merges for high-risk files and require explicit Jules05 approval for any core trading logic changes.
**Implementation owner:** Jules05
**Risk level:** Medium
**Estimated time saved:** 30 minutes per PR

### 14. Friction: Model Promotion to Production
**Current state:** Manual movement of model files from `models/trained/` to production paths and manual config updates. No formal verification that the candidate model is actually better than the current one.
**Proposed automation:** `Branch promotion logic`. Implement `scripts/promote_model.py` which validates a candidate model against "Golden Metadata" (e.g., Sharpe > Baseline). If successful, it auto-updates the production config and archives the old model, creating a verifiable audit trail.
**Implementation owner:** Jules05
**Risk level:** High
**Estimated time saved:** 60 minutes per model release

### 15. Friction: Log Sanitization & Secret Leaks
**Current state:** Manual review of log files to ensure no passwords or API keys are leaked. Frequent "panic" cleanups after accidentally committing plaintext secrets to CI logs.
**Proposed automation:** `Acceptance contracts`. Implement a `SecretMaskingProcessor` in `src/core/log_config.py` that automatically redacts any field annotated as `SecretStr` or `SecretBytes` in `TradingConfig`. Ensure `make lint` or a dedicated CI check (`pip-audit`) blocks any code that uses plain `print()` instead of the sanitized logger.
**Implementation owner:** Jules02
**Risk level:** Low
**Estimated time saved:** 15 minutes per security audit

---
*Generated by Jules05 — Repository Anti-Friction Strategy.*
