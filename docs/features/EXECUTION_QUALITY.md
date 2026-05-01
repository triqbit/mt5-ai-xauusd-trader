# Execution Quality Analytics

The `ExecutionAnalyzer` module provides institutional-grade analytics to measure execution efficiency and trade quality. It helps distinguish between alpha quality (model performance) and execution quality (the cost of getting in and out of the market).

## Features

- **Execution Slippage**: Measures the difference between the signal's entry price and the actual fill price.
- **Fill Quality Score**: A heuristic score (0.0 to 1.0) that penalizes high slippage and latency.
- **Opportunity Cost Analysis**: Evaluates signals rejected by the Risk Manager by calculating their potential PnL, Maximum Favorable Excursion (MFE), and Maximum Adverse Excursion (MAE).
- **Timing Efficiency**: Measures how close the entry price was to the optimal price within the entry candle.
- **Edge Capture**: Compares realized profit against the theoretical potential of the signal.
- **Post-Entry Drift**: Tracks price movement 5 and 15 minutes after entry to monitor alpha decay.

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
| Edge Capture | `(Exit - Entry) / (TakeProfit - SignalEntry)` |
| Drift | Price movement N minutes after entry in the direction of the trade. |

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
