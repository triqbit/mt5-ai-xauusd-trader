# Pre-Production Deployment Gate Checklist

This document defines the mandatory gates that must be satisfied and verified before any deployment to the production environment. No production push is permitted without explicit completion of this checklist.

## 1. Quality & Security Gates
- [ ] **CI Pipeline Status:** All CI checks (linting, type checking) are passing.
- [ ] **Automated Testing:** All unit and integration tests pass successfully.
- [ ] **Test Coverage:** Statement coverage is ≥ 80% (aligned with `docs/SLO_TARGETS.md`).
- [ ] **Security Scanning:** `pip-audit` and `Trivy` scans are clean with zero unresolved High or Critical vulnerabilities.

## 2. Configuration & Validation
- [ ] **Environment Validation:** Environment configuration is validated via `scripts/validate_env.py`.
- [ ] **Risk Compliance:** Hard risk limits are confirmed and enforced in the production config.

## 3. Strategy & Performance
- [ ] **Backtest Review:** Latest backtest results for the release candidate have been reviewed and meet acceptable benchmarks.

## 4. Staging & Infrastructure
- [ ] **Staging Verification:** Full health checks (`/health/readiness`) are passing in the staging environment.
- [ ] **Observability:** Monitoring and alerting (Prometheus, Telegram) are verified functional and receiving data.

## 5. Safety & Recoverability
- [ ] **Rollback Plan:** A version-specific rollback plan is documented and has been successfully tested.
- [ ] **Migration Reversibility:** Database migrations have been verified for safe downgrade via `scripts/verify_migrations.py`.

## 6. Governance & Documentation
- [ ] **Release Notes:** Version-specific release notes are prepared, reviewed, and finalized in `CHANGELOG.md`.
- [ ] **Bug Audit:** Zero open Critical or High-severity bugs impacting the release candidate.
- [ ] **Documentation:** `README.md`, `docs/runbooks/`, and API documentation are updated for the current release.
- [ ] **Stakeholder Sign-off:** Final formal sign-off obtained from Trading and DevOps leads.

---
**Verified By:** ____________________
**Date:** ____________________
**Release Version:** ____________________
**Status:** [ ] GO / [ ] NO-GO
