# Technical Debt Log

This log tracks architectural drift, code quality degradation, and technical debt introduced by multi-agent parallelism.

### Debt Item: Double initialization and redundant execution loop in `main.py`
**Category:** Fragmentation | Quality
**Impact:** High
**Effort:** S
**Resolution plan:** Remove duplicate `RiskManager` initialization and redundant `run_live` calls. Ensure components are passed correctly.
**Owner:** Jules05

### Debt Item: Redundant interface aliases in `MT5Connector`
**Category:** Duplication
**Impact:** Medium
**Effort:** S
**Resolution plan:** Remove `initialize`, `shutdown`, and `get_rates` aliases. Standardize on `connect`, `disconnect`, and `get_ohlcv`.
**Owner:** Jules05

### Debt Item: Debug print statements in `gym_env.py`
**Category:** Quality | Dead Code
**Impact:** Low
**Effort:** S
**Resolution plan:** Replace `print()` in `render()` and other potential areas with structured logging.
**Owner:** Jules05

### Debt Item: Missing type hints and docstrings in core modules
**Category:** Quality
**Impact:** Medium
**Effort:** M
**Resolution plan:** Systematically add missing type hints and docstrings to `src/core`, `src/trading`, and `src/models`.
**Owner:** Jules05

### Debt Item: MetaAPI sync wrapper placeholder
**Category:** Quality
**Impact:** Medium
**Effort:** M
**Resolution plan:** Implement MetaAPI sync wrappers or formalize the "not implemented" state with proper exceptions.
**Owner:** Jules02

### Debt Item: Inconsistent Error Handling in Connectors
**Category:** Quality
**Impact:** Medium
**Effort:** M
**Resolution plan:** Standardize exception handling across `MT5Connector` and `TradeLogger`.
**Owner:** Jules02
