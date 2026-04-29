"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rare_event_simulator.py
Generates rare but plausible market situations for stress testing.
"""

import numpy as np
import pandas as pd
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ScenarioType(str, Enum):
    FLASH_CRASH = "flash_crash"
    LIQUIDITY_VACUUM = "liquidity_vacuum"
    GOLD_GAP = "gold_gap"
    VIOLENT_REVERSAL = "violent_reversal"
    DISLOCATION = "dislocation"
    VOLATILITY_CLUSTER = "volatility_cluster"


class ScenarioConfig(BaseModel):
    """Configuration for synthetic rare event generation."""
    scenario_type: ScenarioType
    duration: int = Field(100, gt=4, description="Number of bars to generate")
    start_price: float = Field(2300.0, gt=0, description="Initial price for XAUUSD")
    volatility: float = Field(0.001, gt=0, description="Base volatility for GBM")
    drift: float = Field(0.0, description="Price drift")
    severity: float = Field(1.0, gt=0, description="Scaling factor for the rare event")
    seed: Optional[int] = None

    @field_validator("duration")
    @classmethod
    def duration_must_be_sufficient(cls, v: int) -> int:
        if v <= 4:
            raise ValueError("Duration must be greater than 4 bars for meaningful scenarios")
        return v


class RareEventSimulator:
    """
    Simulator for generating rare market events using GBM and behavioral overrides.
    Compatible with feature engineering pipelines (produces OHLCV).
    """

    def __init__(self, config: ScenarioConfig):
        self.config = config
        self.rng = np.random.default_rng(config.seed)

    def generate(self) -> pd.DataFrame:
        """
        Generate the synthetic price path based on configuration.
        Returns:
            pd.DataFrame: OHLCV data
        """
        prices = self._generate_base_path()

        if self.config.scenario_type == ScenarioType.FLASH_CRASH:
            prices = self._apply_flash_crash(prices)
        elif self.config.scenario_type == ScenarioType.LIQUIDITY_VACUUM:
            prices = self._apply_liquidity_vacuum(prices)
        elif self.config.scenario_type == ScenarioType.GOLD_GAP:
            prices = self._apply_gold_gap(prices)
        elif self.config.scenario_type == ScenarioType.VIOLENT_REVERSAL:
            prices = self._apply_violent_reversal(prices)
        elif self.config.scenario_type == ScenarioType.DISLOCATION:
            prices = self._apply_dislocation(prices)
        elif self.config.scenario_type == ScenarioType.VOLATILITY_CLUSTER:
            prices = self._apply_volatility_cluster(prices)

        return self._to_ohlcv(prices)

    def _generate_base_path(self) -> np.ndarray:
        """Geometric Brownian Motion."""
        dt = 1.0
        n = self.config.duration
        returns = self.rng.normal(
            (self.config.drift - 0.5 * self.config.volatility**2) * dt,
            self.config.volatility * np.sqrt(dt),
            n
        )
        price_path = self.config.start_price * np.exp(np.cumsum(returns))
        # Ensure we have exact duration by shifting or inserting
        # Prepend start price and take first n
        price_path = np.insert(price_path, 0, self.config.start_price)[:-1]
        return price_path

    def _apply_flash_crash(self, prices: np.ndarray) -> np.ndarray:
        """Sudden sharp drop and quick partial recovery."""
        n = len(prices)
        crash_idx = n // 3
        recovery_idx = crash_idx + max(1, n // 10)

        # Crash phase
        crash_magnitude = 0.08 * self.config.severity
        crash_steps = max(1, recovery_idx - crash_idx)
        for i in range(crash_idx, recovery_idx):
            prices[i:] *= (1 - crash_magnitude / crash_steps)

        # Recovery phase (partial)
        recovery_magnitude = crash_magnitude * 0.6
        recovery_end = min(recovery_idx + max(1, n // 5), n)
        recovery_steps = max(1, recovery_end - recovery_idx)
        for i in range(recovery_idx, recovery_end):
            prices[i:] *= (1 + recovery_magnitude / recovery_steps)

        return prices

    def _apply_liquidity_vacuum(self, prices: np.ndarray) -> np.ndarray:
        """Rapid move with sparse data points (simulated as large steps)."""
        n = len(prices)
        vacuum_start = n // 4
        vacuum_duration = max(1, n // 8)

        move_dir = 1 if self.config.drift >= 0 else -1
        jump_size = 0.01 * self.config.severity

        for i in range(vacuum_start, vacuum_start + vacuum_duration):
            prices[i:] *= (1 + move_dir * jump_size)

        return prices

    def _apply_gold_gap(self, prices: np.ndarray) -> np.ndarray:
        """Large overnight or weekend-style gap."""
        n = len(prices)
        gap_idx = n // 2
        gap_percent = 0.02 * self.config.severity
        gap_dir = 1 if self.rng.random() > 0.5 else -1

        prices[gap_idx:] *= (1 + gap_dir * gap_percent)
        return prices

    def _apply_violent_reversal(self, prices: np.ndarray) -> np.ndarray:
        """Strong trend followed by an even stronger reversal."""
        n = len(prices)
        pivot = n // 2

        # Initial trend
        trend_strength = 0.01 * self.config.severity
        for i in range(1, pivot):
            prices[i:] *= (1 + trend_strength / pivot)

        # Violent reversal
        reversal_strength = trend_strength * 2.5
        for i in range(pivot, n):
            prices[i:] *= (1 - reversal_strength / (n - pivot))

        return prices

    def _apply_dislocation(self, prices: np.ndarray) -> np.ndarray:
        """Price moves and stays away from the initial mean (new paradigm)."""
        n = len(prices)
        dislocate_idx = n // 5
        shift = 0.03 * self.config.severity

        prices[dislocate_idx:] *= (1 + shift)
        # Add extra noise during dislocation
        noise = self.rng.normal(0, self.config.volatility * 2, n - dislocate_idx)
        prices[dislocate_idx:] *= (1 + noise)

        return prices

    def _apply_volatility_cluster(self, prices: np.ndarray) -> np.ndarray:
        """Period of extreme volatility."""
        n = len(prices)
        start = n // 4
        end = 3 * n // 4

        cluster_vol = self.config.volatility * 5 * self.config.severity
        for i in range(start, end):
            ret = self.rng.normal(0, cluster_vol)
            prices[i:] *= (1 + ret)

        return prices

    def _to_ohlcv(self, prices: np.ndarray) -> pd.DataFrame:
        """Convert price path to OHLCV format with internal consistency."""
        df = pd.DataFrame(prices, columns=["close"])
        df["open"] = df["close"].shift(1).fillna(prices[0])

        # Add some intra-bar variance for high/low
        noise = self.rng.uniform(0, 0.002, len(prices)) * prices
        df["high"] = df[["open", "close"]].max(axis=1) + noise
        df["low"] = df[["open", "close"]].min(axis=1) - noise

        # Simulated volume
        df["volume"] = self.rng.integers(100, 1000, len(prices)).astype(float)

        # Reorder
        df = df[["open", "high", "low", "close", "volume"]]

        # Ensure data integrity
        df["high"] = np.maximum(df["high"], df[["open", "close"]].max(axis=1))
        df["low"] = np.minimum(df["low"], df[["open", "close"]].min(axis=1))

        return df
