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
- **Volume Ratio**: Short-term vs. long-term average `tick_volume` to identify high-conviction participation during breakouts and news shocks.
- **Kaufman Efficiency Ratio (ER)**: Measures the efficiency of price moves (net change / sum of absolute changes).
- **Slope and Angle**: Linear regression slope of prices, scaled to degrees, to determine trend strength.
- **Z-Score**: Distance from the rolling mean to identify overextended conditions.
- **Volatility Clustering**: Autocorrelation of absolute returns to detect persistent volatility states.
- **Vol-of-Vol**: Volatility of volatility to distinguish between steady trends and chaotic price action.

## Strategic Alignment

To support institutional-grade signal attribution, the system provides two alignment metrics:

- **Session Alignment**: Measures the alignment of the current timestamp with major trading sessions (London and New York). Peak scores (1.0) are awarded during the London/NY overlap, while lower scores (0.3-0.5) indicate quiet or Asian sessions.
- **Volatility Alignment**: Quantifies how well the current ATR-based volatility matches the detected regime. For example, a `NEWS_SHOCK` is only considered highly aligned if accompanied by extreme volatility, whereas `RANGING` states favor lower volatility.

## Usage

The system supports two detection modes:

1. **Heuristic Detection**: Uses expert-defined thresholds (including ATR, volume, and efficiency ratios) for rapid, explainable classification.
2. **Clustering Detection (GMM)**: Utilizes Gaussian Mixture Models to learn market states from historical data autonomously. Supports adaptive selection of the optimal number of clusters based on the **Bayesian Information Criterion (BIC)**.

### Historical Labeling

The `label_history` method provides a performance-optimized, vectorized utility for adding regime classifications to historical DataFrames, suitable for backtesting and research.

### Visualization

The `print_transition_matrix` method provides a rich terminal visualization of the regime transition probabilities, allowing operators to understand the stability and typical paths of market state changes.

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
