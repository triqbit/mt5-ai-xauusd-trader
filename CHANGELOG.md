# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Configuration Security Hardening:** Converted `redis_url` to `SecretStr` in `TradingConfig` to prevent credential leakage in logs and audit snapshots. Integrated deep redaction for sensitive connection strings.
- **Monitoring & Alerting System:** Comprehensive real-time monitoring in `src/core/monitor.py` including equity curve tracking, Prometheus metrics export, and Telegram bot integration for critical alerts (circuit breakers, margin calls, liquidity crises) and daily performance summaries.
- **Production-Ready Model Stubs:** Enhanced `PPOAgent`, `LSTMModel`, and `DreamerAgent` with robust interfaces, probability extraction, and architecture switching in `src/models/`.
- **Improved Trading Environment:** Refined `TradingEnv` in `src/trading/trading_env.py` with institutional reward skeleton and Gymnasium compatibility.
- **Semantic TUI Visuals:** Enhanced the Decision Support System cockpit with semantic emojis (📈, 📉, ✅, ⚠️, 🛑) and panel icons for improved scannability and accessibility.
- **Enterprise Core Scaffolding:** Refined `src/` package structure and core modules (`config.py`, `mt5_connector.py`, `risk_engine.py`, `ensemble.py`) to meet institutional enterprise standards with full type hints, docstrings, and unit tests.
- **Institutional Backtesting Engine:** Implemented a high-performance, vectorized walk-forward backtesting engine in `src/trading/backtester.py` supporting realistic transaction costs (spread + commission) and path-dependent metrics (MAE/MFE).
- **Backtest Performance Optimization:** Refactored `BacktestEngine` to use O(1) incremental peak tracking for drawdown calculations, eliminating O(N^2) complexity in walk-forward simulations.
- **Institutional Risk Notifications:** Integrated real-time alerts for circuit breaker triggers, margin calls, account balance mismatches, and liquidity (spread) crises into the primary trading loop.
- **Automated Daily Performance Summaries:** Added logic to detect day changes and trigger automated Telegram summaries capturing daily P&L and trade counts.
- **Model Health Monitoring:** Implemented confidence degradation warnings and drift detection alerts to ensure institutional model reliability during live execution.
- **Vectorized Walk-Forward Backtester:** Implemented high-performance `BacktestEngine` in `src/trading/backtester.py` supporting realistic transaction costs (spread + commission), path-dependent metrics (MAE/MFE), and institutional performance reporting (Sharpe, CAGR, MDD).
- **Enhanced RL Evaluation Suite:** Advanced institutional metrics including Tail Ratio, Common Sense Ratio, and Gain-to-Pain Ratio. Improved robustness for regime sensitivity and agent interface integration (SB3, Signal objects).
- **Vectorized Feature Engineering:** Optimized `FeatureEngineer` by refactoring internal methods to return dictionaries of NumPy arrays and using TA-Lib vectorization (`SMA`, `SUM`, `ROCP`), achieving ~20% overall speedup.
- **Dependency Parity Guard:** Introduced `scripts/verify_dependencies.py` and `tests/test_verify_dependencies.py` to automate version synchronization checks across environment-specific requirements files.
- **End-to-End Trace Correlation:** Implemented a unique `trace_id` (UUID) propagation system linking logs, audit trails, and database records (signals/trades) for every iteration of the trading loop.

### Changed
- **CI Dependency Pinning:** Pinned type stub dependencies (`types-redis`, `types-requests`, `types-python-dateutil`, `types-setuptools`, `types-PyYAML`) in `requirements-ci.txt` to stable versions for environment reproducibility and build stability.
- **Dependency Harmonization:** Aligned core dependencies (`pandas==2.3.2`, `fastapi==0.136.1`, `starlette==0.49.1`) across all environments to resolve security vulnerabilities and satisfy `pandas-ta` requirements.
- **Hardened Risk Validation:** Tightened startup configuration checks to treat `model_calibration_threshold` breaches (> 0.25) as critical failures, ensuring runtime alignment with `RISK_LIMITS.md`.

### Fixed
- **CI Pipeline Stabilization:** Resolved over 400 Ruff linting violations and standardized import sorting across the enterprise package.
- **Package Architecture:** Populated missing `__init__.py` files to stabilize sub-package discovery and exported core interfaces.
- **Dependency Security:** Harmonized and secured dependencies across all requirements files to resolve `pip-audit` vulnerabilities.
- **Enterprise Health Monitoring:** Refined the `src/core/health.py` system with robust liveness/readiness probes, multi-layered dependency checks (Database, MT5, Redis, Models, Audit), and a mandatory startup gate.
- **Deployment Validation Gates:** Implemented a robust pre-deployment validation workflow in `.github/workflows/pre-deploy-validation.yml` to prevent unsafe releases.
- **Environment Safety Checks:** Enhanced `scripts/validate_env.py` and synchronized `.env.example` to ensure configuration completeness before deployment.
- **Release Readiness Auditing:** Integrated `scripts/check_release_notes.py` to mandate descriptive changelog entries for all new releases.

### Security
- **Safe PyTorch Deserialization:** Enforced `weights_only=True` in all `torch.load` calls across the codebase (including `main.py` and `src/models/lstm_model.py`) to prevent arbitrary code execution (RCE) from untrusted model files.
- **Security Regression Guard:** Introduced a static analysis test to ensure any future PyTorch model loading points adhere to the `weights_only` security standard.

### Deprecated
- No deprecated items in this section.

### Removed
- No removed items in this section.

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
- Dynamic instrument property detection (pip size, contract size) in `MT5Connector` and `ExecutionAnalyzer`.
- Standardized UTC-aware temporal logic for all execution analytics.

## [1.0.0] - 2024-05-24
### Added
- Initial enterprise-grade trading engine.
- MT5 integration and risk management framework.
- CI/CD pipelines for validation and security.
- Health check system and Prometheus metrics.
- Audit logging for traceability and compliance.
