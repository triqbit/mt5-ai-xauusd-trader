# Execution Quality Analytics

The Execution Quality Analytics system provides institutional-grade metrics to distinguish alpha quality from execution efficiency.

## Key Metrics

- **Execution Slippage**: Measured in pips, this is the difference between the requested signal price and the actual execution price.
- **Alpha Decay**: Measures price movement during the latency window (between signal generation and trade execution). High alpha decay suggests that the strategy's signals are being "front-run" by the market or that execution latency is too high.
- **Fill Quality**: A normalized score (0-1) derived from slippage relative to the market spread and execution latency.
- **Edge Capture**: Measures how much of the theoretical strategy edge was actually realized, adjusted for spread costs.
- **Timing Efficiency**: Evaluates if the entry occurred at a local price extreme within the entry bar.
- **Post-Entry Drift**: Tracks price movement at various horizons (1m, 5m, 15m, 30m, 60m) after entry to identify "toxic" flow or mean reversion patterns.

## Session-Aware Analysis

Execution quality is automatically categorized by market session:
- **Asian**: 00:00 - 09:00 UTC
- **London**: 08:00 - 17:00 UTC
- **London-NY Overlap**: 13:00 - 17:00 UTC
- **NY**: 13:00 - 22:00 UTC

## Blocked-Trade Quality

The system analyzes signals that were rejected by risk management (e.g., due to drawdown limits or circuit breakers). It calculates:
- **Opportunity Cost**: The realized PnL that would have been achieved if the trade had been taken.
- **MFE/MAE**: Maximum Favorable Excursion and Maximum Adverse Excursion for the rejected signal.
- **Would-Have-Won**: A boolean indicating if the signal would have reached its Take Profit before its Stop Loss.

## Integration

Analytics are automatically calculated for every trade and stored in the `execution_qualities` and `blocked_signal_analysis` database tables. Results are summarized in the Institutional Research Report.
