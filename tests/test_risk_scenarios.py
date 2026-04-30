
import pytest

from src.trading.risk_manager import RiskManager, TradeSignal, TradingConfig
from src.utils.synthetic_data import ScenarioGenerator


@pytest.fixture
def config():
    return TradingConfig(
        mt5_password="test",
        mt5_server="test",
        max_positions=3,
        risk_per_trade=0.01,
        max_daily_loss=0.05
    )

@pytest.fixture
def risk_manager(config):
    return RiskManager(config, account_balance=10000.0)

def test_risk_manager_with_volatile_data(risk_manager):
    gen = ScenarioGenerator()
    df = gen.generate_volatile_market(n_bars=10, volatility=50.0)

    # Simulate a signal based on volatile data
    last_price = df["close"].iloc[-1]

    # High risk signal (SL is far)
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=last_price,
        stop_loss=last_price - 100.0,
        take_profit=last_price + 50.0, # R:R = 0.5 < 1.5
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    assert risk_manager.approve(signal) is False # Should fail RR check

def test_risk_manager_with_malformed_signal(risk_manager):
    # This isn't strictly using synthetic data for the signal but testing the RM's robustness
    signal = TradeSignal(
        symbol="INVALID", # Not in portfolio
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    assert risk_manager.approve(signal) is False

def test_circuit_breaker_on_synthetic_drawdown(risk_manager):
    # Simulate a series of losses using synthetic-like data
    risk_manager.update_equity(10000.0)
    risk_manager.update_equity(8000.0) # 20% drawdown > 15% limit

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.9
    )

    assert risk_manager.approve(signal) is False # Circuit breaker should trigger

def test_risk_manager_rr_edge_case(risk_manager):
    # Signal with exactly min_rr
    # Risk = 10, Reward = 15, RR = 1.5
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2015.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )
    assert risk_manager.approve(signal) is True

    # RR = 1.49
    signal.take_profit = 2014.9
    assert risk_manager.approve(signal) is False
