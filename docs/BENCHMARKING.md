# Strategy Benchmarking Framework

The MT5 AI/ML Trading Bot includes a comprehensive benchmarking framework to compare advanced AI models against standard trading baselines using institutional-grade metrics and statistical verification.

## Core Objective

To prove that sophisticated strategies (Ensemble, RL, Deep Learning) outperform simple heuristics in a defensible and measurable way.

## Baseline Strategies

The following rule-based baselines are available in `src/research/benchmarks.py`:

- **Buy and Hold**: Passive long baseline.
- **Sell and Hold**: Passive short baseline.
- **EMA Crossover**: Simple trend-following using fast and slow Exponential Moving Averages.
- **Momentum (ROC)**: Momentum-based strategy using Rate of Change with a configurable noise-filtering threshold.
- **Volatility Breakout**: Bollinger Band breakout strategy.
- **Donchian Channel Breakout**: Trend-following breakout based on high/low price channels.
- **Naive Directional**: Follows the direction of the previous candle.
- **Risk-Filtered EMA**: EMA Crossover supplemented with a volatility filter to avoid choppy markets.
- **Mean Reversion (RSI)**: RSI-based overbought/oversold reversal strategy.
- **Random (Null Hypothesis)**: Generates random signals to establish a baseline for statistical significance.

## Institutional Metrics

The `BenchmarkEvaluator` calculates high-fidelity metrics beyond simple returns:

- **Total Return**: Aggregate percentage P&L.
- **Sharpe Ratio**: Risk-adjusted return (annualized).
- **Sortino Ratio**: Downside risk-adjusted return.
- **Calmar / Recovery Factor**: Ratio of total return to maximum drawdown.
- **Annualized Volatility**: Standard deviation of daily returns scaled to one year.
- **System Quality Number (SQN)**: Evaluates trade quality and expectancy relative to volatility.
- **Profit Factor**: Gross Profit / Gross Loss.
- **Expectancy**: Average profit expected per trade.
- **Skewness & Kurtosis**: Measures of the return distribution shape.
- **Value at Risk (VaR 95%)**: Potential loss at the 95% confidence level.
- **Conditional VaR (CVaR 95%)**: Expected loss exceeding VaR.
- **Stability Score**: Consistency of the equity curve (R-squared of linear fit).
- **Ulcer Index**: Measure of drawdown depth and duration.
- **Tail Ratio**: Ratio of the 95th percentile to the 5th percentile of returns.
- **Common Sense Ratio**: Tail Ratio multiplied by Profit Factor.
- **Gain-to-Pain Ratio**: Sum of positive returns divided by the absolute sum of negative returns.

## Statistical Comparison

The framework uses a **Paired T-Test** (`scipy.stats.ttest_rel`) to compare the return distributions of a strategy against a baseline (typically the Random Baseline).

- **Outperformance**: Absolute difference in total returns.
- **P-Value**: Indicates if the outperformance is statistically significant (p < 0.05).
- **Significant**: Boolean flag indicating if the strategy reliably beats the baseline.

## Model Adapters

To enable a "fair fight," the framework provides adapters that wrap complex models into a consistent `BenchmarkStrategy` interface:

- `EnsembleAdapter`: Wraps the `EnsembleModel`.
- `PPOAdapter`: Wraps the `PPOAgent`.
- `TransformerAdapter`: Wraps the `TimeSeriesTransformer`.
- `LSTMAdapter`: Wraps the `LSTMAttentionModel`.
- `DreamerAdapter`: Wraps the `DreamerAgent`.

## Usage Example

### Running a Benchmark Verification

```python
from src.research import BenchmarkEvaluator, EMACrossoverStrategy, RandomStrategy
import pandas as pd

# 1. Load your data
df = pd.read_csv("data/XAUUSD_M5.csv")

# 2. Define strategies
strategies = [
    EMACrossoverStrategy(9, 21),
    RandomStrategy(seed=42)
]

# 3. Evaluate
evaluator = BenchmarkEvaluator(df)
summary_df = evaluator.evaluate_all(strategies)

# 4. Compare statistically
comparison = evaluator.compare_to_baseline("EMA_Crossover_9_21", "Random_Baseline_seed_42")
print(f"Significant Outperformance: {comparison['Significant']}")
```

### Integrated Reporting

The benchmarking results can be integrated into institutional research reports via the `ResearchReporter` and `ResearchOrchestrator`.

```python
section = evaluator.to_report_section(baseline_name="Random_Baseline_seed_42")
# Add section to ResearchReport
```
