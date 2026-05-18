"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/hyperopt_walkforward.py
Disciplined Walk-Forward Optimization with Robustness Scoring.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
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
    CALMAR = "calmar"
    WIN_RATE = "win_rate"
    ROBUSTNESS_SCORE = "robustness_score"


class RobustnessWeights(BaseModel):
    """
    Weights for the institutional robustness score calculation.
    Defines the relative importance of consistency, stability, and efficiency.
    """

    oos_mean: float = Field(0.4, description="Weight for mean OOS Sharpe Ratio")
    worst_oos: float = Field(0.3, description="Weight for worst window OOS Sharpe Ratio")
    win_rate_consistency: float = Field(0.1, description="Weight for win rate consistency (1-CV)")
    drawdown_consistency: float = Field(
        0.1, description="Weight for max drawdown consistency (1-CV)"
    )
    oos_std: float = Field(0.2, description="Penalty weight for OOS Sharpe standard deviation")
    is_oos_gap: float = Field(0.3, description="Penalty weight for IS-OOS Sharpe gap")
    stability: float = Field(0.4, description="Penalty weight for parameter instability")
    regime_consistency: float = Field(0.2, description="Weight for consistency across regimes")
    walk_forward_efficiency: float = Field(
        0.3, description="Weight for Walk-Forward Efficiency (OOS / IS Sharpe)"
    )


class WalkForwardConfig(BaseModel):
    """
    Configuration for disciplined Walk-Forward Optimization.
    Enforces rolling window constraints and institutional performance thresholds.
    """

    train_size: int = Field(250, description="Number of candles for training/optimization")
    test_size: int = Field(50, description="Number of candles for out-of-sample testing")
    step_size: int = Field(50, description="Step size for rolling windows")
    min_windows: int = Field(3, description="Minimum number of windows required")
    metric: OptimizationMetric = OptimizationMetric.ROBUSTNESS_SCORE
    robustness_weights: RobustnessWeights = Field(default_factory=RobustnessWeights)
    n_trials: int = Field(50, description="Number of trials per window")
    seed: int = 42
    commission: float = 0.0002
    bars_per_year: int = Field(
        6240, description="Bars per year for annualization (e.g. 252 for Daily, 6240 for H1)"
    )
    min_oos_sharpe: float = Field(-float("inf"), description="Minimum allowed OOS Sharpe Ratio")
    max_oos_drawdown: float = Field(1.0, description="Maximum allowed OOS Drawdown (fraction)")
    min_trades_per_window: int = Field(5, description="Minimum trades required in each OOS window")
    min_regime_consistency: float = Field(0.0, description="Minimum required regime consistency score")
    min_walk_forward_efficiency: float = Field(0.0, description="Minimum required WFE (OOS / IS Sharpe)")


class RobustnessMetrics(BaseModel):
    """
    Structured metrics for institutional strategy robustness evaluation.
    Provides transparency into out-of-sample performance consistency and parameter stability.
    """

    oos_sharpe_mean: float
    oos_sharpe_std: float
    worst_window_sharpe: float
    win_rate_consistency: float
    max_drawdown_consistency: float
    is_oos_gap: float
    stability_penalty: float
    parameter_sensitivities: dict[str, float] = Field(default_factory=dict)
    regime_consistency: float
    robustness_score: float
    walk_forward_efficiency: float = 0.0
    constraints_violated: bool = False
    grade: str = "F"

    def calculate_grade(self) -> str:
        """
        Assigns an institutional robustness grade (A-F).

        Criteria:
        - A: Excellent robustness (>1.0), high WFE (>0.7), high regime consistency (>0.7), no violations.
        - B: Good robustness (>0.6), moderate WFE (>0.5), no major violations.
        - C: Acceptable robustness (>0.3), no major violations.
        - D: Poor robustness or minor violations.
        - F: Critical failure or major constraint violations.
        """
        if self.constraints_violated:
            return "F"

        if (
            self.robustness_score > 1.0
            and self.walk_forward_efficiency > 0.7
            and self.regime_consistency > 0.7
            and self.oos_sharpe_mean > 1.0
        ):
            return "A"

        if (
            self.robustness_score > 0.6
            and self.walk_forward_efficiency > 0.5
            and self.oos_sharpe_mean > 0.5
        ):
            return "B"

        if self.robustness_score > 0.3 and self.oos_sharpe_mean > 0.0:
            return "C"

        if self.robustness_score > 0.0:
            return "D"

        return "F"


class WindowResult(BaseModel):
    """Metrics for a single walk-forward window."""

    window_index: int
    is_metrics: dict[str, Any]
    oos_metrics: dict[str, Any]


class WalkForwardResult(BaseModel):
    """
    Comprehensive result of a Walk-Forward Optimization run.
    Stores optimal parameters, aggregated metrics, and window-level performance for auditing.
    """

    best_params: dict[str, Any]
    metrics: RobustnessMetrics
    window_results: list[WindowResult]
    oos_returns: list[float] = Field(default_factory=list, description="Aggregated OOS returns")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def save_json(self, filepath: str) -> None:
        """
        Save result to a JSON file for auditability.

        Args:
            filepath: Path to save the JSON file.
        """
        with open(filepath, "w") as f:
            f.write(self.model_dump_json(indent=4))

    def get_best_strategy(
        self, strategy_factory: Callable[..., BenchmarkStrategy]
    ) -> BenchmarkStrategy:
        """
        Instantiate the strategy with the best parameters found.

        Args:
            strategy_factory: The factory function used during optimization.

        Returns:
            BenchmarkStrategy: Strategy instance with optimal parameters.
        """
        return strategy_factory(**self.best_params)

    def to_report_section(self) -> Any:
        """
        Convert result to HyperparameterSection for ResearchReporter.

        Returns:
            HyperparameterSection: Structured section for the research report.
        """
        from src.research.reporting import HyperparameterSection, ParameterRobustness

        params = []
        for name, value in self.best_params.items():
            sensitivity_val = self.metrics.parameter_sensitivities.get(name, 0.0)
            sensitivity_txt = (
                f"Low (CV: {sensitivity_val:.2f})"
                if sensitivity_val < 0.2
                else f"Medium (CV: {sensitivity_val:.2f})"
                if sensitivity_val < 0.5
                else f"High (CV: {sensitivity_val:.2f})"
            )
            params.append(
                ParameterRobustness(
                    name=name,
                    range="Optimized",
                    optimal=str(value),
                    sensitivity=sensitivity_txt,
                )
            )

        violation_txt = " | [CONSTRAINTS VIOLATED]" if self.metrics.constraints_violated else ""
        insights = (
            f"Grade: {self.metrics.grade} | "
            f"OOS Sharpe Mean: {self.metrics.oos_sharpe_mean:.2f} | "
            f"WFE: {self.metrics.walk_forward_efficiency:.2f} | "
            f"Worst OOS Sharpe: {self.metrics.worst_window_sharpe:.2f} | "
            f"IS-OOS Gap: {self.metrics.is_oos_gap:.2f} | "
            f"Regime Consist: {self.metrics.regime_consistency:.2f} | "
            f"Stability Penalty: {self.metrics.stability_penalty:.2f}"
            f"{violation_txt}"
        )

        # Scale robustness score to 0-100 for report
        # We assume a score of 1.2+ is excellent (100) and 0 is poor (0)
        # Institutional standards typically look for Sharpe > 1.0 OOS
        display_score = float(np.clip(self.metrics.robustness_score / 1.2 * 100, 0, 100))

        return HyperparameterSection(
            stability_score=display_score,
            parameters=params,
            walk_forward_efficiency=float(self.metrics.walk_forward_efficiency),
            grade=self.metrics.grade,
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

    def _evaluate_strategy(
        self, data: pd.DataFrame, params: dict[str, Any]
    ) -> tuple[dict[str, Any], np.ndarray]:
        """
        Evaluates a strategy with given parameters on a dataset.

        Args:
            data: Data to evaluate on.
            params: Strategy parameters.

        Returns:
            Tuple[Dict[str, Any], np.ndarray]: Performance metrics and returns series.
        """
        strategy = self.strategy_factory(**params)
        evaluator = BenchmarkEvaluator(
            data, commission=self.config.commission, bars_per_year=self.config.bars_per_year
        )
        metrics = evaluator._calculate_metrics(strategy.predict(data), strategy.name)
        returns = evaluator.results.get(strategy.name + "_returns", np.zeros(len(data)))
        return metrics, returns

    def _calculate_stability_penalty(
        self, params: dict[str, Any], data: pd.DataFrame, perturbation_pct: float = 0.05
    ) -> tuple[float, dict[str, float]]:
        """
        Calculates a penalty for parameter instability by perturbing parameters.

        Measures how much performance (Sharpe Ratio) changes when parameters are shifted
        by a small amount. Uses only training data to prevent look-ahead bias.
        Utilizes scale-invariant CV and includes a fragility safeguard.

        Args:
            params: Base parameters.
            data: Data to evaluate on (should be training/IS data).
            perturbation_pct: Percentage to perturb parameters (default 5%).

        Returns:
            Tuple[float, Dict[str, float]]: (Aggregate CV penalty, Per-parameter sensitivities).
        """
        all_perturbations = []
        param_sensitivities = {}
        try:
            base_metrics, _ = self._evaluate_strategy(data, params)
            base_sharpe = base_metrics.get("Sharpe Ratio", 0.0)
            if np.isnan(base_sharpe):
                return 10.0, {}  # Fragility safeguard
            all_perturbations.append(base_sharpe)

            for key, value in params.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    original_val = float(value)
                    is_int = isinstance(value, int)
                    param_perturbations = [base_sharpe]

                    delta = (
                        float(max(1, round(abs(original_val) * perturbation_pct)))
                        if is_int
                        else max(1e-5, abs(original_val) * perturbation_pct)
                    )

                    for direction in [-1, 1]:
                        perturbed_params = params.copy()
                        new_val = (
                            round(original_val + (direction * delta))
                            if is_int
                            else original_val + (direction * delta)
                        )

                        if new_val == original_val:
                            continue

                        perturbed_params[key] = new_val

                        try:
                            p_metrics, _ = self._evaluate_strategy(data, perturbed_params)
                            p_sharpe = p_metrics.get("Sharpe Ratio", 0.0)
                            if not np.isnan(p_sharpe):
                                param_perturbations.append(float(p_sharpe))
                                all_perturbations.append(float(p_sharpe))
                                if p_sharpe < 0 and base_sharpe > 0:
                                    logger.warning("Fragility detected for %s=%s", key, new_val)
                                    return 10.0, {}
                            else:
                                return 10.0, {}
                        except Exception as e:
                            logger.debug("Perturbation failed for %s=%s: %s", key, new_val, e)
                            return 10.0, {}

                    # Calculate per-parameter sensitivity (CV)
                    if len(param_perturbations) > 1:
                        p_mean = np.mean(param_perturbations)
                        p_std = np.std(param_perturbations)
                        param_sensitivities[key] = float(p_std / (abs(p_mean) + 1e-9))

        except Exception as e:
            logger.warning("Stability calculation failed: %s", e)
            return 10.0, {}

        if not all_perturbations:
            return 0.0, {}

        mean_sharpe = np.mean(all_perturbations)
        std_sharpe = np.std(all_perturbations)
        aggregate_cv = std_sharpe / (abs(mean_sharpe) + 1e-9)

        return float(np.clip(aggregate_cv, 0.0, 10.0)), param_sensitivities

    def _calculate_regime_consistency(self, data: pd.DataFrame, returns: np.ndarray) -> float:
        """
        Measures how consistent performance (Sharpe Ratio) is across different detected regimes.
        Uses frequency-weighting to ensure that the performance consistency across market
        environments is not skewed by regimes with few observations.

        Args:
            data: Data containing 'regime' column (typically the training/IS window).
            returns: Returns series for the given data.

        Returns:
            float: Frequency-weighted consistency score (1 - CV), clipped at [0, 1].
        """
        if "regime" not in data.columns:
            return 0.5

        temp_df = pd.DataFrame({"returns": returns, "regime": data["regime"]})

        def calc_sharpe(x: pd.Series) -> float | None:
            if len(x) < 5:  # Minimum observations for a valid regime-specific Sharpe
                return None
            std = float(x.std())
            if std < 1e-9:
                return 0.0
            return float(x.mean() / std * np.sqrt(self.config.bars_per_year))

        regime_stats = temp_df.groupby("regime")["returns"].agg([calc_sharpe, "count"])
        # Filter out regimes with None Sharpe
        valid_stats = regime_stats.dropna(subset=["calc_sharpe"])

        if len(valid_stats) == 0:
            return 0.0
        if len(valid_stats) < 2:
            # Only one regime present: we cannot determine consistency.
            # Return a neutral-to-low score (0.5) to avoid over-weighting
            # configurations that only trade in a single environment.
            return 0.5

        # Frequency-weighted Mean and Std
        weights = valid_stats["count"] / valid_stats["count"].sum()
        weighted_mean = np.average(valid_stats["calc_sharpe"], weights=weights)
        weighted_std = np.sqrt(
            np.average((valid_stats["calc_sharpe"] - weighted_mean) ** 2, weights=weights)
        )

        # Return 1 - weighted CV of Sharpe ratios across regimes (higher is more consistent)
        cv = weighted_std / (abs(weighted_mean) + 1e-9)
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
            oos_calmars = []

            constraint_penalty = 0.0
            violated = False

            regime_cons_list = []
            for train_data, test_data in windows:
                is_metrics, is_returns = self._evaluate_strategy(train_data, params)
                oos_metrics, _ = self._evaluate_strategy(test_data, params)

                is_sharpes.append(is_metrics.get("Sharpe Ratio", 0.0))
                oos_sharpes.append(oos_metrics.get("Sharpe Ratio", 0.0))

                oos_returns.append(oos_metrics.get("Total Return", 0.0))
                oos_sortinos.append(oos_metrics.get("Sortino Ratio", 0.0))
                oos_pfs.append(oos_metrics.get("Profit Factor", 0.0))
                oos_win_rates.append(oos_metrics.get("Win Rate", 0.0))
                oos_max_drawdowns.append(oos_metrics.get("Max Drawdown", 0.0))
                oos_calmars.append(oos_metrics.get("Calmar Ratio", 0.0))

                # Track constraints
                num_trades = oos_metrics.get("Num Trades", 0)

                # Track regime consistency across windows using cached IS returns
                regime_cons_list.append(self._calculate_regime_consistency(train_data, is_returns))

                if num_trades < self.config.min_trades_per_window:
                    constraint_penalty += 1.0 * (self.config.min_trades_per_window - num_trades)
                    violated = True

            # Basic metrics
            oos_mean = np.mean(oos_sharpes)
            oos_std = np.std(oos_sharpes)
            is_mean = np.mean(is_sharpes)
            worst_oos = np.min(oos_sharpes)
            max_oos_dd = np.max(oos_max_drawdowns)

            # Check constraints
            if worst_oos < self.config.min_oos_sharpe:
                constraint_penalty += 10.0 * (self.config.min_oos_sharpe - worst_oos)
                violated = True
            if max_oos_dd > self.config.max_oos_drawdown:
                constraint_penalty += 10.0 * (max_oos_dd - self.config.max_oos_drawdown)
                violated = True

            # Average regime consistency across all windows
            regime_cons = float(np.mean(regime_cons_list))
            if regime_cons < self.config.min_regime_consistency:
                constraint_penalty += 10.0 * (self.config.min_regime_consistency - regime_cons)
                violated = True

            wfe_val = oos_mean / (is_mean + 1e-9)
            if wfe_val < self.config.min_walk_forward_efficiency:
                constraint_penalty += 10.0 * (self.config.min_walk_forward_efficiency - wfe_val)
                violated = True

            # Consistency metrics (1 - CV)
            wr_cons = 1.0 - (np.std(oos_win_rates) / (np.mean(oos_win_rates) + 1e-9))
            dd_cons = 1.0 - (np.std(oos_max_drawdowns) / (np.mean(oos_max_drawdowns) + 1e-9))

            # Robustness Components
            gap = max(0, is_mean - oos_mean)

            # Performance Stability (Parameter Sensitivity)
            # Average stability over 2-3 windows for better representativeness
            n_stability_windows = min(3, len(windows))
            indices = np.linspace(0, len(windows) - 1, n_stability_windows, dtype=int)
            stability_scores = []
            all_param_sens = []
            for idx in indices:
                penalty, param_sens = self._calculate_stability_penalty(params, windows[idx][0])
                stability_scores.append(penalty)
                all_param_sens.append(param_sens)

            stability = float(np.mean(stability_scores))
            avg_param_sens = {}
            if all_param_sens:
                for k in params:
                    vals = [s[k] for s in all_param_sens if k in s]
                    if vals:
                        avg_param_sens[k] = float(np.mean(vals))

            # Calculate Robustness Score
            # Reward: high OOS Sharpe, worst-case Sharpe, consistency, high WFE
            # Penalize: high OOS Variance, high IS/OOS Gap, High parameter sensitivity, Low regime consistency, Constraints violated
            w = self.config.robustness_weights
            robustness = (
                (w.oos_mean * oos_mean)
                + (w.worst_oos * worst_oos)
                + (w.win_rate_consistency * wr_cons)
                + (w.drawdown_consistency * dd_cons)
                + (w.walk_forward_efficiency * np.clip(wfe_val, 0, 1.2))  # Reward WFE
                - (w.oos_std * oos_std)
                - (w.is_oos_gap * gap)
                - (w.stability * stability)
                + (w.regime_consistency * regime_cons)
                - constraint_penalty
            )

            trial.set_user_attr("oos_mean", float(oos_mean))
            trial.set_user_attr("oos_std", float(oos_std))
            trial.set_user_attr("worst_oos", float(worst_oos))
            trial.set_user_attr("wr_cons", float(np.clip(wr_cons, 0, 1)))
            trial.set_user_attr("dd_cons", float(np.clip(dd_cons, 0, 1)))
            trial.set_user_attr("gap", float(gap))
            trial.set_user_attr("stability", float(stability))
            trial.set_user_attr("param_sensitivities", avg_param_sens)
            trial.set_user_attr("regime_cons", float(regime_cons))
            trial.set_user_attr("violated", bool(violated))
            trial.set_user_attr("walk_forward_efficiency", float(wfe_val))
            trial.set_user_attr("robustness_score", float(robustness))

            # Select base score based on config
            base_score = 0.0
            if self.config.metric == OptimizationMetric.ROBUSTNESS_SCORE:
                return float(robustness)  # Already includes constraint_penalty
            elif self.config.metric == OptimizationMetric.SHARPE:
                base_score = float(oos_mean)
            elif self.config.metric == OptimizationMetric.SORTINO:
                base_score = float(np.mean(oos_sortinos))
            elif self.config.metric == OptimizationMetric.PROFIT_FACTOR:
                base_score = float(np.mean(oos_pfs))
            elif self.config.metric == OptimizationMetric.TOTAL_RETURN:
                base_score = float(np.mean(oos_returns))
            elif self.config.metric == OptimizationMetric.CALMAR:
                base_score = float(np.mean(oos_calmars))
            elif self.config.metric == OptimizationMetric.WIN_RATE:
                base_score = float(np.mean(oos_win_rates))
            else:
                base_score = float(robustness)
                return base_score

            # For standard metrics, we still apply the constraint penalty
            return float(base_score - constraint_penalty)

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
            parameter_sensitivities=best_trial.user_attrs["param_sensitivities"],
            regime_consistency=best_trial.user_attrs["regime_cons"],
            walk_forward_efficiency=best_trial.user_attrs["walk_forward_efficiency"],
            robustness_score=best_trial.user_attrs["robustness_score"],
            constraints_violated=best_trial.user_attrs["violated"],
        )
        metrics.grade = metrics.calculate_grade()

        # Generate window results for best params and aggregate returns
        window_results = []
        all_oos_returns = []

        for i, (train_data, test_data) in enumerate(windows):
            is_metrics, _ = self._evaluate_strategy(train_data, best_params)
            oos_metrics, oos_returns_iter = self._evaluate_strategy(test_data, best_params)

            all_oos_returns.extend(oos_returns_iter.tolist())

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

    def ema_param_space(trial: optuna.Trial) -> dict[str, Any]:
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
        extra={
            "best_params": result.best_params,
            "robustness_score": round(result.metrics.robustness_score, 4),
            "oos_sharpe_mean": round(result.metrics.oos_sharpe_mean, 4),
        },
    )
