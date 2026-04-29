"""
Tests for RiskManager using synthetic market scenarios.
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock
from src.trading.risk_manager import RiskManager, TradeSignal
from src.core.config import TradingConfig
from src.utils.synthetic_data import ScenarioGenerator

@pytest.fixture
def config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 3
    cfg.risk_per_trade = 0.01
    return cfg

@pytest.fixture
def risk_manager(config):
    return RiskManager(config, account_balance=10000.0)

@pytest.fixture
def generator():
    return ScenarioGenerator(seed=42)

def test_circuit_breaker_on_flash_crash(risk_manager, generator):
    """
    Test that a severe drawdown (flash crash) triggers the circuit breaker.
    """
    # 1. Initial state
    assert risk_manager._check_circuit_breaker() is True

    # 2. Simulate a massive loss (e.g., 20% drawdown)
    # Circuit breaker threshold in risk_manager.py is 15% (0.15)
    risk_manager.update_equity(8000.0) # 20% drop from 10000.0

    # 3. Verify circuit breaker is triggered
    assert risk_manager._check_circuit_breaker() is False

def test_risk_manager_rejects_on_low_confidence(risk_manager):
    """
    Test that signals with low confidence are rejected.
    """
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.4  # Below 0.55 threshold
    )

    assert risk_manager.approve(signal) is False

def test_risk_manager_accepts_valid_signal(risk_manager):
    """
    Test that a valid signal passing all layers is approved.
    """
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    assert risk_manager.approve(signal) is True

def test_missing_data_impact(generator):
    """
    Verify that our generator correctly produces missing data for robustness tests.
    """
    df = generator.generate_missing_data(n_bars=100, gap_at=50, gap_size=10)
    assert df.iloc[50:60].isna().all().all()
    assert not df.iloc[0:50].isna().any().any()

def test_volatility_spike_detection(generator):
    """
    Verify that the volatility spike scenario actually increases price variance.
    """
    df_normal = generator.generate_gbm(n_bars=100)
    df_spike = generator.generate_volatility_spike(n_bars=100, spike_at=20, duration=60, multiplier=10.0)

    std_normal = df_normal["close"].pct_change().std()
    std_spike = df_spike["close"].pct_change().std()

    assert std_spike > std_normal
