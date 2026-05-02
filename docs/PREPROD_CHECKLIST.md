# Pre-Production Deployment Gate Checklist

This document defines the mandatory gates that must be satisfied and verified before any deployment to the production environment. No production push is permitted without explicit completion of this checklist.

## 1. Automated Quality & Security Gates
- [ ] **CI Pipeline Status:** All CI checks (linting, type checking) are passing, and all **unit tests pass** with a minimum of 80% statement coverage.
- [ ] **Security Scans:** **Security scan** (pip-audit) and container scans (Trivy) are clean, with zero unresolved High or Critical vulnerabilities.

## 2. Configuration & Environment Validation
- [ ] **Environment Validation:** Environment configuration is validated via `scripts/validate_env.py` and synchronized with `src/core/config.py`.
- [ ] **Risk Limits:** **Risk limits** (risk_per_trade ≤ 2%, max_daily_loss ≤ 15%) are confirmed and enforced.

## 3. Performance & Strategy Acceptance
- [ ] **Backtest Review:** Latest backtest results for the release candidate have been reviewed and meet acceptable trading benchmarks.

## 4. Staging & Infrastructure Verification
- [ ] **Staging Health:** Full health checks (`/health/readiness`) are passing in the staging/pre-prod environment.
- [ ] **Monitoring:** **Monitoring** and alerting systems (Prometheus, Telegram) are verified as functional and receiving telemetry data.

## 5. Deployment Safety & Recoverability
- [ ] **Rollback Plan:** A **Rollback plan** (per `docs/RELEASE_PLAYBOOK.md`) has been documented, tested, and verified.
- [ ] **Database Reversibility:** Schema migrations have been verified for reversibility via `scripts/verify_migrations.py`.

## 6. Release Governance & Documentation
- [ ] **Release Notes:** `CHANGELOG.md` is updated, and release notes for the new version are prepared and reviewed.
- [ ] **Bug Audit:** There are zero open critical or high-severity bugs impacting the release candidate.
- [ ] **Documentation Update:** `README.md`, operational runbooks (docs/runbooks/), and API documentation are updated.
- [ ] **Stakeholder Sign-off:** Final formal stakeholder sign-off obtained from the Trading and DevOps leads.

---
*Completed by:* ____________________
*Date:* ____________________
*Release Version:* ____________________
