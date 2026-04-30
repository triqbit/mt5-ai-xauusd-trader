# Technical Debt Log - MT5 AI/ML Trading Bot

## Summary of Findings
As of April 2024, an architectural audit has identified several areas of drift and degradation.

### Debt Item: Orphaned PPOAgent abstraction
**Category:** Dead Code / Fragmentation
**Impact:** Medium
**Effort:** S
**Resolution plan:** Consolidation. The `EnsembleModel` already implements PPO loading and prediction. `src/models/ppo_agent.py` is not used in `main.py` and should be either integrated or removed.
**Owner:** Immediate cleanup (Jules05)

### Debt Item: Deprecated datetime.utcnow() usage
**Category:** Quality
**Impact:** Low
**Effort:** S
**Resolution plan:** Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` in `src/trading/risk_manager.py`.
**Owner:** Immediate cleanup (Jules05)

### Debt Item: Debug print in gym_env.py
**Category:** Dead Code
**Impact:** Low
**Effort:** S
**Resolution plan:** Remove the `print` statement on line 96 of `src/environment/gym_env.py` and replace with proper logging.
**Owner:** Immediate cleanup (Jules05)

### Debt Item: Missing Type Hints and Docstrings
**Category:** Quality
**Impact:** Medium
**Effort:** M
**Resolution plan:** Systematically add missing type hints and docstrings identified in the code scan, prioritizing core and trading modules.
**Owner:** Immediate cleanup (Jules05)

### Debt Item: Placeholder MetaAPI implementation in MT5Connector
**Category:** Quality / Fragmentation
**Impact:** Medium
**Effort:** L
**Resolution plan:** Implement the async wrapper for MetaAPI rates fetching or move it to a dedicated provider.
**Owner:** Jules01

### Debt Item: Hardcoded PPO training parameters
**Category:** Quality
**Impact:** Low
**Effort:** S
**Resolution plan:** Move PPO training hyperparameters to `TradingConfig`.
**Owner:** Jules04

### Debt Item: Large monolithic run_live loop in main.py
**Category:** Fragmentation
**Impact:** Medium
**Effort:** M
**Resolution plan:** Refactor `run_live` into a class-based `TradingEngine` to improve testability and modularity.
**Owner:** Jules01

### Debt Item: Fragmented model architectures
**Category:** Duplication
**Impact:** Low
**Effort:** M
**Resolution plan:** Standardize model base class to ensure consistent interfaces for `forward` and `predict` across all architectures.
**Owner:** Jules04
