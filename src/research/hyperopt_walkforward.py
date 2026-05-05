"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/hyperopt_walkforward.py
Disciplined Walk-Forward Optimization with Robustness Scoring.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
import optuna
import pandas as pd
from pydantic import BaseModel, Field

from src.models.regime_detector import RegimeDetector
from src.research.benchmarks import BenchmarkEvaluator, BenchmarkStrategy

logger = logging.getLogger(__name__)


class OptimizationMetric(str, Enum):
    """Available metrics for optimization."""

    SHARPE = "sharpe"
    SORTINO = "sortino"
    PROFIT_FACTOR = "profit_factor"
    TOTAL_RETURN = "total_return"
    ROBUSTNESS_SCORE = "robustness_score"


class WalkForwardConfig(BaseModel):
    """Configuration for Walk-Forward Optimization."""

    train_size: int = Field(250, description="Number of candles for training/optimization")
    test_size: int = Field(50, description="Number of candles for out-of-sample testing")
    step_size: int = Field(50, description="Step size for rolling windows")
    min_windows: int = Field(3, description="Minimum number of windows required")
    metric: OptimizationMetric = OptimizationMetric.ROBUSTNESS_SCORE
    n_trials: int = Field(50, description="Number of trials per window")
    seed: int = 42
    commission: float = 0.0002
    bars_per_year: int = Field(
        252, description="Bars per year for annualization (e.g. 252 for Daily)"
    )


class RobustnessMetrics(BaseModel):
    """Structured robustness metrics."""

    oos_sharpe_mean: float
    oos_sharpe_std: float
    worst_window_sharpe: float
    win_rate_consistency: float
    max_drawdown_consistency: float
    is_oos_gap: float
    stability_penalty: float
    regime_consistency: float
    robustness_score: float


class WindowResult(BaseModel):
    """Metrics for a single walk-forward window."""

    window_index: int
    is_metrics: dict[str, Any]
    oos_metrics: dict[str, Any]


class WalkForwardResult(BaseModel):
    """Result of a Walk-Forward Optimization run."""

    best_params: dict[str, Any]
    metrics: RobustnessMetrics
    window_results: list[WindowResult]
    oos_returns: list[float] = Field(default_factory=list, description="Aggregated OOS returns")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_report_section(self) -> Any:
        """
        Convert result to HyperparameterSection for ResearchReporter.

        Returns:
            HyperparameterSection: Structured section for the research report.
        """
        from src.research.reporting import HyperparameterSection, ParameterRobustness

        params = []
        for name, value in self.best_params.items():
            params.append(
                ParameterRobustness(
                    name=name,
                    range="Optimized",
                    optimal=str(value),
                    sensitivity="Tracked via stability penalty",
                )
            )

        insights = (
            f"OOS Sharpe Mean: {self.metrics.oos_sharpe_mean:.2f}, "
            f"Worst Window Sharpe: {self.metrics.worst_window_sharpe:.2f}, "
            f"IS-OOS Gap: {self.metrics.is_oos_gap:.2f}, "
            f"Regime Consistency: {self.metrics.regime_consistency:.2f}, "
            f"WinRate Consistency: {self.metrics.win_rate_consistency:.2f}"
        )

        # Scale robustness score to 0-100 for report
        # We assume a score of 1.5+ is excellent (100) and 0 is poor (0)
        display_score = float(np.clip(self.metrics.robustness_score / 1.5 * 100, 0, 100))

        return HyperparameterSection(
            stability_score=display_score,
            parameters=params,
            insights=insights,
        )


class WalkForwardOptimizer:
    """
    Implements disciplined walk-forward optimization with robustness scoring.

    This optimizer finds parameter sets that perform consistently across multiple
    rolling windows, penalizing over-optimization and instability.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        strategy_factory: Callable[..., BenchmarkStrategy],
        param_space: Callable[[optuna.Trial], dict[str, Any]],
        config: WalkForwardConfig = WalkForwardConfig(),
    ):
        """
        Initialize the optimizer.

        Args:
            data: Historical OHLCV data.
            strategy_factory: Function that creates a BenchmarkStrategy given parameters.
            param_space: Function that defines the Optuna search space.
            config: Configuration parameters for the walk-forward process.
        """
        self.data = data.copy()
        self.strategy_factory = strategy_factory
        self.param_space = param_space
        self.config = config
        self.regime_detector = RegimeDetector()

        # Pre-calculate regimes if possible
        if "regime" not in self.data.columns:
            logger.info("Regime column missing, labeling history...")
            self.data = self.regime_detector.label_history(self.data)

    def generate_windows(self) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Generates rolling train/test splits.

        Returns:
            List[Tuple[pd.DataFrame, pd.DataFrame]]: List of (train_df, test_df) pairs.
        """
        windows = []
        n = len(self.data)

        start = 0
        while start + self.config.train_size + self.config.test_size <= n:
            train_end = start + self.config.train_size
            test_end = train_end + self.config.test_size

            train_data = self.data.iloc[start:train_end]
            test_data = self.data.iloc[train_end:test_end]

            windows.append((train_data, test_data))
            start += self.config.step_size

        return windows

    def _evaluate_strategy(self, data: pd.DataFrame, params: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluates a strategy with given parameters on a dataset.

        Args:
            data: Data to evaluate on.
            params: Strategy parameters.

        Returns:
            Dict[str, Any]: Performance metrics.
        """
        strategy = self.strategy_factory(**params)
        evaluator = BenchmarkEvaluator(
            data, commission=self.config.commission, bars_per_year=self.config.bars_per_year
        )
        metrics = evaluator._calculate_metrics(strategy.predict(data), strategy.name)
        return metrics

    def _calculate_stability_penalty(self, params: dict[str, Any], data: pd.DataFrame) -> float:
        """
        Calculates a penalty for parameter instability by perturbing continuous parameters.

        Measures how much performance (Sharpe Ratio) changes when parameters are shifted
        by a small amount. Uses only training data to prevent look-ahead bias.

        Args:
            params: Base parameters.
            data: Data to evaluate on (should be training/IS data).

        Returns:
            float: Standard deviation of Sharpe ratios under perturbation.
        """
        perturbations = []
        for key, value in params.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                # Small perturbation (5%)
                original_val = value
                for direction in [-1, 1]:
                    perturbed_params = params.copy()
                    delta = (
                        max(1, abs(original_val) * 0.05)
                        if isinstance(original_val, int)
                        else original_val * 0.05
                    )
                    perturbed_params[key] = original_val + (direction * delta)

                    try:
                        p_metrics = self._evaluate_strategy(data, perturbed_params)
                        perturbations.append(p_metrics.get("Sharpe Ratio", 0.0))
                    except Exception as e:
                        logger.warning(f"Failed to evaluate perturbed params: {e}")
                        continue

        if not perturbations:
            return 0.0

        # Penalty is the standard deviation of Sharpe ratios under perturbation
        return float(np.std(perturbations))

    def _calculate_regime_consistency(
        self, data: pd.DataFrame, strategy_params: dict[str, Any]
    ) -> float:
        """
        Measures how consistent performance is across different detected regimes.

        Args:
            data: Data containing 'regime' column (typically the training/IS window).
            strategy_params: Strategy parameters.

        Returns:
            float: Consistency score (1 - Coefficient of Variation), clipped at [0, 1].
        """
        strategy = self.strategy_factory(**strategy_params)
        evaluator = BenchmarkEvaluator(
            data, commission=self.config.commission, bars_per_year=self.config.bars_per_year
        )
        signals = strategy.predict(data)

        # Use evaluator to get returns
        _ = evaluator._calculate_metrics(signals, strategy.name)
        returns = evaluator.results.get(strategy.name + "_returns", np.zeros(len(data)))

        temp_df = pd.DataFrame({"returns": returns, "regime": data["regime"]})
        regime_returns = temp_df.groupby("regime")["returns"].mean()

        if len(regime_returns) < 2:
            return 1.0  # Not enough regimes to judge

        # Return 1 - CV of returns across regimes (higher is more consistent)
        mean_ret = np.mean(regime_returns)
        std_ret = np.std(regime_returns)

        cv = std_ret / (abs(mean_ret) + 1e-9)
        return float(np.clip(1.0 - cv, 0.0, 1.0))

    def run_optimization(self) -> WalkForwardResult:
        """
        Runs the full walk-forward optimization process.

        Optimizes for the selected metric (default: robustness score) across
        all rolling windows.

        Returns:
            WalkForwardResult: Best parameters and associated robustness metrics.
        """
        windows = self.generate_windows()
        if len(windows) < self.config.min_windows:
            raise ValueError(
                f"Insufficient data for {self.config.min_windows} windows. "
                f"Have {len(windows)}, need {self.config.min_windows}."
            )

        study = optuna.create_study(
            direction="maximize", sampler=optuna.samplers.TPESampler(seed=self.config.seed)
        )

        def objective(trial: optuna.Trial) -> float:
            params = self.param_space(trial)

            is_sharpes = []
            oos_sharpes = []

            # Additional metrics for selection
            oos_returns = []
            oos_sortinos = []
            oos_pfs = []
            oos_win_rates = []
            oos_max_drawdowns = []

            for train_data, test_data in windows:
                is_metrics = self._evaluate_strategy(train_data, params)
                oos_metrics = self._evaluate_strategy(test_data, params)

                is_sharpes.append(is_metrics.get("Sharpe Ratio", 0.0))
                oos_sharpes.append(oos_metrics.get("Sharpe Ratio", 0.0))

                oos_returns.append(oos_metrics.get("Total Return", 0.0))
                oos_sortinos.append(oos_metrics.get("Sortino Ratio", 0.0))
                oos_pfs.append(oos_metrics.get("Profit Factor", 0.0))
                oos_win_rates.append(oos_metrics.get("Win Rate", 0.0))
                oos_max_drawdowns.append(oos_metrics.get("Max Drawdown", 0.0))

            # Basic metrics
            oos_mean = np.mean(oos_sharpes)
            oos_std = np.std(oos_sharpes)
            is_mean = np.mean(is_sharpes)
            worst_oos = np.min(oos_sharpes)

            # Consistency metrics (1 - CV)
            wr_cons = 1.0 - (np.std(oos_win_rates) / (np.mean(oos_win_rates) + 1e-9))
            dd_cons = 1.0 - (np.std(oos_max_drawdowns) / (np.mean(oos_max_drawdowns) + 1e-9))

            # Robustness Components
            gap = max(0, is_mean - oos_mean)
            # Use only the first train window for stability check during optimization for speed
            # or use entire data. To be safe and disciplined, use the first window's training data.
            stability = self._calculate_stability_penalty(params, windows[0][0])
            # Use current train window for regime consistency to maintain discipline
            regime_cons = self._calculate_regime_consistency(train_data, params)

            # Calculate Robustness Score
            # Reward: high OOS Sharpe, worst-case Sharpe, consistency
            # Penalize: high OOS Variance, high IS/OOS Gap, High parameter sensitivity, Low regime consistency
            robustness = (
                (0.4 * oos_mean)
                + (0.2 * worst_oos)
                + (0.1 * wr_cons)
                + (0.1 * dd_cons)
                - (0.3 * oos_std)
                - (0.2 * gap)
                - (0.3 * stability)
                + (0.1 * regime_cons)
            )

            trial.set_user_attr("oos_mean", float(oos_mean))
            trial.set_user_attr("oos_std", float(oos_std))
            trial.set_user_attr("worst_oos", float(worst_oos))
            trial.set_user_attr("wr_cons", float(np.clip(wr_cons, 0, 1)))
            trial.set_user_attr("dd_cons", float(np.clip(dd_cons, 0, 1)))
            trial.set_user_attr("gap", float(gap))
            trial.set_user_attr("stability", float(stability))
            trial.set_user_attr("regime_cons", float(regime_cons))
            trial.set_user_attr("robustness_score", float(robustness))

            # Select return value based on config
            if self.config.metric == OptimizationMetric.ROBUSTNESS_SCORE:
                return float(robustness)
            if self.config.metric == OptimizationMetric.SHARPE:
                return float(oos_mean)
            if self.config.metric == OptimizationMetric.SORTINO:
                return float(np.mean(oos_sortinos))
            if self.config.metric == OptimizationMetric.PROFIT_FACTOR:
                return float(np.mean(oos_pfs))
            if self.config.metric == OptimizationMetric.TOTAL_RETURN:
                return float(np.mean(oos_returns))

            return float(robustness)

        study.optimize(objective, n_trials=self.config.n_trials)

        best_trial = study.best_trial
        best_params = best_trial.params

        # Final Metrics from best trial
        metrics = RobustnessMetrics(
            oos_sharpe_mean=best_trial.user_attrs["oos_mean"],
            oos_sharpe_std=best_trial.user_attrs["oos_std"],
            worst_window_sharpe=best_trial.user_attrs["worst_oos"],
            win_rate_consistency=best_trial.user_attrs["wr_cons"],
            max_drawdown_consistency=best_trial.user_attrs["dd_cons"],
            is_oos_gap=best_trial.user_attrs["gap"],
            stability_penalty=best_trial.user_attrs["stability"],
            regime_consistency=best_trial.user_attrs["regime_cons"],
            robustness_score=best_trial.user_attrs["robustness_score"],
        )

        # Generate window results for best params and aggregate returns
        window_results = []
        all_oos_returns = []

        for i, (train_data, test_data) in enumerate(windows):
            is_metrics = self._evaluate_strategy(train_data, best_params)

            # Re-evaluate to get returns series
            strategy = self.strategy_factory(**best_params)
            evaluator = BenchmarkEvaluator(
                test_data,
                commission=self.config.commission,
                bars_per_year=self.config.bars_per_year,
            )
            oos_metrics = evaluator._calculate_metrics(strategy.predict(test_data), strategy.name)

            # Extract returns from evaluator results
            returns = evaluator.results.get(strategy.name + "_returns", np.zeros(len(test_data)))
            all_oos_returns.extend(returns.tolist())

            window_results.append(
                WindowResult(window_index=i, is_metrics=is_metrics, oos_metrics=oos_metrics)
            )

        return WalkForwardResult(
            best_params=best_params,
            metrics=metrics,
            window_results=window_results,
            oos_returns=all_oos_returns,
        )


if __name__ == "__main__":
    # Example usage / test harness
    from src.research.benchmarks import EMACrossoverStrategy

    df = pd.DataFrame(
        {
            "open": np.random.randn(1000) + 2000,
            "high": np.random.randn(1000) + 2005,
            "low": np.random.randn(1000) + 1995,
            "close": np.random.randn(1000) + 2000,
            "tick_volume": np.random.randint(100, 1000, 1000),
        }
    )

    def ema_param_space(trial):
        return {
            "fast_window": trial.suggest_int("fast_window", 5, 20),
            "slow_window": trial.suggest_int("slow_window", 21, 50),
        }

    optimizer = WalkForwardOptimizer(
        data=df,
        strategy_factory=EMACrossoverStrategy,
        param_space=ema_param_space,
        config=WalkForwardConfig(n_trials=5, train_size=200, test_size=50, step_size=50),
    )

    result = optimizer.run_optimization()
    logger.info(
        "Optimization complete",
        best_params=result.best_params,
        score=result.metrics.robustness_score,
    )
