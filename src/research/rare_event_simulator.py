"""
MT5 AI/ML Trading Bot - Research Edition
src/research/rare_event_simulator.py
Rare event simulation for black-swan resilience testing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd


class RareEventSimulator:
    """
    Generates rare but plausible market situations for XAUUSD.
    Designed to extend synthetic data into black-swan resilience testing.
    """

    def __init__(self, base_price: float = 2000.0, timeframe: str = "M5"):
        """
        Initializes the simulator.

        Args:
            base_price: The starting price for simulations.
            timeframe: The timeframe for the generated data (e.g., 'M1', 'M5', 'H1').
        """
        self.base_price = base_price
        self.timeframe = timeframe
        self.freq_map = {
            "M1": "1min",
            "M5": "5min",
            "M15": "15min",
            "H1": "1h",
            "D1": "1d",
        }
        # Standardize frequency for pd.date_range
        # Note: 'min' is deprecated in newer pandas, 'min' -> 'T' or 'min'
        self.freq = self.freq_map.get(timeframe, "5min").lower()

    def _generate_base_df(self, n_bars: int, start_time: Optional[datetime] = None) -> pd.DataFrame:
        if start_time is None:
            start_time = datetime.now(timezone.utc)

        timestamps = pd.date_range(start=start_time, periods=n_bars, freq=self.freq)
        df = pd.DataFrame(index=timestamps)
        df["timestamp"] = timestamps
        return df

    def _to_ohlcv(self, df: pd.DataFrame, prices: np.ndarray, vol_factor: float = 1.0) -> pd.DataFrame:
        """
        Converts a price series to a OHLCV DataFrame.
        """
        n = len(prices)
        # Add some noise for OHLC
        noise = np.random.normal(0, 0.0002 * self.base_price, (n, 4))

        df["close"] = prices
        # For a smooth series, open is previous close
        df["open"] = df["close"].shift(1).fillna(self.base_price)

        # Ensure consistency
        df["high"] = df[["open", "close"]].max(axis=1) + np.abs(noise[:, 0])
        df["low"] = df[["open", "close"]].min(axis=1) - np.abs(noise[:, 1])

        # Tick volume with poisson distribution
        df["tick_volume"] = (np.random.poisson(100, n) * vol_factor).astype(int)

        return df[["timestamp", "open", "high", "low", "close", "tick_volume"]].reset_index(drop=True)

    def generate_flash_crash(
        self, n_bars: int = 100, magnitude: float = 0.05, recovery_rate: float = 0.8
    ) -> pd.DataFrame:
        """
        Simulates a rapid price drop followed by a partial recovery.
        """
        df = self._generate_base_df(n_bars)
        prices = np.full(n_bars, self.base_price)

        crash_start = n_bars // 4
        crash_end = n_bars // 2

        # Crash phase
        crash_len = crash_end - crash_start
        drop = np.linspace(0, magnitude * self.base_price, crash_len)
        prices[crash_start:crash_end] -= drop

        # Recovery phase
        recovery_start = crash_end
        recovery_end = n_bars
        recovery_len = recovery_end - recovery_start
        recovery = np.linspace(0, magnitude * self.base_price * recovery_rate, recovery_len)
        prices[recovery_start:recovery_end] -= magnitude * self.base_price - recovery

        return self._to_ohlcv(df, prices, vol_factor=5.0)

    def generate_liquidity_vacuum(self, n_bars: int = 100, jump_std: float = 0.005) -> pd.DataFrame:
        """
        Simulates high variance and price jumps with low volume.
        """
        df = self._generate_base_df(n_bars)
        prices = np.zeros(n_bars)
        prices[0] = self.base_price

        for i in range(1, n_bars):
            # Random walk with high volatility
            noise = np.random.normal(0, jump_std * self.base_price)
            prices[i] = prices[i - 1] + noise

        return self._to_ohlcv(df, prices, vol_factor=0.2)

    def generate_gold_gap(self, n_bars: int = 100, gap_size: float = 0.01) -> pd.DataFrame:
        """
        Simulates a price discontinuity (gap).
        """
        df = self._generate_base_df(n_bars)
        prices = np.full(n_bars, self.base_price)

        gap_idx = n_bars // 2
        prices[gap_idx:] += gap_size * self.base_price

        ohlcv = self._to_ohlcv(df, prices)
        # Inject the gap at gap_idx: open is significantly different from previous close
        ohlcv.loc[gap_idx, "open"] = ohlcv.loc[gap_idx - 1, "close"] + gap_size * self.base_price
        # Re-adjust high/low for the gap bar
        ohlcv.loc[gap_idx, "high"] = (
            max(ohlcv.loc[gap_idx, "open"], ohlcv.loc[gap_idx, "close"]) + 0.0005 * self.base_price
        )
        ohlcv.loc[gap_idx, "low"] = (
            min(ohlcv.loc[gap_idx, "open"], ohlcv.loc[gap_idx, "close"]) - 0.0005 * self.base_price
        )

        return ohlcv

    def generate_violent_reversal(self, n_bars: int = 100, magnitude: float = 0.03) -> pd.DataFrame:
        """
        Simulates a V-shaped reversal.
        """
        df = self._generate_base_df(n_bars)
        prices = np.full(n_bars, self.base_price)

        mid = n_bars // 2
        prices[:mid] -= np.linspace(0, magnitude * self.base_price, mid)
        prices[mid:] -= np.linspace(magnitude * self.base_price, 0, n_bars - mid)

        return self._to_ohlcv(df, prices, vol_factor=3.0)

    def generate_multi_session_dislocation(
        self, n_bars: int = 500, drift_change: float = 0.0005
    ) -> pd.DataFrame:
        """
        Simulates a structural break in price drift over multiple sessions.
        """
        df = self._generate_base_df(n_bars)
        prices = np.zeros(n_bars)
        prices[0] = self.base_price

        break_pt = n_bars // 2
        for i in range(1, n_bars):
            drift = 0 if i < break_pt else drift_change * self.base_price
            prices[i] = prices[i - 1] + drift + np.random.normal(0, 0.0005 * self.base_price)

        return self._to_ohlcv(df, prices)

    def generate_volatility_cluster(
        self, n_bars: int = 200, burst_magnitude: float = 5.0
    ) -> pd.DataFrame:
        """
        Simulates a burst of high volatility (volatility clustering).
        """
        df = self._generate_base_df(n_bars)
        prices = np.zeros(n_bars)
        prices[0] = self.base_price

        burst_start = n_bars // 3
        burst_end = 2 * n_bars // 3

        for i in range(1, n_bars):
            vol = 0.0005 * self.base_price
            if burst_start <= i <= burst_end:
                vol *= burst_magnitude
            prices[i] = prices[i - 1] + np.random.normal(0, vol)

        return self._to_ohlcv(df, prices)

    def generate_scenario(self, scenario_type: str, **kwargs) -> pd.DataFrame:
        """
        Generic method to generate a scenario by name.
        """
        method = getattr(self, f"generate_{scenario_type}", None)
        if method:
            return method(**kwargs)
        raise ValueError(f"Unknown scenario type: {scenario_type}")
