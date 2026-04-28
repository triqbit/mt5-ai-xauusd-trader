# Technical Debt Log

## Current Status
**System Maturity Score:**
- Architecture: 7/10
- Safety: 7/10
- Connectivity: 6/10
- Code Coherence: 5/10

---

### Debt Item: Fragmented Initialization and Execution Logic
**Category:** Fragmentation
**Impact:** High
**Effort:** S
**Resolution plan:** Unified RiskManager initialization and consolidate run_live calls in main.py.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Hardcoded Risk Thresholds
**Category:** Quality
**Impact:** Medium
**Effort:** S
**Resolution plan:** Synchronize `RiskManager._check_minimum_confidence` with `TradingConfig.confidence_threshold`.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Stale/Redundant Trading Abstractions
**Category:** Fragmentation | Duplication
**Impact:** Medium
**Effort:** M
**Resolution plan:** Consolidate `OrderManager` and `PortfolioManager` into `MT5Connector` or integrate them properly into the main loop. Currently, `main.py` bypasses them for `MT5Connector`.
**Owner:** Jules01 (Architecture)

### Debt Item: Async/Sync Inconsistency
**Category:** Architecture
**Impact:** High
**Effort:** L
**Resolution plan:** Decide on a unified concurrency model. `OrderManager` is async while `MT5Connector` and `main.py` are sync.
**Owner:** Jules01 (Core Development)

### Debt Item: Debug Residue in Environment
**Category:** Dead Code | Quality
**Impact:** Low
**Effort:** S
**Resolution plan:** Replace `print` in `gym_env.py` with structured logging.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Incomplete Type Hinting and Docstrings
**Category:** Quality
**Impact:** Low
**Effort:** M
**Resolution plan:** Audit `src/` for missing type hints (e.g., `OrderManager`) and ensure all public methods have docstrings.
**Owner:** Jules02 (Hardening)

### Debt Item: Missing Integration Tests for New Components
**Category:** Quality
**Impact:** Medium
**Effort:** M
**Resolution plan:** Add integration tests for `OrderManager` and `PortfolioManager`.
**Owner:** Jules02 (Testing)
