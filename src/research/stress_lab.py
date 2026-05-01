"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/stress_lab.py
Adversarial resilience testing framework for strategy stress testing.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List

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
    execution_delay_steps: int = 0  # Number of steps to delay execution

    # Data stress
    missing_tick_prob: float = 0.0  # Probability of missing a price update
    price_noise_sigma: float = 0.0  # Gaussian noise added to OHLC

    # Market structure stress
    choppy_breakout_prob: float = 0.0  # Probability of fake breakouts
    regime_flip_prob: float = 0.0  # Probability of sudden regime transitions

    # External service stress
    service_failure_prob: float = 0.0  # Probability of 'external service' being down


class StressTestMetrics(BaseModel):
    """Metrics captured during a stress test run."""

    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    num_trades: int
    execution_quality_score: float  # 0.0 to 1.0
    latency_impact: float  # Percentage impact of delays


class ResilienceReport(BaseModel):
    """Comprehensive report for a strategy's resilience under stress."""

    strategy_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    baseline_metrics: StressTestMetrics
    scenario_results: Dict[str, StressTestMetrics]
    resilience_score: float  # Composite score 0-100
    fragility_indicators: List[str]
    failure_points: List[str]
    degradation_summary: str


class StressLab:
    """
    Stress testing laboratory for XAUUSD trading strategies.
    Replays adverse conditions to evaluate strategy robustness.
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
        self.results: Dict[str, StressTestMetrics] = {}

    def run_scenario(self, scenario: StressScenario) -> StressTestMetrics:
        """Execute a specific stress scenario."""
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

        return ResilienceReport(
            strategy_name=self.strategy.name,
            baseline_metrics=baseline_metrics,
            scenario_results=scenario_results,
            resilience_score=resilience_score,
            fragility_indicators=fragility,
            failure_points=failure_points,
            degradation_summary=self._generate_summary(baseline_metrics, scenario_results),
        )

    def _generate_summary(self, baseline: StressTestMetrics, results: Dict[str, StressTestMetrics]) -> str:
        summary = f"Strategy '{self.strategy.name}' evaluated against {len(results)} stress scenarios.\n"
        avg_return = np.mean([m.total_return for m in results.values()])
        summary += f"Baseline Return: {baseline.total_return:.2%}, Avg Stressed Return: {avg_return:.2%}\n"

        if avg_return < 0:
            summary += "CRITICAL: Strategy is generally not robust to adverse conditions."
        elif avg_return < baseline.total_return * 0.5:
            summary += "WARNING: Strategy shows significant performance degradation under stress."
        else:
            summary += "OK: Strategy shows reasonable resilience."

        return summary

    def _apply_perturbations(self, df: pd.DataFrame, scenario: StressScenario) -> pd.DataFrame:
        """Apply data-level perturbations."""
        df = df.copy()
        rng = np.random.default_rng(42)

        # 1. Missing ticks
        if scenario.missing_tick_prob > 0:
            mask = rng.random(len(df)) > scenario.missing_tick_prob
            df = df[mask].reset_index(drop=True)

        # 2. Price noise
        if scenario.price_noise_sigma > 0:
            noise = rng.normal(0, scenario.price_noise_sigma, (len(df), 4))
            df[["open", "high", "low", "close"]] += noise
            # Ensure price consistency
            df["high"] = df[["open", "close", "high"]].max(axis=1)
            df["low"] = df[["open", "close", "low"]].min(axis=1)

        # 3. Choppy fake breakouts
        if scenario.choppy_breakout_prob > 0:
            for i in range(2, len(df) - 2):
                if rng.random() < scenario.choppy_breakout_prob:
                    # Inject a fake breakout upwards
                    df.at[i, "high"] += 5.0  # Spike
                    df.at[i, "close"] = df.at[i, "open"] + 0.5
                    # Immediate reversal
                    df.at[i+1, "close"] = df.at[i, "open"] - 2.0
                    df.at[i+1, "low"] = df.at[i+1, "close"] - 0.5

        # 4. Regime transitions (Simulate sudden volatility spike/trend flip)
        if scenario.regime_flip_prob > 0:
            for i in range(len(df)):
                if rng.random() < scenario.regime_flip_prob:
                    # Flip future returns for a window
                    window = min(20, len(df) - i)
                    if window > 1:
                        # Simple trend flip by inverting close price changes
                        returns = df["close"].iloc[i:i+window].pct_change().fillna(0)
                        inverted_returns = -returns * 2.0 # Reversal + Volatility
                        base_price = df.at[i, "close"]
                        new_prices = base_price * np.exp(np.cumsum(inverted_returns))
                        df.loc[df.index[i:i+window], "close"] = new_prices.values
                        # Update high/low for the window to maintain consistency
                        window_slice = df.iloc[i:i+window]
                        df.loc[df.index[i:i+window], "high"] = window_slice[["open", "close", "high"]].max(axis=1)
                        df.loc[df.index[i:i+window], "low"] = window_slice[["open", "close", "low"]].min(axis=1)

        return df

    def _backtest_with_stress(
        self, df: pd.DataFrame, scenario: StressScenario
    ) -> StressTestMetrics:
        """Specialized backtest loop that accounts for slippage and delays."""
        close = df["close"].values
        n = len(df)
        initial_balance = self.initial_balance
        equity = np.ones(n) * initial_balance
        daily_returns = np.zeros(n)
        trade_pnls = []

        # Predict signals on potentially perturbed data
        raw_signals = self.strategy.predict(df)

        # Apply execution delay
        if scenario.execution_delay_steps > 0:
            signals = np.zeros_like(raw_signals)
            signals[scenario.execution_delay_steps:] = raw_signals[:-scenario.execution_delay_steps]
        else:
            signals = raw_signals

        position = 0
        entry_price = 0.0

        # Base spread for XAUUSD if not present
        base_spread = 0.25
        spreads = (df["spread"].values if "spread" in df.columns else np.ones(n) * base_spread) * scenario.spread_multiplier

        rng = np.random.default_rng(42)
        latency_hits = 0

        for i in range(1, n):
            current_sig = signals[i - 1]
            current_price = close[i]
            prev_price = close[i - 1]
            current_equity = equity[i - 1]

            # Service failure
            if scenario.service_failure_prob > 0 and rng.random() < scenario.service_failure_prob:
                current_sig = 0 # Blocked
                latency_hits += 1

            slippage = current_price * (scenario.slippage_bps / 10000.0)

            # Execution Logic
            if current_sig == 1 and position == 0:  # Buy
                position = 1
                entry_price = current_price + (spreads[i] / 2) + slippage
            elif current_sig == -1 and position == 1:  # Close Long
                exit_price = current_price - (spreads[i] / 2) - slippage
                trade_pnls.append(exit_price - entry_price)
                position = 0
            elif current_sig == -1 and position == 0:  # Short
                position = -1
                entry_price = current_price - (spreads[i] / 2) - slippage
            elif current_sig == 1 and position == -1:  # Close Short
                exit_price = current_price + (spreads[i] / 2) + slippage
                trade_pnls.append(entry_price - exit_price)
                position = 0

            # Update Equity
            if position == 1:
                change = (current_price - prev_price) / prev_price
                equity[i] = current_equity * (1 + change)
            elif position == -1:
                change = (prev_price - current_price) / prev_price
                equity[i] = current_equity * (1 + change)
            else:
                equity[i] = current_equity

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
        )
