# Technical Debt Log

This log tracks architectural drift, code quality degradation, and fragmented logic introduced during multi-agent development.

## Active Debt Items

### Debt Item: Risk Management Fragmentation
**Category:** Fragmentation
**Impact:** High
**Effort:** M
**Resolution plan:** Consolidate `RiskEngine` (Institutional logic) and `RiskManager` (Core logic) into a unified `RiskManager`. Ensure `AuditedRiskManager` maintains traceability for the combined logic.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Duplicated DailyStats
**Category:** Duplication
**Impact:** Low
**Effort:** S
**Resolution plan:** Centralize `DailyStats` dataclass in `src/trading/risk_manager.py` (or a shared constants/schemas module) to avoid redundant definitions.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Linting Debt (Ruff)
**Category:** Quality
**Impact:** Medium
**Effort:** M
**Resolution plan:** Systematic application of `ruff --fix` and manual resolution of remaining errors (unused variables, ambiguous names).
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Legacy Temporal Markers (Review)
**Category:** Quality
**Impact:** Medium
**Effort:** S
**Resolution plan:** Ensure no new `datetime.utcnow()` calls were introduced. Verify `src/` is clean of legacy datetime usage.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Fragmented Signal Mapping
**Category:** Duplication
**Impact:** Medium
**Effort:** S
**Resolution plan:** Replace manual string/integer to SignalDirection mappings with `ModelAction(idx).to_direction()` or `SignalDirection` constants.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Fragmented LSTM Architecture
**Category:** Fragmentation
**Impact:** High
**Effort:** M
**Resolution plan:** Relocate `LSTMAttentionModel` from `src/models/ensemble.py` to `src/models/lstm_model.py` to centralize sequence modeling logic. (Completed: May 8)
**Owner:** Jules05

### Debt Item: Placeholder RL Agents (Dreamer/PPO stubs)
**Category:** Fragmentation
**Impact:** Medium
**Effort:** L
**Resolution plan:** Schedule for Jules04 (Quant Research) to replace placeholders with functional world-model implementations.
**Owner:** Jules04

### Debt Item: Inconsistent Model Output Permutations
**Category:** Fragmentation
**Impact:** High
**Effort:** M
**Resolution plan:** Standardize all model outputs to `[HOLD, BUY, SELL]` and remove legacy permutation logic in `EnsembleModel`.
**Owner:** Jules05 (Immediate cleanup)
