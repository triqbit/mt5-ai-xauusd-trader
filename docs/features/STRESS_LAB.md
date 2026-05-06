# Institutional Strategy Stress Lab

The Stress Lab is an adversarial resilience testing framework designed for XAUUSD trading strategies. It goes beyond standard historical backtesting by replaying historical data under synthetic adverse conditions.

## Key Features

- **Adversarial Simulation**: Replays trades with synthetic execution friction including spread widening, stochastic slippage spikes, missing ticks, and execution delays.
- **Realistic Market Stress**: Perturbs price action using ATR-relative shocks to simulate choppy fake breakouts and sudden regime transitions or trend exhaustion.
- **Infrastructure Resilience**: Simulates external service failures to test strategy stability under degraded conditions.
- **Structured Reporting**: Outputs research-grade metrics and resilience reports, identifying failure points and resilience weaknesses. Includes institutional metrics such as **Recovery Factor** and **Profit Factor**.
- **Fragility Intelligence**: Automatically detects 'strategy fragility' indicators including over-trading spikes (2x baseline trade count) and negative edge transitions (Profit Factor dropping below 1.0) under stress.

## Stress Scenarios

The framework provides factory methods for common high-severity scenarios:

1.  **Execution Hell**: Extreme execution friction with wide spreads (3x multiplier), significant slippage spikes (50 bps), and high latency (3 steps).
2.  **Liquidity Crisis**: Fragmented liquidity simulation with 20% missing ticks, price noise, and frequent fake breakouts.
3.  **Regime Shock**: Market structural instability with frequent (10% prob) regime flips and trend reversals.
4.  **Flash Crash**: Violent price dislocation with sudden deep drops (5-10 ATRs) and extreme slippage (200 bps).

## Resilience Metrics

Strategies are evaluated on several robustness indicators:

- **Composite Resilience Score**: A score from 0-100 indicating performance retention under stress.
- **Max Slippage Experienced**: Tracks the single largest slippage event encountered.
- **Execution Quality Score**: Measures the percentage of successfully executed signals despite service outages.
- **Fragility Indicators**: Automated detection of non-linear performance degradation (e.g., drawdown doubling, Sharpe ratio halving, infrastructure delay sensitivity, or extreme slippage sensitivity under stress).

## Integration

The Stress Lab is integrated with the `ResearchReporter` system, allowing resilience results to be included in consolidated institutional research reports.
