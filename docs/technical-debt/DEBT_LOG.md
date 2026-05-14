# Technical Debt Log

This log tracks architectural drift, code quality degradation, and stale abstractions identified during multi-agent development.

## Resolved Debt (Cleaned up by Jules05)

### Debt Item: Fragmented Risk Management Logic
**Category:** Fragmentation | Duplication
**Impact:** High
**Effort:** M
**Resolution plan:** Consolidated `RiskEngine` (Institutional logic) and `RiskManager` (Legacy logic) into a unified `RiskManager`. Moved `RiskDecision` and `DailyStats` to `src/core/schemas.py`.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Inconsistent Method Naming (`approve` vs `validate`)
**Category:** Naming
**Impact:** Medium
**Effort:** S
**Resolution plan:** Renamed `RiskManager.approve` to `RiskManager.validate_signal` to match the Execution Filter naming convention.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Missing Type Hints and Docstrings in Utilities
**Category:** Quality
**Impact:** Low
**Effort:** S
**Resolution plan:** Added type hints and docstrings to `ScenarioGenerator` and its internal mock classes.
**Owner:** Jules05 (Immediate cleanup)

## Pending Debt

### Debt Item: Redundant Indicator Calculations
**Category:** Duplication
**Impact:** Medium
**Effort:** M
**Resolution plan:** Several modules (ExecutionFilter, RegimeDetector) compute EMAs and RSI independently. Centralize indicator computation in `FeatureEngineer` and pass the enriched DataFrame.
**Owner:** Jules01

### Debt Item: Stale Placeholder implementations ("TODO: improve this")
**Category:** Quality
**Impact:** Low
**Effort:** S
**Resolution plan:** Search and replace stubs in `EventIntelligence` and `ExecutionAnalyzer` with production-grade logic.
**Owner:** Jules04 (Macro) / Jules02 (Hardening)

### Debt Item: Lack of formal Interface for Reportable components
**Category:** Fragmentation
**Impact:** Low
**Effort:** S
**Resolution plan:** `src/core/interfaces.py` was created. Now, existing modules with `to_report_section` should be updated to formally implement the `Reportable` protocol.
**Owner:** Jules05/Jules01
