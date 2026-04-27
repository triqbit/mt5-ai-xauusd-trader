"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rare_event_simulator.py
Generator for rare but plausible market situations for black-swan resilience testing.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class ScenarioType(str, Enum):
    FLASH_CRASH = "flash_crash"
    LIQUIDITY_VACUUM = "liquidity_vacuum"
    GOLD_GAP_MOVE = "gold_gap_move"
    VIOLENT_REVERSAL = "violent_reversal"
    MULTI_SESSION_DISLOCATION = "multi_session_dislocation"
    VOLATILITY_CLUSTER = "volatility_cluster"


class ScenarioConfig(BaseModel):
    """Configuration for a rare event scenario."""
    scenario_type: ScenarioType
    duration_bars: int = Field(..., gt=0, description="Duration of the event in bars")
    magnitude: float = Field(..., gt=0, description="Magnitude/intensity of the event (e.g., price drop % or volatility multiplier)")
    recovery_rate: float = Field(0.5, ge=0, le=1, description="Rate of recovery after the event peak (0-1)")
    random_seed: Optional[int] = None


class RareEventSimulator:
    """
    Generates rare market scenarios and overlays them on base OHLCV data.
    Designed for stress-testing XAUUSD strategies.
    """

    def __init__(self, base_data: Optional[pd.DataFrame] = None):
        """
        Initialize the simulator.

        Args:
            base_data: Optional base OHLCV DataFrame (columns: Open, High, Low, Close, Volume)
        """
        self.base_data = base_data
        if base_data is not None:
            self._validate_data(base_data)
        self.rng = np.random.default_rng()

    def _validate_data(self, data: pd.DataFrame):
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"Data must contain columns: {required_columns}")

    def apply_scenario(
        self,
        config: ScenarioConfig,
        start_index: Optional[int] = None,
        data: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Apply a rare event scenario to the data.

        Args:
            config: Scenario configuration
            start_index: Index to start the event. If None, a random index is chosen.
            data: Data to apply the event to. Defaults to self.base_data.

        Returns:
            pd.DataFrame: OHLCV data with the rare event applied.
        """
        target_data = data if data is not None else self.base_data
        if target_data is None:
            raise ValueError("No data provided to apply scenario.")

        self._validate_data(target_data)
        df = target_data.copy()

        if config.random_seed is not None:
            self.rng = np.random.default_rng(config.random_seed)

        if start_index is None:
            max_start = len(df) - config.duration_bars - 1
            if max_start <= 0:
                raise ValueError("Data too short for the configured scenario duration.")
            start_index = self.rng.integers(0, max_start)

        if config.scenario_type == ScenarioType.FLASH_CRASH:
            return self._generate_flash_crash(df, start_index, config)
        elif config.scenario_type == ScenarioType.LIQUIDITY_VACUUM:
            return self._generate_liquidity_vacuum(df, start_index, config)
        elif config.scenario_type == ScenarioType.GOLD_GAP_MOVE:
            return self._generate_gold_gap_move(df, start_index, config)
        elif config.scenario_type == ScenarioType.VIOLENT_REVERSAL:
            return self._generate_violent_reversal(df, start_index, config)
        elif config.scenario_type == ScenarioType.MULTI_SESSION_DISLOCATION:
            return self._generate_multi_session_dislocation(df, start_index, config)
        elif config.scenario_type == ScenarioType.VOLATILITY_CLUSTER:
            return self._generate_volatility_cluster(df, start_index, config)
        else:
            raise ValueError(f"Unsupported scenario type: {config.scenario_type}")

    def _generate_flash_crash(self, df: pd.DataFrame, start_idx: int, config: ScenarioConfig) -> pd.DataFrame:
        """Simulate a sudden deep drop and quick recovery."""
        end_idx = start_idx + config.duration_bars
        peak_idx = start_idx + config.duration_bars // 3

        base_price = df.iloc[start_idx]["Close"]
        drop_magnitude = base_price * config.magnitude

        for i in range(start_idx, end_idx):
            if i < peak_idx:
                # Rapid drop
                factor = (i - start_idx) / (peak_idx - start_idx)
                current_drop = drop_magnitude * factor
            else:
                # Recovery
                factor = (i - peak_idx) / (end_idx - peak_idx)
                current_drop = drop_magnitude * (1 - factor * config.recovery_rate)

            self._apply_price_offset(df, i, -current_drop)
            df.iat[i, df.columns.get_loc("Volume")] *= (1 + config.magnitude * 10)

        return df

    def _generate_liquidity_vacuum(self, df: pd.DataFrame, start_idx: int, config: ScenarioConfig) -> pd.DataFrame:
        """Simulate erratic price moves and wider spreads (modeled via higher volatility and lower volume)."""
        end_idx = start_idx + config.duration_bars

        for i in range(start_idx, end_idx):
            # Increase bar range significantly
            noise = (self.rng.random() - 0.5) * 2 * config.magnitude * df.iloc[i]["Close"]
            df.iat[i, df.columns.get_loc("High")] += abs(noise)
            df.iat[i, df.columns.get_loc("Low")] -= abs(noise)
            df.iat[i, df.columns.get_loc("Close")] += noise

            # Reduce volume to simulate vacuum
            df.iat[i, df.columns.get_loc("Volume")] *= 0.2

        return df

    def _generate_gold_gap_move(self, df: pd.DataFrame, start_idx: int, config: ScenarioConfig) -> pd.DataFrame:
        """Simulate a large price gap between bars."""
        gap_magnitude = df.iloc[start_idx]["Close"] * config.magnitude
        direction = 1 if self.rng.random() > 0.5 else -1
        total_offset = gap_magnitude * direction

        for i in range(start_idx, len(df)):
            self._apply_price_offset(df, i, total_offset)

        return df

    def _generate_violent_reversal(self, df: pd.DataFrame, start_idx: int, config: ScenarioConfig) -> pd.DataFrame:
        """Simulate a sharp trend reversal."""
        end_idx = start_idx + config.duration_bars
        mid_idx = start_idx + config.duration_bars // 2

        reversal_magnitude = df.iloc[start_idx]["Close"] * config.magnitude

        for i in range(start_idx, end_idx):
            if i < mid_idx:
                # Accelerate existing trend (assumed upwards for simplicity, or based on previous bars)
                offset = reversal_magnitude * (i - start_idx) / (mid_idx - start_idx)
            else:
                # Violent reversal
                offset = reversal_magnitude - (reversal_magnitude * 2 * (i - mid_idx) / (end_idx - mid_idx))

            self._apply_price_offset(df, i, offset)
            df.iat[i, df.columns.get_loc("Volume")] *= (1 + config.magnitude * 5)

        return df

    def _generate_multi_session_dislocation(self, df: pd.DataFrame, start_idx: int, config: ScenarioConfig) -> pd.DataFrame:
        """Simulate a persistent deviation from the mean."""
        end_idx = start_idx + config.duration_bars
        dislocation = df.iloc[start_idx]["Close"] * config.magnitude

        for i in range(start_idx, end_idx):
            self._apply_price_offset(df, i, dislocation)

        return df

    def _generate_volatility_cluster(self, df: pd.DataFrame, start_idx: int, config: ScenarioConfig) -> pd.DataFrame:
        """Simulate a period of sustained high variance."""
        end_idx = start_idx + config.duration_bars

        for i in range(start_idx, end_idx):
            returns = (self.rng.random() - 0.5) * 2 * config.magnitude * df.iloc[i]["Close"]
            df.iat[i, df.columns.get_loc("Open")] += returns * 0.5
            df.iat[i, df.columns.get_loc("High")] += abs(returns)
            df.iat[i, df.columns.get_loc("Low")] -= abs(returns)
            df.iat[i, df.columns.get_loc("Close")] += returns
            df.iat[i, df.columns.get_loc("Volume")] *= (1 + config.magnitude)

        return df

    def _apply_price_offset(self, df: pd.DataFrame, idx: int, offset: float) -> None:
        """Helper to apply price offset to all OHLC columns of a bar."""
        for col in ["Open", "High", "Low", "Close"]:
            df.iat[idx, df.columns.get_loc(col)] += offset
