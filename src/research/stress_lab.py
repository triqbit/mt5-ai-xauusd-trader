"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/stress_lab.py
Structured strategy stress testing and adversarial resilience evaluation.
Replays adverse market conditions to identify strategy fragility.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import List, Protocol

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StressType(str, Enum):
    SPREAD_WIDENING = "spread_widening"
    SLIPPAGE_SPIKES = "slippage_spikes"
    MISSING_TICKS = "missing_ticks"
    DELAYED_FILLS = "delayed_fills"
    CHOPPY_FAKE_BREAKOUTS = "choppy_fake_breakouts"
    REGIME_TRANSITIONS = "regime_transitions"
    DEGRADED_SERVICE = "degraded_service"


class FailurePoint(BaseModel):
    """Details about a specific failure during stress testing."""
    timestamp: datetime
    stress_type: StressType
    condition: str
    impact: str
    severity: float  # 0.0 to 1.0


class ResilienceMetrics(BaseModel):
    """Quantifiable resilience indicators."""
    survival_rate: float = 0.0  # Percentage of episodes completed
    pnl_degradation: float = 0.0  # Stress PnL vs Baseline PnL
    max_drawdown_increase: float = 0.0
    recovery_factor_delta: float = 0.0
    stability_score: float = 0.0  # 0 to 100


class StressReport(BaseModel):
    """Final output of a stress testing session."""
    strategy_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scenarios_run: List[StressType]
    metrics: ResilienceMetrics
    failure_points: List[FailurePoint]
    fragility_indicators: List[str]
    summary: str


class Strategy(Protocol):
    """Protocol for strategies/models to be tested."""
    def predict(self, obs: np.ndarray) -> int:
        """Return direction: 1 (Buy), -1 (Sell), 0 (Hold)."""
        ...


@dataclass
class MarketState:
    """Internal state for the stress simulation."""
    price: float
    spread: float
    time: datetime
    is_service_available: bool = True


class StressLab:
    """
    Adversarial testing lab for trading strategies.
    Wraps market data with stressors to evaluate strategy robustness.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        initial_balance: float = 10000.0,
        base_spread: float = 0.00015,  # 1.5 pips for XAUUSD typical
    ) -> None:
        """
        Initialize the Stress Lab.

        Args:
            data: Historical OHLCV data.
            initial_balance: Starting account balance.
            base_spread: Normal market spread.
        """
        self.data = data.copy()
        self.initial_balance = initial_balance
        self.base_spread = base_spread
        self.report_entries: List[FailurePoint] = []

    def run_benchmark(self, strategy: Strategy) -> float:
        """Run a clean backtest without stressors for baseline comparison."""
        return self._simulate(strategy, stressors=[])

    def run_stress_test(
        self,
        strategy: Strategy,
        stressors: List[StressType],
        intensity: float = 1.0,
    ) -> StressReport:
        """
        Execute stress test with specified adverse conditions.

        Args:
            strategy: The strategy/model to test.
            stressors: List of StressType to apply.
            intensity: Severity of stressors (1.0 = standard).

        Returns:
            StressReport with resilience analysis.
        """
        logger.info("Starting stress test | intensity=%.2f | stressors=%s", intensity, stressors)

        baseline_pnl = self.run_benchmark(strategy)
        stress_pnl = self._simulate(strategy, stressors, intensity)

        # Calculate metrics
        pnl_degradation = (baseline_pnl - stress_pnl) / (abs(baseline_pnl) + 1e-9)

        fragility = []
        if pnl_degradation > 0.5:
            fragility.append("High sensitivity to execution quality")
        if stress_pnl < 0 and baseline_pnl > 0:
            fragility.append("Strategy breaks under adverse conditions")

        metrics = ResilienceMetrics(
            survival_rate=1.0 if stress_pnl > -self.initial_balance else 0.0,
            pnl_degradation=pnl_degradation,
            stability_score=max(0, 100 * (1 - pnl_degradation))
        )

        return StressReport(
            strategy_name=type(strategy).__name__,
            scenarios_run=stressors,
            metrics=metrics,
            failure_points=self.report_entries,
            fragility_indicators=fragility,
            summary=f"Stress test completed. PnL Degradation: {pnl_degradation:.2%}"
        )

    def _simulate(
        self,
        strategy: Strategy,
        stressors: List[StressType],
        intensity: float = 1.0
    ) -> float:
        """Internal simulation loop with injectable stressors."""
        balance = self.initial_balance
        position = 0.0  # 1 for long, -1 for short
        entry_price = 0.0

        self.report_entries = []

        # Data-level stressors (Missing Ticks, Regime Transitions, Fake Breakouts)
        sim_data = self.data.copy()

        if StressType.MISSING_TICKS in stressors:
            drop_mask = np.random.rand(len(sim_data)) < (0.05 * intensity)
            sim_data = sim_data[~drop_mask].reset_index(drop=True)
            self.report_entries.append(FailurePoint(
                timestamp=datetime.now(timezone.utc),
                stress_type=StressType.MISSING_TICKS,
                condition=f"Dropped {sum(drop_mask)} bars",
                impact="Data continuity gaps",
                severity=intensity
            ))

        if StressType.REGIME_TRANSITIONS in stressors:
            # Inject sudden volatility spikes
            spike_idx = random.randint(len(sim_data)//4, len(sim_data)//2)
            sim_data.iloc[spike_idx:, 1:4] *= (1 + 0.02 * intensity) # Increase HLC
            self.report_entries.append(FailurePoint(
                timestamp=datetime.now(timezone.utc),
                stress_type=StressType.REGIME_TRANSITIONS,
                condition="Artificial volatility injection",
                impact="Sudden regime shift",
                severity=intensity
            ))

        if StressType.CHOPPY_FAKE_BREAKOUTS in stressors:
            # Create fake breakouts: price goes up then crashes
            for _ in range(int(3 * intensity)):
                idx = random.randint(10, len(sim_data)-20)
                sim_data.iloc[idx:idx+5, 3] *= 1.01 # Up
                sim_data.iloc[idx+5:idx+10, 3] *= 0.98 # Down
            self.report_entries.append(FailurePoint(
                timestamp=datetime.now(timezone.utc),
                stress_type=StressType.CHOPPY_FAKE_BREAKOUTS,
                condition="Injected choppy patterns",
                impact="False signal generation",
                severity=intensity
            ))

        # Execution loop
        for i in range(len(sim_data)):
            row = sim_data.iloc[i]
            current_close = row['close']

            # Dynamic stressors
            current_spread = self.base_spread
            if (
                StressType.SPREAD_WIDENING in stressors
                and random.random() < 0.1 * intensity
            ):
                # Randomly widen spread up to 10x
                current_spread *= 1 + random.uniform(2, 10) * intensity

            service_available = True
            if (
                StressType.DEGRADED_SERVICE in stressors
                and random.random() < 0.02 * intensity
            ):
                service_available = False

            # Build observation (mocking the expected format)
            # In a real scenario, this would use a proper feature engineer
            obs = row[['open', 'high', 'low', 'close', 'tick_volume']].values

            action = 0
            if service_available:
                action = strategy.predict(obs)
            elif i % 10 == 0:  # Log only occasionally to avoid bloat
                self.report_entries.append(FailurePoint(
                    timestamp=datetime.now(timezone.utc),
                    stress_type=StressType.DEGRADED_SERVICE,  # Using service as proxy for system collapse
                    condition="API Timeout / Connection Lost",
                    impact="Missed signal or unable to close",
                    severity=intensity,
                ))

            # Slippage logic
            slippage = 0.0
            if StressType.SLIPPAGE_SPIKES in stressors and random.random() < 0.05 * intensity:
                slippage = current_close * 0.0005 * intensity

            # Order Execution
            if action == 1 and position == 0: # Buy
                fill_price = current_close + (current_spread / 2) + slippage
                # Delayed fills
                if StressType.DELAYED_FILLS in stressors and i + 1 < len(sim_data):
                    fill_price = sim_data.iloc[i+1]['open'] + (current_spread / 2) + slippage

                position = 1
                entry_price = fill_price

            elif action == -1 and position == 0: # Sell
                fill_price = current_close - (current_spread / 2) - slippage
                if StressType.DELAYED_FILLS in stressors and i + 1 < len(sim_data):
                    fill_price = sim_data.iloc[i+1]['open'] - (current_spread / 2) - slippage

                position = -1
                entry_price = fill_price

            elif action == 0 and position != 0: # Close
                # Simplified closing logic for stress testing
                exit_price = current_close - (position * current_spread / 2) - (position * slippage)
                pnl = (exit_price - entry_price) * position
                balance += pnl
                position = 0
                entry_price = 0.0

            if balance <= 0:
                self.report_entries.append(FailurePoint(
                    timestamp=datetime.now(timezone.utc),
                    stress_type=StressType.DEGRADED_SERVICE, # Using service as proxy for system collapse
                    condition="Account Liquidation",
                    impact="Terminal Failure",
                    severity=1.0
                ) )
                break

        # Close any open position at the end
        if position != 0:
            exit_price = sim_data.iloc[-1]['close'] - (position * current_spread / 2)
            pnl = (exit_price - entry_price) * position
            balance += pnl

        return balance - self.initial_balance


__all__ = [
    "FailurePoint",
    "ResilienceMetrics",
    "StressLab",
    "StressReport",
    "StressType",
]
