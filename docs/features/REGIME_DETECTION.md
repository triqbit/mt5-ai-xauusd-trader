# Market Regime Detector

The `RegimeDetector` classifies the market state of XAUUSD into one of the following regimes:

- **Trending**: Strong efficiency ratio and consistent price slope.
- **Ranging**: Low efficiency ratio and low price slope.
- **Volatile Breakout**: High efficiency ratio and high volatility (ATR) expansion.
- **Low-Volatility Drift**: Consistent price slope but low volatility.
- **News Shock**: Massive price move relative to recent volatility (high Z-score or ATR ratio).
- **Mean Reversion**: Extreme Z-score but low efficiency (likely to reverse).

## Features Used

- **ATR Ratio**: Short-term ATR divided by long-term ATR.
- **Efficiency Ratio**: Net price change divided by sum of absolute price changes (Kaufman).
- **Price Slope**: Linear regression slope of close prices.
- **Z-score**: Current price distance from moving average in standard deviations.

## Usage

```python
from src.models.regime_detector import RegimeDetector

detector = RegimeDetector(window=20, long_window=100)
regime_info = detector.detect(data)

print(f"Current Regime: {regime_info.label}")
print(f"Confidence: {regime_info.confidence}")
```

## Historical Labeling

```python
df_labeled = detector.label_history(data)
# Adds 'regime' and 'regime_confidence' columns to the DataFrame
```
