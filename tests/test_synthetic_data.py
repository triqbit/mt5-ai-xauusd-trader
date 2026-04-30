import numpy as np
import pandas as pd

from src.utils.synthetic_data import ScenarioGenerator


def test_determinism():
    gen1 = ScenarioGenerator(seed=42)
    gen2 = ScenarioGenerator(seed=42)

    df1 = gen1.generate_trending_market(n_bars=10)
    df2 = gen2.generate_trending_market(n_bars=10)

    pd.testing.assert_frame_equal(df1, df2)

def test_trending_bullish():
    gen = ScenarioGenerator()
    df = gen.generate_trending_market(n_bars=50, start_price=2000, trend=1.0)

    assert len(df) == 50
    assert df["close"].iloc[-1] > df["close"].iloc[0]
    assert (df["high"] >= df["low"]).all()
    assert (df["high"] >= df[["open", "close"]].max(axis=1)).all()

def test_trending_bearish():
    gen = ScenarioGenerator()
    df = gen.generate_trending_market(n_bars=50, start_price=2000, trend=-1.0)

    assert df["close"].iloc[-1] < df["close"].iloc[0]

def test_ranging_market():
    gen = ScenarioGenerator()
    df = gen.generate_ranging_market(n_bars=100, center_price=2000, range_width=10)

    assert df["close"].max() <= 2010 # Approx, since volatility adds a bit to high/low but close is bounded
    assert df["close"].min() >= 1990
    assert (df["high"] >= df["low"]).all()

def test_malformed_data():
    gen = ScenarioGenerator()
    df = gen.generate_malformed_data()

    # Low > High at index 0
    assert df.at[0, "low"] > df.at[0, "high"]
    # Negative price at index 1
    assert df.at[1, "close"] < 0
    # Zero volume at index 2
    assert df.at[2, "tick_volume"] == 0
    # NaN at index 3
    assert np.isnan(df.at[3, "close"])

def test_gapping_market():
    gen = ScenarioGenerator(seed=123)
    df = gen.generate_gapping_market(n_bars=100, gap_frequency=0.2, gap_size=50)

    # Check for gaps between close and next open
    gaps = (df["open"] - df["close"].shift(1)).dropna()
    assert (gaps.abs() > 10).any()
