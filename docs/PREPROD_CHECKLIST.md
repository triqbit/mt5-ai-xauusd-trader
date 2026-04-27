# Pre-Production Deployment Checklist

This checklist must be completed and signed off before any code is deployed to the production environment. Its purpose is to ensure the stability, security, and reliability of the MT5 AI/ML Trading Bot.

## 🚀 Release Information
- **Version:** `vX.Y.Z`
- **Deployment Date:** `YYYY-MM-DD`
- **Lead Engineer:** ____________________

---

## ✅ Quality & Security Gates
- [ ] **CI Pipeline Passing:** All GitHub Actions (linting, type checking, security audits) must be green.
- [ ] **Unit & Integration Tests:** 100% pass rate across the entire test suite.
- [ ] **Code Coverage:** Minimum coverage of **80%** (verified via `pytest-cov`).
- [ ] **Security Scan:** Clean report from `pip-audit` and `trivy` (no critical or high-severity vulnerabilities).
- [ ] **Dependency Audit:** All dependencies are pinned and verified for license compliance.

## ⚙️ Environment & Configuration
- [ ] **Environment Validation:** `.env` variables verified against `src/core/config.py` schema.
- [ ] **MT5 Connectivity:** Successful connection to the broker's demo/staging server.
- [ ] **Database Readiness:** All migrations applied and verified for reversibility.
- [ ] **Staging Smoke Test:** Application starts and completes a health check in the staging environment.

## 📊 Backtest & Model Review
- [ ] **Performance Review:** Backtest results for the release candidate meet the target metrics (Sharpe Ratio, Max Drawdown).
- [ ] **Walk-Forward Validation:** Model performance is consistent across unseen data periods.
- [ ] **Risk Limits:** Circuit breakers and drawdown limits are correctly configured for the target capital.

## 🛠️ Operational Readiness
- [ ] **Monitoring & Alerting:** Grafana/Prometheus dashboards are functional and alerting rules are active.
- [ ] **Health Checks:** Liveness and readiness probes are verified functional.
- [ ] **Rollback Plan:** Step-by-step rollback procedure is documented and has been tested in staging.
- [ ] **Runbooks:** Operations runbooks for incident response are updated and available.

## 📝 Documentation & Communication
- [ ] **Release Notes:** `CHANGELOG.md` updated with new features, fixes, and breaking changes.
- [ ] **Project Docs:** README.md, API docs, and internal documentation are current.
- [ ] **Known Issues:** No open critical or high-severity bugs in the issue tracker.
- [ ] **Stakeholder Sign-off:** Final approval obtained from trading and technical leadership.

---

## ✍️ Final Approval
- **Technical Lead:** ____________________ Date: __________
- **Risk/Trading Lead:** ____________________ Date: __________

> **Note:** This document must be archived with the release artifacts for audit purposes.
