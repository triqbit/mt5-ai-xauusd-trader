"""
Tests for RareEventSimulator
"""

import pytest
import pandas as pd
import numpy as np
from src.research.rare_event_simulator import (
    RareEventSimulator, FlashCrashConfig, LiquidityVacuumConfig,
    GoldGapConfig, ViolentReversalConfig, DislocationConfig,
    VolatilityClusterConfig
)

@pytest.fixture
def simulator():
    return RareEventSimulator(base_price=2000.0, sigma=0.001)

@pytest.fixture
def base_data(simulator):
    return simulator.generate_base_data(n_steps=100)

def test_generate_base_data(base_data):
    assert len(base_data) == 100
    assert list(base_data.columns) == ['open', 'high', 'low', 'close', 'volume']
    assert (base_data['high'] >= base_data['low']).all()
    assert (base_data['high'] >= base_data[['open', 'close']].max(axis=1)).all()
    assert (base_data['low'] <= base_data[['open', 'close']].min(axis=1)).all()

def test_flash_crash(simulator, base_data):
    config = FlashCrashConfig(start_index=20, duration=20, magnitude=0.1, recovery_rate=0.5)
    result = simulator.apply_scenario(base_data, config)

    # Check that price dropped
    assert result.iloc[30]['close'] < base_data.iloc[30]['close']
    # Check OHLC consistency
    assert (result['high'] >= result[['open', 'close']].max(axis=1)).all()
    assert (result['low'] <= result[['open', 'close']].min(axis=1)).all()

def test_liquidity_vacuum(simulator, base_data):
    config = LiquidityVacuumConfig(start_index=10, duration=10, noise_multiplier=5.0)
    result = simulator.apply_scenario(base_data, config)

    assert (result.iloc[10:20]['volume'] < base_data.iloc[10:20]['volume']).all()
    assert (result['high'] >= result[['open', 'close']].max(axis=1)).all()

def test_gold_gap(simulator, base_data):
    config = GoldGapConfig(start_index=50, duration=1, gap_size=0.05, direction=1)
    result = simulator.apply_scenario(base_data, config)

    assert result.iloc[50]['open'] > base_data.iloc[50]['open'] * 1.04
    assert (result['high'] >= result[['open', 'close']].max(axis=1)).all()

def test_violent_reversal(simulator, base_data):
    config = ViolentReversalConfig(start_index=30, duration=20, trend_magnitude=0.05, reversal_magnitude=0.1)
    result = simulator.apply_scenario(base_data, config)

    # Mid point should be higher
    assert result.iloc[40]['close'] > base_data.iloc[40]['close']
    # End point should be lower than mid point
    assert result.iloc[50]['close'] < result.iloc[40]['close']
    assert (result['high'] >= result[['open', 'close']].max(axis=1)).all()

def test_dislocation(simulator, base_data):
    config = DislocationConfig(start_index=40, duration=10, shift_magnitude=-0.05)
    result = simulator.apply_scenario(base_data, config)

    assert result.iloc[60]['close'] < base_data.iloc[60]['close'] * 0.96
    assert (result['high'] >= result[['open', 'close']].max(axis=1)).all()

def test_volatility_cluster(simulator, base_data):
    config = VolatilityClusterConfig(start_index=20, duration=10, vol_multiplier=10.0)
    result = simulator.apply_scenario(base_data, config)

    # Hard to test randomness but check consistency
    assert (result['high'] >= result[['open', 'close']].max(axis=1)).all()

def test_invalid_duration(simulator, base_data):
    config = FlashCrashConfig(start_index=90, duration=20, magnitude=0.1)
    with pytest.raises(ValueError, match="Scenario exceeds data length"):
        simulator.apply_scenario(base_data, config)

def test_gold_gap_invalid_direction():
    with pytest.raises(ValueError):
        GoldGapConfig(start_index=10, duration=1, gap_size=0.01, direction=0)
