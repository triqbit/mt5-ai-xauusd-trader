# Walk-Forward Optimization Framework

## Overview

The Walk-Forward Optimization (WFO) framework in the MT5 AI/ML Trading Bot is designed for disciplined strategy evaluation and parameter optimization. Unlike simple backtesting, WFO uses a rolling window approach to ensure that strategy parameters are robust across different market regimes and out-of-sample periods.

## Core Components

### 1. Rolling Window Generation
The framework generates multiple "train" and "test" window pairs:
- **Train Window:** Used to optimize strategy parameters.
- **Test Window:** Used to evaluate the optimized parameters on unseen data (Out-of-Sample).
- **Step Size:** Determines how much the windows advance in each iteration.

### 2. Robustness Scoring
Rather than simply maximizing total return or Sharpe ratio, the framework uses a **Robustness Score** to rank configurations. This score rewards consistency and penalizes overfitting.

The Robustness Score is composed of:
- **OOS Sharpe Mean:** The average Sharpe ratio across all out-of-sample windows.
- **Worst Window Sharpe:** Performance in the single worst OOS window, ensuring "no blow-up" scenarios.
- **Consistency Metrics:** Rewards stable win rates and drawdowns across windows.
- **OOS Sharpe Std (Penalty):** Penalizes high variance in performance across windows.
- **IS-OOS Gap (Penalty):** Penalizes significant performance drops between in-sample and out-of-sample data, a key indicator of overfitting.
- **Stability Penalty:** Measures sensitivity to small parameter changes (continuous perturbation) using disciplined training-only evaluation.
- **Regime Consistency:** Rewards strategies that perform consistently across different detected market regimes (Trending, Ranging, Volatile, etc.).

### 3. Parameter Stability Analysis
The optimizer performs "sensitivity checks" by slightly perturbing optimized parameters. If a small change in a parameter leads to a large change in performance, the parameter set is deemed unstable and penalized.

#### Strict Fragility Safeguard
The framework implements a **Strict Fragility** check. If a small parameter perturbation causes the Sharpe Ratio to flip from positive to negative (or return a NaN), the configuration is immediately assigned the maximum stability penalty. This ensures that "edge-of-a-cliff" configurations, which may look good in backtests but are highly sensitive to market noise, are excluded from the final selection.

## Configuration

The `WalkForwardConfig` model allows for granular control:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `train_size` | Number of candles for optimization | 250 |
| `test_size` | Number of candles for OOS testing | 50 |
| `step_size` | Rolling step for windows | 50 |
| `min_windows` | Minimum required windows | 3 |
| `metric` | Optimization target (e.g., `robustness_score`, `sharpe`) | `robustness_score` |
| `robustness_weights` | Configurable weights for score calculation | `RobustnessWeights()` |
| `n_trials` | Optuna trials per optimization | 50 |
| `bars_per_year` | Bars per year for annualization | 252 |

### Robustness Weights

The scoring can be customized via the `RobustnessWeights` model:

| Weight | Description | Default |
|--------|-------------|---------|
| `oos_mean` | Mean OOS Sharpe Ratio | 0.4 |
| `worst_oos` | Worst window OOS Sharpe | 0.2 |
| `win_rate_consistency` | Win rate (1-CV) | 0.1 |
| `drawdown_consistency` | Max drawdown (1-CV) | 0.1 |
| `oos_std` | Sharpe variance penalty | 0.3 |
| `is_oos_gap` | IS-OOS gap penalty | 0.2 |
| `stability` | Parameter sensitivity penalty | 0.3 |
| `regime_consistency` | Consistency across regimes | 0.1 |

## Usage Example

```python
from src.research.hyperopt_walkforward import WalkForwardOptimizer, WalkForwardConfig
from src.research.benchmarks import EMACrossoverStrategy

# 1. Define parameter space
def param_space(trial):
    return {
        "fast_window": trial.suggest_int("fast_window", 5, 20),
        "slow_window": trial.suggest_int("slow_window", 21, 50)
    }

# 2. Initialize optimizer
optimizer = WalkForwardOptimizer(
    data=df,
    strategy_factory=EMACrossoverStrategy,
    param_space=param_space,
    config=WalkForwardConfig(n_trials=20)
)

# 3. Run optimization
result = optimizer.run_optimization()

# 4. Access results
print(f"Best Params: {result.best_params}")
print(f"Robustness Score: {result.metrics.robustness_score}")
```

## Reporting Integration

The results of a walk-forward optimization can be seamlessly integrated into institutional research reports via the `to_report_section()` method, providing stakeholders with clear insights into strategy stability and regime resilience.
