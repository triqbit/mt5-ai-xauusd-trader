# Dynamic Ensemble Weighting

The `DynamicEnsemble` class implements an adaptive weighting engine that adjusts the influence of individual models within an ensemble based on their real-time performance and market context.

## Key Features

- **Adaptive Scoring**: Model weights are adjusted based on a composite score of:
    - **Accuracy**: Recent Sharpe ratio or win-rate.
    - **Calibration Error**: How well the model's confidence aligns with realized outcomes.
    - **Drift Score**: Detection of performance degradation or concept drift.
- **Stability Controls**:
    - **EMA Smoothing**: Prevents erratic jumps in weights.
    - **Weight Swing Caps**: Limits the maximum change in any single update.
    - **Oscillation Dampening**: Detects and slows down adaptation when target weights flip-flop across the current mean.
- **Regime Awareness**: Weights can be adjusted based on the current `MarketRegime` (e.g., penalizing drift during news shocks).

## Implementation Details

The weighting engine ensures that:
1. Weights always sum to 1.0.
2. No model weight falls below a configurable `min_weight` floor.
3. Transitions are smooth and mathematically sound.

## Usage

```python
from src.models.dynamic_ensemble import DynamicEnsemble
from src.models.regime_detector import MarketRegime

ensemble = DynamicEnsemble(
    model_names=["ppo", "lstm", "transformer"],
    smoothing_factor=0.1,
    max_swing=0.05
)

# Update weights with current metrics
metrics = {
    "ppo": {"accuracy": 0.85, "calibration_error": 0.05, "drift_score": 0.02},
    "lstm": {"accuracy": 0.70, "calibration_error": 0.15, "drift_score": 0.08},
}
new_weights = ensemble.update_weights(metrics, regime=MarketRegime.TRENDING)
```
