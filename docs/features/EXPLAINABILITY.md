# Trade Signal Explainability System

The Explainability system provides institutional-grade transparency into why trade signals are generated or rejected by decomposing the decision process into five key areas.

## Core Components

The system breaks down signal attribution into the following structured categories:

### 1. Execution Filters
Monitors connectivity, spread, and timing before a signal even reaches the model.
- **Spread Gate**: Ensures liquidity is sufficient for the trade.
- **Timing Gate**: Verifies the signal occurs within permitted trading windows.
- **Connectivity**: Confirms data feeds and broker connections are active.

### 2. Model Attribution
Provides a weighted breakdown of contributions from the ensemble's constituent models (e.g., PPO, LSTM, Dreamer).
- **Vote Direction**: The raw action suggested by each model.
- **Confidence**: Model-specific certainty scores.
- **Weight**: Current importance of the model in the ensemble.
- **Dominance**: Identifies the primary driver of the final decision.

### 3. Feature Contributions
Attributes decisions to specific feature clusters.
- **Trend Cluster**: Contribution from moving averages (EMA), ADX, and Hilbert Transform (`ht_`) trendlines.
- **Momentum Cluster**: Impact of RSI, MFI, MACD, Stochastic, and price velocity indicators (returns, log returns, and distance from moving averages).
- **Volatility Cluster**: Impact of ATR, Bollinger Band width, Keltner Channels, and price action range features (`body_size`, `day_range`).
- **Volume Cluster**: Influence of relative volume (`rvol`), OBV, VWAP distance, and volume profile proxies.
- **Pattern Cluster**: Contribution from candle pattern recognition (e.g., Hammer, Engulfing).

### 4. Market Regime Context
Provides the environmental background for the signal.
- **Detected Regime**: (e.g., Trending, Ranging, News Shock).
- **Regime Confidence**: Reliability of the regime classification.
- **Favorable Check**: Explicitly flags whether the strategy is optimized for the current state (e.g., "Market state is considered favorable" vs "Market state is UNFAVORABLE/CAUTIONARY").

### 5. Risk Assessment
The final gate where signals are validated against institutional risk constraints.
- **Risk-Reward Ratio**: Mandatory minimum R:R check.
- **Daily Loss Limits**: Protection against intraday drawdown.
- **Position Sizing**: Kelly Criterion or fixed-fractional sizing logic.

## Usage

### Generating an Explanation

```python
from src.core.explainability import SignalExplainer
from src.models.regime_detector import MarketRegime, RegimeInfo
from src.trading.execution_filter import ExecutionDecision

explainer = SignalExplainer()

# Using structured objects for deeper context
regime = RegimeInfo(
    label=MarketRegime.TRENDING,
    confidence=0.95,
    transition_score=0.1,
    volatility_index=1.1
)

explanation = explainer.explain(
    symbol="XAUUSD",
    direction=1,  # BUY
    confidence=0.85,
    model_votes={"ppo": 1, "lstm": 1},
    model_weights={"ppo": 0.7, "lstm": 0.3},
    risk_data={"passed": True, "risk_reward": 2.5, "summary": "Risk within limits"},
    regime_info=regime,
    # Supports automated feature clustering from raw scores
    feature_impacts={"base_M5_rsi": 0.8, "base_M5_slope": 0.7},
    # Pass optional signal_id for end-to-end traceability
    signal_id=42
)
```

### Visualizing in Terminal

The `SignalExplainer` utilizes the `rich` library to produce formatted dashboards:

```python
print(explainer.format_for_terminal(explanation))
```

## Advanced Attribution Features

### Individual Model Confidences
The `SignalExplainer.explain` method supports an optional `model_confidences` dictionary. This allows the ensemble to provide specific confidence scores for each constituent model, enabling more precise attribution and dominance calculation than the standard ensemble-level fallback.

### Granular Machine Attribution
The `machine_attribution` field provides high-fidelity metrics for post-trade analysis, including:
- **`risk_reward_ratio`**: The realized R:R for the trade.
- **`risk_rejection_reasons`**: Structured list of reasons if a signal was blocked by the risk engine.
- **`failed_execution_filters`**: Identification of specific execution gates (e.g., Spread, Timing) that prevented a trade.
- **`feature_impacts`**: Aggregated cluster-level scores for automated alpha decay analysis.

## Institutional Analysis

For post-trade analysis and backtesting, the `SignalExplanation` object includes a `machine_attribution` dictionary containing normalized metrics for automated evaluation of model and risk performance.
