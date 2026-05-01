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

## [2026-05-01] - Institutional Component Harmonization

### 1. Duplicated Ensemble Weighting Logic
- **Conflict**: `EnsembleModel` (Jules01) implements a basic rebalancing logic, while `DynamicEnsemble` (Jules04) provides a more advanced, regime-aware weighting engine.
- **Agents**: Jules01, Jules04
- **Impact**: Medium. Redundant logic and missed opportunity for institutional-grade weighting.
- **Resolution**: Harmonize `EnsembleModel` to use `DynamicEnsemble` for its internal weight management.
- **Owner**: Jules05

### 2. Orphaned Institutional Components (RegimeDetector, CapitalAllocator)
- **Conflict**: High-value components `RegimeDetector` and `CapitalAllocator` (Jules04) exist in the codebase but are not integrated into the main trading loop or risk management flow.
- **Agents**: Jules01, Jules04
- **Impact**: High (Product Value). The system operates without its core "differentiating" features.
- **Resolution**: Integrate `RegimeDetector` into `main.py` and `CapitalAllocator` into `RiskManager`.
- **Owner**: Jules05

### 3. Missing Regime-Awareness in Trading Loop
- **Conflict**: The `run_live` loop in `main.py` performs inference without market regime context, even though `RegimeDetector` is available.
- **Agents**: Jules01, Jules04
- **Impact**: Medium. Suboptimal model performance in different market conditions.
- **Resolution**: Pass detected market regime to the ensemble model and risk manager during the trading loop.
- **Owner**: Jules05
