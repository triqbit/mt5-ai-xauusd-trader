# Execution Quality Analytics

The Execution Quality module (`src/analytics/execution_quality.py`) provides institutional-grade analytics to distinguish between alpha quality (the model's predictive power) and execution quality (the efficiency of trade implementation).

## Key Metrics

### 1. Execution Slippage & Alpha Decay
*   **Total Slippage**: The difference between the signal price and the actual execution price.
*   **Alpha Decay**: Price movement between the signal generation and the execution start. This isolates market movement from broker execution.
*   **Broker Slippage**: Pure execution drag, calculated as `Total Slippage - Alpha Decay`.

### 2. Implementation Shortfall (IS)
The total cost from signal generation to fill, including both alpha decay and execution slippage. This is a comprehensive measure of trade implementation efficiency.

### 3. Excursion Analysis (MFE/MAE)
*   **Maximum Favorable Excursion (MFE)**: The peak profit observed during the trade's duration (or after a blocked signal).
*   **Maximum Adverse Excursion (MAE)**: The maximum loss (drawdown) observed during the trade's duration.
*   Measured in pips for precision.

### 4. Effective Spread
Calculated using the institutional standard: `2.0 * |execution_price - mid_price|`. This measures how much spread was actually paid relative to the estimated mid-price at the time of fill.

### 5. Post-Entry Markouts
Price drift measured at multiple horizons (1m, 5m, 15m, 30m, 60m) using M1 mid-prices. This identifies if entries are being "run over" or if they capture immediate edge.

### 6. Fill Quality & Timing Efficiency
*   **Fill Quality Score**: A normalized score (0-1) based on slippage-to-spread ratio and execution latency.
*   **Timing Efficiency**: Measures if the entry occurred near a local extreme of the execution candle.

## Opportunity Cost Analysis
Rejected signals are analyzed for what *would have happened*.
*   Hypothetical outcomes use Take Profit (TP) and Stop Loss (SL) triggers within a 24-hour look-ahead window.
*   **Conservative Logic**: If both TP and SL are hit within the same candle, the system assumes the SL was hit first.

## Persistence
All metrics are persisted in the `execution_qualities` and `blocked_signal_analysis` database tables. Detailed markout and excursion data are stored as JSON in the `markout_data` field for long-term research.
