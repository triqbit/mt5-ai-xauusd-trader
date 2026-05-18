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
- **Walk-Forward Efficiency (WFE)**: Ratio of OOS Sharpe to IS Sharpe. High WFE indicates a strategy that translates well from training to live-simulated trading. The score rewards WFE up to 1.2.
- **Regime Consistency**: Performance stability across different market regimes (Trending, Ranging, etc.), frequency-weighted to ensure statistical significance. Gracefully handles sparse data by returning a neutral score (0.5) when fewer than two regimes are present.
- **Stability Penalty**: Sensitivity of performance to small parameter perturbations. Uses scale-robust epsilon (1e-5) for float parameters and ensures integer parameters remain integers during sensitivity sweeps. Calculated using Coefficient of Variation (CV) with fragility safeguards. Uses a default annualization of 6240 bars/year, optimized for H1 intraday XAUUSD trading.
- **Granular Sensitivity Tracking**: The optimizer now tracks individual Coefficient of Variation (CV) scores for each parameter across windows. This identifies which specific hyperparameters are most responsible for strategy fragility.

### 3. Institutional Reporting
WFO results are integrated into the `ResearchReport` framework.
- **Robustness Grade**: A qualitative grade (A-F) based on institutional standards:
    - **A**: Excellent robustness (>1.0), high WFE (>0.7), high regime consistency (>0.7), no violations.
    - **B**: Good robustness (>0.6), moderate WFE (>0.5), no major violations.
    - **C**: Acceptable robustness (>0.3), no major violations.
    - **F**: Critical failure or constraint violations.
- **Stability Score**: An aggregate robustness metric scaled from 0 to 100.
- **Parameter Analysis**: Each optimized parameter is tagged with a qualitative sensitivity label:
    - **Low**: CV < 0.2
    - **Medium**: 0.2 <= CV < 0.5
    - **High**: CV >= 0.5 (indicates a potential overfitting risk or extreme fragility)

### 4. Anti-Overfitting Safeguards
- **Fragility Safeguards**: A high penalty (10.0) is applied if parameter perturbations lead to failures or extreme performance drops.
- **Constraint Enforcement**: Institutional constraints are strictly enforced. Configurations failing any of these incur heavy penalties:
    - **Min OOS Sharpe**: Minimum allowed Sharpe ratio in out-of-sample windows.
    - **Max OOS Drawdown**: Maximum allowed drawdown in out-of-sample windows.
    - **Min Regime Consistency**: Minimum required stability across market regimes.
    - **Min Walk-Forward Efficiency**: Minimum required ratio of OOS to IS performance.
- **Minimum Trade Threshold**: A `min_trades_per_window` constraint (default: 5) ensures that OOS performance is statistically grounded. Windows with too few trades incur a linear penalty to the robustness score.

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

## CI Status
This module is verified through automated Walk-Forward Efficiency (WFE) and parameter stability checks.
