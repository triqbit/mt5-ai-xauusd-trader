# Technical Debt Log

### Debt Item: Fragmented Risk Management Logic
**Category:** Fragmentation | Duplication
**Impact:** High
**Effort:** M
**Resolution plan:** Consolidate 8-layer cascade and ATR-based sizing from `RiskEngine` into `RiskManager`. Delete `RiskEngine`.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Redundant "New" Test Files
**Category:** Dead Code | Test Duplication
**Impact:** Medium
**Effort:** S
**Resolution plan:** Identify and remove `*_new.py` test files that duplicate existing coverage or test stale abstractions.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Inconsistent Risk Interface
**Category:** Naming
**Impact:** Medium
**Effort:** S
**Resolution plan:** Standardize on `validate_signal` or `approve` across all risk-related components and ensure `main.py` uses the harmonized API.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Missing Type Hints and Docstrings in Core Trading Logic
**Category:** Quality
**Impact:** Low
**Effort:** S
**Resolution plan:** Add missing type hints and docstrings to `risk_manager.py` and `audited_risk_manager.py` during harmonization.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: PR Residue in Tests
**Category:** Dead Code
**Impact:** Low
**Effort:** S
**Resolution plan:** Clean up orphaned test files and ensure the test suite is lean and focused.
**Owner:** Jules05 (Immediate cleanup)
