"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rare_event_simulator.py
Generates rare but plausible market situations for black-swan resilience testing.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RareEventType(str, Enum):
    """Types of rare market events to simulate."""

    FLASH_CRASH = "flash_crash"
    LIQUIDITY_VACUUM = "liquidity_vacuum"
    GOLD_GAP = "gold_gap"
    VIOLENT_REVERSAL = "violent_reversal"
    DISLOCATION = "dislocation"
    VOL_CLUSTER = "vol_cluster"


class RareEventConfig(BaseModel):
    """Configuration for rare event simulation."""

    event_type: RareEventType
    n_steps: int = Field(500, ge=100)
    start_price: float = Field(2300.0, gt=0)
    base_volatility: float = Field(0.0005, gt=0)
    event_magnitude: float = Field(1.0, gt=0)  # Multiplier for the severity
    seed: Optional[int] = None


class RareEventResult(BaseModel):
    """Metadata about the generated rare event."""

    event_type: RareEventType
    magnitude: float
    start_index: int
    end_index: int
    peak_impact: float
    recovery_rate: Optional[float] = None


class RareEventSimulator:
    """
    Generates synthetic market data representing rare but plausible 'black-swan' events.
    Designed to test XAUUSD strategy resilience beyond historical distributions.
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def generate_scenario(self, config: RareEventConfig) -> pd.DataFrame:
        """
        Generates a synthetic OHLCV DataFrame containing the specified rare event.
        """
        if config.seed is not None:
            self.rng = np.random.default_rng(config.seed)

        if config.event_type == RareEventType.FLASH_CRASH:
            return self._simulate_flash_crash(config)
        elif config.event_type == RareEventType.LIQUIDITY_VACUUM:
            return self._simulate_liquidity_vacuum(config)
        elif config.event_type == RareEventType.GOLD_GAP:
            return self._simulate_gold_gap(config)
        elif config.event_type == RareEventType.VIOLENT_REVERSAL:
            return self._simulate_violent_reversal(config)
        elif config.event_type == RareEventType.DISLOCATION:
            return self._simulate_dislocation(config)
        elif config.event_type == RareEventType.VOL_CLUSTER:
            return self._simulate_vol_cluster(config)
        else:
            raise ValueError(f"Unknown rare event type: {config.event_type}")

    def _generate_base_ohlc(self, prices: np.ndarray, base_vol: float) -> pd.DataFrame:
        """Helper to convert a price series into a valid OHLCV DataFrame."""
        n = len(prices)
        # Generate some noise for OHLC
        noise = self.rng.normal(0, base_vol * 0.5, (n, 3))

        df = pd.DataFrame(
            {
                "open": prices * (1 + noise[:, 0]),
                "high": prices * (1 + np.abs(noise[:, 1])),
                "low": prices * (1 - np.abs(noise[:, 2])),
                "close": prices,
                "tick_volume": self.rng.integers(100, 1000, n),
            }
        )

        # Ensure consistency
        df["high"] = df[["open", "close", "high"]].max(axis=1)
        df["low"] = df[["open", "close", "low"]].min(axis=1)

        # Add a dummy timestamp index
        df.index = pd.date_range(start="2024-01-01", periods=n, freq="5min")

        return df

    def _simulate_flash_crash(self, config: RareEventConfig) -> pd.DataFrame:
        """Simulates a rapid price collapse and partial/full recovery."""
        n = config.n_steps
        returns = self.rng.normal(0, config.base_volatility, n)

        # Event occurs around the middle
        start_idx = n // 2
        duration = int(20 * config.event_magnitude)
        impact = -0.035 * config.event_magnitude  # 3.5% drop base

        # The crash phase
        for i in range(duration // 2):
            returns[start_idx + i] -= abs(self.rng.normal(impact / (duration / 2), 0.001))

        # The recovery phase
        for i in range(duration // 2, duration):
            returns[start_idx + i] += abs(self.rng.normal(-impact / (duration * 0.75), 0.001))

        prices = config.start_price * np.exp(np.cumsum(returns))
        return self._generate_base_ohlc(prices, config.base_volatility)

    def _simulate_liquidity_vacuum(self, config: RareEventConfig) -> pd.DataFrame:
        """Simulates a period of erratic price jumps and extreme spreads."""
        n = config.n_steps
        returns = self.rng.normal(0, config.base_volatility, n)

        start_idx = n // 3
        duration = int(50 * config.event_magnitude)

        # Extreme volatility in the vacuum
        returns[start_idx : start_idx + duration] *= 10.0 * config.event_magnitude

        prices = config.start_price * np.exp(np.cumsum(returns))
        df = self._generate_base_ohlc(prices, config.base_volatility)

        # Inject extreme spreads and low volume during the vacuum
        vacuum_mask = (np.arange(n) >= start_idx) & (np.arange(n) < start_idx + duration)
        df.loc[vacuum_mask, "tick_volume"] = self.rng.integers(1, 50, np.sum(vacuum_mask))

        return df

    def _simulate_gold_gap(self, config: RareEventConfig) -> pd.DataFrame:
        """Simulates discontinuous price jumps (e.g. news or weekend gaps)."""
        n = config.n_steps
        returns = self.rng.normal(0, config.base_volatility, n)

        # One big gap
        gap_idx = n // 2
        gap_magnitude = 0.02 * config.event_magnitude * self.rng.choice([-1, 1])
        returns[gap_idx] += gap_magnitude

        prices = config.start_price * np.exp(np.cumsum(returns))
        return self._generate_base_ohlc(prices, config.base_volatility)

    def _simulate_violent_reversal(self, config: RareEventConfig) -> pd.DataFrame:
        """Simulates a strong trend followed by an abrupt, high-velocity reversal."""
        n = config.n_steps
        returns = self.rng.normal(0, config.base_volatility, n)

        start_idx = n // 4
        trend_duration = n // 4
        reversal_start = start_idx + trend_duration
        reversal_duration = int(30 * config.event_magnitude)

        # Strong uptrend
        returns[start_idx:reversal_start] += 0.002 * config.event_magnitude

        # Violent reversal
        returns[reversal_start : reversal_start + reversal_duration] -= (
            0.005 * config.event_magnitude
        )

        prices = config.start_price * np.exp(np.cumsum(returns))
        return self._generate_base_ohlc(prices, config.base_volatility)

    def _simulate_dislocation(self, config: RareEventConfig) -> pd.DataFrame:
        """Simulates a multi-session breakdown of price levels."""
        n = config.n_steps
        returns = self.rng.normal(0, config.base_volatility, n)

        dislocation_idx = n // 3
        # Permanent shift in mean and volatility
        returns[dislocation_idx:] += self.rng.normal(
            -0.0005 * config.event_magnitude, config.base_volatility * 2, n - dislocation_idx
        )

        prices = config.start_price * np.exp(np.cumsum(returns))
        return self._generate_base_ohlc(prices, config.base_volatility)

    def _simulate_vol_cluster(self, config: RareEventConfig) -> pd.DataFrame:
        """Simulates an abnormal cluster of high volatility (e.g. crisis mode)."""
        n = config.n_steps

        # GARCH-like process for volatility clustering
        vols = np.zeros(n)
        vols[0] = config.base_volatility

        omega = 1e-6
        alpha = 0.2
        beta = 0.7

        # Inject a shock
        shock_idx = n // 4

        for i in range(1, n):
            shock = 0
            if i == shock_idx:
                shock = 0.04 * config.event_magnitude

            vols[i] = np.sqrt(
                omega + alpha * (vols[i - 1] ** 2 + shock**2) + beta * vols[i - 1] ** 2
            )

        returns = self.rng.normal(0, vols, n)
        prices = config.start_price * np.exp(np.cumsum(returns))
        return self._generate_base_ohlc(prices, config.base_volatility)
