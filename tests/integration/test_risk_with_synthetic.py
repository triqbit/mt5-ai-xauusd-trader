"""
Integration test for RiskManager using synthetic data.
"""

import pytest
from datetime import datetime
from src.utils.synthetic_data import SyntheticDataGenerator, MarketRegime
from src.trading.risk_manager import RiskManager, TradeSignal
from src.core.config import TradingConfig


@pytest.fixture
def mock_config():
    return TradingConfig(
        mt5_password="dummy",
        mt5_server="dummy",
        max_positions=3,
        risk_per_trade=0.01,
        max_daily_loss=0.05
    )


def test_risk_manager_with_flash_crash(mock_config):
    """
    Test how RiskManager responds to a flash crash scenario generated synthetically.
    """
    generator = SyntheticDataGenerator(seed=42)
    # Generate 1000 ticks
    base_prices = generator.generate_base_prices(1000, start_price=2000.0)
    # Inject a severe flash crash (10% drop) at tick 500
    crashed_prices = generator.add_flash_crash(base_prices, index=500, depth_pct=0.10, duration_ticks=50)

    # Initialize RiskManager with $10,000 balance
    risk_manager = RiskManager(config=mock_config, account_balance=10000.0)

    # Scenario 1: Normal conditions (before crash)
    normal_price = crashed_prices[100]
    signal_ok = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=normal_price,
        stop_loss=normal_price * 0.99,
        take_profit=normal_price * 1.02,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )
    assert risk_manager.approve(signal_ok) is True

    # Scenario 2: During flash crash
    # Let's say the bot tries to buy the dip during the sharpest point of the crash
    crash_price = crashed_prices[525] # Deep in the crash

    # RiskManager might reject if the drawdown hit the circuit breaker
    # We simulate a loss from a previous trade during the crash
    loss = 1600.0 # 16% of 10000
    risk_manager.update_equity(10000.0 - loss)

    signal_during_crash = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=crash_price,
        stop_loss=crash_price * 0.95,
        take_profit=crash_price * 1.10,
        lot_size=0.1,
        algorithm="test",
        confidence=0.9
    )

    # Circuit breaker should trigger at 15% drawdown
    # Current drawdown is 1600/10000 = 16%
    assert risk_manager.approve(signal_during_crash) is False

    # Verify it was due to circuit breaker (drawdown > 15%)
    assert (risk_manager.peak_equity - risk_manager.balance) / risk_manager.peak_equity >= 0.15


def test_risk_manager_daily_loss_limit(mock_config):
    """
    Test daily loss limit using synthetic PnL.
    """
    risk_manager = RiskManager(config=mock_config, account_balance=10000.0)

    # Simulate a series of losing trades that hit the 5% daily loss limit
    risk_manager.record_pnl(-300.0)
    risk_manager.record_pnl(-250.0)
    # Total loss = 550, which is 5.5% of 10000

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1980.0,
        take_profit=2050.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    assert risk_manager.approve(signal) is False
