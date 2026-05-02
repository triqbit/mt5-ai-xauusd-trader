# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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

### Security
- **Hardened Configuration:** Sensitive fields (MT5 password, API tokens, database URLs) in `TradingConfig` migrated to `pydantic.SecretStr` to prevent accidental exposure.
- **Dependency Hardening:** Bumped `fastapi` to `0.115.8` and aligned `starlette` to resolve security vulnerabilities (GHSA-f96h-pmfr-66vw, GHSA-2c2j-9gv5-cj73).

### Changed
- Refactored release orchestration to integrate automated versioning logic.
- **Environment Standardization:** Standardized full project stack on Python 3.12 across CI pipelines, Docker builds, and metadata.
- **Dependency Hygiene:** Normalized version pins for `fastapi` and `python-telegram-bot` across all requirement files.
- **Cross-Platform Compatibility:** Added environment markers to `MetaTrader5` to fix dependency resolution on Linux systems.

## [1.0.0] - 2024-05-24
### Added
- Initial enterprise-grade trading engine.
- MT5 integration and risk management framework.
- CI/CD pipelines for validation and security.
