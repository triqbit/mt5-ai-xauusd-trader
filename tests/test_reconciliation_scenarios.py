"""
Deterministic tests for ReconciliationScenarioBuilder.
"""

import os

import pytest

from src.core.trade_logger import TradeLogger
from src.utils.synthetic_data import ReconciliationScenarioBuilder


@pytest.fixture
def temp_logger():
    db_path = "test_reconciliation.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    yield logger
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def recon_builder():
    return ReconciliationScenarioBuilder(seed=42)


def test_populate_near_daily_loss(temp_logger, recon_builder):
    balance = 10000.0
    target_loss_pct = 0.045
    recon_builder.populate_near_daily_loss(
        temp_logger, balance=balance, target_loss_pct=target_loss_pct
    )

    report = temp_logger.read_performance_report()

    # Expected loss: 10000 * 0.045 = 450
    # Gross loss should be approximately 450
    # Note: TradeLogger returns gross_loss as positive or negative depending on implementation
    # Based on src/core/trade_logger.py: gross_loss = abs(float(stats.gross_loss or 0.0))
    # So it should be 450.0

    # Let's verify total_trades and pnl sum
    assert report["total_trades"] == 3

    # We need to sum pnl manually or check if read_performance_report has a total pnl
    # It doesn't have total pnl directly, but we can check profit_factor or expectancy
    # Or just query the DB directly for confirmation
    with temp_logger.Session() as session:
        from sqlalchemy import func

        from src.core.trade_logger import Trade

        total_pnl = session.query(func.sum(Trade.pnl)).scalar()
        assert abs(total_pnl + 450.0) < 0.01


def test_populate_active_losing_streak(temp_logger, recon_builder):
    recon_builder.populate_active_losing_streak(temp_logger, count=2)

    report = temp_logger.read_performance_report()
    assert report["total_trades"] == 2
    assert report["win_rate"] == 0.0

    with temp_logger.Session() as session:
        from src.core.trade_logger import Trade

        trades = session.query(Trade).all()
        assert len(trades) == 2
        assert all(t.pnl < 0 for t in trades)
        assert trades[0].ticket == 6000
        assert trades[1].ticket == 6001
