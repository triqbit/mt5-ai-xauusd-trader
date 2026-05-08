# ⚡ Workflow Simplification Log

This log identifies every point where the current repository workflow depends on manual waiting, judgment, or repetitive effort, and defines the automation required to eliminate human intervention while preserving enterprise safety.

---

### Friction: Setup and Installation
**Current state:** Manual step-by-step installation following `SETUP_GUIDE.md` (30-45 mins). Multi-step directory creation and manual dependency installation across different operating systems.
**Proposed automation:** `One-command workflows`. Enhance `make init` and `scripts/bootstrap.sh` to handle full idempotent directory structure creation, automated dependency resolution for ARM/Linux/Windows, and local development certificate generation.
**Implementation owner:** Jules01
**Risk level:** Low
**Estimated time saved:** 30 minutes per new environment

### Friction: Configuration Validation
**Current state:** Manual verification of `.env` correctness. `make validate-config` only checks `.env.example` completeness, not runtime connectivity or secret validity.
**Proposed automation:** `Acceptance contracts`. Expand `scripts/validate_env.py` into a full pre-flight connectivity suite that verifies MT5 server reachability, MetaAPI token validity, and database write permissions before allowing the bot to initialize.
**Implementation owner:** Jules02
**Risk level:** Low
**Estimated time saved:** 15 minutes per configuration change

### Friction: Starting a Backtest
**Current state:** Manual CLI parameter input (`main.py --mode backtest...`). Results are printed to console or local files but require manual comparison against historical baselines.
**Proposed automation:** `One-command workflows`. Implement `make backtest-standard` (last 30d) and `make backtest-stress` (black-swan scenarios) that auto-archive results to a `backtest_registry` and automatically compare metrics against a "Golden Metadata" baseline.
**Implementation owner:** Jules01
**Risk level:** Low
**Estimated time saved:** 20 minutes per backtest run

### Friction: Running in Demo/Paper Mode
**Current state:** Manual selection of account credentials and CLI flags. High risk of human error when switching between Demo and Live accounts.
**Proposed automation:** `Acceptance contracts`. Implement a "Safety Check Gate" that queries the MT5 account type (DEMO vs REAL) and forces the bot to exit if the detected account type does not match the configured mode, unless an explicit override is provided.
**Implementation owner:** Jules02
**Risk level:** Medium (Safety)
**Estimated time saved:** 10 minutes per launch

### Friction: Reviewing Model Performance
**Current state:** Fragmented review using `generate_research_report.py` and manual SQL queries. Decision Cockpit exists but requires manual terminal access.
**Proposed automation:** `Self-service dashboards`. Fully automate `make report` to aggregate `TradeLogger` P&L, `RegimeDetector` confidence, and `ExecutionAnalytics` into a single interactive HTML/PDF report served via a lightweight internal web server.
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 30 minutes per review

### Friction: Deploying to Production
**Current state:** `DEPLOYMENT_GUIDE.md` references non-existent scripts (`pre_deployment_tests.sh`, `smoke_tests.sh`). Manual checklist verification takes 60+ minutes per release.
**Proposed automation:** `Branch promotion logic`. Implement `.github/workflows/production-gate.yml` which requires 100% test pass, 85% coverage, and successful execution of `scripts/smoke_test.py` in a staging environment before allowing a merge to `main`.
**Implementation owner:** Jules03
**Risk level:** High
**Estimated time saved:** 60 minutes per release

### Friction: Monitoring and Alerting
**Current state:** Manual polling of logs and TUI. Alerts via Telegram are informative but lack context for immediate action.
**Proposed automation:** `Self-service dashboards`. Implement "Actionable Alerts" in the Telegram Command Center, allowing the operator to click buttons to "Halve Position Size", "Tighten Stop Loss", or "Emergency Stop" directly from the alert message.
**Implementation owner:** Jules02
**Risk level:** Medium
**Estimated time saved:** 45 minutes per day

### Friction: Incident Response (Emergency Stop)
**Current state:** `make emergency-stop` is a placeholder. Manual terminal intervention or manual position closure in the MT5 terminal is required during high-stress incidents.
**Proposed automation:** `One-command workflows`. Implement a dedicated "Kill Switch" script that sends an interrupt signal to the running bot, immediately closes all open XAUUSD positions, cancels pending orders, and flushes the trade log to the database in < 3 seconds.
**Implementation owner:** Jules03
**Risk level:** High (Safety Critical)
**Estimated time saved:** 10 minutes of critical exposure time

### Friction: Post-Trade Analysis & Attribution
**Current state:** Manual correlation of trades to specific market conditions or feature values. `make analytics` is currently a reporting stub.
**Proposed automation:** `Self-service dashboards`. Automate the "Trade Narrative Memory" where every trade is automatically tagged with the active Regime, Macro Sensitivity score, and Model Confidence Heatmap at the exact moment of entry.
**Implementation owner:** Jules04
**Risk level:** Low
**Estimated time saved:** 60 minutes per trading session

### Friction: Daily Operator Review
**Current state:** Fragmented review of performance logs, health status, and security audit logs (20-30 mins).
**Proposed automation:** `Templates`. Standardize the `make daily-summary` command to generate a "Daily Intelligence Briefing" in Markdown, pre-populated with P&L, system health Gauges, and any anomalous audit events for quick sign-off.
**Implementation owner:** Jules05
**Risk level:** Low
**Estimated time saved:** 20 minutes per day

### Friction: PR Triage and Backlog Management
**Current state:** 400+ PRs in backlog. Manual triage is impossible due to history-grafting turbulence.
**Proposed automation:** `Merge gates that replace manual review`. Use `scripts/generate_triage_report.py` to auto-label PRs as `safe-surface`, `core-logic`, or `high-risk`. Jules05 will auto-approve and merge `safe-surface` PRs that pass all CI gates without human intervention.
**Implementation owner:** Jules05
**Risk level:** Medium
**Estimated time saved:** 120 minutes per day

### Friction: Secret Rotation
**Current state:** Manual 15-step procedure in `docs/runbooks/07-secret-rotation-procedure.md`. High risk of credential leakage or bot downtime.
**Proposed automation:** `One-command workflows`. Create `scripts/rotate_secrets.sh` that automates the revocation of MetaAPI tokens/AWS keys and automatically updates the GitHub Actions secrets via the GitHub CLI.
**Implementation owner:** Jules03
**Risk level:** Medium
**Estimated time saved:** 45 minutes per rotation

### Friction: History Graft Traceability
**Current state:** Frequent history grafting makes tracking the evolution of trading logic difficult. Manual file comparison across disjointed commit histories.
**Proposed automation:** `Self-service dashboards`. Implement a "Governance Audit Tool" that generates a unified diff-report for files in `src/trading` and `src/core/risk_engine.py` across the last 10 graft-points to preserve institutional memory.
**Implementation owner:** Jules05
**Risk level:** Medium
**Estimated time saved:** 30 minutes per audit

### Friction: Dependency Governance
**Current state:** Manual execution of `pip-audit` and `verify_dependencies.py`. New dependencies are often added without license or vulnerability checks.
**Proposed automation:** `Merge gates that replace manual review`. Integrate `pip-audit` and `license-check.yml` as blocking CI gates. Automated PR comments if a new package violates the MIT/Apache/BSD-only policy.
**Implementation owner:** Jules02
**Risk level:** Low
**Estimated time saved:** 15 minutes per dependency update

### Friction: Data Lifecycle and Log Rotation
**Current state:** Manual cleanup of `.log` and `.db` files when they exceed disk limits. `make clean` is destructive (deletes everything).
**Proposed automation:** `One-command workflows`. Implement `make archive-data` which performs intelligent log rotation, compresses historical SQLite databases, and uploads archives to long-term storage (S3/GCS) based on the `DATA_RETENTION_POLICY.md`.
**Implementation owner:** Jules01
**Risk level:** Low
**Estimated time saved:** 20 minutes per week

---
*Generated by Jules05 — Repository Anti-Friction Strategy.*
