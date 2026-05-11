# Dynamic Ensemble Weighting

The Dynamic Ensemble Weighting system provides an institutional-grade adaptive model weighting engine for the XAUUSD trading ensemble. It adjusts model influence based on real-time performance metrics and market context, ensuring the most reliable models dominate the final signal.

## Core Mechanisms

### 1. Multi-Factor Scoring
Models are scored based on three primary metrics:
- **Accuracy (Win Rate)**: The primary driver of model weight.
- **Confidence Calibration (Brier Score)**: Penalizes models that are overconfident or poorly calibrated.
- **Performance Drift**: Detects rapid degradation in recent performance compared to long-term averages.

### 2. Stability Controls
To prevent erratic behavior in live trading, the engine employs several safeguards:
- **EMA Decay**: Weights move towards target scores via an Exponential Moving Average, smoothing out transitions.
- **Swing Caps**: The maximum allowed weight change per update is strictly capped (default 5%).
- **Oscillation Dampening**: Aggressively reduces the adaptation rate if model targets 'flip-flop', preserving portfolio stability.

### 3. Regime Awareness
The weighting logic adapts to the current market environment:
- **Volatility Scaling**: Adaptation slows down automatically in high-volatility regimes to avoid reacting to noise.
- **Regime Heuristics**:
    - In **NEWS_SHOCK**, adaptation is extremely cautious.
    - In **TRENDING** markets, consistency (low drift) is prioritized.
    - In **MEAN_REVERSION**, calibration is critical to avoid overextended entries.

## System Integration

The system is integrated into the core trading loop (`main.py`), where market outcomes are recorded and weights are updated immediately after regime detection but before the next signal generation. This ensures the ensemble is always using the most contextually relevant weights for the current market state.
