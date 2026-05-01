# Technical Debt Log

This document tracks technical debt introduced by multi-agent parallelism and architectural drift.

## Current Debt Items

### Debt Item: Fragmented Model Weighting Logic
**Category:** Fragmentation | Duplication
**Impact:** High
**Effort:** M
**Resolution plan:** Refactor `EnsembleModel` in `src/models/ensemble.py` to use `DynamicEnsemble` from `src/models/dynamic_ensemble.py`. `EnsembleModel` currently implements its own simpler (and slightly different) version of rolling Sharpe rebalancing.
**Owner:** immediate cleanup (Jules05)

### Debt Item: Inconsistent Signal Direction Mapping
**Category:** Naming | Quality
**Impact:** High
**Effort:** S
**Resolution plan:** Create a centralized `SignalDirection` or `TradeSignal` constants in `src/core/constants.py`.
- `EnsembleModel`: `{0: 1, 1: -1, 2: 0}` (0=buy, 1=sell, 2=hold)
- `PPOAgent` (via Adapter): `{0: 0, 1: 1, 2: -1}` (0=hold, 1=buy, 2=sell)
- `TimeSeriesTransformer` (via Adapter): `{0: 1, 1: -1, 2: 0}` (0=buy, 1=sell, 2=hold)
- `GymEnv`: `0=Hold, 1=Buy, 2=Sell`
This inconsistency is a major source of potential bugs.
**Owner:** immediate cleanup (Jules05)

### Debt Item: Incomplete Type Hinting in PPOAgent
**Category:** Quality
**Impact:** Medium
**Effort:** S
**Resolution plan:** Add proper type hints to `src/models/ppo_agent.py` methods and `__init__`.
**Owner:** immediate cleanup (Jules05)

### Debt Item: PR Residue and Debug Prints
**Category:** Dead Code
**Impact:** Low
**Effort:** S
**Resolution plan:** Remove `print()` in `src/environment/gym_env.py` and replace with proper logging or `rich` console if needed.
**Owner:** immediate cleanup (Jules05)

### Debt Item: Missing Standard Model Interface
**Category:** Quality
**Impact:** Medium
**Effort:** M
**Resolution plan:** Define a `TradingModel` Protocol or Abstract Base Class to ensure all models (`PPOAgent`, `TimeSeriesTransformer`, `EnsembleModel`) share a common `predict` signature and metadata properties. This would eliminate the need for many adapters in `src/research/benchmarks.py`.
**Owner:** Jules02 or Jules05 (Future)
