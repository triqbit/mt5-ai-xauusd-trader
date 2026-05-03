# Technical Debt Log

This log tracks architectural drift, code quality degradation, and fragmented logic introduced during multi-agent development.

## Active Debt Items

### Debt Item: Fragmented LSTM Architecture
**Category:** Fragmentation
**Impact:** High
**Effort:** M
**Resolution plan:** Relocate `LSTMAttentionModel` from `src/models/ensemble.py` to `src/models/lstm_model.py` to centralize sequence modeling logic.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Redundant Signal/Action Mapping
**Category:** Duplication
**Impact:** Medium
**Effort:** S
**Resolution plan:** Replace manual `IntEnum` to index mappings with centralized `ModelAction(idx).to_direction()` calls across the codebase.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Raw Print Statements in Research Modules
**Category:** Quality
**Impact:** Low
**Effort:** S
**Resolution plan:** Replace `print()` with `structlog` or `rich.console` in `src/research/hyperopt_walkforward.py` and `main.py`.
**Owner:** Jules05 (Immediate cleanup)

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

### Debt Item: Placeholder Reward Logic in Trading Environment
**Category:** Quality
**Impact:** Medium
**Effort:** M
**Resolution plan:** Schedule for Jules01/Jules04 to implement proper reward shaping based on risk-adjusted returns.
**Owner:** Jules01/Jules04
