# Signal Explainability

The `SignalExplainer` provides institutional-grade transparency into why a trade signal was generated. It decomposes complex ensemble decisions into human-readable and machine-auditable components.

## Overview

In automated trading, "Black Box" models can lead to operator distrust and regulatory challenges. The Explainability module ensures every decision is justifiable by breaking down contributions from:
- **Individual Models:** Voting direction, confidence, and dominance within the ensemble.
- **Feature Clusters:** Aggregated impact from Momentum, Volatility, Trend, Volume, and Pattern features.
- **Market Regime:** Contextual awareness of the current environment (e.g., Trending, Ranging, News Shock).
- **Execution Filters:** Traceability of technical and operational gates.
- **Risk Assessment:** Institutional risk constraints and R:R calculations.

## Key Components

### 1. Feature Attribution
Features are grouped into logical clusters to help operators understand which market dynamics are driving the signal.

| Cluster | Key Features | Strategic Focus |
| :--- | :--- | :--- |
| **Momentum** | RSI, MACD, Returns, Efficiency Ratio, Z-Score | Directional velocity and exhaustion levels. |
| **Volatility** | ATR, Bollinger, Vol-of-Vol, Skewness, Kurtosis | Market stress and expansion potential. |
| **Trend** | EMA Slopes, ADX, Hilbert Transform | Structural directionality and trend strength. |
| **Volume** | RVol, OBV, VWAP, Volume Ratio | Liquidity participation and conviction. |

**Institutional Enhancement:** The explainer identifies the **Top 3 Drivers** within each cluster for granular transparency.

### 2. Regime-Aware Reasoning
The system provides tailored strategic rationale based on the detected institutional regime:
- **Trending:** Prioritizes persistent directional strength.
- **Ranging:** Prioritizes mean-reversion and liquidity corridors.
- **Volatile Breakout:** Focuses on expansion and trailing protection.
- **Mean Reversion:** Identifies corrective snap-back potential from overextended states.
- **News Shock:** Restricts execution to preserve capital during extreme dislocations.

### 3. Confluence Scoring
A unified **Confluence Score** (0.0 to 1.0) is calculated using a weighted formula:
- **40% Ensemble Confidence**
- **30% Regime Alignment**
- **15% Session Alignment**
- **15% Volatility Alignment**

## Usage

```python
from src.core.explainability import SignalExplainer

explainer = SignalExplainer()
explanation = explainer.explain(
    symbol="XAUUSD",
    direction=1,  # Buy
    confidence=0.85,
    model_votes={"PPO": 1, "LSTM": 1, "XGBoost": 0},
    model_weights={"PPO": 0.4, "LSTM": 0.4, "XGBoost": 0.2},
    risk_data={"passed": True, "risk_reward": 2.5},
    regime_info=regime_detector.get_regime(),
    execution_data=execution_filter.last_decision,
    feature_impacts=feature_importance_dict
)

# Access summaries
print(explanation.human_readable_summary)

# Get rendering for Rich terminal
renderable = explainer.get_renderable(explanation)
```

## Machine Attribution
For automated post-trade analysis, the `machine_attribution` field provides a dictionary of quantitative metrics, including model dominance ratios and cluster scores, suitable for storage in institutional trade logs or research databases.
