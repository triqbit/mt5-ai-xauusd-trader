"""
Test suite for RiskManager state reconciliation and recovery.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.core.config import TradingConfig
from src.core.schemas import TradeSignal
from src.core.trade_logger import Trade, TradeLogger
from src.trading.risk_manager import RiskManager


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_trades.db"
    return f"sqlite:///{db_path}"


@pytest.fixture
def logger(temp_db):
    return TradeLogger(db_url=temp_db)


@pytest.fixture
def config():
    return TradingConfig(
        MT5_LOGIN=123456,
        MT5_PASSWORD="password",
        MT5_SERVER="Demo",
        mt5_path="C:/Program Files/MetaTrader 5/terminal64.exe",
        max_daily_loss=0.05,
        max_positions=3,
        max_losing_streak=3,
        risk_per_trade=0.01,
    )


def test_risk_manager_reconciliation_full_cycle(logger, config):
    # 1. Setup historical data in DB
    # Start with $10,000 balance

    # Yesterday: One winner of $200
    yesterday = datetime.now(UTC) - timedelta(days=1)
    with logger.Session() as session:
        t1 = Trade(
            ticket=100,
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.0,
            exit_price=2302.0,
            lot_size=0.1,
            pnl=200.0,
            status="CLOSED",
            created_at=yesterday,
            updated_at=yesterday,
        )
        session.add(t1)
        session.commit()

    # Today: Two losers of $100 each
    today = datetime.now(UTC)
    with logger.Session() as session:
        t2 = Trade(
            ticket=101,
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.0,
            exit_price=2299.0,
            lot_size=0.1,
            pnl=-100.0,
            status="CLOSED",
            created_at=today,
            updated_at=today,
        )
        t3 = Trade(
            ticket=102,
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.0,
            exit_price=2299.0,
            lot_size=0.1,
            pnl=-100.0,
            status="CLOSED",
            created_at=today,
            updated_at=today,
        )
        # One open trade
        t4 = Trade(
            ticket=103,
            symbol="EURUSD",
            direction=-1,
            entry_price=1.0800,
            lot_size=0.1,
            status="OPEN",
            created_at=today,
            updated_at=today,
        )
        session.add_all([t2, t3, t4])
        session.commit()

    # Current balance would be 10000 + 200 - 100 - 100 = 10000
    current_balance = 10000.0

    # 2. Get reconciliation data
    recon_data = logger.get_reconciliation_data(current_balance)
    open_trades = logger.get_open_trades()

    # Verify recon data
    assert recon_data["realised_pnl"] == -200.0
    assert recon_data["trade_count"] == 2
    assert recon_data["consecutive_losses"] == 2
    assert recon_data["all_time_peak_equity"] == 10200.0
    assert open_trades == {"EURUSD": 103}

    # 3. Initialize RiskManager and Reconcile
    risk = RiskManager(config, account_balance=current_balance, logger_db=logger)
    risk.reconcile_state(recon_data, open_trades)

    # 4. Assert RiskManager state
    assert risk.daily.realised_pnl == -200.0
    assert risk.daily.trade_count == 2
    assert risk.daily.consecutive_losses == 2
    assert risk.peak_equity == 10200.0
    assert risk.open_positions == {"EURUSD": 103}

    # 5. Verify circuit breaker triggers based on reconciled state
    # Daily loss limit is 5% of peak ($10200 * 0.05 = $510).
    # Current loss is $200.

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8,
    )

    # Should still be approved
    assert risk.approve(signal) is True

    # Record another big loss today to hit limit
    risk.record_pnl(-400.0)
    assert risk.daily.realised_pnl == -600.0

    # Should now be rejected due to daily loss limit
    assert risk.approve(signal) is False


def test_risk_manager_consecutive_losses_reconciliation(logger, config):
    today = datetime.now(UTC)
    with logger.Session() as session:
        for i in range(3):
            t = Trade(
                ticket=200 + i,
                symbol="XAUUSD",
                direction=1,
                entry_price=2300.0,
                exit_price=2299.0,
                lot_size=0.1,
                pnl=-10.0,
                status="CLOSED",
                created_at=today,
                updated_at=today,
            )
            session.add(t)
        session.commit()

    recon_data = logger.get_reconciliation_data(970.0)
    risk = RiskManager(config, account_balance=970.0)
    risk.reconcile_state(recon_data, {})

    assert risk.daily.consecutive_losses == 3

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8,
    )

    # Should be rejected due to max_losing_streak (3)
    assert risk.approve(signal) is False
