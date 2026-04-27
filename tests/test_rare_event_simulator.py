"""
Tests for RareEventSimulator.
"""

import numpy as np
import pandas as pd
import pytest

from src.research.rare_event_simulator import RareEventSimulator, ScenarioConfig, ScenarioType


@pytest.fixture
def base_data():
    """Create a dummy OHLCV DataFrame."""
    dates = pd.date_range("2023-01-01", periods=100, freq="h")
    data = {
        "Open": np.linspace(2000, 2010, 100),
        "High": np.linspace(2005, 2015, 100),
        "Low": np.linspace(1995, 2005, 100),
        "Close": np.linspace(2000, 2010, 100),
        "Volume": np.random.randint(100, 1000, 100).astype(float)
    }
    return pd.DataFrame(data, index=dates)


def test_flash_crash(base_data):
    simulator = RareEventSimulator(base_data)
    config = ScenarioConfig(
        scenario_type=ScenarioType.FLASH_CRASH,
        duration_bars=10,
        magnitude=0.05,  # 5% drop
        recovery_rate=0.5
    )

    start_idx = 50
    result = simulator.apply_scenario(config, start_index=start_idx)

    # Check that prices are lower after start
    assert result.iloc[start_idx + 3]["Close"] < base_data.iloc[start_idx + 3]["Close"]
    # Check volume increase
    assert result.iloc[start_idx + 3]["Volume"] > base_data.iloc[start_idx + 3]["Volume"]


def test_liquidity_vacuum(base_data):
    simulator = RareEventSimulator(base_data)
    config = ScenarioConfig(
        scenario_type=ScenarioType.LIQUIDITY_VACUUM,
        duration_bars=10,
        magnitude=0.01
    )

    start_idx = 50
    result = simulator.apply_scenario(config, start_index=start_idx)

    # Check volume decrease
    assert result.iloc[start_idx]["Volume"] < base_data.iloc[start_idx]["Volume"]
    # Check high-low range increase
    base_range = base_data.iloc[start_idx]["High"] - base_data.iloc[start_idx]["Low"]
    result_range = result.iloc[start_idx]["High"] - result.iloc[start_idx]["Low"]
    assert result_range > base_range


def test_gold_gap_move(base_data):
    simulator = RareEventSimulator(base_data)
    config = ScenarioConfig(
        scenario_type=ScenarioType.GOLD_GAP_MOVE,
        duration_bars=1,
        magnitude=0.02
    )

    start_idx = 50
    result = simulator.apply_scenario(config, start_index=start_idx)

    # Check persistent gap
    diff = abs(result.iloc[start_idx]["Close"] - base_data.iloc[start_idx]["Close"])
    assert diff > 0
    # Should persist to the end
    last_diff = abs(result.iloc[-1]["Close"] - base_data.iloc[-1]["Close"])
    assert np.isclose(diff, last_diff)


def test_violent_reversal(base_data):
    simulator = RareEventSimulator(base_data)
    config = ScenarioConfig(
        scenario_type=ScenarioType.VIOLENT_REVERSAL,
        duration_bars=20,
        magnitude=0.03
    )

    start_idx = 40
    result = simulator.apply_scenario(config, start_index=start_idx)

    # Initial phase should be different from original
    assert result.iloc[start_idx + 5]["Close"] != base_data.iloc[start_idx + 5]["Close"]
    # Reversal phase should also be different
    assert result.iloc[start_idx + 18]["Close"] != base_data.iloc[start_idx + 18]["Close"]


def test_multi_session_dislocation(base_data):
    simulator = RareEventSimulator(base_data)
    config = ScenarioConfig(
        scenario_type=ScenarioType.MULTI_SESSION_DISLOCATION,
        duration_bars=30,
        magnitude=0.04
    )

    start_idx = 20
    result = simulator.apply_scenario(config, start_index=start_idx)

    expected_offset = base_data.iloc[start_idx]["Close"] * 0.04
    assert np.isclose(result.iloc[start_idx]["Close"] - base_data.iloc[start_idx]["Close"], expected_offset)
    assert np.isclose(result.iloc[start_idx + 29]["Close"] - base_data.iloc[start_idx + 29]["Close"], expected_offset)


def test_volatility_cluster(base_data):
    simulator = RareEventSimulator(base_data)
    config = ScenarioConfig(
        scenario_type=ScenarioType.VOLATILITY_CLUSTER,
        duration_bars=15,
        magnitude=0.02
    )

    start_idx = 30
    result = simulator.apply_scenario(config, start_index=start_idx)

    # Check volume increase
    assert result.iloc[start_idx]["Volume"] > base_data.iloc[start_idx]["Volume"]
    # Range should be different
    base_range = base_data.iloc[start_idx]["High"] - base_data.iloc[start_idx]["Low"]
    result_range = result.iloc[start_idx]["High"] - result.iloc[start_idx]["Low"]
    assert result_range != base_range


def test_random_start(base_data):
    simulator = RareEventSimulator(base_data)
    config = ScenarioConfig(
        scenario_type=ScenarioType.MULTI_SESSION_DISLOCATION,
        duration_bars=10,
        magnitude=0.01,
        random_seed=42
    )

    result1 = simulator.apply_scenario(config)
    result2 = simulator.apply_scenario(config)

    # With same seed and same base data, results should be identical
    pd.testing.assert_frame_equal(result1, result2)


def test_invalid_data():
    invalid_df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    with pytest.raises(ValueError, match="Data must contain columns"):
        RareEventSimulator(invalid_df)

def test_short_data(base_data):
    simulator = RareEventSimulator(base_data)
    config = ScenarioConfig(
        scenario_type=ScenarioType.FLASH_CRASH,
        duration_bars=200, # Longer than base_data
        magnitude=0.05
    )
    with pytest.raises(ValueError, match="Data too short"):
        simulator.apply_scenario(config)
