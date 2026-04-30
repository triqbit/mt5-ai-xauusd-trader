# Pre-Production Acceptance Checklist

This checklist must be completed and validated before any release to the production environment.

## 1. Automated Validation (CI/CD)
- [ ] All unit tests pass with >80% coverage.
- [ ] All integration tests pass.
- [ ] Linting (Ruff) and Type Checking (Mypy) pass.
- [ ] Security scan (pip-audit) shows zero high/critical vulnerabilities.
- [ ] Docker image builds successfully and passes vulnerability scanning.

## 2. Environment & Configuration
- [ ] .env.example is up to date with all required variables.
- [ ] Environment variables for production are verified and ready.
- [ ] Database migration scripts are verified (up/down/up).
- [ ] MT5 Terminal path and connection settings are verified for target environment.

## 3. Risk & Compliance
- [ ] Risk limits (Max positions, Daily loss, etc.) are verified.
- [ ] Circuit breaker logic is tested and functional.
- [ ] Trade logging and audit trails are functional.
- [ ] License compliance check passes.

## 4. Operational Readiness
- [ ] Monitoring and alerting (Telegram/Prometheus) are verified.
- [ ] Rollback plan is documented and tested.
- [ ] Health checks (Health Gate) pass for the release artifact.
- [ ] Release notes and changelog are generated.

## 5. Performance Benchmarks
- [ ] Backtest results meet the minimum Sharpe ratio and Drawdown criteria.
- [ ] Latency for risk approval and execution is within acceptable limits.
