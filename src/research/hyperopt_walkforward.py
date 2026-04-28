"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/hyperopt_walkforward.py
Disciplined walk-forward optimization for strategy parameters.
Supports rolling windows, robustness scoring, and anti-overfitting safeguards.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol, Tuple

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class Strategy(Protocol):
    """Protocol for strategies that can be optimized."""
    def set_params(self, params: Dict[str, Any]) -> None:
        """Update strategy parameters."""
        ...

    def backtest(self, data: np.ndarray) -> Dict[str, float]:
        """
        Run backtest on provided data and return metrics.
        Expected metrics: 'return', 'sharpe', 'max_drawdown'
        """
        ...

class MovingAverageStrategy:
    """
    Sample SMA Crossover strategy for walk-forward testing.
    Params: fast_ema, slow_ema
    """
    def __init__(self) -> None:
        self.fast_ema = 12
        self.slow_ema = 26

    def set_params(self, params: Dict[str, Any]) -> None:
        self.fast_ema = int(params.get("fast_ema", self.fast_ema))
        self.slow_ema = int(params.get("slow_ema", self.slow_ema))

    def backtest(self, data: np.ndarray) -> Dict[str, float]:
        """
        Simple vectorized backtest for demonstration.
        Data expected to have at least 4 columns (OHLC), using column 3 (Close).
        """
        if len(data) < self.slow_ema + 1:
            return {"return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}

        close = data[:, 3]

        # Calculate EMAs
        alpha_fast = 2 / (self.fast_ema + 1)
        alpha_slow = 2 / (self.slow_ema + 1)

        ema_fast = self._ema(close, self.fast_ema)
        ema_slow = self._ema(close, self.slow_ema)

        # Signal: 1 if fast > slow, else 0 (long only for simplicity)
        signals = (ema_fast > ema_slow).astype(float)

        # Daily returns
        rets = np.diff(close) / close[:-1]
        strategy_rets = signals[:-1] * rets

        cum_ret = np.prod(1 + strategy_rets) - 1
        sharpe = np.mean(strategy_rets) / (np.std(strategy_rets) + 1e-9) * np.sqrt(252) # Ann.

        # Max Drawdown
        cum_wealth = np.cumprod(1 + strategy_rets)
        peak = np.maximum.accumulate(cum_wealth)
        drawdown = (cum_wealth - peak) / peak
        max_dd = np.min(drawdown) if len(drawdown) > 0 else 0.0

        return {
            "return": float(cum_ret),
            "sharpe": float(sharpe),
            "max_drawdown": float(abs(max_dd))
        }

    def _ema(self, arr: np.ndarray, window: int) -> np.ndarray:
        """Simple EMA implementation."""
        alpha = 2 / (window + 1)
        ema = np.zeros_like(arr)
        ema[0] = arr[0]
        for i in range(1, len(arr)):
            ema[i] = alpha * arr[i] + (1 - alpha) * ema[i-1]
        return ema

class WalkForwardConfig(BaseModel):
    """Configuration for walk-forward optimization."""
    train_window: int = Field(..., description="Number of bars for training/optimization")
    test_window: int = Field(..., description="Number of bars for out-of-sample testing")
    step_size: int = Field(..., description="Number of bars to shift the window by")
    min_windows: int = Field(default=3, description="Minimum number of windows required")
    robustness_threshold: float = Field(default=0.5, description="Minimum robustness score to accept a configuration")

class WindowResult(BaseModel):
    """Results for a single walk-forward window."""
    window_idx: int
    start_idx: int
    train_end_idx: int
    test_end_idx: int
    best_params: Dict[str, Any]
    train_metrics: Dict[str, float]
    test_metrics: Dict[str, float]
    oos_degradation: float  # (Test Return / Train Return)

class HyperoptReport(BaseModel):
    """Final report for walk-forward optimization."""
    config: WalkForwardConfig
    windows: List[WindowResult]
    overall_robustness: float
    is_robust: bool
    parameter_stability: Dict[str, float]  # Variance of parameters across windows

class WalkForwardOptimizer:
    """
    Orchestrates walk-forward optimization for a given strategy.
    Optimizes only for strategies that survive regime changes and out-of-sample constraints.
    """
    def __init__(self, strategy: Strategy, config: WalkForwardConfig) -> None:
        self.strategy = strategy
        self.config = config

    def generate_windows(self, data_length: int) -> List[Tuple[int, int, int]]:
        """
        Generate (start, train_end, test_end) indices for each rolling window.
        """
        windows = []
        start = 0
        while True:
            train_end = start + self.config.train_window
            test_end = train_end + self.config.test_window

            if test_end > data_length:
                break

            windows.append((start, train_end, test_end))
            start += self.config.step_size

        return windows

    def run(self, data: np.ndarray, param_grid: List[Dict[str, Any]]) -> HyperoptReport:
        """
        Run the walk-forward optimization loop.
        Rank configurations by robustness, not just return.
        """
        windows_indices = self.generate_windows(len(data))
        if len(windows_indices) < self.config.min_windows:
            msg = f"Insufficient data ({len(data)} bars) for {self.config.min_windows} windows."
            logger.error(msg)
            raise ValueError(msg)

        results = []
        for i, (start, train_end, test_end) in enumerate(windows_indices):
            train_data = data[start:train_end]
            test_data = data[train_end:test_end]

            best_train_perf = -np.inf
            best_params = {}
            best_train_metrics = {}

            # 1. In-Sample Optimization
            for params in param_grid:
                self.strategy.set_params(params)
                metrics = self.strategy.backtest(train_data)
                # Primary metric: Sharpe Ratio if available, fallback to Return
                score = metrics.get("sharpe", metrics.get("return", -1e9))

                if score > best_train_perf:
                    best_train_perf = score
                    best_params = params
                    best_train_metrics = metrics

            # 2. Out-of-Sample Validation
            if not best_params:
                logger.warning("No suitable parameters found for window %d", i)
                continue

            self.strategy.set_params(best_params)
            test_metrics = self.strategy.backtest(test_data)

            # Calculate OOS degradation (Test Performance / Train Performance)
            train_ret = best_train_metrics.get("return", 0.0)
            test_ret = test_metrics.get("return", 0.0)

            if train_ret > 0:
                oos_degradation = test_ret / train_ret
            else:
                # If train return was negative or zero, but we picked it (best of bad options)
                oos_degradation = 1.0 if test_ret > train_ret else 0.0

            results.append(WindowResult(
                window_idx=i,
                start_idx=start,
                train_end_idx=train_end,
                test_end_idx=test_end,
                best_params=best_params,
                train_metrics=best_train_metrics,
                test_metrics=test_metrics,
                oos_degradation=float(oos_degradation)
            ))

        # 3. Robustness & Stability Analysis
        stability = self._calculate_stability(results)
        robustness = self._calculate_robustness(results, stability)

        return HyperoptReport(
            config=self.config,
            windows=results,
            overall_robustness=robustness,
            is_robust=robustness >= self.config.robustness_threshold,
            parameter_stability=stability
        )

    def _calculate_stability(self, results: List[WindowResult]) -> Dict[str, float]:
        """
        Measure parameter variance across windows.
        High variance indicates unstable parameters that might be overfitting to local regimes.
        """
        if not results:
            return {}

        all_params = [r.best_params for r in results]
        keys = all_params[0].keys()
        stability = {}

        for key in keys:
            values = []
            for p in all_params:
                val = p.get(key)
                if isinstance(val, (int, float, bool)):
                    values.append(float(val))

            if values:
                # Coefficient of variation (std / mean) as a measure of instability
                std = np.std(values)
                mean = np.abs(np.mean(values)) + 1e-9
                stability[key] = float(std / mean)
            else:
                # Categorical params: fraction of unique values
                unique = len(set(str(p.get(key)) for p in all_params))
                stability[key] = float(unique / len(all_params))

        return stability

    def _calculate_robustness(self, results: List[WindowResult], stability: Dict[str, float]) -> float:
        """
        Consolidated robustness score [0, 1].
        - OOS Consistency: % of windows with positive test returns.
        - OOS Degradation: How much performance drops out-of-sample.
        - Parameter Stability: Penalize configurations that shift wildly across windows.
        """
        if not results:
            return 0.0

        # 1. Consistency (40% weight)
        positive_oos = sum(1 for r in results if r.test_metrics.get("return", 0.0) > 0)
        consistency_score = positive_oos / len(results)

        # 2. Average degradation (40% weight), capped at 1.0
        # We penalize if OOS is much worse than IS
        avg_degradation = np.mean([np.clip(r.oos_degradation, 0.0, 1.0) for r in results])
        degradation_score = float(avg_degradation)

        # 3. Stability Penalty (20% weight)
        # Average instability across all params
        avg_instability = np.mean(list(stability.values())) if stability else 0.0
        stability_score = 1.0 / (1.0 + avg_instability)

        return float(0.4 * consistency_score + 0.4 * degradation_score + 0.2 * stability_score)
