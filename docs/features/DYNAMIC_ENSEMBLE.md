# Dynamic Ensemble Weighting

The `DynamicEnsemble` class implements an adaptive weighting engine that adjusts the influence of individual models within an ensemble based on their real-time performance and market context.

## Key Features

- **Adaptive Scoring**: Model weights are adjusted based on a composite score of:
    - **Accuracy**: Recent Sharpe ratio or win-rate.
    - **Calibration Error**: Uses **Brier Score** (squared error) to quantify alignment between confidence and realized outcomes.
    - **Drift Score**: Uses a **sensitivity-ratio approach** `(acc - recent_acc) / (acc + 1e-9) * 2.0` for proactive detection of performance degradation.
- **Stability Controls**:
    - **EMA Smoothing**: Prevents erratic jumps in weights.
    - **Weight Swing Caps**: Limits the maximum change in any single update.
- **Initial Weight Support**: Allows setting custom starting weight distributions.
    - **Oscillation Dampening**: Detects and slows down adaptation when target weights flip-flop across the current mean.
- **Regime & Volatility Awareness**: Weights are adjusted based on the current `RegimeInfo`, including `MarketRegime` (e.g., penalizing drift during news shocks) and a `volatility_index` which modulates the adaptation speed.
- **XAUUSD Heuristics**: Specific scoring logic tailored for gold market behaviors:
    - **Trending**: Favors models with low drift to capitalize on sustained moves.
    - **Low Volatility Drift**: Focuses on accuracy as the primary weight driver.
    - **Volatile Breakout**: Prioritizes calibration for reliable stop-loss and exit signals.
    - **Mean Reversion**: Penalizes overconfidence/high calibration error to avoid traps.
    - **News Shock**: Aggressively penalizes models showing significant performance drift.

## Implementation Details

The weighting engine ensures that:
1. Weights always sum to 1.0.
2. No model weight falls below a configurable `min_weight` floor.
3. Transitions are smooth and mathematically sound, with adaptation speed automatically slowing down during high volatility or target oscillations.
4. Memory safety is maintained in the orchestrator via rolling window deques for performance metrics.

## Usage

```python
from src.models.dynamic_ensemble import DynamicEnsemble
from src.models.regime_detector import MarketRegime, RegimeInfo

ensemble = DynamicEnsemble(
    model_names=["ppo", "lstm", "transformer"],
    smoothing_factor=0.1,
    max_swing=0.05
)

# Mock regime info
regime_info = RegimeInfo(
    label=MarketRegime.TRENDING,
    confidence=0.9,
    transition_score=0.1,
    volatility_index=1.2
)

# Update weights with current metrics
metrics = {
    "ppo": {"accuracy": 0.85, "calibration_error": 0.05, "drift_score": 0.02},
    "lstm": {"accuracy": 0.70, "calibration_error": 0.15, "drift_score": 0.08},
}
new_weights = ensemble.update_weights(metrics, regime_info=regime_info)
```
