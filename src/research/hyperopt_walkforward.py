"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/hyperopt_walkforward.py
Disciplined walk-forward optimization with robustness scoring.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol, Tuple

import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HyperparameterSet(BaseModel):
    """Container for a set of hyperparameters."""

    params: Dict[str, Any]
    id: Optional[str] = None


class WindowConfig(BaseModel):
    """Indices for a single walk-forward window."""

    window_id: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int


class WindowResult(BaseModel):
    """Performance metrics for a single window."""

    window_id: int
    params: HyperparameterSet
    is_metrics: Dict[str, float]
    oos_metrics: Dict[str, float]
    is_oos_ratio: float


class WalkForwardConfig(BaseModel):
    """Configuration for the walk-forward process."""

    train_window_size: int
    test_window_size: int
    step_size: int
    anchored: bool = False
    min_oos_is_ratio: float = 0.5
    robustness_threshold: float = 0.7


class WalkForwardSummary(BaseModel):
    """Overall results of the walk-forward optimization."""

    best_params: HyperparameterSet
    robustness_score: float
    avg_oos_performance: float
    window_results: List[WindowResult]
    stability_metrics: Dict[str, float]


class Evaluator(Protocol):
    """Protocol for an evaluator that can score a parameter set on a data slice."""

    def evaluate(
        self, params: Dict[str, Any], start_idx: int, end_idx: int
    ) -> Dict[str, float]: ...


class WalkForwardOptimizer:
    """
    Orchestrates walk-forward optimization, ensuring out-of-sample validity.
    """

    def __init__(self, config: WalkForwardConfig, data_length: int):
        self.config = config
        self.data_length = data_length

    def generate_windows(self) -> List[WindowConfig]:
        """
        Generates indices for rolling/anchored train/test windows.
        """
        windows = []
        window_id = 0
        current_test_start = self.config.train_window_size

        while current_test_start + self.config.test_window_size <= self.data_length:
            train_start = (
                0 if self.config.anchored else (current_test_start - self.config.train_window_size)
            )
            train_end = current_test_start
            test_start = current_test_start
            test_end = current_test_start + self.config.test_window_size

            windows.append(
                WindowConfig(
                    window_id=window_id,
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                )
            )

            current_test_start += self.config.step_size
            window_id += 1

        return windows

    def calculate_robustness_score(self, oos_performances: List[float]) -> float:
        """
        Calculates a robustness score based on OOS performance consistency.
        Score = Mean / (1 + StdDev) - penalizes high variance.
        """
        if not oos_performances:
            return 0.0

        perf = np.array(oos_performances)
        mean_perf = np.mean(perf)
        std_perf = np.std(perf)

        # Penalize variance and negative returns
        robustness = mean_perf / (1.0 + std_perf)

        # Penalize negative performance
        return float(max(robustness, 0.0))

    def analyze_parameter_stability(self, param_history: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Analyzes how much parameters fluctuate across windows.
        Returns coefficient of variation for each numeric parameter.
        """
        if not param_history:
            return {}

        stability = {}
        keys = param_history[0].keys()

        for key in keys:
            values = [p[key] for p in param_history if isinstance(p.get(key), (int, float))]
            if len(values) < 2:
                continue

            v_arr = np.array(values)
            mean_v = np.mean(v_arr)
            std_v = np.std(v_arr)

            # Coefficient of Variation (CV)
            cv = std_v / abs(mean_v) if mean_v != 0 else std_v
            stability[f"{key}_cv"] = float(cv)

        return stability

    def calculate_performance_haircut(self, is_perf: float, oos_perf: float) -> float:
        """
        Calculates the ratio of OOS to IS performance.
        Lower ratio indicates potential overfitting.
        """
        if is_perf <= 0:
            return 0.0 if oos_perf <= 0 else 1.0
        return oos_perf / is_perf

    def run_walk_forward(
        self,
        evaluator: Evaluator,
        param_candidates: List[HyperparameterSet],
        metric_key: str = "sharpe",
    ) -> WalkForwardSummary:
        """
        Runs the full walk-forward process.
        """
        windows = self.generate_windows()
        window_results = []
        param_history = []
        oos_performances = []

        for window in windows:
            best_window_params = None
            best_window_is_metric = -float("inf")
            best_window_oos_metric = 0.0

            # 1. Training Phase: Find best params in-sample
            for hp_set in param_candidates:
                is_metrics = evaluator.evaluate(hp_set.params, window.train_start, window.train_end)
                is_val = is_metrics.get(metric_key, 0.0)

                if is_val > best_window_is_metric:
                    best_window_is_metric = is_val
                    best_window_params = hp_set

            # 2. Testing Phase: Validate best params out-of-sample
            if best_window_params:
                oos_metrics = evaluator.evaluate(
                    best_window_params.params, window.test_start, window.test_end
                )
                best_window_oos_metric = oos_metrics.get(metric_key, 0.0)
                is_oos_ratio = self.calculate_performance_haircut(
                    best_window_is_metric, best_window_oos_metric
                )

                res = WindowResult(
                    window_id=window.window_id,
                    params=best_window_params,
                    is_metrics={metric_key: best_window_is_metric},
                    oos_metrics=oos_metrics,
                    is_oos_ratio=is_oos_ratio,
                )
                window_results.append(res)
                param_history.append(best_window_params.params)
                oos_performances.append(best_window_oos_metric)

        # 3. Aggregation and Stability Analysis
        robustness_score = self.calculate_robustness_score(oos_performances)
        stability_metrics = self.analyze_parameter_stability(param_history)
        avg_oos = float(np.mean(oos_performances)) if oos_performances else 0.0

        # Heuristic for overall "best" params could be the most frequent or last window's best
        # For simplicity, we return the last window's best if it exists
        final_params = window_results[-1].params if window_results else param_candidates[0]

        return WalkForwardSummary(
            best_params=final_params,
            robustness_score=robustness_score,
            avg_oos_performance=avg_oos,
            window_results=window_results,
            stability_metrics=stability_metrics,
        )

    def rank_candidates(
        self,
        evaluator: Evaluator,
        param_candidates: List[HyperparameterSet],
        metric_key: str = "sharpe",
    ) -> List[Tuple[HyperparameterSet, float]]:
        """
        Ranks parameter sets by their average OOS robustness across all windows.
        """
        windows = self.generate_windows()
        scores = []

        for hp_set in param_candidates:
            oos_perfs = []
            for window in windows:
                # In a real ranking, we'd probably train on IS and test on OOS
                # but for simple ranking we can just look at OOS consistency
                oos_metrics = evaluator.evaluate(hp_set.params, window.test_start, window.test_end)
                oos_perfs.append(oos_metrics.get(metric_key, 0.0))

            robustness = self.calculate_robustness_score(oos_perfs)
            scores.append((hp_set, robustness))

        # Sort by robustness descending
        return sorted(scores, key=lambda x: x[1], reverse=True)
