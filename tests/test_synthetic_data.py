"""
Unit tests for the ScenarioGenerator.
"""

import pytest
import numpy as np
import pandas as pd
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


def test_invalid_regime():
    gen = ScenarioGenerator()
    with pytest.raises(ValueError, match="Unknown regime"):
        gen.generate(regime="invalid")
