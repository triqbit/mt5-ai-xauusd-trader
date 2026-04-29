"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/hyperopt_walkforward.py
Disciplined Walk-Forward Optimization (WFO) for strategy parameter validation.
"""

import logging
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class OptimizationWindow(BaseModel):
    """Defines a single train/test window for walk-forward optimization."""
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    window_id: int

class HyperoptResult(BaseModel):
    """Results for a specific parameter configuration in a window."""
    params: Dict[str, Any]
    train_metric: float
    test_metric: float
    window_id: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WalkForwardReport(BaseModel):
    """Aggregated report for a full walk-forward optimization run."""
    strategy_name: str
    total_windows: int
    overall_robustness_score: float
    oos_consistency: float  # Percentage of profitable OOS windows
    parameter_stability: float # 0 to 1, higher is more stable
    performance_degradation: float # train vs test gap
    best_overall_params: Dict[str, Any]
    window_results: List[HyperoptResult]
    summary: str

class WalkForwardOptimizer:
    """
    Orchestrates walk-forward optimization for trading strategies.
    Implements rolling windows, OOS validation, and robustness scoring.
    """
    def __init__(
        self,
        data: pd.DataFrame,
        train_size: int,
        test_size: int,
        step_size: int,
        metric_fn: Callable[[pd.DataFrame, Dict[str, Any]], float],
    ):
        self.data = data
        self.train_size = train_size
        self.test_size = test_size
        self.step_size = step_size
        self.metric_fn = metric_fn
        self.logger = logging.getLogger(__name__)

    def generate_windows(self) -> List[OptimizationWindow]:
        """Generates rolling train/test window indices."""
        windows = []
        n_points = len(self.data)
        current_train_start = 0
        window_id = 0

        while True:
            train_end = current_train_start + self.train_size
            test_start = train_end
            test_end = test_start + self.test_size

            if test_end > n_points:
                break

            windows.append(OptimizationWindow(
                train_start=current_train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                window_id=window_id
            ))

            current_train_start += self.step_size
            window_id += 1

        self.logger.info(f"Generated {len(windows)} walk-forward windows.")
        return windows

    def run_optimization(
        self,
        param_grid: List[Dict[str, Any]],
        strategy_name: str = "GenericStrategy"
    ) -> WalkForwardReport:
        """Runs the full walk-forward optimization cycle."""
        windows = self.generate_windows()
        all_results: List[HyperoptResult] = []

        for window in windows:
            train_data = self.data.iloc[window.train_start:window.train_end]
            test_data = self.data.iloc[window.test_start:window.test_end]

            best_train_metric = -float('inf')
            best_params = {}
            test_metric_for_best_train = 0.0

            for params in param_grid:
                train_metric = self.metric_fn(train_data, params)
                if train_metric > best_train_metric:
                    best_train_metric = train_metric
                    best_params = params
                    # Validate OOS immediately with the best in-sample parameters
                    test_metric_for_best_train = self.metric_fn(test_data, params)

            all_results.append(HyperoptResult(
                params=best_params,
                train_metric=best_train_metric,
                test_metric=test_metric_for_best_train,
                window_id=window.window_id
            ))

        return self._build_report(all_results, strategy_name)

    def _build_report(self, results: List[HyperoptResult], strategy_name: str) -> WalkForwardReport:
        """Calculates robustness metrics and aggregates results."""
        if not results:
            raise ValueError("No optimization results to report.")

        # 1. OOS Consistency (percentage of positive OOS windows)
        oos_returns = [r.test_metric for r in results]
        oos_consistency = sum(1 for r in oos_returns if r > 0) / len(results)

        # 2. Performance Degradation (avg test / avg train)
        avg_train = np.mean([r.train_metric for r in results])
        avg_test = np.mean(oos_returns)
        degradation = (avg_train - avg_test) / (abs(avg_train) + 1e-8)

        # 3. Parameter Stability
        # We look at how many unique parameter sets were chosen across windows.
        # High stability = few changes.
        unique_param_sets = len({tuple(sorted(r.params.items())) for r in results})
        stability = 1.0 - (unique_param_sets - 1) / len(results) if len(results) > 1 else 1.0

        # Overall Robustness Score: Weighted combination
        # Higher consistency, higher stability, lower degradation
        robustness_score = (oos_consistency * 0.5) + (stability * 0.3) + (max(0, 1 - degradation) * 0.2)

        # Find best overall params (mode of params across windows)
        param_counts: Dict[str, int] = {}
        for r in results:
            p_str = str(tuple(sorted(r.params.items())))
            param_counts[p_str] = param_counts.get(p_str, 0) + 1

        best_p_str = max(param_counts, key=param_counts.get)
        # Convert back from string to dict (hacky but works for simple grids)
        best_overall_params = next(r.params for r in results if str(tuple(sorted(r.params.items()))) == best_p_str)

        summary = (
            f"WFO for {strategy_name}: {len(results)} windows. "
            f"Robustness Score: {robustness_score:.2f}. "
            f"OOS Consistency: {oos_consistency:.2%}. "
            f"Stability: {stability:.2f}."
        )

        return WalkForwardReport(
            strategy_name=strategy_name,
            total_windows=len(results),
            overall_robustness_score=robustness_score,
            oos_consistency=oos_consistency,
            parameter_stability=stability,
            performance_degradation=degradation,
            best_overall_params=best_overall_params,
            window_results=results,
            summary=summary
        )

class MovingAverageStrategy:
    """Simple EMA Crossover strategy for WFO demonstration."""
    def __init__(self, fast_period: int, slow_period: int):
        self.fast_period = fast_period
        self.slow_period = slow_period

    def backtest(self, data: pd.DataFrame) -> float:
        """Returns total PnL from EMA crossover."""
        if len(data) < self.slow_period:
            return 0.0

        df = data.copy()
        df['fast'] = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        df['slow'] = df['close'].ewm(span=self.slow_period, adjust=False).mean()

        df['signal'] = 0.0
        df.loc[df['fast'] > df['slow'], 'signal'] = 1.0
        df.loc[df['fast'] < df['slow'], 'signal'] = -1.0

        # Simple daily returns (pct_change) * position shifted
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']

        return df['strategy_returns'].sum()

def ma_metric_fn(data: pd.DataFrame, params: Dict[str, Any]) -> float:
    """Wrapper for MovingAverageStrategy backtest."""
    strategy = MovingAverageStrategy(
        fast_period=params['fast_period'],
        slow_period=params['slow_period']
    )
    return strategy.backtest(data)
