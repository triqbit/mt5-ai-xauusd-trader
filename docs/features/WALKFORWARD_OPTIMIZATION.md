# Walk-Forward Optimization (WFO)

The `WalkForwardOptimizer` provides a disciplined framework for strategy parameter optimization, focusing on robustness and anti-overfitting safeguards.

## Core Concepts

Traditional optimization often leads to "curve-fitting," where parameters perform exceptionally well on historical data but fail in live trading. WFO addresses this by using rolling windows of train/test data.

### Rolling Windows

The optimizer splits historical data into multiple overlapping segments:
- **In-Sample (IS)**: The "training" window where parameters are optimized.
- **Out-of-Sample (OOS)**: The "testing" window where the best IS parameters are validated.

## Robustness Scoring

Unlike simple return-based optimization, the `WalkForwardOptimizer` ranks configurations using a multi-factor **Robustness Score**:

$$Score = \mu_{OOS} - 0.5 \sigma_{OOS} - 0.2 Gap_{IS-OOS} - 0.3 Penalty_{stability} + 0.1 Consistency_{regime}$$

-   **OOS Mean ($\mu_{OOS}$)**: Average Sharpe ratio across all out-of-sample windows.
-   **OOS Variance ($\sigma_{OOS}$)**: Penalizes inconsistent performance across windows.
-   **IS-OOS Gap**: Penalizes configurations that perform significantly better in-sample than out-of-sample (a key indicator of overfitting).
-   **Stability Penalty**: Measures sensitivity to small parameter perturbations. If a small change in a hyperparameter leads to a large drop in performance, the configuration is considered "brittle" and penalized.
-   **Regime Consistency**: Measures how consistently the strategy performs across different market regimes (Trending, Ranging, etc.) detected by the `RegimeDetector`.

## Usage

```python
from src.research.hyperopt_walkforward import WalkForwardOptimizer, WalkForwardConfig
from src.research.benchmarks import EMACrossoverStrategy

# 1. Define parameter space
def param_space(trial):
    return {
        "fast_window": trial.suggest_int("fast_window", 5, 20),
        "slow_window": trial.suggest_int("slow_window", 21, 50)
    }

# 2. Configure Optimizer
config = WalkForwardConfig(
    train_size=500,
    test_size=100,
    step_size=100,
    n_trials=100
)

# 3. Run Optimization
optimizer = WalkForwardOptimizer(
    data=ohlcv_df,
    strategy_factory=EMACrossoverStrategy,
    param_space=param_space,
    config=config
)

result = optimizer.run_optimization()

print(f"Best Params: {result.best_params}")
print(f"Robustness Score: {result.metrics.robustness_score}")
```

## Anti-Overfitting Safeguards

1.  **Walk-Forward Validation**: Ensures parameters work on unseen data.
2.  **Sensitivity Analysis**: Rejects "knife-edge" optimizations that only work with very specific values.
3.  **Regime Awareness**: Ensures the strategy isn't just a "one-trick pony" that only works in a specific market state.
4.  **Performance Consistency**: Prioritizes steady performance over lucky spikes.
