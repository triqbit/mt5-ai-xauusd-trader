# Walk-Forward Optimization (WFO)

## Overview
The Walk-Forward Optimization module (`src/research/hyperopt_walkforward.py`) implements a disciplined approach to strategy parameter selection. Unlike static backtesting, WFO simulates the process of periodically re-optimizing a strategy on recent history and testing it on a subsequent "out-of-sample" period.

## Core Components

### 1. Rolling Windows
The system generates a series of training (In-Sample) and testing (Out-of-Sample) data splits.
- **Train Size**: Number of bars used for parameter optimization.
- **Test Size**: Number of bars used for validation.
- **Step Size**: The interval by which the windows advance.

### 2. Robustness Scoring
Configurations are ranked by a multi-factor `Robustness Score` rather than simple total return. This score rewards consistency and penalizes instability:
- **OOS Mean Sharpe**: Average Sharpe ratio across all test windows.
- **Worst OOS Sharpe**: Performance in the most difficult market period.
- **Consistency**: 1 - Coefficient of Variation for win rates and drawdowns.
- **IS-OOS Gap**: Penalty for strategies that perform significantly better in training than in testing (overfitting).
- **Regime Consistency**: Performance stability across different market regimes (Trending, Ranging, etc.), frequency-weighted to ensure statistical significance.
- **Stability Penalty**: Sensitivity of performance to small parameter perturbations, calculated using Coefficient of Variation (CV) with fragility safeguards.

### 3. Anti-Overfitting Safeguards
- **Fragility Safeguards**: A high penalty (10.0) is applied if parameter perturbations lead to failures or extreme performance drops.
- **Constraint Enforcement**: Minimum allowed OOS Sharpe and maximum allowed OOS Drawdown are strictly enforced.

## Usage
```python
from src.research.hyperopt_walkforward import WalkForwardOptimizer, WalkForwardConfig

optimizer = WalkForwardOptimizer(
    data=df,
    strategy_factory=MyStrategy,
    param_space=my_param_space,
    config=WalkForwardConfig(
        train_size=250,
        test_size=50,
        step_size=50,
        n_trials=100
    )
)

result = optimizer.run_optimization()
print(f"Best Params: {result.best_params}")
print(f"Robustness Score: {result.metrics.robustness_score}")
```
