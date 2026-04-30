"""
Synthetic scenario generation for deterministic testing of trading logic.
Produces OHLCV dataframes representing various market conditions and edge cases.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

class ScenarioGenerator:
    """
    Generates deterministic synthetic OHLCV data for testing.
    Uses fixed seeds to ensure reproducibility.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def _base_range(self, n_bars: int) -> pd.DataFrame:
        """Create base datetime index and basic columns."""
        end_time = datetime(2024, 1, 1, 12, 0, 0)
        times = [end_time - timedelta(minutes=5 * i) for i in range(n_bars)]
        times.reverse()

        return pd.DataFrame({
            "time": times,
            "open": np.zeros(n_bars),
            "high": np.zeros(n_bars),
            "low": np.zeros(n_bars),
            "close": np.zeros(n_bars),
            "tick_volume": self.rng.integers(100, 1000, n_bars)
        })

    def generate_trending_market(self, n_bars: int = 100, start_price: float = 2000.0, trend: float = 0.5, volatility: float = 2.0) -> pd.DataFrame:
        """
        Generate a trending market (bullish or bearish).
        trend > 0: Bullish
        trend < 0: Bearish
        """
        df = self._base_range(n_bars)
        prices = [start_price]
        for i in range(1, n_bars):
            change = trend + self.rng.normal(0, volatility)
            prices.append(prices[-1] + change)

        df["close"] = prices
        df["open"] = df["close"].shift(1).fillna(start_price)
        df["high"] = df[["open", "close"]].max(axis=1) + self.rng.uniform(0, volatility, n_bars)
        df["low"] = df[["open", "close"]].min(axis=1) - self.rng.uniform(0, volatility, n_bars)

        return df

    def generate_ranging_market(self, n_bars: int = 100, center_price: float = 2000.0, range_width: float = 10.0, volatility: float = 1.0) -> pd.DataFrame:
        """Generate a sideways market within a specified range."""
        df = self._base_range(n_bars)
        df["close"] = center_price + self.rng.uniform(-range_width/2, range_width/2, n_bars)
        df["open"] = df["close"].shift(1).fillna(center_price)
        df["high"] = df[["open", "close"]].max(axis=1) + self.rng.uniform(0, volatility, n_bars)
        df["low"] = df[["open", "close"]].min(axis=1) - self.rng.uniform(0, volatility, n_bars)

        return df

    def generate_volatile_market(self, n_bars: int = 100, start_price: float = 2000.0, volatility: float = 10.0) -> pd.DataFrame:
        """Generate a high-volatility market with large price swings."""
        df = self._base_range(n_bars)
        prices = [start_price]
        for i in range(1, n_bars):
            change = self.rng.normal(0, volatility)
            prices.append(prices[-1] + change)

        df["close"] = prices
        df["open"] = df["close"].shift(1).fillna(start_price)
        df["high"] = df[["open", "close"]].max(axis=1) + self.rng.uniform(0, volatility * 2, n_bars)
        df["low"] = df[["open", "close"]].min(axis=1) - self.rng.uniform(0, volatility * 2, n_bars)

        return df

    def generate_gapping_market(self, n_bars: int = 100, start_price: float = 2000.0, gap_frequency: float = 0.05, gap_size: float = 20.0) -> pd.DataFrame:
        """Generate a market with occasional large price gaps between bars."""
        df = self._base_range(n_bars)
        prices = [start_price]
        for i in range(1, n_bars):
            gap = 0
            if self.rng.random() < gap_frequency:
                gap = self.rng.choice([-1, 1]) * gap_size

            prices.append(prices[-1] + self.rng.normal(0, 1.0) + gap)

        df["close"] = prices
        df["open"] = df["close"].shift(1).fillna(start_price)
        # Randomly introduce gaps at the open
        for i in range(1, n_bars):
            if self.rng.random() < gap_frequency:
                df.at[i, "open"] = df.at[i-1, "close"] + self.rng.choice([-1, 1]) * gap_size

        df["high"] = df[["open", "close"]].max(axis=1) + self.rng.uniform(0, 2, n_bars)
        df["low"] = df[["open", "close"]].min(axis=1) - self.rng.uniform(0, 2, n_bars)

        return df

    def generate_malformed_data(self, n_bars: int = 10) -> pd.DataFrame:
        """Generate intentionally broken data for robustness testing."""
        df = self.generate_ranging_market(n_bars=n_bars)

        # Case 1: Low > High
        df.at[0, "low"] = 3000.0
        df.at[0, "high"] = 1000.0

        # Case 2: Negative price
        df.at[1, "close"] = -100.0

        # Case 3: Zero volume
        df.at[2, "tick_volume"] = 0

        # Case 4: Missing values (NaN)
        df.at[3, "close"] = np.nan

        return df
