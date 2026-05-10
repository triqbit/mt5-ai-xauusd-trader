# Technical Debt Log

This log tracks architectural drift, code quality degradation, and fragmented logic introduced by multi-agent parallelism and incremental feature additions.

### Debt Item: Risk Management Fragmentation
**Category:** Fragmentation | Duplication
**Impact:** High
**Effort:** M
**Resolution plan:** Harmonize `RiskEngine` and `RiskManager`. Integrate the advanced 8-layer cascade and ATR-based position sizing from `RiskEngine` into the unified `RiskManager` class.
**Owner:** Jules05

### Debt Item: Schema Duplication and Inconsistency
**Category:** Duplication | Naming
**Impact:** High
**Effort:** S
**Resolution plan:** Centralize `DailyStats`, `RiskDecision`, and `ExecutionDecision` in `src/core/schemas.py`. Ensure all components use these unified schemas. Resolve differences between the `ExecutionDecision` defined in `src/core/schemas.py` and `src/trading/execution_filter.py`.
**Owner:** Jules05

### Debt Item: Test Suite Bloat and Fragmentation
**Category:** Fragmentation | Quality
**Impact:** Medium
**Effort:** M
**Resolution plan:** Consolidate fragmented test files (e.g., `test_event_intelligence_v2.py`, `test_risk_engine_new.py`, `test_mt5_connector_new.py`) into their respective base test files or well-named unified suites.
**Owner:** Jules05

### Debt Item: Inconsistent Terminology (Balance vs Equity)
**Category:** Naming
**Impact:** Low
**Effort:** S
**Resolution plan:** Standardize the use of `balance` (realized funds) and `equity` (balance + unrealized PnL) across `src/trading/`, `src/research/`, and `src/core/`.
**Owner:** Jules05

### Debt Item: Dead Code and Unused Imports
**Category:** Dead Code
**Impact:** Low
**Effort:** S
**Resolution plan:** Remove redundant `src/trading/risk_engine.py` after harmonization. Cleanup unused imports across the `src/` directory.
**Owner:** Jules05
