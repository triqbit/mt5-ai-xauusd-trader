# Strategy Stress Laboratory

The Stress Lab is an institutional-grade resilience testing framework that evaluates trading strategies under adversarial market conditions. It goes beyond standard historical backtesting by injecting synthetic friction, data instability, and regime shocks to identify non-linear failure points.

## Key Adverse Conditions

The Stress Lab replays historical data with the following perturbations:

- **Spread Widening**: Simulates liquidity dry-ups by applying multipliers to base spreads and injecting random spikes.
- **Slippage Spikes**: Models extreme execution costs during high-volatility events (e.g., news shocks).
- **Execution Delays**: Tests strategy sensitivity to infrastructure latency and delayed fills.
- **Data Gaps**: Simulates missing ticks and stale data to verify strategy stability during feed interruptions.
- **Market Structural Shocks**: Induces choppy fake breakouts, sudden regime flips, and flash crashes.
- **Service Outages**: Simulates external service failures that block signals.

## Resilience Reporting

Each stress test generates a comprehensive report including:

- **Resilience Score (0-100)**: A composite metric of performance retention under stress.
- **Fragility Indicators**: Automated detection of over-trading, drawdown explosions, or negative edge transitions.
- **Breaking Points**: Identifies the exact level of friction (e.g., number of delay steps) where a strategy becomes unprofitable.
- **Institutional Metrics**: Tracks Profit Factor (PF) and Recovery Factor across all scenarios.
- **Hardened Analytics**: Implements robust decay calculations for Sharpe and Sortino ratios, handling negative or near-zero baselines with absolute scaling and outlier clipping for enterprise stability.

## Usage

```python
from src.research.stress_lab import StressLab, StressTestMetrics
from src.research.benchmarks import EMACrossoverStrategy

# 1. Initialize strategy and data
strategy = EMACrossoverStrategy()
data = ... # pd.DataFrame with OHLCV

# 2. Define baseline metrics (from normal backtest)
baseline = StressTestMetrics(...)

# 3. Run the stress laboratory
lab = StressLab(strategy, data)
report = lab.run_standard_suite(baseline)

# 4. Generate research report
report_section = report.to_report_section()
```

For a full demonstration, run:
`PYTHONPATH=. python3 src/research/stress_test_demo.py`
