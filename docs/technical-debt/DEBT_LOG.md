# Technical Debt Log

This log tracks architectural drift, code quality degradation, and stale abstractions within the MT5 AI/ML Trading Bot project.

### Debt Item: Redundant Component Initialization and Execution Loop in `main.py`
**Category:** Fragmentation / Logic Duplication
**Impact:** Medium
**Effort:** S
**Resolution plan:** Consolidate `RiskManager` initialization to a single call passing both `TradeLogger` and `Monitor`. Unify the `run_live` calls into a single execution.
**Owner:** Immediate cleanup (Jules05)

### Debt Item: Stale Trading Abstractions (`OrderManager`, `PortfolioManager`)
**Category:** Dead Code / Stale Abstractions
**Impact:** Low
**Effort:** S
**Resolution plan:** Remove `src/trading/order_manager.py` and `src/trading/portfolio_manager.py` as their functionality is either redundant or already integrated into `MT5Connector` and `RiskManager`.
**Owner:** Immediate cleanup (Jules05)

### Debt Item: Inconsistent MT5Connector API and Aliases
**Category:** Naming / Fragmentation
**Impact:** Low
**Effort:** S
**Resolution plan:** Remove redundant aliases (`initialize`, `shutdown`, `get_rates`) in `MT5Connector` to favor the standardized API (`connect`, `disconnect`, `get_ohlcv`).
**Owner:** Immediate cleanup (Jules05)

### Debt Item: Deprecated `datetime.utcnow()` Usage
**Category:** Quality
**Impact:** Low
**Effort:** S
**Resolution plan:** Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` in `src/trading/risk_manager.py` to comply with modern Python standards and prevent future deprecation issues.
**Owner:** Immediate cleanup (Jules05)

### Debt Item: Fragmented Model Abstractions
**Category:** Fragmentation
**Impact:** Medium
**Effort:** M
**Resolution plan:** `EnsembleModel` lazily loads and wraps models, but `PPOAgent` and `TimeSeriesTransformer` exist as separate, slightly redundant wrappers. Align model loading and inference strictly through the `EnsembleModel` or a unified `ModelFactory`.
**Owner:** Jules01 (scheduled)

### Debt Item: Missing Integration for MetaAPI in `MT5Connector`
**Category:** Fragmentation / Placeholder
**Impact:** Medium
**Effort:** M
**Resolution plan:** Implement the async MetaAPI data fetching and order execution in `MT5Connector` to fulfill the "dual-path" promise.
**Owner:** Jules01 (scheduled)

### Debt Item: Redundant `TradeSignal` and `DailyStats` in `risk_manager.py`
**Category:** Fragmentation
**Impact:** Low
**Effort:** S
**Resolution plan:** Consider moving `TradeSignal` to a common `src/core/types.py` or similar to avoid circular dependencies if other modules need it.
**Owner:** Jules02 (scheduled)
