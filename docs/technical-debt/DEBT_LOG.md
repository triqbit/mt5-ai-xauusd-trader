# Technical Debt Log

This document tracks technical debt introduced by multi-agent parallelism and architectural drift.

## Current Debt Items

### Debt Item: Signal Mapping Inconsistency (TimeSeriesTransformer)
**Category:** Naming | Quality
**Impact:** High
**Effort:** S
**Resolution plan:** Standardize `TimeSeriesTransformer` output and `TransformerAdapter` to follow the `ModelAction` enum (`0=HOLD, 1=BUY, 2=SELL`). Currently uses legacy `0=BUY, 1=SELL, 2=HOLD`.
**Owner:** immediate cleanup (Jules05)

### Debt Item: Duplicated LSTM Architectures
**Category:** Duplication | Fragmentation
**Impact:** Medium
**Effort:** M
**Resolution plan:** Unify `LSTMAttentionModel` (currently in `src/models/ensemble.py`) and `LSTMPricePredictor` (in `src/models/lstm_model.py`) into a single, high-performance LSTM module in `src/models/lstm_model.py`.
**Owner:** immediate cleanup (Jules05)

### Debt Item: Weak Model Confidence Implementations
**Category:** Quality
**Impact:** Medium
**Effort:** M
**Resolution plan:** Implement proper confidence calibration (e.g., using Platt scaling or Temperature scaling) for `PPOAgent` instead of using the hardcoded `0.85` placeholder.
**Owner:** Jules04 or Jules02

### Debt Item: PR Residue and Debug Prints
**Category:** Dead Code
**Impact:** Low
**Effort:** S
**Resolution plan:** Remove `print()` in `src/research/hyperopt_walkforward.py` and replace with proper logging.
**Owner:** immediate cleanup (Jules05)

### Debt Item: Incomplete Type Hinting in Research Adapters
**Category:** Quality
**Impact:** Medium
**Effort:** S
**Resolution plan:** Replace `Any` types with proper Protocols or specific class types in `src/research/benchmarks.py` adapters.
**Owner:** immediate cleanup (Jules05)

### Debt Item: Missing Standard Model Interface (Harmonization)
**Category:** Quality
**Impact:** Medium
**Effort:** M
**Resolution plan:** Ensure all models (`PPOAgent`, `TimeSeriesTransformer`, `EnsembleModel`) strictly adhere to the `BaseModel` abstract class and return standardized `Signal` objects.
**Owner:** Jules05 (Verification)

## Resolved / Partially Addressed
- **Fragmented Model Weighting Logic**: Integrated `DynamicEnsemble` into `EnsembleModel`.
- **Inconsistent Signal Direction Mapping**: Core models (PPO, LSTM) now use `ModelAction` mappings.
- **Incomplete Type Hinting in PPOAgent**: Initial hints added.
