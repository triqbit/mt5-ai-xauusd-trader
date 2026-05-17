# Dynamic Ensemble Weighting Engine

The `DynamicEnsemble` system (located in `src/models/dynamic_ensemble.py`) provides institutional-grade adaptive weight management for model ensembles. It transitions the system from static voting to a regime-aware, performance-driven consensus model.

## Core Mission
The primary goal of the Dynamic Ensemble is to intelligently adjust the influence of individual models (e.g., PPO, Dreamer, LSTM) based on their real-time performance and the current market context, while maintaining strict stability controls to prevent erratic behavior.

## Key Features

### 1. Multi-Factor Scoring
Models are scored using a composite formula that balances performance against reliability:
`Score = Accuracy - (0.3 * CalibrationError) - (0.4 * DriftScore)`

*   **Accuracy**: Win-rate or normalized Sharpe over a rolling window.
*   **Calibration Error**: Measures how well a model's confidence aligns with its actual success (using Brier score logic).
*   **Drift Score**: A blended metric detecting both **Accuracy Drift** (70% weight) and **Calibration Drift** (30% weight) by comparing recent history (last 20%) vs. the full window. Calibration drift specifically identifies "reliability decay" where a model's confidence estimates become less predictive.

### 2. Market Regime Awareness
The engine applies XAUUSD-specific heuristics that modulate both scoring weights and adaptation rates based on the `MarketRegime` detected:
*   **NEWS_SHOCK**: Adaptation rate (`alpha`) is halved to prevent overreacting to outliers, and drifting models are heavily penalized.
*   **TRENDING**: Adaptation is slightly accelerated (1.2x) to capitalize on consistent model performance.
*   **VOLATILE_BREAKOUT**: Calibration becomes critical; uncalibrated models are penalized to ensure reliable stop-loss placement.

### 3. Stability Mechanisms
To prevent "flip-flopping" and ensure institutional-grade stability, several safeguards are active:
*   **EMA Decay**: Weights transition towards targets using an Exponential Moving Average (smoothing factor).
*   **Swing Caps**: The maximum weight change per update is strictly limited by `max_swing` (default 5%).
*   **Oscillation Dampening**: If target weights begin to alternate rapidly across the current weight, the adaptation rate is aggressively reduced (0.2x multiplier).
*   **Volatility Scaling**: In high-volatility environments, the adaptation speed slows down automatically to avoid reacting to transient noise. Additionally, if the `volatility_index` exceeds 2.0, the **Drift Penalty** is automatically increased by 50% to enforce defensive weighting during turbulent periods.

## Integration
The `DynamicEnsemble` is integrated into the `EnsembleModel`, which uses the dynamic weights to calculate a weighted consensus signal. It also supports autonomous closed-loop tracking via `record_prediction` and `record_outcome` methods.

## Verification
Institutional verification is performed via `tests/test_dynamic_ensemble.py`, covering 27 scenarios including regime-specific behavior, volatility thresholds, and stability under extreme conditions.

## Recent Improvements
- **Python 3.10 Compatibility**: Switched to `timezone.utc` for broader environment support.
- **Structured Logging**: Integrated `structlog` for enhanced traceability in institutional research workflows.
- **Refined Drift Logic**: Improved the blending of accuracy and calibration drift for more reliable degradation signals.
