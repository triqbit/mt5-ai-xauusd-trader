"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/utils/synthetic_data.py
Synthetic market data generation for testing and development.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

import numpy as np
import pandas as pd


class MarketRegime(Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    CHOPPY = "choppy"


class SyntheticDataGenerator:
    """
    Generates realistic synthetic OHLCV data for testing.
    Uses Geometric Brownian Motion (GBM) as the base and applies various market regimes and events.
    """

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            np.random.seed(seed)

    def generate_base_prices(
        self,
        n_ticks: int,
        start_price: float = 2000.0,
        mu: float = 0.0001,
        sigma: float = 0.001
    ) -> np.ndarray:
        """
        Generate raw price ticks using Geometric Brownian Motion.

        Args:
            n_ticks: Number of price ticks to generate.
            start_price: Initial price.
            mu: Drift coefficient (expected return).
            sigma: Volatility coefficient.
        """
        # Generate random returns
        returns = np.random.normal(loc=mu / 1000, scale=sigma, size=n_ticks)
        price_ratios = np.exp(returns)
        prices = start_price * np.cumprod(price_ratios)
        # Ensure we have start_price as the first element and keep length at n_ticks
        prices = np.insert(prices, 0, start_price)[:-1]
        return prices

    def apply_regime(
        self,
        n_ticks: int,
        regime: MarketRegime,
        start_price: float = 2000.0
    ) -> np.ndarray:
        """
        Generate prices based on a specific market regime.
        """
        if regime == MarketRegime.TRENDING:
            # Strong drift, moderate volatility
            mu = 0.05 if np.random.random() > 0.5 else -0.05
            sigma = 0.0005
        elif regime == MarketRegime.RANGING:
            # Zero drift, low volatility
            mu = 0.0
            sigma = 0.0003
        elif regime == MarketRegime.CHOPPY:
            # Zero drift, high volatility
            mu = 0.0
            sigma = 0.002
        else:
            mu, sigma = 0.0001, 0.001

        return self.generate_base_prices(n_ticks, start_price, mu, sigma)

    def add_flash_crash(
        self,
        prices: np.ndarray,
        index: int,
        depth_pct: float = 0.05,
        duration_ticks: int = 20
    ) -> np.ndarray:
        """
        Insert a flash crash (sudden drop and quick recovery).
        """
        new_prices = prices.copy()
        if index + duration_ticks > len(prices):
            duration_ticks = len(prices) - index

        half_duration = duration_ticks // 2

        # Crash phase
        for i in range(half_duration):
            factor = 1.0 - (depth_pct * (i + 1) / half_duration)
            new_prices[index + i] = prices[index] * factor

        # Recovery phase
        for i in range(half_duration, duration_ticks):
            factor = 1.0 - (depth_pct * (duration_ticks - i) / half_duration)
            new_prices[index + i] = prices[index] * factor

        # Adjust remaining prices to the last recovery level to avoid a huge jump back
        remaining_shift = new_prices[index + duration_ticks - 1] / prices[index + duration_ticks - 1]
        new_prices[index + duration_ticks:] *= remaining_shift

        return new_prices

    def add_gap(
        self,
        prices: np.ndarray,
        index: int,
        gap_pct: float = 0.01
    ) -> np.ndarray:
        """
        Insert a price gap.
        """
        new_prices = prices.copy()
        if index >= len(prices):
            return new_prices

        direction = 1 if np.random.random() > 0.5 else -1
        shift = 1.0 + (direction * gap_pct)
        new_prices[index:] = new_prices[index:] * shift
        return new_prices

    def add_news_event(
        self,
        prices: np.ndarray,
        index: int,
        vol_multiplier: float = 5.0,
        duration_ticks: int = 100
    ) -> np.ndarray:
        """
        Increase volatility and add a directional spike to simulate a news event.
        """
        new_prices = prices.copy()
        if index + duration_ticks > len(prices):
            duration_ticks = len(prices) - index

        spike_direction = 1 if np.random.random() > 0.5 else -1
        spike_magnitude = 0.005 # 0.5% spike

        for i in range(duration_ticks):
            # Increase volatility during event
            noise = np.random.normal(0, 0.001 * vol_multiplier)
            # Add directional component that fades over time
            spike = spike_direction * spike_magnitude * (1 - i / duration_ticks)

            if i == 0:
                new_prices[index + i] = prices[index] * (1 + noise + spike)
            else:
                new_prices[index + i] = new_prices[index + i - 1] * (1 + noise + (spike/10))

        # Re-align remaining prices
        if index + duration_ticks < len(prices):
            remaining_shift = new_prices[index + duration_ticks - 1] / prices[index + duration_ticks - 1]
            new_prices[index + duration_ticks:] *= remaining_shift

        return new_prices

    def create_ohlcv(
        self,
        prices: np.ndarray,
        ticks_per_bar: int,
        start_time: datetime = datetime(2024, 1, 1)
    ) -> pd.DataFrame:
        """
        Aggregate tick prices into OHLCV bars.
        """
        n_bars = len(prices) // ticks_per_bar
        ohlcv_data = []

        for i in range(n_bars):
            segment = prices[i * ticks_per_bar : (i + 1) * ticks_per_bar]
            bar_time = start_time + timedelta(seconds=i * ticks_per_bar)

            bar = {
                "timestamp": bar_time,
                "open": segment[0],
                "high": np.max(segment),
                "low": np.min(segment),
                "close": segment[-1],
                "volume": np.random.randint(100, 1000)
            }
            ohlcv_data.append(bar)

        df = pd.DataFrame(ohlcv_data)
        if not df.empty:
            df.set_index("timestamp", inplace=True)
        return df

    def generate_multi_timeframe(
        self,
        total_ticks: int,
        timeframe_map: Dict[str, int],
        regime: MarketRegime = MarketRegime.TRENDING,
        start_price: float = 2000.0,
        start_time: datetime = datetime(2024, 1, 1)
    ) -> Dict[str, pd.DataFrame]:
        """
        Generate synchronized OHLCV data for multiple timeframes.

        Args:
            total_ticks: Total number of base ticks to generate.
            timeframe_map: Dict mapping timeframe name to ticks per bar (e.g., {"M1": 60, "M5": 300}).
            regime: Market regime for the base price series.
        """
        base_prices = self.apply_regime(total_ticks, regime, start_price)

        # Inject some random events to make it interesting
        # 1. A news event at 25%
        base_prices = self.add_news_event(base_prices, total_ticks // 4)
        # 2. A gap at 50%
        base_prices = self.add_gap(base_prices, total_ticks // 2, gap_pct=0.005)
        # 3. A flash crash at 75%
        base_prices = self.add_flash_crash(base_prices, 3 * total_ticks // 4)

        results = {}
        for tf_name, ticks_per_bar in timeframe_map.items():
            results[tf_name] = self.create_ohlcv(base_prices, ticks_per_bar, start_time)

        return results


if __name__ == "__main__":
    # Example usage
    generator = SyntheticDataGenerator(seed=42)

    # Generate 1 hour of data at 1 tick/sec (3600 ticks)
    tf_configs = {
        "M1": 60,
        "M5": 300,
        "M15": 900
    }

    data = generator.generate_multi_timeframe(3600, tf_configs, MarketRegime.TRENDING)

    for tf, df in data.items():
        print(f"\n--- {tf} Data (First 5 bars) ---")
        print(df.head())
