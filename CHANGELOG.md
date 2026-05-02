# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Typed exception hierarchy in `src/core/exceptions.py` for domain-specific error handling.
- Robust `@with_retry` decorator in `src/core/retry.py` with exponential backoff and jitter.
- Actionable diagnostic guide in `main.py` for MT5 connection failures at startup.
- Enterprise-grade monitoring and alerting system in `src/core/monitor.py` with Prometheus integration and Telegram bot support.
- Disciplined walk-forward optimization framework in `src/research/hyperopt_walkforward.py` with Optuna integration.
- Robustness scoring logic (Sharpe consistency, MDD preservation, parameter stability).
- Rolling and expanding window support for out-of-sample validation.
- Comprehensive unit tests for walk-forward research in `tests/test_hyperopt_walkforward.py`.
- Enterprise-grade health check system in `src/core/health.py`.
- Mandatory startup health gate in `main.py` to prevent execution in invalid states.
- FastAPI-compatible health endpoints for production monitoring.
- Comprehensive unit and integration tests for the health check framework.
- Semantic versioning policy (`docs/VERSIONING_POLICY.md`).
- Automated changelog generation workflow (`.github/workflows/changelog.yml`).
- Initial `CHANGELOG.md` template.

### Changed
- Hardened `MT5Connector` in `src/trading/mt5_connector.py` with typed exceptions and retry logic.
- Improved `main.py` trading loop with structured recovery paths (e.g., active reconnection).
- Refactored release orchestration to integrate automated versioning logic.

## [1.0.0] - 2024-05-24
### Added
- Initial enterprise-grade trading engine.
- MT5 integration and risk management framework.
- CI/CD pipelines for validation and security.
