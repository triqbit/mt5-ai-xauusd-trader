# Technical Debt Log

This log tracks architectural drift, code quality degradation, and fragmented logic introduced during multi-agent development.

## Active Debt Items

### Debt Item: Legacy Temporal Markers
**Category:** Quality
**Impact:** Medium
**Effort:** S
**Resolution plan:** Replace all `datetime.utcnow()` calls with `datetime.now(timezone.utc)` for Python 3.12 compatibility and standardization.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Linting Debt (Ruff/UP)
**Category:** Quality
**Impact:** Low
**Effort:** M
**Resolution plan:** Systematic application of `ruff --fix` to resolve hundreds of `UP` (Upgrade), `I` (Import), and `F` (Pyflakes) errors.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Raw Print Statements
**Category:** Quality
**Impact:** Low
**Effort:** S
**Resolution plan:** Replace `print()` with `structlog` or `rich.console` across core modules (main.py, explainability, etc.).
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Fragmented Signal Mapping
**Category:** Duplication
**Impact:** Medium
**Effort:** S
**Resolution plan:** Replace manual string/integer to SignalDirection mappings with `ModelAction(idx).to_direction()` or `SignalDirection` constants.
**Owner:** Jules05 (Immediate cleanup)

### Debt Item: Placeholder Secrets in Validator
**Category:** Quality
**Impact:** Medium
**Effort:** S
**Resolution plan:** Ensure `ConfigValidator` strictly rejects placeholder passwords ("password", "change_me") in production-like environments.
**Owner:** Jules03 (Governance)

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
