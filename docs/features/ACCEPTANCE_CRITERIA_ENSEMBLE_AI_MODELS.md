# Acceptance Criteria: Ensemble AI Models

## Functional Acceptance Criteria
- **Behavior:**
    - Combine predictions from PPO (Stable-Baselines3), Dreamer V3, and LSTM-Attention models.
    - Implement weighted voting based on rolling Sharpe ratio performance of each algorithm.
    - Support lazy loading of models to optimize memory usage.
    - LSTM model must use multi-head attention and bidirectional LSTM layers.
- **Edge Cases:**
    - Handle missing model checkpoints gracefully (return HOLD or use available models).
    - Handle input observation shapes mismatches.
    - Rebalance weights with a minimum floor (5%) to prevent total algorithm exclusion.
- **Inputs/Outputs:**
    - Input: Market observation (NumPy array) and optional sequence tensor.
    - Output: Direction (+1, -1, 0), Confidence (0.0-1.0), and per-algorithm votes.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for `EnsembleModel` logic and weight rebalancing.
    - Inference smoke tests with dummy data.
- **Performance:**
    - Total ensemble inference time < 100ms on CPU.
    - Peak memory usage < 4GB for full ensemble.
- **Error Handling:**
    - Comprehensive error logging for model loading and inference failures.
- **Logging/Observability:**
    - Log blended confidence and per-model votes for every prediction.

## Operational Acceptance
- **Documentation:**
    - Model architecture summary and training instructions in `README.md`.
- **Configuration:**
    - Configurable `algorithm` and `model_path` in `TradingConfig`.
    - Configurable `device` (cpu, cuda, mps, auto).
- **Rollback:**
    - Capability to switch back to a single model if ensemble diverges.
- **Monitoring:**
    - Track and alert on model confidence degradation (below 0.6).

## Release Readiness
- **Deployment:**
    - Requires `torch`, `numpy`, and `stable-baselines3`.
- **Backward Compatibility:**
    - Ensure saved model checkpoints (.pt, .zip) are version-tracked.
- **Migration:**
    - Requires download of model weights to `models/trained/`.
- **Stakeholder Sign-off:**
    - Required from Lead Quant / ML Engineer.
