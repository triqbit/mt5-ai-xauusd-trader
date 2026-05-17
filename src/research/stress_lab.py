"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/stress_lab.py
Adversarial resilience testing framework for strategy stress testing.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from src.research.benchmarks import BenchmarkStrategy

logger = logging.getLogger(__name__)


class StressSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StressScenario(BaseModel):
    """
    Institutional configuration for a specific adversarial stress scenario.

    This model defines the parameters for market data perturbations and execution friction
    used to test strategy resilience under adverse conditions. It covers execution
    inefficiencies, data quality issues, and structural market shifts.

    Attributes:
        name: Unique identifier for the scenario.
        description: Qualitative description of the stress conditions.
        severity: Qualitative assessment of the stress intensity (LOW to CRITICAL).
        spread_multiplier: Scaler for the base market spread.
        spread_spike_prob: Probability of a sudden, extreme spread expansion.
        spread_spike_magnitude: Additional spread added during a spike.
        slippage_bps: Base execution slippage in basis points.
        slippage_spike_prob: Probability of an extreme slippage event.
        slippage_spike_magnitude_bps: Additional slippage bps during a spike.
        execution_delay_steps: Number of price bars to delay execution signals.
        execution_delay_jitter: Random variance (+/-) added to the execution delay.
        missing_tick_prob: Probability of the strategy missing a price update.
        stale_data_prob: Probability of receiving repeated (stale) price data.
        price_noise_sigma: Standard deviation of Gaussian noise added to OHLC prices.
        choppy_breakout_prob: Probability of adversarial price spikes designed to trap trends.
        regime_flip_prob: Probability of inducing a sudden regime transition or trend reversal.
        service_failure_prob: Probability of simulated infrastructure or API failure.
        flash_crash_prob: Probability of a violent, deep price dislocation and recovery.
    """

    name: str
    description: str
    severity: StressSeverity = StressSeverity.MEDIUM

    # Execution stress
    spread_multiplier: float = 1.0  # 1.0 = normal
    spread_spike_prob: float = 0.0  # Probability of a sudden spread explosion
    spread_spike_magnitude: float = 0.0  # Magnitude of the spread spike
    slippage_bps: float = 0.0  # Basis points
    slippage_spike_prob: float = 0.0  # Probability of an extreme slippage event
    slippage_spike_magnitude_bps: float = 0.0  # Magnitude of the spike in bps
    execution_delay_steps: int = 0  # Number of steps to delay execution
    execution_delay_jitter: int = 0  # Max +/- steps of random jitter

    # Data stress
    missing_tick_prob: float = 0.0  # Probability of missing a price update
    stale_data_prob: float = 0.0  # Probability of price data not updating (stale)
    price_noise_sigma: float = 0.0  # Gaussian noise added to OHLC

    # Market structure stress
    choppy_breakout_prob: float = 0.0  # Probability of fake breakouts
    regime_flip_prob: float = 0.0  # Probability of sudden regime transitions

    # External service stress
    service_failure_prob: float = 0.0  # Probability of 'external service' being down

    # Tail risk events
    flash_crash_prob: float = 0.0  # Probability of a sudden deep price dislocation

    # Configuration overrides
    lot_size: float = 0.1
    commission_per_lot: float = 7.0  # Matches BacktestEngine default
    seed: int = 42


class StressTestMetrics(BaseModel):
    """
    Standardized performance and resilience metrics captured during a stress simulation.

    This model aggregates institutional-grade performance, risk, and execution quality
    data to facilitate rigorous comparative analysis against baseline (neutral) runs.

    Attributes:
        total_return: Percentage return over the simulation period.
        max_drawdown: Maximum peak-to-trough equity decline.
        sharpe_ratio: Annualized risk-adjusted return (using 252-day scaling).
        win_rate: Proportion of trades with positive realized P&L.
        num_trades: Total number of round-trip trades executed.
        recovery_factor: Ratio of total net profit to maximum drawdown.
        profit_factor: Ratio of gross profit to gross loss.
        execution_quality_score: 0.0-1.0 score based on successfully processed signals vs failures.
        latency_impact: Percentage of signals delayed or blocked by simulated latency.
        max_slippage_experienced: Maximum basis points of slippage seen in any single trade.
        sortino_ratio: Annualized return relative to downside volatility.
    """

    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    num_trades: int
    recovery_factor: float = 0.0
    profit_factor: float = 0.0
    execution_quality_score: float  # 0.0 to 1.0
    latency_impact: float  # Percentage impact of delays
    max_slippage_experienced: float = 0.0  # Max bps of slippage seen
    total_commission_cost: float = 0.0
    total_slippage_cost: float = 0.0
    sortino_ratio: float = 0.0


class ResilienceReport(BaseModel):
    """
    Comprehensive institutional audit report for a strategy's resilience under stress.

    This model serves as the final analytical output of the StressLab, synthesizing
    results from multiple adversarial scenarios and sensitivity analyses to provide
    a definitive assessment of strategy fragility.

    Attributes:
        strategy_name: Name of the strategy under evaluation.
        timestamp: Audit execution time.
        baseline_metrics: Reference performance metrics under normal market conditions.
        scenario_results: Dictionary mapping scenario names to their respective metrics.
        sensitivity_results: Results from parameter sweep sensitivity analyses.
        resilience_score: Composite 0-100 score representing overall robustness.
        sharpe_decay: Average percentage degradation in Sharpe ratio across scenarios.
        sortino_decay: Average percentage degradation in Sortino ratio across scenarios.
        win_rate_decay: Average percentage degradation in win rate across scenarios.
        fragility_indicators: List of qualitative warnings identifying specific weaknesses.
        failure_points: List of conditions where the strategy becomes fundamentally unviable.
        degradation_summary: Human-readable executive summary of the strategy's robustness.
    """

    strategy_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    baseline_metrics: StressTestMetrics
    scenario_results: dict[str, StressTestMetrics]
    sensitivity_results: dict[str, list[tuple[float, float]]] = Field(default_factory=dict)
    resilience_score: float  # Composite score 0-100
    sharpe_decay: float = 0.0
    sortino_decay: float = 0.0
    win_rate_decay: float = 0.0
    fragility_indicators: list[str]
    failure_points: list[str]
    degradation_summary: str

    def to_report_section(self) -> Any:
        """
        Converts the ResilienceReport into a StressTestSection for institutional reporting.

        This facilitates seamless integration with the ResearchReporter pipeline,
        ensuring that stress test outcomes are presented with high-fidelity formatting.

        Returns:
            StressTestSection: A populated Pydantic model for the reporting orchestrator.
        """
        from src.research.reporting import StressedMetric, StressTestSection

        def _map_metric(name: str, m: StressTestMetrics) -> StressedMetric:
            return StressedMetric(
                name=name,
                total_return=f"{m.total_return:.2%}",
                max_drawdown=f"{m.max_drawdown:.2%}",
                sharpe=f"{m.sharpe_ratio:.2f}",
                recovery_factor=f"{m.recovery_factor:.2f}",
                profit_factor=f"{m.profit_factor:.2f}",
                outcome="FAIL" if m.total_return < 0 else "PASS",
            )

        # Exclude sensitivity runs from the main scenarios table for readability
        main_scenarios = [
            _map_metric(name, res)
            for name, res in self.scenario_results.items()
            if not name.startswith("Sensitivity_")
        ]

        return StressTestSection(
            resilience_score=self.resilience_score,
            baseline=_map_metric("Baseline", self.baseline_metrics),
            scenarios=main_scenarios,
            sharpe_decay=self.sharpe_decay,
            win_rate_decay=self.win_rate_decay,
            fragility_indicators=self.fragility_indicators,
            failure_points=self.failure_points,
            insights=self.degradation_summary,
        )


class StressLab:
    """
    Institutional-grade stress testing laboratory for XAUUSD trading strategies.

    This module implements an adversarial simulation framework that goes beyond
    standard historical backtesting. It evaluates strategy resilience by:
    1. Replaying historical data with synthetic execution friction (slippage spikes, spread widening).
    2. Perturbing price action using ATR-relative shocks to simulate 'fake breakouts'.
    3. Inducing sudden regime transitions and trend exhaustion to test adaptive logic.
    4. Simulating infrastructure instability via service failure injection and execution delays.

    Goal: Quantify 'strategy fragility' and identify the exact market conditions under
    which a system's risk-adjusted performance degrades non-linearly.
    """

    def __init__(
        self,
        strategy: BenchmarkStrategy,
        data: pd.DataFrame,
        initial_balance: float = 10000.0,
        contract_multiplier: float = 100.0,  # Default for XAUUSD
        commission_per_lot: float = 7.0,
    ):
        self.strategy = strategy
        self.data = data.copy()
        self.initial_balance = initial_balance
        self.contract_multiplier = contract_multiplier
        self.commission_per_lot = commission_per_lot
        self.results: dict[str, StressTestMetrics] = {}
        self.sensitivity_data: dict[str, list[tuple[float, float]]] = {}

    def create_execution_hell_scenario(self) -> StressScenario:
        """Create a scenario with high slippage, wide spreads, and delays."""
        return StressScenario(
            name="Execution Hell",
            description="Extreme execution friction: wide spreads, slippage spikes, and delays.",
            severity=StressSeverity.CRITICAL,
            spread_multiplier=3.0,
            spread_spike_prob=0.1,
            spread_spike_magnitude=2.0,
            slippage_bps=5.0,
            slippage_spike_prob=0.1,
            slippage_spike_magnitude_bps=50.0,
            execution_delay_steps=3,
            execution_delay_jitter=2,
            service_failure_prob=0.05,
            commission_per_lot=self.commission_per_lot,
        )

    def create_liquidity_crisis_scenario(self) -> StressScenario:
        """Create a scenario with missing data and extreme choppy price action."""
        return StressScenario(
            name="Liquidity Crisis",
            description="Fragmented liquidity: missing ticks, price noise, and choppy breakouts.",
            severity=StressSeverity.HIGH,
            missing_tick_prob=0.2,
            price_noise_sigma=1.0,
            choppy_breakout_prob=0.15,
            spread_multiplier=2.5,
            spread_spike_prob=0.05,
            spread_spike_magnitude=1.0,
            commission_per_lot=self.commission_per_lot,
        )

    def create_regime_shock_scenario(self) -> StressScenario:
        """Create a scenario with frequent and violent regime transitions."""
        return StressScenario(
            name="Regime Shock",
            description="Market structural instability: frequent regime flips and trend reversals.",
            severity=StressSeverity.HIGH,
            regime_flip_prob=0.1,
            choppy_breakout_prob=0.05,
            commission_per_lot=self.commission_per_lot,
        )

    def create_flash_crash_scenario(self) -> StressScenario:
        """Create a scenario with a violent flash crash event."""
        return StressScenario(
            name="Flash Crash",
            description="Violent price dislocation: sudden deep drop and extreme slippage.",
            severity=StressSeverity.CRITICAL,
            flash_crash_prob=0.01,
            slippage_bps=10.0,
            slippage_spike_prob=0.2,
            slippage_spike_magnitude_bps=200.0,
            spread_multiplier=5.0,
            commission_per_lot=self.commission_per_lot,
        )

    def create_data_freeze_scenario(self) -> StressScenario:
        """Create a scenario with prolonged stale price data (API/Feed freeze)."""
        return StressScenario(
            name="Data Freeze",
            description="Feed instability: prolonged periods of stale price data and missed updates.",
            severity=StressSeverity.HIGH,
            stale_data_prob=0.8,
            missing_tick_prob=0.1,
            spread_multiplier=1.5,
            commission_per_lot=self.commission_per_lot,
        )

    def run_standard_suite(self, baseline_metrics: StressTestMetrics) -> ResilienceReport:
        """
        Executes the standard suite of adversarial stress scenarios and sensitivity analysis.

        This suite covers:
        - Execution Hell: High friction and latency.
        - Liquidity Crisis: Data gaps and choppy price action.
        - Regime Shock: Structural market instability.
        - Flash Crash: Extreme tail risk events.
        - Data Freeze: Feed instability and stale data.
        - Sensitivity Analysis: Spread and slippage breaking point detection.

        Args:
            baseline_metrics: Metrics from a neutral/normal run for comparison.

        Returns:
            ResilienceReport: Aggregated results and fragility analysis.
        """
        scenarios = [
            self.create_execution_hell_scenario(),
            self.create_liquidity_crisis_scenario(),
            self.create_regime_shock_scenario(),
            self.create_flash_crash_scenario(),
            self.create_data_freeze_scenario(),
        ]

        for scenario in scenarios:
            self.run_scenario(scenario)

        # Run sensitivity analysis for key friction parameters
        self.analyze_sensitivity("spread_multiplier", np.linspace(1.0, 5.0, 5))
        self.analyze_sensitivity("slippage_bps", np.linspace(0.0, 20.0, 5))

        return self.generate_report(baseline_metrics)

    def analyze_sensitivity(self, parameter: str, values: np.ndarray | list[float]) -> None:
        """
        Performs sensitivity analysis for a specific stress parameter.

        Runs multiple simulations with varying levels of the specified parameter
        to identify non-linear performance decay and 'breaking points'.

        Args:
            parameter: The attribute name in StressScenario to vary.
            values: A list or array of values to test for the parameter.
        """
        logger.info(f"Analyzing sensitivity for {parameter}...")
        results = []

        for val in values:
            val_str = f"{val:.2f}"
            scenario = StressScenario(
                name=f"Sensitivity_{parameter}_{val_str}",
                description=f"Sensitivity test for {parameter} at {val_str}",
                commission_per_lot=self.commission_per_lot,
            )
            setattr(scenario, parameter, val)
            metrics = self.run_scenario(scenario)
            results.append((float(val), float(metrics.total_return)))

        self.sensitivity_data[parameter] = results

    def run_scenario(self, scenario: StressScenario) -> StressTestMetrics:
        """
        Executes a specific stress scenario against the loaded strategy and data.

        The process involves:
        1. Injecting data-level perturbations (noise, gaps, regime flips).
        2. Simulating the strategy's signals on this 'hostile' data.
        3. Running a high-fidelity execution loop that applies slippage spikes,
           latency, and external service outages.

        Args:
            scenario: The StressScenario configuration to apply.

        Returns:
            StressTestMetrics: Performance metrics captured under the specified stress.
        """
        logger.info(f"Running stress scenario: {scenario.name} for {self.strategy.name}")

        # 1. Perturb data based on scenario
        perturbed_data = self._apply_perturbations(self.data, scenario)

        # 2. Run specialized backtest with execution stress
        metrics = self._backtest_with_stress(perturbed_data, scenario)

        self.results[scenario.name] = metrics
        return metrics

    def generate_report(self, baseline_metrics: StressTestMetrics) -> ResilienceReport:
        """
        Synthesizes results from all executed scenarios into a structured report.

        Calculates a composite resilience score based on performance retention,
        identifies non-linear failure points, and detects 'fragility indicators'
        such as over-trading spikes or negative edge transitions.

        Args:
            baseline_metrics: The reference performance metrics under normal conditions.

        Returns:
            ResilienceReport: A typed report with insights and metrics.
        """
        scenario_results = self.results

        # Calculate resilience score (0-100)
        # Average performance retention across all scenarios
        scores = []
        sharpe_decays = []
        sortino_decays = []
        win_rate_decays = []

        for metrics in scenario_results.values():
            # Robust retention calculation handling negative baselines
            b_ret = baseline_metrics.total_return
            m_ret = metrics.total_return
            if abs(b_ret) < 1e-9:
                retention = 1.0 if m_ret >= 0 else 0.0
            else:
                # 1.0 means no change, <1.0 means worse, >1.0 means better
                retention = 1.0 + (m_ret - b_ret) / abs(b_ret)

            # Clip between 0 and 1.2 for the score
            scores.append(np.clip(retention, 0, 1.2))

            # Calculate decays (percentage degradation relative to baseline magnitude)
            def _calc_decay(b: float, m: float) -> float:
                """Robust decay calculation handling zero/near-zero baselines."""
                if abs(b) < 1e-9:
                    # If baseline is zero, any negative result is 100% decay, positive is 0%
                    return 0.0 if m >= b else 1.0
                # Use absolute baseline for relative comparison to handle negative metrics (e.g., negative Sharpe)
                decay = (b - m) / abs(b)
                # Cap extreme outliers for reporting stability
                return float(np.clip(decay, -2.0, 2.0))

            s_decay = _calc_decay(baseline_metrics.sharpe_ratio, metrics.sharpe_ratio)
            so_decay = _calc_decay(baseline_metrics.sortino_ratio, metrics.sortino_ratio)
            wr_decay = _calc_decay(baseline_metrics.win_rate, metrics.win_rate)

            # Record decays (allow negative if improved, but cap for aggregation)
            sharpe_decays.append(max(-1.0, s_decay))
            sortino_decays.append(max(-1.0, so_decay))
            win_rate_decays.append(max(-1.0, wr_decay))

        resilience_score = float(np.mean(scores) * 100) if scores else 0.0
        avg_sharpe_decay = float(np.mean(sharpe_decays)) if sharpe_decays else 0.0
        avg_sortino_decay = float(np.mean(sortino_decays)) if sortino_decays else 0.0
        avg_win_rate_decay = float(np.mean(win_rate_decays)) if win_rate_decays else 0.0

        # Identify fragility indicators
        fragility = []
        failure_points = []

        for scenario_name, metrics in scenario_results.items():
            if metrics.max_drawdown > baseline_metrics.max_drawdown * 2:
                fragility.append(f"Drawdown explosion in {scenario_name}")
            if metrics.total_return < 0 and baseline_metrics.total_return > 0:
                failure_points.append(f"Strategy becomes unprofitable under {scenario_name}")
            if metrics.max_drawdown > 0.5:
                failure_points.append(f"Critical drawdown (>50%) in {scenario_name}")
            if metrics.sharpe_ratio < baseline_metrics.sharpe_ratio * 0.5:
                fragility.append(f"Sharpe ratio halved under {scenario_name}")
            if metrics.latency_impact > 0.1:
                fragility.append(f"High sensitivity to infrastructure delays in {scenario_name}")
            if metrics.max_slippage_experienced > 100:
                fragility.append(f"Extreme slippage sensitivity in {scenario_name}")
            if metrics.num_trades > baseline_metrics.num_trades * 2:
                fragility.append(f"Over-trading spike in {scenario_name}")
            if metrics.profit_factor < 1.0 and baseline_metrics.profit_factor >= 1.0:
                fragility.append(f"Negative edge (PF < 1.0) in {scenario_name}")

        return ResilienceReport(
            strategy_name=self.strategy.name,
            baseline_metrics=baseline_metrics,
            scenario_results=scenario_results,
            sensitivity_results=self.sensitivity_data,
            resilience_score=resilience_score,
            sharpe_decay=avg_sharpe_decay,
            sortino_decay=avg_sortino_decay,
            win_rate_decay=avg_win_rate_decay,
            fragility_indicators=fragility,
            failure_points=failure_points,
            degradation_summary=self._generate_summary(
                baseline_metrics, scenario_results, self.sensitivity_data
            ),
        )

    def _generate_summary(
        self,
        baseline: StressTestMetrics,
        results: dict[str, StressTestMetrics],
        sensitivity: dict[str, list[tuple[float, float]]],
    ) -> str:
        """
        Generates a human-readable summary of the strategy's overall robustness.

        Args:
            baseline: Baseline performance metrics.
            results: Dictionary of scenario names to their respective metrics.
            sensitivity: Sensitivity analysis results.

        Returns:
            str: A multi-line summary with return comparisons and status labels.
        """
        # Exclude sensitivity-specific runs and the baseline/normal runs from the general scenario count for clarity
        excluded_prefixes = ("Sensitivity_", "Baseline", "Normal", "Neutral")
        scenario_keys = [k for k in results if not any(k.startswith(p) for p in excluded_prefixes)]
        stressed_returns = [results[k].total_return for k in scenario_keys]

        num_stressed = len(stressed_returns)
        summary = (
            f"Strategy '{self.strategy.name}' evaluated against {num_stressed} stress scenarios.\n"
        )
        avg_return = np.mean(stressed_returns) if stressed_returns else 0.0
        summary += (
            f"Baseline Return: {baseline.total_return:.2%}, Avg Stressed Return: {avg_return:.2%}\n"
        )

        if avg_return < 0:
            summary += "CRITICAL: Strategy is generally not robust to adverse conditions.\n"
        elif avg_return < baseline.total_return * 0.5:
            summary += "WARNING: Strategy shows significant performance degradation under stress.\n"
        else:
            summary += "OK: Strategy shows reasonable resilience.\n"

        # Add quantitative sensitivity insights
        if sensitivity:
            summary += "\nSensitivity Analysis Insights:"
            for param, data in sensitivity.items():
                breaking_point = None
                fifty_pct_decay = None

                for val, ret in data:
                    # Detect breaking point (unprofitable)
                    if ret < 0 and breaking_point is None:
                        breaking_point = val

                    # Detect 50% performance decay
                    if (
                        baseline.total_return > 0
                        and ret <= baseline.total_return * 0.5
                        and fifty_pct_decay is None
                    ):
                        fifty_pct_decay = val

                if breaking_point is not None:
                    summary += f"\n- Breaking point for {param} detected at {breaking_point:.2f}."
                if fifty_pct_decay is not None:
                    summary += f"\n- 50% performance decay for {param} at {fifty_pct_decay:.2f}."

                # Calculate Alpha Decay (Slope of performance degradation)
                if len(data) > 1:
                    vals = [d[0] for d in data]
                    rets = [d[1] for d in data]
                    # Linear slope between first and last tested points
                    slope = (rets[-1] - rets[0]) / (vals[-1] - vals[0] + 1e-9)

                    if param == "slippage_bps":
                        # Return loss in basis points per bp of slippage
                        summary += f"\n- Alpha Decay: {abs(slope) * 10000:.1f} bps return loss per bp of slippage."
                    elif param == "spread_multiplier":
                        summary += f"\n- Alpha Decay: {abs(slope):.2%} return loss per unit of spread multiplier."
                    else:
                        summary += f"\n- Alpha Decay: {abs(slope):.2f} units of return loss per unit of {param}."

        return summary

    def _apply_perturbations(self, df: pd.DataFrame, scenario: StressScenario) -> pd.DataFrame:
        """Apply data-level perturbations using adversarial logic."""
        df = df.copy()
        rng = np.random.default_rng(scenario.seed)

        # Calculate a rolling ATR for relative perturbations
        high_low = df["high"] - df["low"]
        high_cp = np.abs(df["high"] - df["close"].shift(1))
        low_cp = np.abs(df["low"] - df["close"].shift(1))
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean().fillna(tr.mean())

        # 1. Missing ticks
        if scenario.missing_tick_prob > 0:
            mask = rng.random(len(df)) > scenario.missing_tick_prob
            df = df[mask].reset_index(drop=True)
            # Re-index ATR to match new dataframe size if needed, but we use it pointwise below
            atr = atr[mask].reset_index(drop=True)

        # 2. Price noise
        if scenario.price_noise_sigma > 0:
            noise = rng.normal(0, scenario.price_noise_sigma, (len(df), 4))
            df[["open", "high", "low", "close"]] += noise
            # Ensure price consistency
            df["high"] = df[["open", "close", "high"]].max(axis=1)
            df["low"] = df[["open", "close", "low"]].min(axis=1)

        # 3. Choppy fake breakouts (Adversarial spikes after consolidation)
        if scenario.choppy_breakout_prob > 0:
            # Calculate rolling range to find consolidation
            price_range = (df["high"].rolling(5).max() - df["low"].rolling(5).min()) / atr

            for i in range(5, len(df) - 2):
                # Only trigger if in relative consolidation (range < 2 ATRs)
                if price_range.iloc[i] < 2.0 and rng.random() < scenario.choppy_breakout_prob:
                    # Inject a fake breakout relative to ATR
                    spike_size = atr.iloc[i] * 3.0
                    direction = rng.choice([1, -1])

                    idx = df.index[i]
                    next_idx = df.index[i + 1]

                    if direction == 1:
                        # Spike up, trap longs
                        df.at[idx, "high"] = np.float32(
                            max(df.at[idx, "high"], df.at[idx, "open"] + spike_size)
                        )
                        df.at[idx, "close"] = np.float32(df.at[idx, "open"] + (spike_size * 0.2))
                        # Violent reversal
                        df.at[next_idx, "open"] = np.float32(df.at[idx, "close"])
                        df.at[next_idx, "close"] = np.float32(
                            df.at[idx, "open"] - (spike_size * 0.4)
                        )
                        df.at[next_idx, "low"] = np.float32(
                            min(df.at[next_idx, "low"], df.at[next_idx, "close"] - 0.5)
                        )
                    else:
                        # Spike down, trap shorts
                        df.at[idx, "low"] = np.float32(
                            min(df.at[idx, "low"], df.at[idx, "open"] - spike_size)
                        )
                        df.at[idx, "close"] = np.float32(df.at[idx, "open"] - (spike_size * 0.2))
                        # Violent reversal
                        df.at[next_idx, "open"] = np.float32(df.at[idx, "close"])
                        df.at[next_idx, "close"] = np.float32(
                            df.at[idx, "open"] + (spike_size * 0.4)
                        )
                        df.at[next_idx, "high"] = np.float32(
                            max(df.at[next_idx, "high"], df.at[next_idx, "close"] + 0.5)
                        )

                    # Ensure continuity for the bar after reversal
                    if i + 2 < len(df):
                        df.at[df.index[i + 2], "open"] = df.at[next_idx, "close"]

        # 4. Regime transitions (Sudden volatility expansion or trend reversals)
        if scenario.regime_flip_prob > 0:
            i = 10
            while i < len(df) - 15:
                if rng.random() < scenario.regime_flip_prob:
                    # Detect current trend
                    recent_return = (df["close"].iloc[i] - df["close"].iloc[i - 10]) / df[
                        "close"
                    ].iloc[i - 10]

                    window = min(15, len(df) - i)
                    # Force a reversal if a trend exists, otherwise expand volatility
                    if abs(recent_return) > 0.001:
                        direction = -1 if recent_return > 0 else 1
                        reversal_magnitude = atr.iloc[i] * 5.0 * direction

                        base_price = df["close"].iloc[i]
                        for j in range(window):
                            idx = df.index[i + j]
                            if j > 0:
                                df.at[idx, "open"] = np.float32(df.at[df.index[i + j - 1], "close"])
                            # Linear reversal
                            df.at[idx, "close"] = np.float32(
                                base_price + (reversal_magnitude * (j + 1) / window)
                            )
                            df.at[idx, "high"] = np.float32(
                                max(df.at[idx, "open"], df.at[idx, "close"]) + atr.iloc[i + j]
                            )
                            df.at[idx, "low"] = np.float32(
                                min(df.at[idx, "open"], df.at[idx, "close"]) - atr.iloc[i + j]
                            )
                    else:
                        # Volatility expansion (News Shock style)
                        for j in range(window):
                            idx = df.index[i + j]
                            if j > 0:
                                df.at[idx, "open"] = np.float32(df.at[df.index[i + j - 1], "close"])
                            noise = rng.normal(0, atr.iloc[i + j] * 2.0)
                            df.at[idx, "close"] = np.float32(df.at[idx, "close"] + noise)
                            df.at[idx, "high"] = np.float32(
                                max(df.at[idx, "open"], df.at[idx, "close"]) + atr.iloc[i + j] * 2
                            )
                            df.at[idx, "low"] = np.float32(
                                min(df.at[idx, "open"], df.at[idx, "close"]) - atr.iloc[i + j] * 2
                            )

                    if i + window < len(df):
                        df.at[df.index[i + window], "open"] = np.float32(
                            df.at[df.index[i + window - 1], "close"]
                        )
                    i += window
                else:
                    i += 1

        # 5. Flash Crash (Sudden deep drop and recovery)
        if scenario.flash_crash_prob > 0:
            i = 10
            while i < len(df) - 10:
                if rng.random() < scenario.flash_crash_prob:
                    # Deep drop: 5-10 ATRs
                    drop_size = atr.iloc[i] * rng.uniform(5.0, 10.0)
                    df.at[df.index[i], "low"] = np.float32(df.at[df.index[i], "low"] - drop_size)
                    df.at[df.index[i], "close"] = np.float32(
                        df.at[df.index[i], "close"] - drop_size * 0.8
                    )

                    if i + 1 < len(df):
                        df.at[df.index[i + 1], "open"] = np.float32(df.at[df.index[i], "close"])

                    # Partial recovery in next 3 candles
                    for j in range(1, 4):
                        curr_idx = df.index[i + j]
                        recovery = drop_size * rng.uniform(0.1, 0.2)
                        df.at[curr_idx, "close"] = np.float32(df.at[curr_idx, "close"] + recovery)
                        df.at[curr_idx, "high"] = np.float32(
                            max(df.at[curr_idx, "high"], df.at[curr_idx, "close"] + 1.0)
                        )
                        if i + j + 1 < len(df):
                            df.at[df.index[i + j + 1], "open"] = np.float32(
                                df.at[curr_idx, "close"]
                            )

                    i += 5  # Skip ahead
                else:
                    i += 1

        # Capture "Real" Market state before applying observer perturbations
        df["_real_close"] = df["close"]
        df["_real_spread"] = df["spread"] if "spread" in df.columns else 0.25

        # 6. Stale data (Observer sees old data, but execution is real)
        if scenario.stale_data_prob > 0:
            ohlc_cols = ["open", "high", "low", "close"]
            for i in range(1, len(df)):
                if rng.random() < scenario.stale_data_prob:
                    # Trader sees previous bar's data
                    df.iloc[i, df.columns.get_indexer(ohlc_cols)] = df.iloc[
                        i - 1, df.columns.get_indexer(ohlc_cols)
                    ]

        return df

    def _backtest_with_stress(
        self, df: pd.DataFrame, scenario: StressScenario
    ) -> StressTestMetrics:
        """Specialized backtest loop that accounts for slippage and delays."""
        # Execution prices (Real market)
        close = df["_real_close"].values if "_real_close" in df.columns else df["close"].values
        n = len(df)
        initial_balance = self.initial_balance
        equity = np.ones(n) * initial_balance
        cash = initial_balance
        daily_returns = np.zeros(n)
        trade_pnls = []

        # Institutional parameters
        contract_multiplier = self.contract_multiplier
        lot_size = scenario.lot_size

        # Predict signals on potentially perturbed data
        raw_signals = self.strategy.predict(df)

        position = 0
        entry_price = 0.0

        # Base spread for XAUUSD if not present
        base_spread = 0.25
        if "_real_spread" in df.columns:
            base_spreads = df["_real_spread"].values * scenario.spread_multiplier
        else:
            base_spreads = (
                df["spread"].values if "spread" in df.columns else np.ones(n) * base_spread
            ) * scenario.spread_multiplier

        rng = np.random.default_rng(scenario.seed)
        latency_hits = 0
        max_slippage = 0.0
        total_commission = 0.0
        total_slippage = 0.0

        for i in range(1, n):
            # 1. Determine signal with delay and jitter
            delay = scenario.execution_delay_steps
            if scenario.execution_delay_jitter > 0:
                delay += rng.integers(
                    -scenario.execution_delay_jitter, scenario.execution_delay_jitter + 1
                )
            delay = max(0, delay)

            # Signal from 'delay' steps ago
            sig_idx = max(0, i - 1 - delay)
            current_sig = raw_signals[sig_idx]

            current_price = close[i]

            # 2. Apply service failure
            if scenario.service_failure_prob > 0 and rng.random() < scenario.service_failure_prob:
                current_sig = 0  # Signal blocked by infrastructure failure
                latency_hits += 1

            # 3. Calculate dynamic spread and slippage
            current_spread = base_spreads[i]
            if scenario.spread_spike_prob > 0 and rng.random() < scenario.spread_spike_prob:
                current_spread += scenario.spread_spike_magnitude

            current_slippage_bps = scenario.slippage_bps
            if scenario.slippage_spike_prob > 0 and rng.random() < scenario.slippage_spike_prob:
                current_slippage_bps += scenario.slippage_spike_magnitude_bps

            max_slippage = max(max_slippage, current_slippage_bps)
            slippage = current_price * (current_slippage_bps / 10000.0)

            # 4. Execution Logic
            # Exit existing position if signal changed or is zero
            if position == 1 and current_sig != 1:
                exit_price = current_price - (current_spread / 2) - slippage
                raw_pnl = (exit_price - entry_price) * lot_size * contract_multiplier
                commission = lot_size * scenario.commission_per_lot
                total_commission += commission
                total_slippage += slippage * lot_size * contract_multiplier

                pnl = raw_pnl - commission
                trade_pnls.append(pnl)
                cash += pnl
                position = 0
            elif position == -1 and current_sig != -1:
                exit_price = current_price + (current_spread / 2) + slippage
                raw_pnl = (entry_price - exit_price) * lot_size * contract_multiplier
                commission = lot_size * scenario.commission_per_lot
                total_commission += commission
                total_slippage += slippage * lot_size * contract_multiplier

                pnl = raw_pnl - commission
                trade_pnls.append(pnl)
                cash += pnl
                position = 0

            # Open new position if signal is non-zero
            if position == 0 and current_sig != 0:
                total_slippage += slippage * lot_size * contract_multiplier

                if current_sig == 1:
                    position = 1
                    entry_price = current_price + (current_spread / 2) + slippage
                elif current_sig == -1:
                    position = -1
                    entry_price = current_price - (current_spread / 2) - slippage

            # Update Equity (Mark-to-Market including potential exit cost and commission)
            exit_cost = (current_spread / 2) + slippage
            commission = lot_size * scenario.commission_per_lot
            if position == 1:
                unrealized = (
                    ((current_price - exit_cost) - entry_price) * lot_size * contract_multiplier
                ) - commission
                equity[i] = cash + unrealized
            elif position == -1:
                unrealized = (
                    (entry_price - (current_price + exit_cost)) * lot_size * contract_multiplier
                ) - commission
                equity[i] = cash + unrealized
            else:
                equity[i] = cash

            daily_returns[i] = (equity[i] - equity[i - 1]) / (equity[i - 1] + 1e-9)

        # Final Metrics
        net_pnl = equity[-1] - initial_balance
        total_return = net_pnl / initial_balance
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / (peak + 1e-9)
        max_drawdown = float(np.max(drawdown))

        sharpe = 0.0
        sortino = 0.0
        if np.std(daily_returns) > 0:
            sharpe = float(np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252))

            downside_returns = daily_returns[daily_returns < 0]
            downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
            if downside_std > 0:
                sortino = float(np.mean(daily_returns) / downside_std * np.sqrt(252))

        win_rate = len([p for p in trade_pnls if p > 0]) / (len(trade_pnls) + 1e-9)

        # Profit Factor
        gross_profit = sum([p for p in trade_pnls if p > 0])
        gross_loss = abs(sum([p for p in trade_pnls if p < 0]))
        profit_factor = (
            gross_profit / gross_loss if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0)
        )

        # Recovery Factor
        recovery_factor = (
            net_pnl / (max_drawdown * initial_balance)
            if max_drawdown > 0
            else (5.0 if net_pnl > 0 else 0.0)
        )

        return StressTestMetrics(
            total_return=total_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            num_trades=len(trade_pnls),
            recovery_factor=recovery_factor,
            profit_factor=profit_factor,
            execution_quality_score=1.0 - (latency_hits / n),
            latency_impact=latency_hits / n,
            max_slippage_experienced=max_slippage,
            total_commission_cost=total_commission,
            total_slippage_cost=total_slippage,
            sortino_ratio=sortino,
        )
