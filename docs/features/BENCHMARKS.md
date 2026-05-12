# Institutional Benchmarking Framework

The Institutional Benchmarking Framework provides a standardized way to evaluate advanced AI trading models against classic industry baselines for XAUUSD trading.

## Supported Baselines

- **EMA Crossover**: Standard fast/slow moving average crossover.
- **Momentum (ROC)**: Rate of Change indicator to follow price trends.
- **Volatility Breakout**: Bollinger Band expansion signals.
- **Naive Directional**: Persistence of the previous candle's direction.
- **ADX Trend**: Trend-following strategy using the Average Directional Index (ADX) and Directional Indicators (+DI/-DI).
- **Risk-Filtered EMA**: EMA crossover logic combined with a volatility regime filter.
- **MACD**: Moving Average Convergence Divergence.
- **Mean Reversion**: RSI-based overbought/oversold logic.
- **Random**: Null-hypothesis baseline generating reproducible random signals.
- **Buy and Hold**: Benchmark for market beta.

## Advanced Metrics

The framework calculates a wide array of institutional-grade metrics:
- **Execution Costs**: Support for transaction commissions and execution slippage per trade.
- **Risk-Adjusted Returns**: Sharpe Ratio, Sortino Ratio, Calmar Ratio.
- **Trading Quality**: Profit Factor, Expectancy, System Quality Number (SQN).
- **Risk Metrics**: Max Drawdown, Value at Risk (VaR 95%), Conditional VaR (CVaR 95%), Ulcer Index.
- **Stability**: Stability Score (R-squared of equity curve), Tail Ratio, Gain-to-Pain Ratio.

## Statistical Comparison

Sophisticated strategies can be compared against any baseline using dual statistical tests:
1. **Paired T-test**: Compares the distribution of returns under identical market conditions.
2. **Wilcoxon Signed-Rank Test**: A non-parametric test for performance significance, robust to non-normal return distributions.

## Model Adapters

Adapters are provided for all major project models, supporting rolling window lookbacks and market regime awareness:
- `EnsembleAdapter`
- `PPOAdapter`
- `TransformerAdapter`
- `LSTMAdapter`
- `DreamerAdapter`

## Usage Example

See `src/research/benchmark_demo.py` for a full demonstration of the benchmarking pipeline.
