# Market Regime Detection

The XAUUSD trading system utilizes a statistical regime detection layer to adapt its strategy to changing market conditions. This system classifies the market into six distinct regimes based on OHLCV data.

## Supported Regimes

| Regime | Description | Key Indicators |
|--------|-------------|----------------|
| `TRENDING` | Persistent directional movement with low noise. | High Efficiency Ratio, Consistent Slope. |
| `RANGING` | Choppy, sideways movement with no clear direction. | Low Efficiency Ratio, Low Volatility. |
| `VOLATILE_BREAKOUT` | Sharp directional move with increased volatility. | High ATR Ratio, High Efficiency Ratio. |
| `LOW_VOLATILITY_DRIFT` | Slow, persistent move on low volume/volatility. | Low ATR Ratio, Persistent Slope. |
| `NEWS_SHOCK` | Extreme volatility spike, typically news-driven. | Extreme ATR Ratio (> 2.5), High Efficiency. |
| `MEAN_REVERSION` | Price overextended from average, likely to pull back. | High Z-Score, Low Efficiency Ratio. |

## Statistical Features

The `RegimeDetector` calculates the following features:

1.  **ATR Ratio**: Ratio of short-term ATR (20 bars) to long-term ATR (100 bars). Used to detect volatility expansion/contraction.
2.  **Kaufman Efficiency Ratio (ER)**: Net price change divided by sum of absolute changes. Measures the "smoothness" of the price move.
3.  **Normalized Slope**: Linear regression slope of close prices, normalized by price level.
4.  **Price Z-Score**: Distance of current price from its moving average, measured in standard deviations.
5.  **Volatility Clustering**: Autocorrelation of absolute returns, identifying periods of persistent high or low volatility.

## Usage

### Real-time Detection

```python
from src.models.regime_detector import RegimeDetector

detector = RegimeDetector()
regime_info = detector.detect(ohlcv_df)

print(f"Current Regime: {regime_info.label}")
print(f"Confidence: {regime_info.confidence}")
```

### Historical Labeling (for Backtesting)

```python
df_with_regimes = detector.label_history(historical_df)
```

## Implementation Details

The implementation is located in `src/models/regime_detector.py` and is designed for high performance using vectorized operations via `pandas` and `numpy`.
