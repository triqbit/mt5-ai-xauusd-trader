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
- **Trend Cluster**: Contribution from moving averages and price action.
- **Volatility Cluster**: Impact of ATR and Bollinger Band features.
- **Liquidity Cluster**: Influence of volume and order book depth.

### 4. Market Regime Context
Provides the environmental background for the signal.
- **Detected Regime**: (e.g., Trending, Ranging, News Shock).
- **Regime Confidence**: Reliability of the regime classification.
- **Favorable Check**: Whether the strategy is optimized for the current state.

### 5. Risk Assessment
The final gate where signals are validated against institutional risk constraints.
- **Risk-Reward Ratio**: Mandatory minimum R:R check.
- **Daily Loss Limits**: Protection against intraday drawdown.
- **Position Sizing**: Kelly Criterion or fixed-fractional sizing logic.

## Usage

### Generating an Explanation

```python
from src.core.explainability import SignalExplainer

explainer = SignalExplainer()
explanation = explainer.explain(
    symbol="XAUUSD",
    direction=1,  # BUY
    confidence=0.85,
    model_votes={"ppo": 0, "lstm": 0},
    model_weights={"ppo": 0.7, "lstm": 0.3},
    risk_data={"passed": True, "risk_reward": 2.5, "summary": "Risk within limits"},
    regime_info={"name": "Trending", "confidence": 0.9, "volatility": "Normal"},
    feature_impacts=[{"cluster": "Trend", "score": 0.8, "impact": "High", "summary": "Strong momentum"}]
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

## Institutional Analysis

For post-trade analysis and backtesting, the `SignalExplanation` object includes a `machine_attribution` dictionary containing normalized metrics for automated evaluation of model and risk performance.
