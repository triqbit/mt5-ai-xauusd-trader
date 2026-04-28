"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/utils/synthetic_data.py
Deterministic market scenario generator for testing and validation.
"""

import numpy as np
import pandas as pd


class ScenarioGenerator:
    """
    Generates deterministic market data scenarios for robust testing.
    Uses numpy seeds to ensure reproducibility.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def generate_gbm(
        self,
        n_bars: int = 100,
        start_price: float = 2000.0,
        mu: float = 0.0001,
        sigma: float = 0.001
    ) -> pd.DataFrame:
        """
        Generate standard Geometric Brownian Motion OHLCV data.
        """
        returns = self.rng.normal(mu, sigma, n_bars)
        price_path = start_price * np.exp(np.cumsum(returns))

        # Create OHLC
        high = price_path * (1 + abs(self.rng.normal(0, sigma/2, n_bars)))
        low = price_path * (1 - abs(self.rng.normal(0, sigma/2, n_bars)))
        open_p = np.zeros_like(price_path)
        open_p[0] = start_price
        open_p[1:] = price_path[:-1]

        # Volume
        volume = self.rng.integers(100, 1000, n_bars)

        df = pd.DataFrame({
            "open": open_p,
            "high": np.maximum.reduce([open_p, price_path, high]),
            "low": np.minimum.reduce([open_p, price_path, low]),
            "close": price_path,
            "tick_volume": volume,
            "time": pd.date_range(start="2024-01-01", periods=n_bars, freq="5min")
        })
        return df

    def generate_flash_crash(
        self,
        n_bars: int = 100,
        crash_at: int = 50,
        crash_depth: float = 0.10
    ) -> pd.DataFrame:
        """
        Generates a scenario with a sudden price drop.
        """
        df = self.generate_gbm(n_bars=n_bars)
        # Apply crash
        crash_factor = 1.0 - crash_depth
        df.iloc[crash_at:, :4] *= crash_factor
        # Spike high/low to simulate panic
        df.loc[df.index[crash_at], "low"] *= 0.95
        return df

    def generate_volatility_spike(
        self,
        n_bars: int = 100,
        spike_at: int = 50,
        sigma_mult: float = 5.0
    ) -> pd.DataFrame:
        """
        Generates a scenario where volatility suddenly increases.
        """
        # First half normal
        df1 = self.generate_gbm(n_bars=spike_at)
        # Second half volatile
        last_price = df1.iloc[-1]["close"]
        df2 = self.generate_gbm(n_bars=n_bars - spike_at, start_price=last_price, sigma=0.001 * sigma_mult)
        # Adjust time for df2
        df2["time"] = pd.date_range(start=df1.iloc[-1]["time"] + pd.Timedelta(minutes=5), periods=len(df2), freq="5min")

        return pd.concat([df1, df2], ignore_index=True)

    def generate_data_gap(
        self,
        n_bars: int = 100,
        gap_at: int = 50,
        gap_size: int = 5
    ) -> pd.DataFrame:
        """
        Generates a scenario with missing data bars.
        """
        df = self.generate_gbm(n_bars=n_bars)
        return df.drop(df.index[gap_at : gap_at + gap_size]).reset_index(drop=True)
