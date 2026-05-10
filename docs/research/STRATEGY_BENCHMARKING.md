# Strategy Benchmarking Framework

## Overview
The Strategy Benchmarking Framework is designed to rigorously evaluate sophisticated trading models (e.g., RL agents, ensembles) against strong, rule-based baselines. This ensures that advanced strategies provide a measurable and defensible edge over simpler heuristics.

## Baseline Strategies
The framework includes several classic and naive strategies:
- **EMA Crossover**: Simple trend-following using fast and slow EMAs.
- **Momentum (ROC)**: Signal based on the Rate of Change of prices.
- **Volatility Breakout**: Bollinger Band breakout logic.
- **MACD**: Trend and momentum signals using the Moving Average Convergence Divergence.
- **Mean Reversion (RSI)**: Contrarian signals based on overbought/oversold levels.
- **Naive Directional**: Simple "follow the leader" (last candle direction).
- **Risk-Filtered EMA**: EMA crossover with a volatility filter.
- **Buy and Hold**: Simple benchmark that consistently maintains a long position.
- **Random**: Null hypothesis baseline for statistical comparison.

## Institutional Metrics
The evaluator calculates a comprehensive suite of metrics:
- **Stability**: R-squared of the equity curve, Ulcer Index, Lake Ratio.
- **Risk-Adjusted**: Sharpe, Sortino, Calmar, Gain-to-Pain Ratio.
- **Tail Risk**: VaR (95%), CVaR (95%), Tail Ratio.
- **Quality**: SQN, Profit Factor, Expectancy, Recovery Factor.

## Statistical Comparison
The framework uses a dual statistical approach to compare return distributions:
1.  **Paired T-test**: Parametric test for comparing means of return distributions.
2.  **Wilcoxon Signed-Rank Test**: Non-parametric test that is more robust to non-normal return distributions common in financial data.

These tests calculate **P-Values** to determine if a strategy's outperformance over a baseline is statistically significant (p < 0.05).

## Usage
Benchmarks are integrated into the `ResearchReporter` and can be evaluated using the `BenchmarkEvaluator`. Adapters are provided for standard model architectures (PPO, Ensemble, Transformer, etc.).
