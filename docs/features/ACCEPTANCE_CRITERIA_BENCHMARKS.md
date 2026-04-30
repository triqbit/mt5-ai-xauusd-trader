# Benchmarking Framework

## Overview
This document outlines the acceptance criteria and usage for the benchmarking framework in `src/research/benchmarks.py`.

## Features
- **Consistent Interface**: All strategies implement the `BenchmarkStrategy` protocol.
- **Baseline Strategies**:
    - `EMACrossoverStrategy`: Fast/Slow EMA crossover logic.
    - `MomentumStrategy`: ROC-based trend following.
    - `VolatilityBreakoutStrategy`: Bollinger Band breakout signals.
    - `NaiveDirectionalStrategy`: Last candle direction persistence.
    - `RiskFilteredBaseline`: EMA crossover with a volatility threshold filter.
- **Quantitative Evaluator**:
    - Equity-curve-based backtesting.
    - Metrics: Total Return, Sharpe Ratio, Max Drawdown, Win Rate, Trade Count.
- **Statistical Comparison**:
    - Support for comparing strategy return distributions using Welch's t-test.
- **Model Adapters**:
    - `EnsembleAdapter`: Wraps `EnsembleModel`.
    - `PPOAdapter`: Wraps `PPOAgent`.
    - `TransformerAdapter`: Wraps `TimeSeriesTransformer`.

## Acceptance Criteria
- [x] All baseline strategies produce signals in the set {-1, 0, 1}.
- [x] Evaluator correctly calculates metrics from synthetic OHLCV data.
- [x] Comparison logic provides t-statistic and p-value for significance testing.
- [x] Linting passes (Ruff).
- [x] Unit tests in `tests/test_benchmarks.py` pass.
