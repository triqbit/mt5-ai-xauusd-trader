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
    """Configuration for a specific stress scenario."""

    name: str
    description: str
    severity: StressSeverity = StressSeverity.MEDIUM

    # Execution stress
    spread_multiplier: float = 1.0  # 1.0 = normal
    slippage_bps: float = 0.0  # Basis points
    slippage_spike_prob: float = 0.0  # Probability of an extreme slippage event
    slippage_spike_magnitude_bps: float = 0.0  # Magnitude of the spike in bps
    execution_delay_steps: int = 0  # Number of steps to delay execution

    # Data stress
    missing_tick_prob: float = 0.0  # Probability of missing a price update
    price_noise_sigma: float = 0.0  # Gaussian noise added to OHLC

    # Market structure stress
    choppy_breakout_prob: float = 0.0  # Probability of fake breakouts
    regime_flip_prob: float = 0.0  # Probability of sudden regime transitions

    # External service stress
    service_failure_prob: float = 0.0  # Probability of 'external service' being down

    # Tail risk events
    flash_crash_prob: float = 0.0  # Probability of a sudden deep price dislocation


class StressTestMetrics(BaseModel):
    """Metrics captured during a stress test run."""

    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    num_trades: int
    execution_quality_score: float  # 0.0 to 1.0
    latency_impact: float  # Percentage impact of delays
    max_slippage_experienced: float = 0.0  # Max bps of slippage seen


class ResilienceReport(BaseModel):
    """Comprehensive report for a strategy's resilience under stress."""

    strategy_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    baseline_metrics: StressTestMetrics
    scenario_results: dict[str, StressTestMetrics]
    resilience_score: float  # Composite score 0-100
    fragility_indicators: list[str]
    failure_points: list[str]
    degradation_summary: str

    def to_report_section(self) -> Any:
        """Convert to StressTestSection for ResearchReporter."""
        from src.research.reporting import StressedMetric, StressTestSection

        def _map_metric(name: str, m: StressTestMetrics) -> StressedMetric:
            return StressedMetric(
                name=name,
                total_return=f"{m.total_return:.2%}",
                max_drawdown=f"{m.max_drawdown:.2%}",
                sharpe=f"{m.sharpe_ratio:.2f}",
                outcome="FAIL" if m.total_return < 0 else "PASS",
            )

        return StressTestSection(
            resilience_score=self.resilience_score,
            baseline=_map_metric("Baseline", self.baseline_metrics),
            scenarios=[_map_metric(name, res) for name, res in self.scenario_results.items()],
            fragility_indicators=self.fragility_indicators,
            failure_points=self.failure_points,
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
    ):
        self.strategy = strategy
        self.data = data.copy()
        self.initial_balance = initial_balance
        self.results: dict[str, StressTestMetrics] = {}

    @staticmethod
    def create_execution_hell_scenario() -> StressScenario:
        """Create a scenario with high slippage, wide spreads, and delays."""
        return StressScenario(
            name="Execution Hell",
            description="Extreme execution friction: wide spreads, slippage spikes, and delays.",
            severity=StressSeverity.CRITICAL,
            spread_multiplier=3.0,
            slippage_bps=5.0,
            slippage_spike_prob=0.1,
            slippage_spike_magnitude_bps=50.0,
            execution_delay_steps=3,
            service_failure_prob=0.05,
        )

    @staticmethod
    def create_liquidity_crisis_scenario() -> StressScenario:
        """Create a scenario with missing data and extreme choppy price action."""
        return StressScenario(
            name="Liquidity Crisis",
            description="Fragmented liquidity: missing ticks, price noise, and choppy breakouts.",
            severity=StressSeverity.HIGH,
            missing_tick_prob=0.2,
            price_noise_sigma=1.0,
            choppy_breakout_prob=0.15,
            spread_multiplier=2.5,
        )

    @staticmethod
    def create_regime_shock_scenario() -> StressScenario:
        """Create a scenario with frequent and violent regime transitions."""
        return StressScenario(
            name="Regime Shock",
            description="Market structural instability: frequent regime flips and trend reversals.",
            severity=StressSeverity.HIGH,
            regime_flip_prob=0.1,
            choppy_breakout_prob=0.05,
        )

    @staticmethod
    def create_flash_crash_scenario() -> StressScenario:
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
        )

    def run_standard_suite(self, baseline_metrics: StressTestMetrics) -> ResilienceReport:
        """Runs the full standard suite of stress tests and returns a report."""
        scenarios = [
            self.create_execution_hell_scenario(),
            self.create_liquidity_crisis_scenario(),
            self.create_regime_shock_scenario(),
            self.create_flash_crash_scenario(),
        ]

        for scenario in scenarios:
            self.run_scenario(scenario)

        return self.generate_report(baseline_metrics)

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
        """Generate a comprehensive resilience report after running scenarios."""
        scenario_results = self.results

        # Calculate resilience score (0-100)
        # Average performance retention across all scenarios
        scores = []
        for metrics in scenario_results.values():
            retention = metrics.total_return / (baseline_metrics.total_return + 1e-9)
            # Clip between 0 and 1.2
            scores.append(np.clip(retention, 0, 1.2))

        resilience_score = float(np.mean(scores) * 100) if scores else 0.0

        # Identify fragility indicators
        fragility = []
        failure_points = []

        for scenario_name, metrics in scenario_results.items():
            if metrics.max_drawdown > baseline_metrics.max_drawdown * 2:
                fragility.append(f"Drawdown explosion in {scenario_name}")
            if metrics.total_return < 0 and baseline_metrics.total_return > 0:
                failure_points.append(f"Strategy becomes unprofitable under {scenario_name}")
            if metrics.sharpe_ratio < baseline_metrics.sharpe_ratio * 0.5:
                fragility.append(f"Sharpe ratio halved under {scenario_name}")
            if metrics.latency_impact > 0.1:
                fragility.append(f"High sensitivity to infrastructure delays in {scenario_name}")
            if metrics.max_slippage_experienced > 100:
                fragility.append(f"Extreme slippage sensitivity in {scenario_name}")

        return ResilienceReport(
            strategy_name=self.strategy.name,
            baseline_metrics=baseline_metrics,
            scenario_results=scenario_results,
            resilience_score=resilience_score,
            fragility_indicators=fragility,
            failure_points=failure_points,
            degradation_summary=self._generate_summary(baseline_metrics, scenario_results),
        )

    def _generate_summary(
        self, baseline: StressTestMetrics, results: dict[str, StressTestMetrics]
    ) -> str:
        summary = (
            f"Strategy '{self.strategy.name}' evaluated against {len(results)} stress scenarios.\n"
        )
        avg_return = np.mean([m.total_return for m in results.values()])
        summary += (
            f"Baseline Return: {baseline.total_return:.2%}, Avg Stressed Return: {avg_return:.2%}\n"
        )

        if avg_return < 0:
            summary += "CRITICAL: Strategy is generally not robust to adverse conditions."
        elif avg_return < baseline.total_return * 0.5:
            summary += "WARNING: Strategy shows significant performance degradation under stress."
        else:
            summary += "OK: Strategy shows reasonable resilience."

        return summary

    def _apply_perturbations(self, df: pd.DataFrame, scenario: StressScenario) -> pd.DataFrame:
        """Apply data-level perturbations using adversarial logic."""
        df = df.copy()
        rng = np.random.default_rng(42)

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

        # 3. Choppy fake breakouts (Adversarial spikes)
        if scenario.choppy_breakout_prob > 0:
            for i in range(2, len(df) - 2):
                if rng.random() < scenario.choppy_breakout_prob:
                    # Inject a fake breakout relative to ATR
                    spike_size = atr.iloc[i] * 3.0
                    direction = rng.choice([1, -1])

                    idx = df.index[i]
                    next_idx = df.index[i + 1]

                    if direction == 1:
                        df.at[idx, "high"] += spike_size
                        df.at[idx, "close"] = df.at[idx, "open"] + (spike_size * 0.1)
                        # Immediate reversal in next candle
                        df.at[next_idx, "close"] = df.at[idx, "open"] - (spike_size * 0.5)
                        df.at[next_idx, "low"] = df.at[next_idx, "close"] - (spike_size * 0.1)
                    else:
                        df.at[idx, "low"] -= spike_size
                        df.at[idx, "close"] = df.at[idx, "open"] - (spike_size * 0.1)
                        # Immediate reversal
                        df.at[next_idx, "close"] = df.at[idx, "open"] + (spike_size * 0.5)
                        df.at[next_idx, "high"] = df.at[next_idx, "close"] + (spike_size * 0.1)

        # 4. Regime transitions (Simulate sudden volatility expansion or trend exhaustion)
        if scenario.regime_flip_prob > 0:
            i = 0
            while i < len(df):
                if rng.random() < scenario.regime_flip_prob:
                    window = min(30, len(df) - i)
                    if window > 5:
                        # Trend exhaustion: slow down then flip
                        returns = df["close"].iloc[i : i + window].pct_change().fillna(0)
                        # Flip and amplify volatility
                        inverted_returns = -returns * 2.5
                        base_price = df.at[df.index[i], "close"]
                        new_prices = base_price * np.exp(np.cumsum(inverted_returns))
                        df.loc[df.index[i : i + window], "close"] = new_prices.values

                        # Re-calculate high/low to be consistent and 'messy'
                        for idx in range(i, i + window):
                            local_vol = atr.iloc[idx] * 0.5
                            df.at[df.index[idx], "high"] = (
                                max(df.at[df.index[idx], "open"], df.at[df.index[idx], "close"])
                                + local_vol
                            )
                            df.at[df.index[idx], "low"] = (
                                min(df.at[df.index[idx], "open"], df.at[df.index[idx], "close"])
                                - local_vol
                            )
                        i += window  # Skip the modified window
                    else:
                        i += 1
                else:
                    i += 1

        # 5. Flash Crash (Sudden deep drop and recovery)
        if scenario.flash_crash_prob > 0:
            i = 10
            while i < len(df) - 10:
                if rng.random() < scenario.flash_crash_prob:
                    # Deep drop: 5-10 ATRs
                    drop_size = atr.iloc[i] * rng.uniform(5.0, 10.0)
                    df.at[df.index[i], "low"] -= drop_size
                    df.at[df.index[i], "close"] -= drop_size * 0.8

                    # Partial recovery in next 3 candles
                    for j in range(1, 4):
                        recovery = drop_size * rng.uniform(0.1, 0.2)
                        df.at[df.index[i + j], "close"] += recovery
                        df.at[df.index[i + j], "high"] = max(
                            df.at[df.index[i + j], "high"], df.at[df.index[i + j], "close"] + 1.0
                        )
                    i += 5  # Skip ahead
                else:
                    i += 1

        return df

    def _backtest_with_stress(
        self, df: pd.DataFrame, scenario: StressScenario
    ) -> StressTestMetrics:
        """Specialized backtest loop that accounts for slippage and delays."""
        close = df["close"].values
        n = len(df)
        initial_balance = self.initial_balance
        equity = np.ones(n) * initial_balance
        cash = initial_balance
        daily_returns = np.zeros(n)
        trade_pnls = []

        # Predict signals on potentially perturbed data
        raw_signals = self.strategy.predict(df)

        # Apply execution delay
        if scenario.execution_delay_steps > 0:
            signals = np.zeros_like(raw_signals)
            signals[scenario.execution_delay_steps :] = raw_signals[
                : -scenario.execution_delay_steps
            ]
        else:
            signals = raw_signals

        position = 0
        entry_price = 0.0

        # Base spread for XAUUSD if not present
        base_spread = 0.25
        spreads = (
            df["spread"].values if "spread" in df.columns else np.ones(n) * base_spread
        ) * scenario.spread_multiplier

        rng = np.random.default_rng(42)
        latency_hits = 0
        max_slippage = 0.0

        for i in range(1, n):
            current_sig = signals[i - 1]
            current_price = close[i]

            # Service failure
            if scenario.service_failure_prob > 0 and rng.random() < scenario.service_failure_prob:
                current_sig = 0  # Blocked
                latency_hits += 1

            # Calculate slippage
            current_slippage_bps = scenario.slippage_bps
            if scenario.slippage_spike_prob > 0 and rng.random() < scenario.slippage_spike_prob:
                current_slippage_bps += scenario.slippage_spike_magnitude_bps

            max_slippage = max(max_slippage, current_slippage_bps)
            slippage = current_price * (current_slippage_bps / 10000.0)

            # Execution Logic
            if current_sig == 1 and position == 0:  # Buy
                position = 1
                entry_price = current_price + (spreads[i] / 2) + slippage
            elif current_sig == -1 and position == 1:  # Close Long
                exit_price = current_price - (spreads[i] / 2) - slippage
                pnl = exit_price - entry_price
                trade_pnls.append(pnl)
                cash += pnl
                position = 0
            elif current_sig == -1 and position == 0:  # Short
                position = -1
                entry_price = current_price - (spreads[i] / 2) - slippage
            elif current_sig == 1 and position == -1:  # Close Short
                exit_price = current_price + (spreads[i] / 2) + slippage
                pnl = entry_price - exit_price
                trade_pnls.append(pnl)
                cash += pnl
                position = 0

            # Update Equity (Mark-to-Market including potential exit cost)
            exit_cost = (spreads[i] / 2) + slippage
            if position == 1:
                unrealized = (current_price - exit_cost) - entry_price
                equity[i] = cash + unrealized
            elif position == -1:
                unrealized = entry_price - (current_price + exit_cost)
                equity[i] = cash + unrealized
            else:
                equity[i] = cash

            daily_returns[i] = (equity[i] - equity[i - 1]) / (equity[i - 1] + 1e-9)

        # Final Metrics
        total_return = (equity[-1] - initial_balance) / initial_balance
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / (peak + 1e-9)
        max_drawdown = float(np.max(drawdown))

        sharpe = 0.0
        if np.std(daily_returns) > 0:
            sharpe = float(np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252))

        win_rate = len([p for p in trade_pnls if p > 0]) / (len(trade_pnls) + 1e-9)

        return StressTestMetrics(
            total_return=total_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            num_trades=len(trade_pnls),
            execution_quality_score=1.0 - (latency_hits / n),
            latency_impact=latency_hits / n,
            max_slippage_experienced=max_slippage,
        )
