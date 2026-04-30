"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/hyperopt_walkforward.py
Disciplined walk-forward optimization with parameter stability analysis and robustness scoring.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Protocol, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Strategy(Protocol):
    """Protocol for a trading strategy that can be evaluated."""
    def run(self, data: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, float]:
        """Run the strategy on data with given params and return metrics."""
        ...


class WindowMetrics(BaseModel):
    """Performance metrics for a specific time window."""
    sharpe_ratio: float
    total_return: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    num_trades: int
    consistency_score: float = 0.0


class WindowResult(BaseModel):
    """Results for a single walk-forward window."""
    window_index: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    best_params: Dict[str, Any]
    is_metrics: WindowMetrics
    oos_metrics: WindowMetrics
    robustness_score: float


class WalkForwardSummary(BaseModel):
    """Aggregate summary of a full walk-forward analysis."""
    total_windows: int
    avg_oos_sharpe: float
    avg_oos_return: float
    max_oos_drawdown: float
    robustness_index: float  # Scale 0-1
    parameter_stability: float  # Scale 0-1
    windows: List[WindowResult]


class WalkForwardOptimizer:
    """
    Implements rolling/expanding walk-forward optimization with Optuna.
    Focuses on robustness and parameter stability to prevent overfitting.
    """

    def __init__(
        self,
        strategy: Strategy,
        data: pd.DataFrame,
        param_space: Callable[[Any], Dict[str, Any]],
        n_trials: int = 100,
        validation_split: float = 0.2,
    ) -> None:
        """
        Initialize the optimizer.

        Args:
            strategy: An object implementing the Strategy protocol.
            data: Full historical OHLCV data with DatetimeIndex.
            param_space: A function that takes an Optuna trial and returns a param dict.
            n_trials: Number of optimization trials per window.
            validation_split: Fraction of training data to use for internal validation.
        """
        self.strategy = strategy
        self.data = data
        self.param_space = param_space
        self.n_trials = n_trials
        self.validation_split = validation_split
        self.results: List[WindowResult] = []

    def generate_windows(
        self,
        train_size_bars: int,
        test_size_bars: int,
        step_size_bars: int,
        expanding: bool = False,
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Generate train/test data splits for walk-forward.

        Args:
            train_size_bars: Number of bars in initial training window.
            test_size_bars: Number of bars in each OOS test window.
            step_size_bars: Number of bars to shift for next window.
            expanding: If True, training window grows; if False, it slides.
        """
        windows = []
        n_bars = len(self.data)
        current_train_start = 0

        while True:
            train_end = current_train_start + train_size_bars
            test_end = train_end + test_size_bars

            if test_end > n_bars:
                break

            train_data = self.data.iloc[current_train_start:train_end]
            test_data = self.data.iloc[train_end:test_end]

            windows.append((train_data, test_data))

            # Shift for next window
            current_train_start += step_size_bars
            if expanding:
                # In expanding window, we always start from 0
                current_train_start = 0
                train_size_bars += step_size_bars

        logger.info("Generated %d walk-forward windows", len(windows))
        return windows

    def _calculate_robustness(
        self,
        is_metrics: WindowMetrics,
        oos_metrics: WindowMetrics,
        stability_score: float,
    ) -> float:
        """
        Calculate a composite robustness score (0.0 to 1.0).
        Penalizes OOS degradation and parameter instability.
        """
        # 1. Performance Ratio: OOS Sharpe vs IS Sharpe
        # Penalise if OOS is much worse than IS (overfitting indicator)
        is_sharpe = max(is_metrics.sharpe_ratio, 0.001)
        oos_sharpe = max(oos_metrics.sharpe_ratio, 0.0)
        perf_ratio = min(oos_sharpe / is_sharpe, 1.2)  # Cap at 1.2

        # 2. Drawdown Penalty
        dd_penalty = 1.0 - min(oos_metrics.max_drawdown / 0.3, 1.0)  # Penalise DD > 30%

        # 3. Trade Frequency Penalty
        # Low trade count makes metrics unreliable
        freq_penalty = min(oos_metrics.num_trades / 10, 1.0)

        # Composite score
        score = (perf_ratio * 0.4) + (stability_score * 0.3) + (dd_penalty * 0.2) + (freq_penalty * 0.1)
        return float(np.clip(score, 0.0, 1.0))

    def _objective(
        self,
        trial: Any,
        train_data: pd.DataFrame,
    ) -> float:
        """Optuna objective function for a single window."""
        params = self.param_space(trial)
        metrics_dict = self.strategy.run(train_data, params)
        metrics = WindowMetrics(**metrics_dict)

        # We optimize for a combination of Sharpe and Consistency
        # to find stable regions during IS phase
        return metrics.sharpe_ratio * (1.0 + metrics.consistency_score)

    def optimize(
        self,
        train_size_bars: int,
        test_size_bars: int,
        step_size_bars: int,
        expanding: bool = False,
    ) -> WalkForwardSummary:
        """
        Run the full walk-forward optimization process.
        """
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        windows = self.generate_windows(train_size_bars, test_size_bars, step_size_bars, expanding)
        self.results = []

        for i, (train_data, test_data) in enumerate(windows):
            logger.info("Optimizing Window %d/%d", i + 1, len(windows))

            study = optuna.create_study(direction="maximize")
            study.optimize(
                lambda t, td=train_data: self._objective(t, td),
                n_trials=self.n_trials,
            )

            best_params = study.best_params

            # Evaluate best params on IS and OOS
            is_metrics = WindowMetrics(**self.strategy.run(train_data, best_params))
            oos_metrics = WindowMetrics(**self.strategy.run(test_data, best_params))

            # Calculate parameter stability (Implementation in next step)
            stability_score = self._analyze_stability(train_data, best_params)

            robustness = self._calculate_robustness(is_metrics, oos_metrics, stability_score)

            result = WindowResult(
                window_index=i,
                train_start=train_data.index[0],
                train_end=train_data.index[-1],
                test_start=test_data.index[0],
                test_end=test_data.index[-1],
                best_params=best_params,
                is_metrics=is_metrics,
                oos_metrics=oos_metrics,
                robustness_score=robustness,
            )
            self.results.append(result)

        # Aggregate summary
        if not self.results:
            return WalkForwardSummary(
                total_windows=0, avg_oos_sharpe=0, avg_oos_return=0,
                max_oos_drawdown=0, robustness_index=0, parameter_stability=0, windows=[]
            )

        oos_sharpes = [r.oos_metrics.sharpe_ratio for r in self.results]
        oos_returns = [r.oos_metrics.total_return for r in self.results]
        oos_drawdowns = [r.oos_metrics.max_drawdown for r in self.results]
        robustness_scores = [r.robustness_score for r in self.results]

        # We use robustness scores as a proxy for stability here for the aggregate
        stability_avg = float(np.mean([r.robustness_score for r in self.results]))

        summary = WalkForwardSummary(
            total_windows=len(self.results),
            avg_oos_sharpe=float(np.mean(oos_sharpes)),
            avg_oos_return=float(np.mean(oos_returns)),
            max_oos_drawdown=float(np.max(oos_drawdowns)),
            robustness_index=float(np.mean(robustness_scores)),
            parameter_stability=stability_avg,
            windows=self.results,
        )
        return summary

    def _analyze_stability(
        self,
        data: pd.DataFrame,
        params: Dict[str, Any],
        perturb_scale: float = 0.05,
        n_perturbations: int = 10,
    ) -> float:
        """
        Evaluate how performance changes with small parameter perturbations.
        High variance in performance indicates a 'brittle' or overfitted configuration.
        """
        base_metrics = WindowMetrics(**self.strategy.run(data, params))
        base_sharpe = max(base_metrics.sharpe_ratio, 0.001)

        sharpe_variants = []

        for _ in range(n_perturbations):
            perturbed_params = {}
            for k, v in params.items():
                if isinstance(v, (int, float)):
                    # Add Gaussian noise
                    noise = np.random.normal(0, abs(v) * perturb_scale)
                    new_val = v + noise
                    # Keep type consistency
                    perturbed_params[k] = type(v)(new_val)
                else:
                    perturbed_params[k] = v

            try:
                variant_metrics = WindowMetrics(**self.strategy.run(data, perturbed_params))
                sharpe_variants.append(variant_metrics.sharpe_ratio)
            except Exception as e:
                logger.warning("Failed to run perturbed strategy: %s", e)
                sharpe_variants.append(0.0)

        if not sharpe_variants:
            return 0.0

        # Calculate Coefficient of Variation (CV)
        # Low CV means high stability
        std_sharpe = np.std(sharpe_variants)
        stability = 1.0 - min(std_sharpe / base_sharpe, 1.0)

        return float(stability)
