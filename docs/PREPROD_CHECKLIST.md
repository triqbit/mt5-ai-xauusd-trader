# Pre-Production Deployment Gate Checklist

This document defines the mandatory gates that must be satisfied and verified before any deployment to the production environment. No production push is permitted without explicit completion of this checklist.

## 1. Automated Quality & Security Gates
- [ ] **CI Pipeline Status:** All CI checks (linting, type checking) are passing on the target branch.
- [ ] **Testing & Coverage:** All unit tests pass with a minimum of 80% statement coverage.
- [ ] **Security Scans:** Dependency audits (pip-audit) and container scans (Trivy) are clean, with zero unresolved High or Critical vulnerabilities.

## 2. Configuration & Environment Validation
- [ ] **Environment Sync:** `.env.example` is synchronized with `src/core/config.py`.
- [ ] **Variable Validation:** All production environment variables are validated via `scripts/validate_env.py`.
- [ ] **MT5 Connectivity:** Connectivity to the production MT5 server and login credentials have been verified.
- [ ] **Risk Limits:** Safe startup thresholds for risk (risk_per_trade <= 2%, max_daily_loss <= 15%) are confirmed in config.

## 3. Performance & Strategy Acceptance
- [ ] **Backtest Review:** Latest backtest results for the release candidate have been reviewed.
- [ ] **Benchmark Compliance:** Performance metrics (Sharpe ratio, Max Drawdown) meet the minimum established trading benchmarks.

## 4. Staging & Infrastructure Verification
- [ ] **Staging Health:** Full health check (`/health/readiness`) is passing in the staging/pre-prod environment and correctly reflects component status.
- [ ] **Monitoring:** Telemetry, Prometheus metrics, and Telegram alerting are verified as active and receiving data.
- [ ] **Alerting Thresholds:** Critical alert thresholds are confirmed and functional.

## 5. Deployment Safety & Recoverability
- [ ] **Rollback Plan:** A documented rollback procedure (per `docs/RELEASE_PLAYBOOK.md`) has been tested and verified.
- [ ] **Database Reversibility:** Any schema migrations have been verified for reversibility via `scripts/verify_migrations.py`.

## 6. Release Governance & Documentation
- [ ] **Release Notes:** `CHANGELOG.md` is updated, and release notes for the new version are prepared and reviewed.
- [ ] **Documentation Audit:** `README.md`, `docs/runbooks/`, and API documentation are updated to reflect the new version's changes.
- [ ] **Bug Status:** There are zero open Critical or High-severity bugs impacting the release candidate.
- [ ] **Stakeholder Sign-off:** Final approval for deployment has been obtained from the Stakeholders (Trading Lead & DevOps Lead).

---
*Completed by:* ____________________
*Date:* ____________________
*Release Version:* ____________________
