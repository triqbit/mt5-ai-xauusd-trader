# Pre-Production Acceptance Checklist

This checklist must be fully completed and verified before any production release.

## 1. Automated Validation Gates
- [ ] **CI Pass**: All GitHub Actions workflows (CI, Security) must be green.
- [ ] **Test Coverage**: Minimum 80% line coverage across the `src/` directory.
- [ ] **Security Scan**: Trivy and pip-audit must show zero CRITICAL or HIGH vulnerabilities.
- [ ] **Linting**: Ruff lint and format checks must pass with zero violations.
- [ ] **Type Checking**: Mypy strict mode must pass for all core modules.

## 2. Environment Readiness
- [ ] **.env.example Sync**: `scripts/validate_env.py` must return SUCCESS.
- [ ] **Database Migrations**: All migrations must be tested for upgrade and downgrade compatibility.
- [ ] **Connectivity**: MT5 connectivity verified in Demo mode on the production-equivalent server.

## 3. Risk & Compliance
- [ ] **Risk Limits**: `src/trading/risk_manager.py` circuit breakers (15% drawdown) verified.
- [ ] **License Check**: All third-party dependencies must comply with the MIT/Apache/BSD license policy.
- [ ] **Audit Logging**: Verified that sensitive credentials are redacted in logs.

## 4. Operational Readiness
- [ ] **Backups**: Verified that the daily SQLite backup script is functional.
- [ ] **Monitoring**: Prometheus metrics endpoints are accessible and reporting health.
- [ ] **Runbooks**: Disaster recovery and incident response runbooks are up to date.

## 5. Release Approval
- [ ] **Changelog**: `CHANGELOG.md` updated with all changes since the last version.
- [ ] **Sign-off**: Release approved by the Technical Lead and Risk Manager.
