# Walk-Forward Optimization

## Overview
Walk-Forward Optimization (WFO) is a disciplined method for cross-validating strategy parameters by rolling through historical data in a series of "train" and "test" windows. This prevents over-fitting to a specific period and ensures the strategy remains robust across different market regimes.

## Implementation Details
Located in `src/research/hyperopt_walkforward.py`, the system provides:
- **Rolling Windows**: Automatic generation of overlapping or non-overlapping windows.
- **Robustness Scoring**: A multi-factor scoring system that penalizes instability.
- **Parameter Stability**: Measures how sensitive performance is to small changes in parameters.
- **Regime Consistency**: Rewards strategies that perform well across all detected market states.

## Robustness Metric
The `ROBUSTNESS_SCORE` is calculated as follows:
- **Reward**: Mean OOS Sharpe, Worst OOS Sharpe, consistency in win rate and drawdown.
- **Penalty**: Variance in OOS performance, IS-OOS performance gap, and Parameter Instability (Coefficient of Variation).

## Usage
```python
from src.research.hyperopt_walkforward import WalkForwardOptimizer, WalkForwardConfig
from src.research.benchmarks import EMACrossoverStrategy

# Define search space
def param_space(trial):
    return {
        "fast_window": trial.suggest_int("fast_window", 5, 20),
        "slow_window": trial.suggest_int("slow_window", 21, 50),
    }

# Configure and run
optimizer = WalkForwardOptimizer(
    data=df,
    strategy_factory=EMACrossoverStrategy,
    param_space=param_space,
    config=WalkForwardConfig(n_trials=50)
)
result = optimizer.run_optimization()
```
