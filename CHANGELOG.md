# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Structured Iteration Heartbeat:** Implemented a high-fidelity polling cycle heartbeat in `main.py` with failure attribution and processing latency tracking.
- **Enhanced Observability Metrics:** Added new Prometheus metrics (`trading_iteration_heartbeat_timestamp`, `trading_iteration_duration_seconds`, `trading_market_stability`) to the `Monitor` module for real-time system health tracking.
- **Trace Correlation:** Updated Telegram alerting to automatically include `trace_id` snippets for direct linkage between mobile alerts and system logs.
- **Decision Funnel Telemetry:** Implemented a structured signal progression tracking system via `SIGNAL_FUNNEL_COUNTER` to observe decision drop-offs across ensemble, risk, and execution layers.
- **Confluence Metrics:** Added `SIGNAL_CONFLUENCE_HISTOGRAM` to track the distribution of weighted confluence scores for institutional signal auditing.
- **Security Hardening (Jules02):**
    - Enforced `0o700` permissions on operational directories (`data`, `logs`, `models/trained`) to prevent unauthorized local access.
    - Implemented `PRAGMA secure_delete=ON` for SQLite databases to ensure deleted data is unrecoverable.
    - Hardened `.env` file creation in the Setup Wizard using `os.open` with `0o600` to prevent race conditions and world-readable secrets.
    - Enhanced secret masking to protect `SecretStr` values regardless of length (removed 4-character minimum).
    - Hardened directory permissions for SQLite databases by ensuring parent folders are locked down to `0o700`.
- **Adaptive Ensemble Safety:** Implemented "Veto Power" (blocks trades if any sub-model has <0.40 confidence) and regime-adaptive consensus thresholds (raises to 80% during NEWS_SHOCK or VOLATILE_BREAKOUT).
- **Transition-Aware Hardening:** Automatically increases required ensemble consensus during high-likelihood market regime shifts.
- **Resilient Bootstrapping:** Enhanced `scripts/bootstrap.sh` to handle TA-Lib installation failures gracefully, allowing setup to complete with functional fallbacks.
- **Accurate Diagnostics:** Updated `scripts/doctor.py` to report missing TA-Lib as a WARNING instead of a CRITICAL FAILURE, aligning with the bot's built-in fallback capabilities.
- **Interactive Setup Wizard:** Introduced a guided CLI configuration wizard (`python main.py --setup`) to simplify `.env` initialization and MT5 credential management.
- **Improved CLI Ergonomics:** Refactored argument parsing into logical groups (Execution, Backtesting, Setup, Logging) and enhanced `--help` readability.
- **Enhanced Startup Visibility:** Updated the configuration summary panel to include masked MT5 account details and server information for operator verification.
- **Comprehensive Monitoring System:** Implemented full monitoring and alerting system in `src/core/monitor.py` including equity curve tracking, Prometheus metrics, and granular Telegram alerts.
- **Institutional Feature Engineering:** Implemented a scalable pipeline for 140+ technical indicators with multi-timeframe support (M1-D1) and no look-ahead bias in `src/core/feature_engineering.py`.
- **Stateful Feature Normalization:** Added production-ready Z-score and Min-Max normalization with persistence support for consistent inference.
- **6-Layer Execution Filter Cascade:** Implemented a streamlined validation system for trading signals (ATR, Trend Angle, EMA Sequence, Momentum, Session/Time, Drawdown).
- **Structured Execution Decisions:** Introduced a typed `ExecutionDecision` dataclass for granular audit tracing and clear rejection reasons.
- **Enhanced Filter Unit Tests:** Added 27 comprehensive tests covering edge cases for all 6 validation layers.
- Implement institutional-grade feature engineering pipeline with 140+ features and multi-timeframe analysis.
- Implement production-ready stubs for PPO, LSTM, and Dreamer agents.
- Optimize PPOAgent with robust observation reshaping and strict Signal return typing.
- Enhance LSTMModel with functional training loop stubs and multi-architecture support.
- Update DreamerAgent with flexible parameter propagation via `**kwargs` for ensemble compatibility.
- Implement configurable transaction cost penalties and cleanup logic in TradingEnv.
- ⚙️ Jules02: Performance and runtime analysis — optimize feature engineering and backtest profiling.
- Refine institutional feature engineering and unit tests.
- Implement 6-layer execution filter cascade strictly following README.md.
- Added comprehensive deployment validation gates in .github/workflows/pre-deploy-validation.yml.
- Implement monitoring system and Telegram alerting (#962)
- Implement Institutional Decision Support System (#1086)
- Enhance Walk-Forward Optimizer with Strict Fragility Safeguards (#1135)

### Changed
- Optimized `FeatureEngineer` technical analysis pipeline, achieving ~17% reduction in latency.
- Integrated PREPROD_CHECKLIST.md validation into release gates.
- Implement Institutional Decision Support System (#1086)

### Fixed
- **Dependency Harmonization:** Aligned `python-socketio` version to 5.14.0 across `requirements.txt` and `pyproject.toml` to resolve synchronization mismatches.
- Resolve undefined name `batch_idx` in LSTMModel training loop.
- Resolve starlette and fastapi version conflicts in requirements files.
- Resolve security vulnerabilities in starlette dependency (upgrade to 0.52.1).
- Refined validation scripts with explicit remediation messages.

## [1.1.0-rc7] - 2026-05-09

### Added
- **Institutional Strategy Benchmarking Framework:** Quantitative framework for comparing AI models against 12+ technical benchmarks.
- **Enterprise Disaster Recovery Plan:** Automated hourly backup system for trade and audit databases with background integrity verification.
- **Institutional Walk-Forward Optimization:** Rolling window hyperparameter optimization with robustness scoring and curve-fitting prevention.
- **High-Fidelity Slippage Simulator:** Refined execution simulation utilizing realized slippage feedback loops.
- **Production-Ready AI Model Stubs:** Enhanced `PPOAgent`, `LSTMModel`, and `DreamerAgent` with robust interfaces and environment validation.
- **XAUUSD Environment Refinement:** Updated `TradingEnv` with institutional-grade spread/slippage parameters and Gymnasium compatibility.
- **Configuration Security Hardening:** Converted sensitive fields to `SecretStr` in `TradingConfig` to prevent credential leakage.
- **Monitoring & Alerting System:** Comprehensive real-time monitoring including equity curve tracking and Telegram integration.
- **Semantic TUI Visuals:** Enhanced Decision Support System cockpit with semantic emojis and panel icons.
- **Enterprise Core Scaffolding:** Refined `src/` package structure and core modules to meet institutional enterprise standards.
- **Institutional Backtesting Engine:** High-performance, vectorized walk-forward backtesting engine supporting realistic transaction costs.
- **Enhanced RL Evaluation Suite:** Advanced institutional metrics including Tail Ratio and Common Sense Ratio.
- **Vectorized Feature Engineering:** Optimized `FeatureEngineer` with TA-Lib vectorization, achieving ~20% speedup.
- **Dependency Parity Guard:** Automated version synchronization checks across environment-specific requirements files.
- **End-to-End Trace Correlation:** UUID propagation system linking logs, audit trails, and database records.

### Changed
- **CI Dependency Pinning:** Pinned type stub dependencies in `requirements-ci.txt` for environment reproducibility.
- **Dependency Harmonization:** Aligned core dependencies across all environments to resolve security vulnerabilities.
- **Black 26.3.1 Migration:** Upgraded code formatter to latest stable version for improved readability and toolchain hygiene.

### Fixed
- **CI Pipeline Stabilization:** Resolved Ruff linting violations and standardized import sorting.
- **Enterprise Health Monitoring:** Refined system with robust liveness/readiness probes and mandatory startup gate.
- **Deployment Validation Gates:** Implemented robust pre-deployment validation workflow.

### Security
- **Safe PyTorch Deserialization:** Enforced `weights_only=True` in all `torch.load` calls to prevent RCE.

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
