"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rare_event_simulator.py
Generator for rare but plausible market situations for stress testing and strategy research.
"""

from __future__ import annotations

from enum import Enum
from typing import Union

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, field_validator


class ScenarioType(str, Enum):
    FLASH_CRASH = "flash_crash"
    LIQUIDITY_VACUUM = "liquidity_vacuum"
    GOLD_GAP = "gold_gap"
    VIOLENT_REVERSAL = "violent_reversal"
    DISLOCATION = "dislocation"
    VOLATILITY_CLUSTER = "volatility_cluster"


class BaseConfig(BaseModel):
    """Base configuration for all scenarios."""
    start_index: int = Field(..., description="Index where the event begins", ge=0)
    duration: int = Field(..., description="Duration of the event in steps", gt=4)


class FlashCrashConfig(BaseConfig):
    """Configuration for a flash crash scenario."""
    magnitude: float = Field(..., description="Maximum price drop as a fraction of current price", gt=0, lt=1)
    recovery_rate: float = Field(0.5, description="Fraction of the drop recovered during the event")


class LiquidityVacuumConfig(BaseConfig):
    """Configuration for a liquidity vacuum scenario."""
    noise_multiplier: float = Field(2.0, description="Multiplier for price noise")
    spread_widening: float = Field(3.0, description="Multiplier for synthetic spread")


class GoldGapConfig(BaseConfig):
    """Configuration for a sudden price gap."""
    duration: int = Field(1, description="Gaps are instantaneous, duration is ignored", ge=1)
    gap_size: float = Field(..., description="Size of the gap as a fraction of current price", gt=0)
    direction: int = Field(..., description="1 for gap up, -1 for gap down")

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v):
        if v not in [1, -1]:
            raise ValueError("direction must be 1 or -1")
        return v


class ViolentReversalConfig(BaseConfig):
    """Configuration for a sharp trend followed by immediate reversal."""
    trend_magnitude: float = Field(..., description="Magnitude of the initial trend")
    reversal_magnitude: float = Field(..., description="Magnitude of the reversal")


class DislocationConfig(BaseConfig):
    """Configuration for a persistent shift in price levels."""
    shift_magnitude: float = Field(..., description="Permanent shift in price as a fraction")


class VolatilityClusterConfig(BaseConfig):
    """Configuration for sustained period of high volatility."""
    vol_multiplier: float = Field(3.0, description="Multiplier for standard deviation")


class RareEventSimulator:
    """
    Generates synthetic market data with rare-event overlays.
    """

    def __init__(self, base_price: float = 2000.0, sigma: float = 0.001, dt: float = 1.0):
        self.base_price = base_price
        self.sigma = sigma
        self.dt = dt

    def generate_base_data(self, n_steps: int) -> pd.DataFrame:
        """
        Generates base market data using Geometric Brownian Motion.
        """
        returns = np.random.normal(0, self.sigma, n_steps)
        price_path = self.base_price * np.exp(np.cumsum(returns))

        data = []
        for i in range(n_steps):
            prev_close = price_path[i-1] if i > 0 else self.base_price
            open_p = prev_close
            close_p = price_path[i]

            # Simple OHLC generation
            high_p = max(open_p, close_p) + abs(np.random.normal(0, self.sigma * 0.5))
            low_p = min(open_p, close_p) - abs(np.random.normal(0, self.sigma * 0.5))
            volume = np.random.poisson(1000)

            data.append([open_p, high_p, low_p, close_p, float(volume)])

        return pd.DataFrame(data, columns=['open', 'high', 'low', 'close', 'volume'])

    def apply_scenario(self, df: pd.DataFrame, config: Union[
        FlashCrashConfig, LiquidityVacuumConfig, GoldGapConfig,
        ViolentReversalConfig, DislocationConfig, VolatilityClusterConfig
    ]) -> pd.DataFrame:
        """
        Applies a specific rare-event scenario to the provided data.
        """
        df_copy = df.copy()
        start = config.start_index
        end = start + config.duration

        if end > len(df_copy):
            raise ValueError("Scenario exceeds data length")

        if isinstance(config, FlashCrashConfig):
            self._apply_flash_crash(df_copy, config)
        elif isinstance(config, LiquidityVacuumConfig):
            self._apply_liquidity_vacuum(df_copy, config)
        elif isinstance(config, GoldGapConfig):
            self._apply_gold_gap(df_copy, config)
        elif isinstance(config, ViolentReversalConfig):
            self._apply_violent_reversal(df_copy, config)
        elif isinstance(config, DislocationConfig):
            self._apply_dislocation(df_copy, config)
        elif isinstance(config, VolatilityClusterConfig):
            self._apply_volatility_cluster(df_copy, config)

        return self._ensure_ohlc_consistency(df_copy)

    def _apply_flash_crash(self, df: pd.DataFrame, config: FlashCrashConfig):
        start, end = config.start_index, config.start_index + config.duration
        bottom_idx = start + config.duration // 4

        # Crash phase
        for i in range(start, bottom_idx):
            fraction = (i - start) / (bottom_idx - start)
            drop = 1 - (fraction * config.magnitude)
            df.iloc[i, :4] *= drop

        # Recovery phase
        recovery_bottom = 1 - config.magnitude
        recovery_target = 1 - config.magnitude * (1 - config.recovery_rate)
        for i in range(bottom_idx, end):
            fraction = (i - bottom_idx) / (end - bottom_idx)
            recovery = recovery_bottom + fraction * (recovery_target - recovery_bottom)
            df.iloc[i, :4] *= recovery

        # Rest of the data shifted
        shift = 1 - config.magnitude * (1 - config.recovery_rate)
        df.iloc[end:, :4] *= shift

    def _apply_liquidity_vacuum(self, df: pd.DataFrame, config: LiquidityVacuumConfig):
        start, end = config.start_index, config.start_index + config.duration
        for i in range(start, end):
            noise = np.random.normal(0, self.sigma * config.noise_multiplier)
            df.iloc[i, :4] *= (1 + noise)
            df.iloc[i, 4] *= 0.1  # Volume drop

    def _apply_gold_gap(self, df: pd.DataFrame, config: GoldGapConfig):
        start = config.start_index
        gap = 1 + (config.direction * config.gap_size)
        df.iloc[start:, :4] *= gap

    def _apply_violent_reversal(self, df: pd.DataFrame, config: ViolentReversalConfig):
        start, end = config.start_index, config.start_index + config.duration
        mid = start + config.duration // 2

        # Trend up/down
        for i in range(start, mid):
            fraction = (i - start) / (mid - start)
            df.iloc[i, :4] *= (1 + fraction * config.trend_magnitude)

        # Reversal
        base_at_mid = 1 + config.trend_magnitude
        for i in range(mid, end):
            fraction = (i - mid) / (end - mid)
            df.iloc[i, :4] *= (base_at_mid - fraction * config.reversal_magnitude)

        # Carry over
        final_multiplier = base_at_mid - config.reversal_magnitude
        df.iloc[end:, :4] *= final_multiplier

    def _apply_dislocation(self, df: pd.DataFrame, config: DislocationConfig):
        start, end = config.start_index, config.start_index + config.duration
        for i in range(start, end):
            fraction = (i - start) / config.duration
            df.iloc[i, :4] *= (1 + fraction * config.shift_magnitude)
        df.iloc[end:, :4] *= (1 + config.shift_magnitude)

    def _apply_volatility_cluster(self, df: pd.DataFrame, config: VolatilityClusterConfig):
        start, end = config.start_index, config.start_index + config.duration
        for i in range(start, end):
            vol_noise = np.random.normal(0, self.sigma * config.vol_multiplier)
            df.iloc[i, :4] *= (1 + vol_noise)

    def _ensure_ohlc_consistency(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fixes any OHLC violations."""
        df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
        df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
        return df
