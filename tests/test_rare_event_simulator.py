"""
Tests for RareEventSimulator.
"""

import pandas as pd
import numpy as np
import pytest

from src.research.rare_event_simulator import (
    RareEventConfig,
    RareEventSimulator,
    RareEventType,
    RareEventResult,
)


@pytest.fixture
def simulator():
    return RareEventSimulator(seed=42)


def test_simulator_basic_structure(simulator):
    config = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=200)
    df, result = simulator.generate_scenario(config)

    assert isinstance(df, pd.DataFrame)
    assert isinstance(result, RareEventResult)
    assert len(df) == 200
    assert all(col in df.columns for col in ["open", "high", "low", "close", "tick_volume"])
    assert not df.isnull().values.any()


def test_ohlc_consistency(simulator):
    for event_type in RareEventType:
        config = RareEventConfig(event_type=event_type, n_steps=200)
        df, _ = simulator.generate_scenario(config)

        assert (df["high"] >= df["open"]).all()
        assert (df["high"] >= df["close"]).all()
        assert (df["low"] <= df["open"]).all()
        assert (df["low"] <= df["close"]).all()
        assert (df["high"] >= df["low"]).all()

        # Continuity check (except for gaps)
        if event_type != RareEventType.GOLD_GAP:
            # We check if open is very close to previous close
            # In our implementation it should be exact
            opens = df["open"].values[1:]
            prev_closes = df["close"].values[:-1]
            np.testing.assert_allclose(opens, prev_closes, atol=1e-8)


def test_reproducibility(simulator):
    config = RareEventConfig(event_type=RareEventType.GOLD_GAP, n_steps=100, seed=123)
    df1, res1 = simulator.generate_scenario(config)

    # Re-run with same seed
    df2, res2 = simulator.generate_scenario(config)

    pd.testing.assert_frame_equal(df1, df2)
    assert res1 == res2


def test_flash_crash_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=300, event_magnitude=2.0, recovery_factor=0.8)
    df, result = simulator.generate_scenario(config)

    assert result.peak_impact_pct < -0.05
    assert result.recovery_attained > 0.5

    # Check that volume is still reasonable
    assert df["tick_volume"].mean() > 400


def test_liquidity_vacuum_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.LIQUIDITY_VACUUM, n_steps=300)
    df, result = simulator.generate_scenario(config)

    # Should have some very low volume bars
    vacuum_df = df.iloc[result.start_index : result.end_index]
    assert (vacuum_df["tick_volume"] < 20).all()

    # Volatility in vacuum should be higher
    returns = df["close"].pct_change().dropna()
    vacuum_returns = returns.iloc[result.start_index : result.end_index]
    normal_returns = returns.iloc[:result.start_index]
    assert vacuum_returns.std() > normal_returns.std() * 5


def test_gold_gap_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.GOLD_GAP, n_steps=200, event_magnitude=1.0)
    df, result = simulator.generate_scenario(config)

    # Calculate gap
    gap_idx = result.start_index
    gap = df["open"].iloc[gap_idx] - df["close"].iloc[gap_idx - 1]
    assert abs(gap) > 10 # Assuming start_price 2300 and 2% gap
    assert abs(result.peak_impact_pct) > 0.01


def test_violent_reversal_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.VIOLENT_REVERSAL, n_steps=400)
    df, result = simulator.generate_scenario(config)

    # Reversal index
    rev_idx = result.start_index

    # Prices before reversal should be generally increasing (due to trend injection)
    # Price after reversal should crash
    pre_rev_price = df["close"].iloc[rev_idx]
    post_rev_price = df["close"].iloc[result.end_index]

    assert pre_rev_price > config.start_price
    assert post_rev_price < pre_rev_price


def test_dislocation_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.DISLOCATION, n_steps=500, event_magnitude=1.0)
    df, result = simulator.generate_scenario(config)

    returns = df["close"].pct_change().dropna()
    pre_dis_returns = returns.iloc[:result.start_index-1]
    post_dis_returns = returns.iloc[result.start_index + 1:]

    pre_dis_vol = pre_dis_returns.std()
    post_dis_vol = post_dis_returns.std()

    assert post_dis_vol > pre_dis_vol * 2


def test_vol_cluster_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.VOL_CLUSTER, n_steps=500)
    df, result = simulator.generate_scenario(config)

    returns = df["close"].pct_change().dropna()
    # Volatility should not be constant
    rolling_std = returns.rolling(20).std().dropna()
    assert rolling_std.max() > rolling_std.min() * 3
