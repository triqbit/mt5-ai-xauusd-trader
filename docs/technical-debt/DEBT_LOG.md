# Technical Debt Log

This log tracks architectural drift, code quality degradation, and fragmented logic introduced during multi-agent development.

## Resolved Debt Items (2026-05-16)

### Debt Item: Risk Management Fragmentation
**Category:** Fragmentation
**Impact:** High
**Effort:** M
**Resolution plan:** Consolidated institutional 8-layer ATR risk logic into `RiskManager`. Standardized `AuditedRiskManager` and `main.py` to use the unified `validate_signal()` API. Deleted redundant `risk_engine.py`.
**Owner:** Jules05

### Debt Item: Feature Engineering Domain Disconnect
**Category:** Fragmentation
**Impact:** Medium
**Effort:** S
**Resolution plan:** Relocated `FeatureEngineer` from `src/core` to `src/data` to align with domain-driven design. Updated all system-wide imports.
**Owner:** Jules05

### Debt Item: Legacy Temporal Markers
**Category:** Quality
**Impact:** Medium
**Effort:** S
**Resolution plan:** Verified no `datetime.utcnow()` usage in `src/`. Standardization complete.
**Owner:** Jules05

### Debt Item: Fragmented Signal Mapping
**Category:** Duplication
**Impact:** Medium
**Effort:** S
**Resolution plan:** (In progress) Standardizing `ModelAction` usage across ensemble and RL agents.
**Owner:** Jules05

### Debt Item: Inconsistent Model Output Permutations
**Category:** Fragmentation
**Impact:** High
**Effort:** M
**Resolution plan:** (In progress) Standardizing all model outputs to `[HOLD, BUY, SELL]` in `EnsembleModel`.
**Owner:** Jules05

## Active Debt Items

### Debt Item: Linting Debt (Ruff/UP)
**Category:** Quality
**Impact:** Low
**Effort:** M
**Resolution plan:** Systematic application of `ruff --fix` to resolve hundreds of `UP` (Upgrade), `I` (Import), and `F` (Pyflakes) errors.
**Owner:** Jules05 (Next immediate cleanup)

### Debt Item: Raw Print Statements
**Category:** Quality
**Impact:** Low
**Effort:** S
**Resolution plan:** Replace remaining `print()` with `structlog` or `rich.console` in non-bootstrap CLI paths.
**Owner:** Jules05

### Debt Item: Placeholder Secrets in Validator
**Category:** Quality
**Impact:** Medium
**Effort:** S
**Resolution plan:** Ensure `ConfigValidator` strictly rejects placeholder passwords ("password", "change_me") in production-like environments.
**Owner:** Jules03 (Governance)

### Debt Item: Placeholder RL Agents (Dreamer/PPO stubs)
**Category:** Fragmentation
**Impact:** Medium
**Effort:** L
**Resolution plan:** Schedule for Jules04 (Quant Research) to replace placeholders with functional world-model implementations.
**Owner:** Jules04

### Debt Item: Placeholder Reward Logic in Trading Environment
**Category:** Quality
**Impact:** Medium
**Effort:** M
**Resolution plan:** Schedule for Jules01/Jules04 to implement proper reward shaping based on risk-adjusted returns.
**Owner:** Jules01/Jules04
