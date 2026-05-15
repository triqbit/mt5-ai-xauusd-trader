# Market Regime Detection

The market regime detection system is designed to classify XAUUSD market states into distinct environments to improve strategy adaptability and risk management.

## Detected Regimes

The system classifies the market into the following regimes:

- **Trending**: Strong directional move with high efficiency.
- **Ranging**: Side-ways price action with low directional conviction.
- **Volatile Breakout**: High volatility expansion with significant price moves.
- **Low-Volatility Drift**: Slow, steady directional movement with low noise.
- **News Shock**: Extreme volatility spikes and violent price adjustments, typically driven by macroeconomic events.
- **Mean-Reversion**: Overextended price levels likely to snap back to the mean.

## Methodology

The `RegimeDetector` utilizes institutional-grade normalization and a combination of statistical features derived from OHLCV data:

- **Robust Normalization**: All features are normalized using `StandardScaler` from `scikit-learn` before being passed to the GMM. Centroids are inverse-transformed to ensure heuristic mapping logic remains explainable on raw feature scales.

- **ATR Ratio**: Short-term vs. long-term Average True Range to detect volatility expansions or contractions.
- **Kaufman Efficiency Ratio (ER)**: Measures the efficiency of price moves (net change / sum of absolute changes).
- **Slope and Angle**: Linear regression slope of prices, scaled to degrees, to determine trend strength.
- **Z-Score**: Distance from the rolling mean to identify overextended conditions.
- **Volatility Clustering**: Autocorrelation of absolute returns to detect persistent volatility states.
- **Vol-of-Vol**: Volatility of volatility to distinguish between steady trends and chaotic price action.

## Usage

The system supports two detection modes:

1. **Heuristic Detection**: Uses expert-defined thresholds for rapid, explainable classification.
2. **Clustering Detection (GMM)**: Utilizes Gaussian Mixture Models to learn market states from historical data autonomously.

### Historical Labeling

The `label_history` method provides a performance-optimized, vectorized utility for adding regime classifications to historical DataFrames, suitable for backtesting and research.

### Performance Analysis

The `get_regime_performance` method calculates historical P&L analysis partitioned by market regime, providing critical metrics for strategy optimization:

- **Sharpe Ratio**: Risk-adjusted returns per regime.
- **Mean Return**: Expected profitability in specific environments.
- **Total Return**: Cumulative impact of the regime on the portfolio.

```python
from src.models.regime_detector import RegimeDetector

detector = RegimeDetector()
df_with_regimes = detector.label_history(historical_df)
```
