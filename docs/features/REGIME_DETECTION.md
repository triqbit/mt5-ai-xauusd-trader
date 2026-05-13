# Market Regime Detection

The XAUUSD trading system utilizes a statistical regime detection layer to adapt its strategy to changing market conditions. This system classifies the market into six distinct regimes based on OHLCV data.

## Supported Regimes

| Regime | Description | Key Indicators |
|--------|-------------|----------------|
| `TRENDING` | Persistent directional movement with low noise. | High Efficiency Ratio, Consistent Slope. |
| `RANGING` | Choppy, sideways movement with no clear direction. | Low Efficiency Ratio, Low Volatility. |
| `VOLATILE_BREAKOUT` | Sharp directional move with increased volatility. | High ATR Ratio, High Efficiency Ratio. |
| `LOW_VOLATILITY_DRIFT` | Slow, persistent move on low volume/volatility. | Low ATR Ratio, Persistent Slope. |
| `NEWS_SHOCK` | Extreme volatility spike, typically news-driven. | Extreme ATR Ratio (> 2.0), High Efficiency. |
| `MEAN_REVERSION` | Price overextended from average, likely to pull back. | High Z-Score, Low Efficiency Ratio. |

## Statistical Features

The `RegimeDetector` calculates the following features:

1.  **ATR Ratio**: Ratio of short-term ATR (20 bars) to long-term ATR (100 bars). Used to detect volatility expansion/contraction.
2.  **Kaufman Efficiency Ratio (ER)**: Net price change divided by sum of absolute changes. Measures the "smoothness" of the price move.
3.  **Normalized Slope**: Linear regression slope of close prices, normalized by price level.
4.  **Price Z-Score**: Distance of current price from its moving average, measured in standard deviations.
5.  **Volatility Clustering**: Autocorrelation of absolute returns, identifying periods of persistent high or low volatility.
6.  **Vol-of-Vol**: Volatility of the rolling standard deviation, used to identify regime transitions and news-driven shocks.

## Transition Intelligence

The `RegimeDetector` includes advanced transition logic:
- **Transition Matrix**: During the `fit` phase, the detector calculates a transition probability matrix from the training data.
- **Dynamic Transition Score**: The `transition_score` returned by `detect` combines Shannon entropy of cluster probabilities with historical transition likelihoods. Higher scores indicate greater uncertainty or a more probable regime shift.

## Model Persistence

Fitted detectors can be persisted to disk to maintain consistency across trading sessions and research environments:

```python
# Saving
detector.save_model("models/regime_v1.joblib")

# Loading
new_detector = RegimeDetector()
new_detector.load_model("models/regime_v1.joblib")
```

## Usage

### Real-time Detection

```python
from src.models.regime_detector import RegimeDetector

detector = RegimeDetector()
# detector.load_model("path/to/model.joblib") # Recommended for production
regime_info = detector.detect(ohlcv_df)

print(f"Current Regime: {regime_info.label}")
print(f"Confidence: {regime_info.confidence}")
print(f"Transition Score: {regime_info.transition_score}")

# Granular transition distribution
print(f"Probabilities: {regime_info.transition_probabilities}")

# Raw features for explainability
print(f"Efficiency Ratio: {regime_info.raw_features['efficiency_ratio']}")
```

### Historical Labeling (for Backtesting)

The detector supports highly optimized vectorized labeling for research and backtesting:

```python
# Vectorized labeling
df_with_regimes = detector.label_history(historical_df, use_vectorized=True)
```

### Institutional Research Reporting

Generate comprehensive regime analysis reports directly from historical data:

```python
# Run historical analysis
analysis_report = detector.run_analysis(historical_df)

# Convert to reporting section for ResearchReporter
report_section = analysis_report.to_report_section()
```

### CLI Utility: Batch Labeling

A dedicated script is provided for batch processing of OHLCV CSV files:

```bash
# Label data using heuristic logic
python scripts/label_market_regimes.py --input data.csv --output labeled_data.csv

# Train a GMM model and label data
python scripts/label_market_regimes.py --input data.csv --output labeled_data.csv --model models/gmm_v1.joblib
```

## Implementation Details

The implementation is located in `src/models/regime_detector.py`. It unifies the logic between real-time inference and historical labeling by using the same vectorized feature extraction path, ensuring "what you test is what you trade."

## Validation Status

- [x] Vectorized feature extraction verified.
- [x] Heuristic regime transitions validated.
- [x] GMM clustering and cluster-to-regime mapping tested.
- [x] Historical labeling CLI utility verified.
- [x] Integration with institutional reporting suite confirmed.
