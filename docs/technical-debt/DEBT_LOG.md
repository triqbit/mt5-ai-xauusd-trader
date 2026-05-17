# Technical Debt Log

This log tracks architectural drift, code quality degradation, and fragmentation introduced by multi-agent parallelism.

## Active Debt Items

### Debt Item: Risk Management Fragmentation
**Category:** Fragmentation | Duplication
**Impact:** High
**Effort:** M
**Resolution plan:** Harmonize `RiskManager` and `RiskEngine`. Port 8-layer ATR-based logic to `RiskManager`, standardize on `validate_signal()` API, and deprecate `RiskEngine`.
**Owner:** Jules05 (Immediate Cleanup)

### Debt Item: Feature Engineering Misplacement
**Category:** Naming | Fragmentation
**Impact:** Medium
**Effort:** S
**Resolution plan:** Relocate `src/core/feature_engineering.py` to `src/data/feature_engineering.py` to align with modular domain separation standards. Update all system-wide imports.
**Owner:** Jules05 (Immediate Cleanup)

### Debt Item: Inconsistent Risk API in Main Loop
**Category:** Naming | Quality
**Impact:** High
**Effort:** S
**Resolution plan:** Update `main.py` to use the harmonized `validate_signal()` method which returns a structured `RiskDecision` object, replacing the legacy boolean `approve()` method.
**Owner:** Jules05 (Immediate Cleanup)

### Debt Item: Redundant Position Sizing Logic
**Category:** Duplication
**Impact:** Medium
**Effort:** S
**Resolution plan:** Consolidate Kelly Criterion sizing and ATR-based sizing into a single, robust `calculate_position_size` method within the harmonized `RiskManager`.
**Owner:** Jules05 (Immediate Cleanup)

### Debt Item: Stale Imports and Exports
**Category:** Dead Code
**Impact:** Low
**Effort:** S
**Resolution plan:** Cleanup `__init__.py` files and remove redundant exports (e.g., `RiskEngine`, misplaced `FeatureEngineer`).
**Owner:** Jules05 (Immediate Cleanup)

---
*Last Updated: 2026-05-17*
