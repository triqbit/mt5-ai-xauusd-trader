# Pre-Production Deployment Gate Checklist

This document defines the mandatory formal gate checklist that must be successfully completed and verified before any production deployment of the MT5 AI/ML XAUUSD Trading Bot.

## Deployment Information
- **Release Version:** `vX.Y.Z`
- **Deployment Date:** `YYYY-MM-DD`
- **Primary Engineer:**
- **Approving Stakeholder:**

---

## 1. CI/CD & Technical Validation
- [ ] **All CI checks passing:** Verify that the latest build on the deployment branch has passed all automated workflows.
  - [ ] Linting (Ruff/Mypy) - *Reference: `ENTERPRISE_STANDARDS.md`*
  - [ ] Unit & Integration Tests (Pytest)
  - [ ] Coverage ≥ 80% (Mandatory for production)
  - [ ] Security scan clean (Trivy/Gitleaks/pip-audit) - *Reference: `SECURITY_FRAMEWORK.md`*

## 2. Configuration & Environment
- [ ] **Environment configuration validated:** All `.env` variables and `config.py` settings are verified for the production environment.
  - [ ] `CONFIRM_LIVE_TRADING="YES"` set (if applicable)
  - [ ] API keys and MT5 credentials securely stored
- [ ] **Database state verified:** All migrations are applied and verified. - *Reference: `DATABASE_STANDARDS.md`*

## 3. Strategy & Performance
- [ ] **Backtest results reviewed and acceptable:** Recent backtest results for the model version being deployed have been reviewed and meet performance targets.
- [ ] **Risk limits aligned:** Verify that risk parameters in the configuration match authorized limits. - *Reference: `RISK_LIMITS.md` / `TRADING_STANDARDS.md`*

## 4. Operational Readiness
- [ ] **Staging health checks passing:** Verify that all health endpoints (`/health/liveness`, `/health/readiness`) are returning success in the staging environment.
- [ ] **Monitoring & Alerting functional:** Confirm that Prometheus metrics are being scraped and Telegram alerts are functional for critical severities. - *Reference: `MONITORING_ALERTING.md`*
- [ ] **Rollback plan documented and tested:** A clear rollback procedure is in place and has been verified. - *Reference: `DEPLOYMENT_GUIDE.md`*

## 5. Governance & Documentation
- [ ] **Release notes prepared and reviewed:** Comprehensive release notes (features, fixes, breaking changes) are ready.
- [ ] **No open critical/high-severity bugs:** All P0 and P1 issues related to this release are resolved.
- [ ] **Documentation updated:** README, Runbooks, and API documentation reflect the changes in this release.
- [ ] **Stakeholder sign-off obtained:** Explicit approval from the lead engineer or product owner is recorded.

---

## Final Verification
*I, the undersigned, certify that all items above have been verified according to enterprise standards.*

**Signature:** __________________________  **Date:** __________

---

### Related Documentation
- [Deployment Guide](../DEPLOYMENT_GUIDE.md)
- [Enterprise Standards](../ENTERPRISE_STANDARDS.md)
- [Trading Standards](../TRADING_STANDARDS.md)
- [Security Framework](../SECURITY_FRAMEWORK.md)
