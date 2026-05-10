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
    assert df.loc[0, "high"] < df.loc[0, "low"]

    # Negative price at index 1
    assert df.loc[1, "close"] < 0

    # NaN at index 2
    assert np.isnan(df.loc[2, "open"])

    # Zero volume at index 3
    assert df.loc[3, "tick_volume"] == 0

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


def test_noisy_regime():
    gen = ScenarioGenerator(seed=42)
    vol = 0.001
    df = gen.generate(n_steps=200, regime="noisy", volatility=vol)
    # Check for extreme spikes (returns > 10 * vol)
    returns = df["close"].pct_change().dropna()
    spikes = returns[returns.abs() > vol * 10]
    assert not spikes.empty


def test_missing_data_regime():
    gen = ScenarioGenerator(seed=42)
    df = gen.generate(n_steps=100, regime="missing_data")
    # Check that we have NaNs in at least one expected column
    has_nans = False
    for col in ["open", "high", "low", "close", "tick_volume"]:
        if df[col].isna().any():
            has_nans = True
            break
    assert has_nans
