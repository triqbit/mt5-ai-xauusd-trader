import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

def generate_synthetic_ohlcv(
    symbol: str = "XAUUSD",
    n_bars: int = 1000,
    timeframe: str = "M5",
    start_price: float = 2000.0,
    volatility: float = 0.001,
    seed: int = 42
) -> pd.DataFrame:
    """
    Generates synthetic OHLCV data using Geometric Brownian Motion.
    """
    np.random.seed(seed)

    # Timeframe to minutes
    tf_map = {
        "M1": 1, "M5": 5, "M15": 15, "M30": 30,
        "H1": 60, "H4": 240, "D1": 1440
    }
    minutes = tf_map.get(timeframe, 5)

    # Generate log returns
    returns = np.random.normal(0, volatility, n_bars)
    price_path = start_price * np.exp(np.cumsum(returns))

    # Create OHLC from price path
    # To make it look like OHLC, we add some noise to the path for high/low
    high = price_path * (1 + np.abs(np.random.normal(0, volatility * 0.5, n_bars)))
    low = price_path * (1 - np.abs(np.random.normal(0, volatility * 0.5, n_bars)))
    open_p = np.zeros_like(price_path)
    open_p[0] = start_price
    open_p[1:] = price_path[:-1]

    # Ensure high and low are actually high and low
    high = np.maximum(high, np.maximum(open_p, price_path))
    low = np.minimum(low, np.minimum(open_p, price_path))

    # Timestamps
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=minutes * n_bars)
    timestamps = [start_time + timedelta(minutes=minutes * i) for i in range(n_bars)]

    df = pd.DataFrame({
        "time": timestamps,
        "open": open_p,
        "high": high,
        "low": low,
        "close": price_path,
        "tick_volume": np.random.randint(100, 1000, n_bars).astype(float)
    })

    return df
