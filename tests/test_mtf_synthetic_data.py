"""
Tests for MTF consistency, price continuity, and fault injection in ScenarioGenerator.
"""

import numpy as np
import pytest

from src.utils.synthetic_data import ScenarioGenerator


@pytest.fixture
def gen():
    return ScenarioGenerator(seed=42)


def test_price_continuity(gen):
    """Verifies that Open[i] == Close[i-1] for generated data."""
    df = gen.generate(n_steps=100, regime="trending")

    opens = df["open"].values[1:]
    closes = df["close"].values[:-1]

    np.testing.assert_array_almost_equal(opens, closes)


def test_ohlc_realism(gen):
    """Verifies that High is the highest and Low is the lowest in every bar."""
    df = gen.generate(n_steps=100, regime="volatile")

    assert (df["high"] >= df["open"]).all()
    assert (df["high"] >= df["close"]).all()
    assert (df["low"] <= df["open"]).all()
    assert (df["low"] <= df["close"]).all()
    assert (df["high"] >= df["low"]).all()


def test_mtf_consistency(gen):
    """Verifies that M5 data correctly aggregates M1 data."""
    mtf_data = gen.generate_multi_timeframe(
        n_steps_base=100, base_freq="1min", timeframes=["M5"], regime="trending"
    )

    df_m1 = mtf_data["1min"]
    df_m5 = mtf_data["M5"]

    # Check first M5 bar
    first_m5_bar = df_m5.iloc[0]
    corresponding_m1_bars = df_m1.iloc[0:5]

    assert first_m5_bar["open"] == corresponding_m1_bars.iloc[0]["open"]
    assert first_m5_bar["close"] == corresponding_m1_bars.iloc[-1]["close"]
    assert first_m5_bar["high"] == corresponding_m1_bars["high"].max()
    assert first_m5_bar["low"] == corresponding_m1_bars["low"].min()
    assert first_m5_bar["tick_volume"] == corresponding_m1_bars["tick_volume"].sum()


def test_fault_injection_stale(gen):
    """Verifies stale data injection (repeated bars)."""
    df = gen.generate(n_steps=50, regime="ranging")
    # Inject stale bars with high probability to ensure some hits
    df_faulty = gen.inject_faults(df, fault_type="stale", prob=0.2)

    # Check for identical consecutive bars
    is_stale = (df_faulty.diff().dropna() == 0).all(axis=1)
    assert is_stale.any()


def test_fault_injection_outliers(gen):
    """Verifies outlier injection (extreme price spikes)."""
    df = gen.generate(n_steps=50, regime="ranging")
    df_faulty = gen.inject_faults(df, fault_type="outliers", prob=0.1)

    # Compare with original
    diff = df_faulty["close"] != df["close"]
    assert diff.any()

    # Check that outliers are significant (around 10%)
    faulty_indices = diff[diff].index
    for idx in faulty_indices:
        ratio = df_faulty.loc[idx, "close"] / df.loc[idx, "close"]
        assert abs(ratio - 1.0) > 0.05


def test_fault_injection_zero_volume(gen):
    """Verifies zero volume injection."""
    df = gen.generate(n_steps=50, regime="ranging")
    df_faulty = gen.inject_faults(df, fault_type="zero_volume", prob=0.2)

    assert (df_faulty["tick_volume"] == 0).any()


def test_fault_injection_gaps(gen):
    """Verifies gap injection (broken price continuity)."""
    df = gen.generate(n_steps=50, regime="trending")
    df_faulty = gen.inject_faults(df, fault_type="gaps", prob=0.1)

    # Check for continuity breaks: Open[i] != Close[i-1]
    opens = df_faulty["open"].values[1:]
    closes = df_faulty["close"].values[:-1]

    breaks = opens != closes
    assert breaks.any()
