# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Standardized startup UX in `main.py` using `rich.Table` for configuration validation and health reporting.
- Standardized `BaseModel` interface and `Signal` output format in `src/models/base_model.py`.
- Production-ready stubs for `PPOAgent`, `LSTMModel`, and `DreamerAgent` in `src/models/`.
- Gymnasium-compatible `TradingEnv` skeleton for XAUUSD in `src/trading/trading_env.py`.
- Comprehensive unit tests for model stubs and environment interface in `tests/test_models_stubs.py`.
- Enterprise-grade feature engineering pipeline in `src/core/feature_engineering.py`.
- Support for 190+ technical indicators, multi-timeframe analysis (M1-D1), and candle patterns.
- Volume profile features (Rolling VWAP, VPT, OBV).
- Vectorized rolling slope calculation for high-performance feature extraction.
- Comprehensive unit tests in `tests/test_feature_engineering.py` using synthetic XAUUSD data.
- Cascading 6-layer execution filter in `src/trading/execution_filter.py` validating ATR, Trend Angle, EMA sequence, Momentum, Session time, and Drawdown.
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

### Changed
- Refactored release orchestration to integrate automated versioning logic.

### Fixed
- Dependency conflict in CI by updating `gymnasium` version constraint.

## [1.0.0] - 2024-05-24
### Added
- Initial enterprise-grade trading engine.
- MT5 integration and risk management framework.
- CI/CD pipelines for validation and security.
