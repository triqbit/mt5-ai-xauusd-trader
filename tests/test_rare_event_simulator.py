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
    assert all(col in df.columns for col in ["open", "high", "low", "close", "tick_volume", "spread"])
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

    # Check volume spike
    crash_vol = df["tick_volume"].iloc[result.start_index : result.start_index + 10].mean()
    normal_vol = df["tick_volume"].iloc[:result.start_index].mean()
    assert crash_vol > normal_vol * 2

    # Verify peak impact calculation (it should be negative for a crash)
    assert result.peak_impact_pct < 0


def test_liquidity_vacuum_behavior(simulator):
    config = RareEventConfig(event_type=RareEventType.LIQUIDITY_VACUUM, n_steps=300)
    df, result = simulator.generate_scenario(config)

    # Should have some very low volume bars
    vacuum_df = df.iloc[result.start_index : result.end_index]
    assert (vacuum_df["tick_volume"] < 10).all()

    # Spreads should be high
    normal_spread = df["spread"].iloc[:result.start_index].mean()
    vacuum_spread = vacuum_df["spread"].mean()
    assert vacuum_spread > normal_spread * 3

    # Volatility in vacuum should be higher
    returns = df["close"].pct_change().dropna()
    vacuum_returns = returns.iloc[result.start_index : result.end_index]
    normal_returns = returns.iloc[:result.start_index]
    assert vacuum_returns.std() > normal_returns.std() * 5

    # Check high/low expansion in vacuum
    vacuum_range = (df["high"] - df["low"]).iloc[result.start_index : result.end_index].mean()
    normal_range = (df["high"] - df["low"]).iloc[:result.start_index].mean()
    assert vacuum_range > normal_range * 2


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


def test_multi_session_dislocation(simulator):
    config = RareEventConfig(event_type=RareEventType.MULTI_SESSION_DISLOCATION, n_steps=600)
    df, result = simulator.generate_scenario(config)

    assert len(df) == 600
    assert result.event_type == RareEventType.MULTI_SESSION_DISLOCATION

    # Check that different sessions have different volatilities
    returns = df["close"].pct_change().dropna()
    session_size = 600 // 4
    vol1 = returns.iloc[:session_size].std()
    vol2 = returns.iloc[session_size:2*session_size].std()
    vol4 = returns.iloc[3*session_size:].std()

    assert vol2 > vol1 * 2
    assert vol4 > vol2


def test_generate_suite(simulator):
    suite = simulator.generate_suite(n_steps=200, magnitude=1.5, seed=100)

    assert len(suite) == len(RareEventType)
    for event_type in RareEventType:
        assert event_type.value in suite
        df, result = suite[event_type.value]
        assert len(df) == 200
        assert result.config.event_magnitude == 1.5


def test_custom_bars_per_day(simulator):
    # Test M1 frequency (1440 bars per day)
    config = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=100, bars_per_day=1440)
    df, result = simulator.generate_scenario(config)

    # Frequency should be 60 seconds (1 minute)
    freq = (df.index[1] - df.index[0]).total_seconds()
    assert freq == 60

    # Test H1 frequency (24 bars per day)
    config_h1 = RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=100, bars_per_day=24)
    df_h1, result_h1 = simulator.generate_scenario(config_h1)

    freq_h1 = (df_h1.index[1] - df_h1.index[0]).total_seconds()
    assert freq_h1 == 3600
