"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/utils/synthetic_data.py
Deterministic scenario generator for robust testing of trading logic and risk guards.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class ScenarioGenerator:
    """
    Generates deterministic market data scenarios for testing.
    Uses fixed seeds for reproducibility where applicable.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(self.seed)

    def generate_gbm(
        self,
        n_bars: int = 200,
        s0: float = 2000.0,
        mu: float = 0.0001,
        sigma: float = 0.002,
        dt: float = 1.0,
    ) -> pd.DataFrame:
        """
        Generates price data using Geometric Brownian Motion (GBM).
        """
        np.random.seed(self.seed)
        returns = np.random.normal(
            (mu - 0.5 * sigma**2) * dt, sigma * np.sqrt(dt), n_bars
        )
        price_path = s0 * np.exp(np.cumsum(returns))

        return self._to_ohlcv(price_path)

    def generate_flash_crash(
        self,
        n_bars: int = 200,
        crash_at: int = 100,
        crash_depth: float = 0.1,  # 10% drop
        recovery_rate: float = 0.5, # 50% recovery
    ) -> pd.DataFrame:
        """
        Generates a scenario with a sudden price drop (flash crash).
        """
        df = self.generate_gbm(n_bars=n_bars)
        prices = df["close"].values

        # Apply crash
        prices[crash_at:] = prices[crash_at:] * (1 - crash_depth)

        # Partial recovery
        recovery_len = min(20, n_bars - crash_at - 1)
        if recovery_len > 0:
            recovery_steps = np.linspace(0, crash_depth * recovery_rate, recovery_len)
            prices[crash_at:crash_at + recovery_len] *= (1 + recovery_steps)

        return self._to_ohlcv(prices)

    def generate_volatility_spike(
        self,
        n_bars: int = 200,
        spike_at: int = 100,
        duration: int = 50,
        multiplier: float = 5.0,
    ) -> pd.DataFrame:
        """
        Generates a scenario where volatility suddenly increases.
        """
        np.random.seed(self.seed)
        s0 = 2000.0
        mu = 0.0001
        sigma = 0.002
        dt = 1.0

        returns = np.random.normal(
            (mu - 0.5 * sigma**2) * dt, sigma * np.sqrt(dt), n_bars
        )

        # Apply spike
        end_spike = min(spike_at + duration, n_bars)
        returns[spike_at:end_spike] *= multiplier

        price_path = s0 * np.exp(np.cumsum(returns))
        return self._to_ohlcv(price_path)

    def generate_missing_data(
        self,
        n_bars: int = 200,
        gap_at: int = 100,
        gap_size: int = 10,
    ) -> pd.DataFrame:
        """
        Generates data with missing bars (NaNs).
        """
        df = self.generate_gbm(n_bars=n_bars)

        gap_end = min(gap_at + gap_size, n_bars)
        df.iloc[gap_at:gap_end] = np.nan

        return df

    def _to_ohlcv(self, price_path: np.ndarray) -> pd.DataFrame:
        """
        Converts a price path into a pseudo-OHLCV DataFrame.
        """
        n = len(price_path)
        # Create small variations for OHL
        noise = np.random.normal(0, 0.0005, (n, 3))

        df = pd.DataFrame({
            "time": pd.date_range(start="2024-01-01", periods=n, freq="5min"),
            "open": price_path * (1 + noise[:, 0]),
            "high": price_path * (1 + np.abs(noise[:, 1])),
            "low": price_path * (1 - np.abs(noise[:, 2])),
            "close": price_path,
            "tick_volume": np.random.randint(100, 1000, n)
        })

        # Ensure H >= max(O, C) and L <= min(O, C)
        df["high"] = df[["open", "close", "high"]].max(axis=1)
        df["low"] = df[["open", "close", "low"]].min(axis=1)

        return df
