"""
Unit tests for the ScenarioGenerator.
"""
import numpy as np
import pandas as pd
import pytest

from src.utils.synthetic_data import ScenarioGenerator


def test_determinism():
    gen1 = ScenarioGenerator(seed=42)
    gen2 = ScenarioGenerator(seed=42)

    df1 = gen1.generate(n_steps=50, regime="trending")
    df2 = gen2.generate(n_steps=50, regime="trending")

    pd.testing.assert_frame_equal(df1, df2)

def test_trending_regime():
    gen = ScenarioGenerator(seed=42)
    # Bullish trend
    df = gen.generate(n_steps=100, regime="trending", trend_strength=0.01)
    assert df["close"].iloc[-1] > df["close"].iloc[0]

    # Bearish trend
    df_bear = gen.generate(n_steps=100, regime="trending", trend_strength=-0.01)
    assert df_bear["close"].iloc[-1] < df_bear["close"].iloc[0]

def test_ohlc_validity():
    gen = ScenarioGenerator(seed=42)
    df = gen.generate(n_steps=100, regime="ranging")

    assert (df["high"] >= df["low"]).all()
    assert (df["high"] >= df["open"]).all()
    assert (df["high"] >= df["close"]).all()
    assert (df["low"] <= df["open"]).all()
    assert (df["low"] <= df["close"]).all()

def test_malformed_regime():
    gen = ScenarioGenerator(seed=42)
    df = gen.generate(n_steps=10, regime="malformed")

    # High < Low at index 0
    assert df.iloc[0]["high"] < df.iloc[0]["low"]

    # Negative price at index 1
    assert df.iloc[1]["close"] < 0

    # NaN at index 2
    assert np.isnan(df.iloc[2]["open"])

    # Zero volume at index 3
    assert df.iloc[3]["tick_volume"] == 0

def test_whipsaw_regime():
    gen = ScenarioGenerator(seed=42)
    df = gen.generate(n_steps=100, regime="whipsaw")
    # Midpoint should show a spike then drop
    # mid = 50. returns[45:50] = 0.01, returns[50:55] = -0.015
    # Price at index 50 should be higher than at 45
    # Price at index 55 should be lower than at 50
    assert df["close"].iloc[50] > df["close"].iloc[45]
    assert df["close"].iloc[55] < df["close"].iloc[50]

def test_stale_regime():
    gen = ScenarioGenerator(seed=42)
    df = gen.generate(n_steps=50, regime="stale")
    # Prices should be mostly constant (only minor noise in OHLC if any)
    # Actually _generate_base adds noise to open/high/low but close is exact
    assert (df["close"].diff().dropna() == 0).all()

def test_invalid_regime():
    gen = ScenarioGenerator()
    with pytest.raises(ValueError, match="Unknown regime"):
        gen.generate(regime="invalid")

def test_flash_crash_regime():
    gen = ScenarioGenerator(seed=42)
    df = gen.generate(n_steps=100, regime="flash_crash")
    # Midpoint should show a sharp drop
    # returns[50:55] = -0.04
    # Compare price before crash (49) and after crash (54)
    assert df["close"].iloc[54] < df["close"].iloc[49] * 0.85
    # Partial recovery follows
    # returns[55:60] = 0.02
    assert df["close"].iloc[59] > df["close"].iloc[54]

def test_regime_shift_regime():
    gen = ScenarioGenerator(seed=42)
    df = gen.generate(n_steps=100, regime="regime_shift", volatility=0.001)
    # First half should be less volatile than second half
    first_half_vol = df["close"].iloc[:50].pct_change().std()
    second_half_vol = df["close"].iloc[50:].pct_change().std()
    assert second_half_vol > first_half_vol * 2

def test_generate_with_holes():
    gen = ScenarioGenerator(seed=42)
    df = gen.generate_with_holes(n_steps=100, hole_pct=0.2)

    # Check that holes (NaNs) were injected
    assert df.isnull().any().any()
    # The last row should NEVER be a hole
    assert not df.iloc[-1].isnull().any()

def test_generate_stale_feed():
    gen = ScenarioGenerator(seed=42)
    stale_len = 5
    n_steps = 100
    df = gen.generate_stale_feed(n_steps=n_steps, stale_len=stale_len)

    # The last 5 bars should be identical to the 6th from last bar
    # Check closing prices specifically
    last_bars = df["close"].iloc[-stale_len:]
    base_bar_val = df["close"].iloc[n_steps - stale_len - 1]
    assert (last_bars == base_bar_val).all()
