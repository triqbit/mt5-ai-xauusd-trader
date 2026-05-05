# Technical Debt Log

This log tracks architectural drift, code quality degradation, and fragmented logic introduced during multi-agent development.

## Resolved Debt Items (May 2026 Cleanup)

### Debt Item: Fragmented Signal and Direction types
**Category:** Fragmentation | Naming
**Impact:** High
**Effort:** M
**Resolution plan:** Created `src/core/types.py` to centralize `SignalDirection`, `TradeSignal` (NamedTuple), and `TradeSignalExecution` (dataclass).
**Owner:** Jules05 (Resolved)

### Debt Item: Redundant Risk Management implementations
**Category:** Duplication | Fragmentation
**Impact:** High
**Effort:** M
**Resolution plan:** Migrated institutional audit logging from `AuditedRiskManager` into `RiskEngine`. Centralized risk logic in `RiskEngine`.
**Owner:** Jules05 (Resolved)

### Debt Item: Redundant and fragmented test files
**Category:** Duplication | Dead Code
**Impact:** Medium
**Effort:** S
**Resolution plan:** Merged `tests/test_config_new.py` into `tests/test_config.py` and `tests/test_ensemble_new.py` into `tests/test_ensemble_refactor.py`. Removed redundant files.
**Owner:** Jules05 (Resolved)

### Debt Item: Legacy temporal markers (datetime.utcnow)
**Category:** Quality
**Impact:** Medium
**Effort:** S
**Resolution plan:** Replaced `datetime.utcnow()` with `datetime.now(UTC)` in `tests/test_model_stability_guard.py` to align with enterprise standards.
**Owner:** Jules05 (Resolved)

### Debt Item: Residual print statements in core paths
**Category:** Quality
**Impact:** Low
**Effort:** S
**Resolution plan:** Replaced raw `print()` with `logger.error()` in `main.py` bootstrap sequence.
**Owner:** Jules05 (Resolved)

### Debt Item: Duplicate SignalDirection definitions
**Category:** Duplication
**Impact:** Medium
**Effort:** S
**Resolution plan:** Removed redundant `SignalDirection` definitions from `src/core/schemas.py` and `src/core/constants.py`, delegating to `src/core/types.py`.
**Owner:** Jules05 (Resolved)

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
