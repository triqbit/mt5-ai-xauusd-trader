"""
Tests for RareEventSimulator.
"""

import numpy as np
import pandas as pd
import pytest
from src.research.rare_event_simulator import (
    RareEventConfig,
    RareEventSimulator,
    RareEventType,
)


@pytest.fixture
def simulator():
    return RareEventSimulator(seed=42)


def test_simulator_basic_structure(simulator):
    config = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=200)
    df = simulator.generate_scenario(config)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 200
    assert all(col in df.columns for col in ["open", "high", "low", "close", "tick_volume"])
    assert not df.isnull().values.any()


def test_ohlc_consistency(simulator):
    for event_type in RareEventType:
        config = RareEventConfig(event_type=event_type, n_steps=200)
        df = simulator.generate_scenario(config)

        assert (df["high"] >= df["open"]).all()
        assert (df["high"] >= df["close"]).all()
        assert (df["low"] <= df["open"]).all()
        assert (df["low"] <= df["close"]).all()
        assert (df["high"] >= df["low"]).all()


def test_reproducibility(simulator):
    config = RareEventConfig(event_type=RareEventType.GOLD_GAP, n_steps=100, seed=123)
    df1 = simulator.generate_scenario(config)

    # Re-run with same seed
    df2 = simulator.generate_scenario(config)

    pd.testing.assert_frame_equal(df1, df2)


def test_flash_crash_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=300, event_magnitude=2.0)
    df = simulator.generate_scenario(config)

    # Should see a significant drop compared to start
    min_price = df["close"].min()
    assert min_price < config.start_price * 0.95  # At least 5% drop given magnitude 2.0


def test_liquidity_vacuum_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.LIQUIDITY_VACUUM, n_steps=300)
    df = simulator.generate_scenario(config)

    # Should have some very low volume bars
    assert (df["tick_volume"] < 50).any()


def test_gold_gap_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.GOLD_GAP, n_steps=200, event_magnitude=1.0)
    df = simulator.generate_scenario(config)

    # Calculate returns to find the gap
    returns = df["close"].pct_change().dropna()
    assert (returns.abs() > 0.01).any()  # 1% gap expected


def test_violent_reversal_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.VIOLENT_REVERSAL, n_steps=400)
    df = simulator.generate_scenario(config)

    # Should see price go up then down significantly
    peak_idx = df["close"].idxmax()
    end_price = df["close"].iloc[-1]
    peak_price = df["close"].loc[peak_idx]

    assert peak_price > config.start_price
    assert end_price < peak_price


def test_vol_cluster_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.VOL_CLUSTER, n_steps=500)
    df = simulator.generate_scenario(config)

    returns = df["close"].pct_change().dropna()
    # Volatility should not be constant
    rolling_std = returns.rolling(20).std().dropna()
    assert rolling_std.max() > rolling_std.min() * 5
