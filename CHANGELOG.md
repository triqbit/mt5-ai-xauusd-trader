# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0-rc4] - 2026-05-05

### Added
- **Docker Multi-Stage Infrastructure:** Refactored `Dockerfile` into a multi-stage build system for smaller, more secure, and multi-arch production images.
- **Institutional Risk Engine:** Comprehensive risk management system featuring ATR-based position sizing, cascading daily loss circuit breakers (Level 1-4), and hard drawdown safeguards in `src/trading/risk_engine.py`.
- **Audited Risk Management:** Introduced `AuditedRiskManager` and a dedicated `RiskEngine` to separate risk calculation logic from execution management.
- **Production-Ready Model Stubs:** Enhanced `PPOAgent`, `LSTMModel`, and `DreamerAgent` with robust interfaces, probability extraction, and architecture switching.
- **Improved Trading Environment:** Refined `TradingEnv` with institutional reward skeleton and Gymnasium 1.0 compatibility fixes.
- **Enterprise Core Configuration:** Implemented Pydantic Settings V2 based configuration system with robust environment variable mapping and risk parameter validation in `src/core/config.py`.
- **Hybrid MT5 Connector:** Dual-path connection architecture supporting native Windows MT5 SDK and MetaAPI cloud failover for cross-platform reliability in `src/trading/mt5_connector.py`.
- **Ensemble Consensus Layer:** Weighted signal aggregation engine with model dissent checks and institutional confidence thresholds in `src/models/ensemble.py`.
- **Institutional Capital Allocation:** Enhanced `CapitalAllocator` with portfolio heat tracking, symbol/family concentration limits, linear 'Diversification Guard' scaling, and performance-based cooling-off periods in `src/trading/capital_allocator.py`.
- **Robustness Scoring:** Integrated Sharpe consistency and MDD preservation scoring into the walk-forward optimization framework in `src/research/hyperopt_walkforward.py`.

### Changed
- **9-Layer Execution Filter (Finalized):** Standardized the entry filter cascade to include 9 distinct validation layers (ATR, Trend, EMA, Momentum, Session, Drawdown, Stability, Performance, Confidence).
- **Temporal Standardization:** All temporal markers across the `src/` directory now use `datetime.now(timezone.utc)`.
- **Core Type Consolidation:** Centralized core data structures (e.g. `TradeSignal`, `ExecutionDecision`) to resolve circular dependencies and improve systemic coherence.
- Refactored `EnsembleModel` to support weighted voting across PPO, Dreamer, and LSTM models with dynamic weight adaptation.
- Standardized `MT5Connector.place_order` signature to accept `TradeSignal` objects.

### Fixed
- **Technical Debt Cleanup:** Resolved over 400 Ruff linting errors and standardized operational logs.
- **Backtest Metrics:** Fixed IndexError in `BacktestEngine` and aligned historical price data with feature-engineered indices.
- Restored missing `get_rates_range` functionality in MT5 connector.

## [1.1.0-rc3] - 2026-05-04

### Added
- **Enterprise Monitoring:** Centralized metrics and alerting system with Prometheus and Telegram support in `src/core/monitor.py`.
- **RL Evaluation Framework:** Institutional-grade performance metrics and regime-aware evaluation in `src/research/rl_evaluation.py`.
- **Enterprise Audit Logging:** Persistent system-wide audit tracing for compliance and debugging in `src/core/audit_log.py`.
- **Workflow Simplification:** Automated operational friction mapping and detailed automation designs in `docs/operations/WORKFLOW_SIMPLIFICATION_LOG.md`.

### Fixed
- Stabilized CI pipeline with `numpy < 2` pinning for TA-Lib compatibility.
- Resolved coroutine awaiting issues in system monitoring tests.
- Removed unused `pandas-ta` dependency to resolve version conflicts on Python 3.12.

## [1.1.0-rc2] - 2026-05-03

### Added
- **Institutional Capital Allocation:** Implemented a multi-strategy budget management system with concentration limits and performance-based scaling in `src/trading/capital_allocator.py`.
- **Vectorized Backtesting v2:** Enhanced the walk-forward backtesting engine with vectorized trade execution and performance metrics in `src/research/hyperopt_walkforward.py`.
- **Market Regime Detection:** Statistical market state classifier for XAUUSD (Trending, Ranging, News Shock, etc.) in `src/models/regime_detector.py`.
- **Institutional Feature Engineering:** Scalable pipeline for 190+ technical indicators with multi-timeframe support in `src/core/feature_engineering.py`.
- **CI Quality Gates:** Mandatory Mypy type enforcement and Docker dependency harmonization for enterprise stability.
- **Versioning Policy:** Defined comprehensive SemVer criteria and automated release workflows in `docs/VERSIONING_POLICY.md`.
- **Automated Changelog:** Integrated conventional commit-based changelog updates in `.github/workflows/changelog.yml`.

### Changed
- Standardized `BaseModel` and `Signal` interfaces across all institutional models.
- Enhanced release orchestration logic to automate version bumping and changelog transitions.

### Fixed
- Resolved critical import errors and synchronized CI dependencies across 18 files.
- Optimized rolling slope calculations and row access in benchmark adapters (2000x speedup).

## [1.1.0-rc1] - 2026-05-02
### Added
- Refined the 6-layer execution filter in `src/trading/execution_filter.py` with EMA20 trend angle logic.
- Institutional-grade decision support system in `src/core/decision_support.py`.
- Go/No-Go logic integrating execution filters, risk management, and macro event blocks.
- Enhanced `JournalMiner` with multi-dimensional motif detection (volatility, confidence).
- Institutional-grade research reporting system in `src/research/reporting.py`.
- Enterprise-grade trade signal explainability and attribution system in `src/core/explainability.py`.
- High-impact macroeconomic event intelligence module in `src/data/event_intelligence.py`.
- Institutional-grade rare event simulation framework in `src/research/rare_event_simulator.py`.
- Institutional-grade dynamic ensemble weighting engine in `src/models/dynamic_ensemble.py`.
- Institutional-grade execution quality analytics in `src/analytics/execution_quality.py`.

## [1.0.0] - 2024-05-24
### Added
- Initial enterprise-grade trading engine.
- MT5 integration and risk management framework.
- CI/CD pipelines for validation and security.
- Health check system and Prometheus metrics.
- Audit logging for traceability and compliance.
