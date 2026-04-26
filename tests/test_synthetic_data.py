"""
Tests for Synthetic Data Generator
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from src.utils.synthetic_data import SyntheticDataGenerator, MarketRegime


@pytest.fixture
def generator():
    return SyntheticDataGenerator(seed=42)


def test_generate_base_prices(generator):
    n_ticks = 100
    start_price = 2000.0
    prices = generator.generate_base_prices(n_ticks, start_price)

    assert len(prices) == n_ticks
    assert prices[0] == start_price
    assert np.all(prices > 0)


def test_market_regimes(generator):
    n_ticks = 1000

    for regime in MarketRegime:
        prices = generator.apply_regime(n_ticks, regime)
        assert len(prices) == n_ticks
        assert np.all(prices > 0)


def test_flash_crash(generator):
    prices = np.full(100, 2000.0)
    crash_index = 50
    depth_pct = 0.1
    duration = 20

    crashed_prices = generator.add_flash_crash(prices, crash_index, depth_pct, duration)

    assert len(crashed_prices) == 100
    # Price at half duration should be around start * (1 - depth)
    assert crashed_prices[crash_index + 9] < 2000.0
    assert crashed_prices[crash_index + 10] < 2000.0
    # It should recover towards the end of duration
    assert crashed_prices[crash_index + 19] > crashed_prices[crash_index + 10]


def test_gap(generator):
    prices = np.full(100, 2000.0)
    gap_index = 50
    gap_pct = 0.05

    gapped_prices = generator.add_gap(prices, gap_index, gap_pct)

    assert len(gapped_prices) == 100
    assert gapped_prices[49] == 2000.0
    assert abs(gapped_prices[50] - 2000.0) > 0


def test_create_ohlcv(generator):
    prices = generator.generate_base_prices(600)
    df = generator.create_ohlcv(prices, ticks_per_bar=60)

    assert len(df) == 10
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    for i in range(len(df)):
        assert df.iloc[i]["high"] >= df.iloc[i]["open"]
        assert df.iloc[i]["high"] >= df.iloc[i]["close"]
        assert df.iloc[i]["low"] <= df.iloc[i]["open"]
        assert df.iloc[i]["low"] <= df.iloc[i]["close"]


def test_multi_timeframe_synchronization(generator):
    tf_configs = {"M1": 60, "M5": 300}
    total_ticks = 600
    data = generator.generate_multi_timeframe(total_ticks, tf_configs)

    assert "M1" in data
    assert "M5" in data
    assert len(data["M1"]) == 10
    assert len(data["M5"]) == 2

    # Check if they are synchronized (start at the same time)
    assert data["M1"].index[0] == data["M5"].index[0]
    # Check if the high/low of M5 covers M1
    assert data["M5"].iloc[0]["high"] >= data["M1"].iloc[0:5]["high"].max()
    assert data["M5"].iloc[0]["low"] <= data["M1"].iloc[0:5]["low"].min()
