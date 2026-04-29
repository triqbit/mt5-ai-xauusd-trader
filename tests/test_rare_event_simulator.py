"""
Tests for RareEventSimulator.
"""

import pytest
import pandas as pd
from src.research.rare_event_simulator import RareEventSimulator, ScenarioConfig, ScenarioType


def test_scenario_config_validation():
    """Test that ScenarioConfig validates its inputs."""
    with pytest.raises(ValueError):
        ScenarioConfig(scenario_type=ScenarioType.FLASH_CRASH, duration=3)

    config = ScenarioConfig(scenario_type=ScenarioType.FLASH_CRASH, duration=10)
    assert config.duration == 10


@pytest.mark.parametrize("scenario_type", list(ScenarioType))
def test_all_scenarios_generate_ohlcv(scenario_type):
    """Test that all scenario types generate a valid OHLCV DataFrame."""
    config = ScenarioConfig(
        scenario_type=scenario_type,
        duration=50,
        start_price=2000.0,
        seed=42
    )
    simulator = RareEventSimulator(config)
    df = simulator.generate()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 50
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]

    # Consistency checks
    assert (df["high"] >= df["open"]).all()
    assert (df["high"] >= df["close"]).all()
    assert (df["low"] <= df["open"]).all()
    assert (df["low"] <= df["close"]).all()


def test_flash_crash_behavior():
    """Test that FLASH_CRASH actually drops the price."""
    config = ScenarioConfig(
        scenario_type=ScenarioType.FLASH_CRASH,
        duration=100,
        start_price=2300.0,
        severity=2.0,
        seed=42
    )
    simulator = RareEventSimulator(config)
    df = simulator.generate()

    # It should drop significantly below start price at some point
    assert df["low"].min() < 2300.0 * 0.9  # At least 10% drop with severity 2.0


def test_gold_gap_behavior():
    """Test that GOLD_GAP creates a price jump."""
    config = ScenarioConfig(
        scenario_type=ScenarioType.GOLD_GAP,
        duration=100,
        start_price=2300.0,
        severity=1.0,
        seed=42
    )
    simulator = RareEventSimulator(config)
    df = simulator.generate()

    # Check for a large single-step change (gap)
    # df.close.pct_change() should have at least one entry around 2%
    pct_changes = df["close"].pct_change().abs()
    assert pct_changes.max() >= 0.015  # Expecting ~2% gap


def test_reproducibility():
    """Test that seed works."""
    config1 = ScenarioConfig(
        scenario_type=ScenarioType.VOLATILITY_CLUSTER,
        duration=50,
        seed=123
    )
    config2 = ScenarioConfig(
        scenario_type=ScenarioType.VOLATILITY_CLUSTER,
        duration=50,
        seed=123
    )

    df1 = RareEventSimulator(config1).generate()
    df2 = RareEventSimulator(config2).generate()

    pd.testing.assert_frame_equal(df1, df2)
