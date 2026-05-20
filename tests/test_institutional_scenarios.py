"""
Tests for Institutional Flow Scenario Generator.
"""
import pytest

from src.utils.synthetic_data import InstitutionalFlowGenerator


@pytest.fixture
def institutional_builder():
    return InstitutionalFlowGenerator(seed=42)

def test_stop_hunting_behavior(institutional_builder):
    n_steps = 100
    df = institutional_builder.stop_hunting(n_steps=n_steps)

    assert len(df) == n_steps
    # Midpoint should have steady prices
    # Then a sharp dip and reversal
    mid = n_steps // 2
    dip_start = mid - 1  # Last bar of ranging
    dip_bottom = mid + 4  # Bottom of the 5-bar dip
    dip_recovery = mid + 9  # End of 5-bar recovery

    # Check for sharp dip (expect ~2.5% drop)
    assert df["close"].iloc[dip_bottom] < df["close"].iloc[dip_start] * 0.98
    # Check for rapid recovery
    assert df["close"].iloc[dip_recovery] > df["close"].iloc[dip_bottom] * 1.02

def test_iceberg_absorption_behavior(institutional_builder):
    n_steps = 100
    start_price = 2300.0
    df = institutional_builder.iceberg_absorption(n_steps=n_steps, start_price=start_price)

    assert len(df) == n_steps
    mid = n_steps // 2

    # 1. Price should trend up to the iceberg level (approx 1.01 * start_price)
    iceberg_level = start_price * 1.01
    assert df["close"].iloc[mid-1] > start_price

    # 2. Absorption phase should have multiple attempts but fail to sustain break above level
    # Since we capped it in logic, max price should be close to iceberg_level
    # but might briefly spike above in OHLC noise (though _generate_base adds noise)
    # The 'close' prices should be strictly controlled
    absorption_closes = df["close"].iloc[mid:]
    # High volume should be present in second half
    vol_first_half = df["tick_volume"].iloc[:mid].mean()
    vol_second_half = df["tick_volume"].iloc[mid:].mean()

    assert vol_second_half > vol_first_half * 3
    # Price progress should be stalled
    assert (absorption_closes <= iceberg_level * 1.001).all()

def test_trend_exhaustion_behavior(institutional_builder):
    n_steps = 150
    df = institutional_builder.trend_exhaustion(n_steps=n_steps)

    assert len(df) == n_steps
    one_third = n_steps // 3

    # 1. First 1/3 should be steady trend
    ret1 = df["close"].iloc[one_third] / df["close"].iloc[0] - 1
    assert ret1 > 0

    # 2. Second 1/3 should be parabolic (sharper)
    ret2 = df["close"].iloc[2*one_third] / df["close"].iloc[one_third] - 1
    assert ret2 > ret1

    # 3. Final 1/3 should be sharp collapse
    ret3 = df["close"].iloc[-1] / df["close"].iloc[2*one_third] - 1
    assert ret3 < -0.05
