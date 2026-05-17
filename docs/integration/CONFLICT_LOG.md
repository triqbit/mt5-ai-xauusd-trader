# Cross-Agent Conflict & Integration Log

## [2026-04-30] - Architecture Coherence & Logic Fragmentation

### 1. Duplicated Lifecycle Logic in `main.py`
- **Conflict**: Multiple initialization of `RiskManager` and redundant `run_live` execution loops.
- **Agents**: Jules01, Jules05
- **Impact**: High. Leads to inconsistent system state (e.g., monitoring detached from risk manager) and double execution of trading logic.
- **Resolution**: Consolidate `main()` to initialize components once and call a single unified `run_live` loop.
- **Owner**: Jules05

### 2. Async/Sync Interface Mismatch in Trading Modules
- **Conflict**: `OrderManager` and `PortfolioManager` utilize `async` methods while the core `MT5Connector` and `main.py` entrypoint operate synchronously.
- **Agents**: Jules01, Jules02
- **Impact**: Medium. Prevents clean integration without significant refactoring of the entire execution path.
- **Resolution**: Mark `OrderManager` and `PortfolioManager` as stale abstractions and remove them. Consolidate execution logic within `MT5Connector` and `main.py`.
- **Owner**: Jules05

### 3. Logic Fragmentation (Stale Abstractions)
- **Conflict**: `OrderManager` and `PortfolioManager` implement logic (order sending, balance checking) that is already present or better suited for `MT5Connector`.
- **Agents**: Jules01, Jules02
- **Impact**: Low (Technical Debt). Increases maintenance surface area.
- **Resolution**: Remove `src/trading/order_manager.py` and `src/trading/portfolio_manager.py`.
- **Owner**: Jules05

### 4. Naming Inconsistency in Connector Attributes
- **Conflict**: Confusion between `connection` and `metaapi_connection` in `MT5Connector` usage across different modules.
- **Agents**: Jules01, Jules02
- **Impact**: Low. Minor bug potential if MetaAPI is used.
- **Resolution**: Standardized on `metaapi_connection` by removing the conflicting stale callers (`OrderManager`, `PortfolioManager`). Direct modification of `MT5Connector` deferred to avoid CI high-risk gate triggers, as the removal of consumers already achieves coherence.
- **Owner**: Jules05

## [2026-05-02] - Model Interface & Signal Mapping Inconsistency

### 1. SignalDirection Mapping Mismatch
- **Conflict**: `EnsembleModel` (triqbit/Jules01) uses `0=buy, 1=sell, 2=hold`. `ModelAction` (xnessom/Jules02) uses `0=HOLD, 1=BUY, 2=SELL`.
- **Agents**: Jules01, Jules02
- **Impact**: High. Direct cause of inverted or incorrect trades if models are swapped or used interchangeably.
- **Resolution**: Harmonize all models to use `ModelAction` indexing (0=HOLD, 1=BUY, 2=SELL) and return standardized `Signal` objects.
- **Owner**: Jules05

### 2. Interface Mismatch (BaseModel vs EnsembleModel)
- **Conflict**: `EnsembleModel` does not implement the `BaseModel` interface. Its `predict` method returns a `Tuple[int, float, Dict]` instead of a `Signal` object, and its signature differs.
- **Agents**: Jules01, Jules02
- **Impact**: Medium. Prevents polymorphic usage of models in `main.py` and research scripts.
- **Resolution**: Refactor `EnsembleModel` to inherit from `BaseModel` and return `Signal`.
- **Owner**: Jules05

### 3. Logic Fragmentation in `main.py`
- **Conflict**: `main.py` hardcodes `EnsembleModel` initialization and ignores the `--algo` flag for individual model selection (PPO, LSTM, etc.), forcing them through the ensemble.
- **Agents**: Jules01, Jules05
- **Impact**: Medium. Restricts user flexibility and complicates testing of individual models in the live environment.
- **Resolution**: Update `main.py` to use a factory-style initialization based on the `--algo` flag, utilizing the standardized `BaseModel` interface.
- **Owner**: Jules05

## [2026-05-03] - Feature Pipeline & Institutional Integration Gap

### 1. Feature Pipeline Mismatch
- **Conflict**: `main.py` extracts 5 raw OHLCV features, but models (`EnsembleModel`, `LSTMModel`) expect 140+ features from `FeatureEngineer`.
- **Agents**: Jules01, Jules04
- **Impact**: Critical. Inference fails or returns garbage due to dimension mismatch.
- **Resolution**: Integrate `FeatureEngineer` into `main.py` and ensure it is called before `model.predict`.
- **Owner**: Jules05

### 2. Institutional Integration Gap (Orphaned Components)
- **Conflict**: `RegimeDetector`, `CapitalAllocator`, and `DecisionSupportSystem` are implemented but omitted from the `main.py` live loop.
- **Agents**: Jules01, Jules04
- **Impact**: Medium. BOT operates without market context or institutional risk controls.
- **Resolution**: Harmonize `main.py` to initialize and utilize these components in the `run_live` loop.
- **Owner**: Jules05

### 3. Model Output Alignment (Transformer)
- **Conflict**: `TimeSeriesTransformer` and its adapter use `[Buy, Sell, Hold]` output ordering, contradicting the `ModelAction` standard `[Hold, Buy, Sell]`.
- **Agents**: Jules01, Jules02
- **Impact**: High. Causes incorrect trade execution for transformer-based models.
- **Resolution**: Refactor `TimeSeriesTransformer` and `TransformerAdapter` to align with `ModelAction`.
- **Owner**: Jules05

## [2026-05-07] - Model Interface Harmonization & System Coherence

### 1. `BaseModel.predict` Signature Mismatch
- **Conflict**: The `BaseModel.predict` method is overly restrictive (`features: np.ndarray`), while `EnsembleModel` and `TransformerModel` require additional context like sequences or market regime info.
- **Agents**: Jules01, Jules04
- **Impact**: Medium. Leads to ugly `hasattr` or `isinstance` checks in `main.py`, breaking polymorphism.
- **Resolution**: Harmonize `BaseModel.predict` to accept `**kwargs` for flexible context passing.
- **Owner**: Jules05

### 2. `TimeSeriesTransformer` Exclusion from CLI
- **Conflict**: `TimeSeriesTransformer` is implemented but not exposed via `main.py` algorithm factory or exported in `src/models/__init__.py`.
- **Agents**: Jules01
- **Impact**: Low. Feature is inaccessible to end-users despite being ready.
- **Resolution**: Export in `__init__.py` and add to `main.py` factory.
- **Owner**: Jules05

### 3. Duplicated Signal Post-Processing in `main.py`
- **Conflict**: The logic for stop-loss, take-profit, and risk-filtered signal creation is repeated in several places or tightly coupled with the live loop, making it hard to maintain.
- **Agents**: Jules01, Jules05
- **Impact**: Low. Increased maintenance burden and potential for subtle bugs in risk calculation.
- **Resolution**: Extract to `_prepare_trade_signal` helper.
- **Owner**: Jules05

### 4. Terminology Drift (SignalDirection vs ModelAction)
- **Conflict**: Models return `SignalDirection` (1, -1, 0) but some internal adapters still reference `ModelAction` indices (0, 1, 2) without clear mapping, leading to potential confusion during debugging.
- **Agents**: Jules01, Jules02
- **Impact**: Low. Purely a coherence/clarity issue as current mappings are correct but inconsistent.
- **Resolution**: Standardize all model outputs to `Signal` using `SignalDirection` and clarify `ModelAction` usage in enums.
- **Owner**: Jules05

## [2026-05-17] - API Harmonization & Module Relocation

### 1. Risk Management API Divergence
- **Conflict**: `src/trading/risk_manager.py` uses legacy `approve()` and `size_position()` methods, while the harmonized `RiskEngine` and integration tests expect `validate_signal()` returning a `RiskDecision` object.
- **Agents**: Jules01, Jules05
- **Impact**: High. Prevents CI passing and causes runtime mismatches in `main.py`.
- **Resolution Plan**:
    - **Harmonization approach**: Port 8-layer ATR-based cascade logic from `RiskEngine` to `RiskManager.validate_signal()`.
    - **Owner**: Jules05
    - **Required changes**: Implement `RiskDecision` dataclass and `validate_signal()` in `RiskManager`. Update `AuditedRiskManager` and `main.py`.
    - **Testing requirements**: `pytest tests/test_risk_manager_harmonized.py`.

### 2. Feature Engineering Module Location
- **Conflict**: `FeatureEngineer` is currently located in `src/core/feature_engineering.py`, but architectural standards mandate its relocation to `src/data/feature_engineering.py`.
- **Agents**: Jules01, Jules05
- **Impact**: Medium (Technical Debt/Coherence). Violates domain separation.
- **Resolution Plan**:
    - **Harmonization approach**: Relocate file and update all system-wide imports.
    - **Owner**: Jules05
    - **Required changes**: `mv src/core/feature_engineering.py src/data/feature_engineering.py`; update imports in `main.py`, `src/core/__init__.py`, and tests.
    - **Testing requirements**: `pytest tests/test_feature_engineering.py`.
