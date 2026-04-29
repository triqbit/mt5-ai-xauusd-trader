# Pre-Production Deployment Checklist

This document defines the formal gate checklist that must be completed and verified before any deployment to the production environment. No production push should occur without explicit confirmation of every item below.

## 1. CI/CD & Quality Gates
- [ ] **All CI checks passing**: Verified that the latest build on the deployment branch has passed all automated checks.
- [ ] **Linting**: No linting errors or formatting violations (Ruff/Mypy).
- [ ] **Testing**: All unit and integration tests passing.
- [ ] **Code Coverage**: Minimum 80% test coverage maintained or exceeded.
- [ ] **Security Scan**: Dependency audit (pip-audit) and security scans (Gitleaks, Trivy) are clean with no critical or high-severity vulnerabilities.

## 2. Environment & Configuration
- [ ] **Environment Configuration**: All environment variables for production are validated and synchronized with `TradingConfig`.
- [ ] **Secrets Management**: Production secrets are securely stored and verified (not hardcoded).
- [ ] **Health Checks**: Readiness and liveness probes are passing in the staging environment.

## 3. Performance & Strategy Validation
- [ ] **Backtest Results**: Latest model backtest results have been reviewed by the quant team and meet acceptance criteria.
- [ ] **Resource Limits**: CPU and memory limits are appropriately configured for the production workload.

## 4. Operational Readiness
- [ ] **Monitoring & Alerting**: Monitoring dashboards are active, and alerting channels (e.g., Telegram) are verified functional.
- [ ] **Rollback Plan**: A specific rollback plan for this release is documented and has been tested in staging.
- [ ] **Documentation**: README, operational runbooks, and API documentation are updated to reflect changes in this release.
- [ ] **Bug Status**: No open critical or high-severity bugs are present in the release candidate.

## 5. Release Management
- [ ] **Release Notes**: Formal release notes have been prepared, reviewed, and included in the repository.
- [ ] **Stakeholder Sign-off**: Final approval for deployment has been obtained from all relevant stakeholders (Product, Engineering, Risk).

---
**Deployment Authorization:**
*Date:* ____________________
*Authorized By:* ____________________
