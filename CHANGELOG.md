# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Institutional Capital Allocation:** Implemented a multi-strategy budget management system with concentration limits and performance-based scaling in `src/trading/capital_allocator.py`.
- **Vectorized Backtesting v2:** Enhanced the walk-forward backtesting engine with vectorized trade execution and performance metrics in `src/research/hyperopt_walkforward.py`.
- **Market Regime Detection:** Statistical market state classifier for XAUUSD (Trending, Ranging, News Shock, etc.) in `src/models/regime_detector.py`.
- **Institutional Feature Engineering:** Scalable pipeline for 190+ technical indicators with multi-timeframe support in `src/core/feature_engineering.py`.
- **CI Quality Gates:** Mandatory Mypy type enforcement and Docker dependency harmonization for enterprise stability.
- **Versioning Policy:** Defined comprehensive SemVer criteria and automated release workflows in `docs/VERSIONING_POLICY.md`.
- **Automated Changelog:** Integrated conventional commit-based changelog updates in `.github/workflows/changelog.yml`.
- **Enterprise Contribution Governance:** Established comprehensive controls including `CODEOWNERS`, a robust PR template with quality gates, and structured issue forms for bugs, features, and security reports.
- **Contributor Workflow:** Formally defined role-based governance and mandatory quality gates (85% coverage) in `docs/CONTRIBUTING.md`.

### Changed
- Rebalanced the 6-layer execution filter in `src/trading/execution_filter.py` with refined trend angle thresholds.
- Standardized `BaseModel` and `Signal` interfaces across all institutional models.
- Enhanced release orchestration logic to automate version bumping and changelog transitions.

### Fixed
- Resolved critical import errors and synchronized CI dependencies across 18 files.
- Optimized rolling slope calculations and row access in benchmark adapters (2000x speedup).
- Dependency conflict in CI by updating `gymnasium` version constraint.
- Unused `Dict` imports in `src/models/lstm_model.py` and `src/models/ppo_agent.py`.

## [1.1.0-rc1] - 2024-05-02
### Added
- Refined the 6-layer execution filter in `src/trading/execution_filter.py` with EMA20 trend angle logic.
- Comprehensive unit test suite for execution filters in `tests/test_execution_filter.py`.
- Institutional-grade decision support system in `src/core/decision_support.py`.
- Aggregation of signal explainability, market regime, macro-risk status, and recent performance into a unified `DecisionPacket`.
- High-fidelity terminal reporting with `rich` dashboarding for operator oversight.
- Go/No-Go logic integrating execution filters, risk management, and macro event blocks.
- Comprehensive unit tests for decision support in `tests/test_decision_support.py`.
- Enhanced `JournalMiner` in `src/analytics/journal_mining.py` with multi-dimensional motif detection (volatility, confidence).
- Implemented `detect_pre_drawdown_motifs` for early warning pattern recognition.
- Added symbol-based concentration analysis to `find_profitable_patterns`.
- Integrated `cluster_frequency` tracking into `SignalMotif` to identify toxic signal combinations.
- Comprehensive unit tests for new journal mining capabilities in `tests/test_journal_mining.py`.
- Institutional-grade research reporting system in `src/research/reporting.py`.
- Automated report aggregation via `ResearchOrchestrator` integrating regimes, stress tests, benchmarks, and rare events.
- High-quality Jinja2 templates for Markdown and HTML research summaries.
- Enhanced journal mining with signal motif reporting and behavioral risk identification.
- Integrated rare event simulation metadata into standardized research reports.
- Enterprise-grade trade signal explainability and attribution system in `src/core/explainability.py`.
- Decomposition of signals into execution, model, regime, risk, and feature cluster contributions.
- Standardized signal direction mapping (0=HOLD, 1=BUY, 2=SELL) across the explainer.
- Robust handling of model confidence ties and dominant driver identification.
- Support for human-readable terminal formatting (via `rich`) and machine-readable metadata.
- Comprehensive unit tests for the explainability module in `tests/test_explainability.py`.
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
- High-impact macroeconomic event intelligence module in `src/data/event_intelligence.py`.
- Support for CPI, NFP, FOMC, rate decisions, and geopolitical risk windows.
- Event severity scoring and typed risk models using Pydantic.
- Pre-event risk windows and post-event cooldown logic for XAUUSD.
- Enterprise-safe fallback behavior for external event data feeds.
- Comprehensive unit tests for event intelligence in `tests/test_event_intelligence.py`.
- Institutional-grade rare event simulation framework in `src/research/rare_event_simulator.py`.
- Support for Flash Crashes, Liquidity Vacuums, Gold Gaps, Violent Reversals, and Market Dislocations.
- Statistical verification tests for synthetic black-swan scenario generation in `tests/test_rare_event_simulator.py`.
- Institutional-grade dynamic ensemble weighting engine in `src/models/dynamic_ensemble.py`.
- Stability controls for ensemble rebalancing including EMA decay, swing caps, and oscillation dampening.
- Regime-aware scoring heuristics for XAUUSD (Trending, News Shock, Mean Reversion, etc.).
- Integration of `DynamicEnsemble` into the core `EnsembleModel` in `src/models/ensemble.py`.
- Comprehensive unit tests for dynamic weighting and stability in `tests/test_dynamic_ensemble.py`.
- Institutional-grade execution quality analytics in `src/analytics/execution_quality.py`.
- Multi-horizon markout (drift) tracking (1m, 5m, 15m, 30m, 60m).
- Spread-relative sigmoid fill quality model.
- Execution cost tracking (slippage + half-spread).
- Automated timezone handling for accurate market data comparisons.
- Comprehensive unit tests for execution quality in `tests/test_execution_quality.py`.

### Changed
- Refactored release orchestration to integrate automated versioning logic.

### Fixed
- Dependency conflict in CI by updating `gymnasium` version constraint.
- Unused `Dict` imports in `src/models/lstm_model.py` and `src/models/ppo_agent.py`.

## [1.0.0] - 2024-05-24
### Added
- Initial enterprise-grade trading engine.
- MT5 integration and risk management framework.
- CI/CD pipelines for validation and security.
- Health check system and Prometheus metrics.
- Audit logging for traceability and compliance.
