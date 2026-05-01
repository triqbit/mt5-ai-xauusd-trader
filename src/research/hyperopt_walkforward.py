"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/hyperopt_walkforward.py
Walk-forward optimization framework for strategy robustness.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Protocol, Tuple

import numpy as np
import optuna
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class Strategy(Protocol):
    """Protocol for strategies compatible with WalkForwardOptimizer."""

    def run(self, data: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, float]:
        """
        Run the strategy on data with given params.
        Returns a dict of metrics (e.g., {'sharpe': 1.2, 'mdd': 0.1}).
        """
        ...

class WindowResult(BaseModel):
    """Result of optimization for a single window."""

    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    best_params: Dict[str, Any]
    train_metrics: Dict[str, float]
    test_metrics: Dict[str, float]
    robustness_score: float

class WalkForwardReport(BaseModel):
    """Aggregate report for walk-forward optimization."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    windows: List[WindowResult]
    overall_robustness: float
    parameter_stability: Dict[str, float]

class WalkForwardOptimizer:
    """
    Performs walk-forward optimization to ensure strategy robustness.
    Supports rolling and expanding windows, out-of-sample validation,
    and parameter stability analysis.
    """

    def __init__(
        self,
        strategy: Strategy,
        data: pd.DataFrame,
        param_space: Dict[str, Tuple[str, Any, Any]],
        n_trials: int = 50,
        objective_metric: str = "sharpe",
    ):
        """
        Initialize the optimizer.
        Args:
            strategy: Strategy implementation following the Strategy protocol.
            data: DataFrame with market data.
            param_space: Dictionary mapping param names to (type, min, max) or (type, options).
                         Example: {'fast_ma': ('int', 5, 20), 'threshold': ('float', 0.01, 0.05)}
            n_trials: Number of Optuna trials per window.
            objective_metric: Metric to optimize for (must be returned by strategy.run).
        """
        self.strategy = strategy
        self.data = data
        self.param_space = param_space
        self.n_trials = n_trials
        self.objective_metric = objective_metric

    def generate_windows(
        self,
        train_size: int,
        test_size: int,
        step_size: int,
        expanding: bool = False,
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Generates train/test data splits for walk-forward analysis.
        Args:
            train_size: Number of bars for training.
            test_size: Number of bars for testing.
            step_size: Number of bars to move forward in each step.
            expanding: If True, training window grows from start. If False, it slides.
        """
        windows = []
        n = len(self.data)
        start = 0

        while start + train_size + test_size <= n:
            train_end = start + train_size
            test_end = train_end + test_size

            train_data = self.data.iloc[0 if expanding else start : train_end]
            test_data = self.data.iloc[train_end : test_end]

            windows.append((train_data, test_data))
            start += step_size

        return windows

    def _optimize_window(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        window_id: int,
    ) -> WindowResult:
        """Optimizes parameters on train_data and validates on test_data."""

        def objective(trial: optuna.Trial) -> float:
            params = {}
            for name, config in self.param_space.items():
                ptype = config[0]
                if ptype == "int":
                    params[name] = trial.suggest_int(name, config[1], config[2])
                elif ptype == "float":
                    params[name] = trial.suggest_float(name, config[1], config[2])
                elif ptype == "categorical":
                    params[name] = trial.suggest_categorical(name, config[1])

            # Base performance
            base_results = self.strategy.run(train_data, params)
            base_performance = base_results.get(self.objective_metric, -1e9)

            # Parameter stability check (perturbation)
            perturbation_penalty = self._calculate_perturbation_penalty(train_data, params, base_performance)

            return base_performance - perturbation_penalty

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=self.n_trials)

        best_params = study.best_params
        train_metrics = self.strategy.run(train_data, best_params)
        test_metrics = self.strategy.run(test_data, best_params)

        robustness = self._calculate_robustness_score(train_metrics, test_metrics)

        return WindowResult(
            window_id=window_id,
            train_start=train_data.index[0] if isinstance(train_data.index[0], datetime) else datetime.fromtimestamp(0, tz=timezone.utc),
            train_end=train_data.index[-1] if isinstance(train_data.index[-1], datetime) else datetime.fromtimestamp(0, tz=timezone.utc),
            test_start=test_data.index[0] if isinstance(test_data.index[0], datetime) else datetime.fromtimestamp(0, tz=timezone.utc),
            test_end=test_data.index[-1] if isinstance(test_data.index[-1], datetime) else datetime.fromtimestamp(0, tz=timezone.utc),
            best_params=best_params,
            train_metrics=train_metrics,
            test_metrics=test_metrics,
            robustness_score=float(robustness),
        )

    def _calculate_perturbation_penalty(
        self,
        data: pd.DataFrame,
        params: Dict[str, Any],
        base_performance: float,
        perturbation_scale: float = 0.05,
    ) -> float:
        """Calculates penalty based on performance sensitivity to parameter changes."""
        perturbations = []
        for name, value in params.items():
            config = self.param_space[name]
            ptype = config[0]

            if ptype == "int":
                # For int, check +/- 1
                for p in [value + 1, value - 1]:
                    if config[1] <= p <= config[2]:
                        p_params = params.copy()
                        p_params[name] = p
                        p_perf = self.strategy.run(data, p_params).get(self.objective_metric, -1e9)
                        perturbations.append(p_perf)
            elif ptype == "float":
                # For float, check +/- perturbation_scale of range
                range_val = config[2] - config[1]
                step = range_val * perturbation_scale
                for p in [value + step, value - step]:
                    if config[1] <= p <= config[2]:
                        p_params = params.copy()
                        p_params[name] = p
                        p_perf = self.strategy.run(data, p_params).get(self.objective_metric, -1e9)
                        perturbations.append(p_perf)

        if not perturbations:
            return 0.0

        avg_perturbed = np.mean(perturbations)
        # Only penalize if performance drops significantly
        penalty = max(0, base_performance - avg_perturbed)
        return float(penalty)

    def _calculate_robustness_score(
        self,
        train_metrics: Dict[str, float],
        test_metrics: Dict[str, float],
    ) -> float:
        """
        Calculates a robustness score based on OOS vs IS performance.
        Higher is better. 1.0 means OOS performance matched or exceeded IS.
        """
        # 1. Sharpe Ratio consistency
        train_sharpe = train_metrics.get("sharpe", 0.0)
        test_sharpe = test_metrics.get("sharpe", 0.0)

        if train_sharpe <= 0:
            sharpe_score = 0.0
        else:
            # We cap it at 1.2 to avoid rewarding extreme luck in OOS
            sharpe_score = min(test_sharpe / (train_sharpe + 1e-9), 1.2)
            sharpe_score = max(0.0, sharpe_score)

        # 2. Max Drawdown preservation
        train_mdd = train_metrics.get("mdd", 1.0)
        test_mdd = test_metrics.get("mdd", 1.0)

        # Penalty if OOS drawdown is much worse than IS
        mdd_ratio = test_mdd / (train_mdd + 1e-9)
        mdd_score = max(0.0, 1.0 - max(0, mdd_ratio - 1.5))

        # Combined score (70% Sharpe, 30% MDD)
        return float((sharpe_score * 0.7) + (mdd_score * 0.3))

    def run_walk_forward(
        self,
        train_size: int,
        test_size: int,
        step_size: int,
        expanding: bool = False,
    ) -> WalkForwardReport:
        """
        Executes the full walk-forward process.
        """
        windows_data = self.generate_windows(train_size, test_size, step_size, expanding)
        if not windows_data:
            raise ValueError("No windows generated with the given parameters and data size.")

        results = []
        for i, (train_data, test_data) in enumerate(windows_data):
            logger.info(f"Optimizing window {i+1}/{len(windows_data)}...")
            res = self._optimize_window(train_data, test_data, i)
            results.append(res)

        overall_robustness = np.mean([r.robustness_score for r in results])
        stability = self._analyze_parameter_stability(results)

        return WalkForwardReport(
            windows=results,
            overall_robustness=float(overall_robustness),
            parameter_stability=stability,
        )

    def _analyze_parameter_stability(self, results: List[WindowResult]) -> Dict[str, float]:
        """Analyzes how much parameters drifted across windows."""
        if not results:
            return {}

        param_values: Dict[str, List[float]] = {}
        for res in results:
            for k, v in res.best_params.items():
                if isinstance(v, (int, float)):
                    if k not in param_values:
                        param_values[k] = []
                    param_values[k].append(float(v))

        stability = {}
        for k, vals in param_values.items():
            if len(vals) > 1:
                # Lower coefficient of variation means more stable
                cv = np.std(vals) / (abs(np.mean(vals)) + 1e-9)
                # Normalize: 1.0 is perfectly stable, 0.0 is unstable
                stability[k] = float(1.0 / (1.0 + cv))
            else:
                stability[k] = 1.0

        return stability
