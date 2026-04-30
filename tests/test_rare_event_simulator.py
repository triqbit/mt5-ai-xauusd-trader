"""
Tests for RareEventSimulator.
"""

import pytest
import pandas as pd
import numpy as np
from src.research.rare_event_simulator import RareEventSimulator

@pytest.fixture
def simulator():
    return RareEventSimulator(base_price=2000.0, timeframe="M5")

def test_flash_crash(simulator):
    n_bars = 100
    df = simulator.generate_flash_crash(n_bars=n_bars, magnitude=0.05)

    assert len(df) == n_bars
    assert all(col in df.columns for col in ["timestamp", "open", "high", "low", "close", "tick_volume"])
    # Price should drop significantly
    assert df["close"].min() <= 2000.0 * 0.96 # At least 4% drop (magnitude is 0.05)
    # Check OHLC consistency
    assert (df["high"] >= df["low"]).all()
    assert (df["high"] >= df["open"]).all()
    assert (df["high"] >= df["close"]).all()
    assert (df["low"] <= df["open"]).all()
    assert (df["low"] <= df["close"]).all()

def test_gold_gap(simulator):
    n_bars = 50
    gap_size = 0.02
    df = simulator.generate_gold_gap(n_bars=n_bars, gap_size=gap_size)

    assert len(df) == n_bars
    # Find the gap
    gap_idx = n_bars // 2
    # Open of gap bar should be significantly higher than previous close
    price_diff = df.loc[gap_idx, "open"] - df.loc[gap_idx - 1, "close"]
    assert price_diff >= (2000.0 * gap_size * 0.99)

def test_liquidity_vacuum(simulator):
    n_bars = 100
    df = simulator.generate_liquidity_vacuum(n_bars=n_bars)

    assert len(df) == n_bars
    # Volume should be low
    assert df["tick_volume"].mean() < 50 # Base poisson 100 * 0.2 = 20

def test_violent_reversal(simulator):
    n_bars = 100
    df = simulator.generate_violent_reversal(n_bars=n_bars, magnitude=0.03)

    assert len(df) == n_bars
    mid = n_bars // 2
    # Should drop then rise
    assert df.loc[mid-1, "close"] < 2000.0
    assert df.loc[n_bars-1, "close"] > df.loc[mid-1, "close"]

def test_generic_scenario_generation(simulator):
    df = simulator.generate_scenario("flash_crash", n_bars=50)
    assert len(df) == 50

    with pytest.raises(ValueError):
        simulator.generate_scenario("unknown_event")
