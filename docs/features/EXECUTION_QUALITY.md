# Execution Quality Analytics

The `ExecutionAnalyzer` module provides institutional-grade analytics to measure execution efficiency and trade quality. It helps distinguish between alpha quality (model performance) and execution quality (the cost of getting in and out of the market).

## Features

- **Execution Slippage**: Measures the difference between the signal's entry price and the actual fill price.
- **Fill Quality Score**: A heuristic score (0.0 to 1.0) that penalizes high slippage and latency.
- **Opportunity Cost Analysis**: Evaluates signals rejected by the Risk Manager by calculating their potential PnL, Maximum Favorable Excursion (MFE), and Maximum Adverse Excursion (MAE).
- **Timing Efficiency**: Measures how close the entry price was to the optimal price within the entry candle.
- **Edge Capture**: Compares realized profit against the theoretical potential of the signal.
- **Post-Entry Drift (Markouts)**: Tracks price movement at multiple horizons (1m, 5m, 15m, 30m, 60m) after entry to distinguish alpha from execution quality.
- **Execution Cost Tracking**: Introduced `execution_cost_pips` which includes both slippage and half of the prevailing spread.
- **Improved Fill Quality Score**: Uses a spread-relative sigmoid model to penalize slippage more fairly across different volatility regimes.
- **Alpha Decay Tracking**: Measures price movement between signal generation and actual execution to quantify information loss.
- **Spread-Aware Metrics**: Tracks spread at execution and calculates slippage-to-spread ratios.
- **Dynamic Instrument Property Detection**: Automatically detects pip sizes and contract sizes for diverse asset classes (FX, Gold, Indices) via the `MT5Connector`.
- **Standardized UTC Temporal Logic**: Ensures consistent timezone handling for robust cross-instrument analytics.

## Implementation Details

The system correlates records from three database tables:
1. `ModelSignal`: The theoretical intent.
2. `Trade`: The actual execution.
3. `RiskEvent`: Logs of rejected signals.

### Key Metrics

| Metric | Description |
|--------|-------------|
| Slippage (Pips) | `(Actual Price - Signal Price) * Direction / PipSize` |
| Latency (ms) | `Execution Time - Signal Time` |
| Edge Capture | `(Realized PnL - 0.5 * Spread) / Theoretical PnL` |
| Drift | Price movement N minutes after entry in the direction of the trade. |
| Alpha Decay | Price movement between signal and execution. |
| Slippage/Spread Ratio | Slippage relative to the prevailing spread. |

## Usage

```python
from src.analytics.execution_quality import ExecutionAnalyzer

analyzer = ExecutionAnalyzer(db_url="sqlite:///trades.db", connector=mt5_connector)

# Analyze a specific trade
quality = analyzer.analyze_trade(trade_id=123)

# Generate a weekly summary report
summary = analyzer.generate_summary_report(days=7)
print(summary.model_dump_json(indent=2))
```
