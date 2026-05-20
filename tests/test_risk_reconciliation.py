"""
Tests for Risk Reconciliation logic and scenarios.
"""

import os
from datetime import datetime, timezone

import pytest

from src.core.config import TradingConfig
from src.core.trade_logger import TradeLogger
from src.trading.risk_manager import RiskManager
from src.utils.synthetic_data import ReconciliationScenarioBuilder


@pytest.fixture
def trade_logger():
    db_path = "test_reconciliation.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    yield logger
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def config():
    return TradingConfig(
        MT5_PASSWORD="test",
        MT5_SERVER="test",
        max_daily_loss=0.05,  # 5%
        max_losing_streak=5,
    )


@pytest.fixture
def risk_builder(trade_logger):
    return ReconciliationScenarioBuilder(trade_logger)


def test_reconciliation_near_daily_loss(config, trade_logger, risk_builder):
    # 1. Setup scenario: $450 loss (near 5% of $10,000 balance = $500)
    risk_builder.populate_near_daily_loss()

    # 2. Get reconciliation data
    recon_data = trade_logger.get_reconciliation_data()
    assert recon_data["realised_pnl"] == -450.0
    assert recon_data["trade_count"] == 3
    assert recon_data["consecutive_losses"] == 3

    # 3. Reconcile RiskManager
    risk_manager = RiskManager(config, account_balance=10000.0)
    risk_manager.reconcile_state(recon_data)

    assert risk_manager.daily.realised_pnl == -450.0
    assert risk_manager.daily.consecutive_losses == 3
    # Peak equity should be restored to $10,450 (since balance is $10k and we lost $450)
    assert risk_manager.daily.peak_equity == 10450.0

    # 4. Verify limits are enforced
    from src.core.schemas import TradeSignal
    from src.core.constants import SignalDirection

    # Small trade that would push loss past $500 (5% of $10,450 is $522.5)
    # $450 + $100 loss = $550 > $522.5
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2200.0, # Large SL
        take_profit=2500.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.9
    )

    # Mock realised PnL calculation for the next trade to see if it would breach
    # RiskManager._check_daily_loss uses realised_pnl / peak_equity
    # -450 / 10450 = -4.3% (PASS)
    assert risk_manager._check_daily_loss() is True

    # Simulate one more loss
    risk_manager.record_pnl(-100.0)
    # -550 / 10450 = -5.2% (FAIL)
    assert risk_manager._check_daily_loss() is False


def test_reconciliation_losing_streak(config, trade_logger, risk_builder):
    # 1. Setup scenario: 5 consecutive losses
    risk_builder.populate_active_losing_streak(n_losses=5)

    # 2. Get reconciliation data and reconcile
    recon_data = trade_logger.get_reconciliation_data()
    risk_manager = RiskManager(config, account_balance=10000.0)
    risk_manager.reconcile_state(recon_data)

    assert risk_manager.daily.consecutive_losses == 5

    # 3. Verify immediate rejection due to streak
    assert risk_manager._check_consecutive_losses() is False


def test_reconciliation_mixed_streak(config, trade_logger, risk_builder):
    # 1. Setup scenario: Loss, Loss, Win, Loss -> Streak should be 1
    risk_builder.populate_mixed_outcomes()

    # 2. Reconcile
    recon_data = trade_logger.get_reconciliation_data()
    risk_manager = RiskManager(config, account_balance=10000.0)
    risk_manager.reconcile_state(recon_data)

    assert risk_manager.daily.consecutive_losses == 1
    assert risk_manager._check_consecutive_losses() is True
