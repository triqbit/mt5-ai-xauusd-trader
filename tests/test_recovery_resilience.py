"""
Tests for state recovery and database resilience.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.core.trade_logger import TradeLogger, PerformanceMetric, Trade
from src.trading.risk_manager import RiskManager
from src.core.config import TradingConfig
from sqlalchemy.exc import OperationalError

@pytest.fixture
def db_url(tmp_path):
    d = tmp_path / "test.db"
    return f"sqlite:///{d}"

@pytest.fixture
def trade_logger(db_url):
    return TradeLogger(db_url)

@pytest.fixture
def risk_manager():
    cfg = MagicMock(spec=TradingConfig)
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 5
    cfg.max_losing_streak = 3
    return RiskManager(cfg, account_balance=10000.0)

def test_trade_logger_retry_on_operational_error(db_url):
    # We want to test that the @with_retry decorator is working on TradeLogger methods.

    logger = TradeLogger(db_url)

    # We need to mock logger.Session() call which returns a context manager.
    with patch.object(logger, "Session") as mock_session_factory:
        mock_session = MagicMock()
        mock_session_factory.return_value.__enter__.return_value = mock_session

        # Raise OperationalError twice, then succeed on commit
        mock_session.commit.side_effect = [
            OperationalError("locked", {}, None),
            OperationalError("locked", {}, None),
            None
        ]

        # This should succeed after 2 retries
        logger.log_signal({
            "symbol": "XAUUSD",
            "direction": 1,
            "entry_price": 2000.0
        })

        assert mock_session.commit.call_count == 3

def test_risk_manager_reconcile_open_positions(trade_logger, risk_manager):
    # 1. Manually add open trades to DB
    trade_logger.log_trade(ticket=111, symbol="XAUUSD", direction=1, entry_price=2000.0, lot_size=0.1, status="OPEN")
    trade_logger.log_trade(ticket=222, symbol="EURUSD", direction=-1, entry_price=1.1000, lot_size=0.2, status="OPEN")
    # Add a closed trade too
    trade_logger.log_trade(ticket=333, symbol="GBPUSD", direction=1, entry_price=1.2500, lot_size=0.1, status="CLOSED")

    # 2. Reconcile
    risk_manager.reconcile_state(trade_logger)

    # 3. Verify
    assert "XAUUSD" in risk_manager.open_positions
    assert risk_manager.open_positions["XAUUSD"] == 111
    assert "EURUSD" in risk_manager.open_positions
    assert risk_manager.open_positions["EURUSD"] == 222
    assert "GBPUSD" not in risk_manager.open_positions
    assert len(risk_manager.open_positions) == 2

def test_risk_manager_reconcile_peak_equity(trade_logger, risk_manager):
    # 1. Add some trades and a performance snapshot with high peak equity
    trade_logger.log_trade(ticket=1, symbol="XAUUSD", direction=1, entry_price=2000.0, lot_size=1.0, status="CLOSED")
    # Manually update pnl for the closed trade
    with trade_logger.Session() as session:
        from sqlalchemy import select
        t = session.execute(select(Trade).where(Trade.ticket == 1)).scalar_one()
        t.pnl = 500.0
        session.commit()

    # Persist a report (this will calculate peak_equity as 10500 if initial was 10000,
    # but wait, read_performance_report uses the trades in DB)
    # Actually, let's just use the persist=True and see what happens.
    # The read_performance_report in current impl doesn't know about initial balance,
    # it just sums pnls starting from 0.
    # equity_curve = np.cumsum(pnls) -> [500]
    # peak_eq = 500.0

    trade_logger.read_performance_report(persist=True)

    # Now simulate a crash and restart.
    # New risk manager with 10000 balance.
    risk_manager.balance = 10000.0
    risk_manager.peak_equity = 10000.0

    risk_manager.reconcile_state(trade_logger)

    # It should have restored peak_equity.
    # snapshot.peak_equity was 500.0 (based on PnL sequence).
    # reconcile_state does restored_peak = max(snapshot.peak_equity, self.balance)
    # So it will be 10000.0.

    # Let's test with a real scenario where PnL sequence actually goes above 0.
    with trade_logger.Session() as session:
        from src.core.trade_logger import PerformanceMetric
        p = PerformanceMetric(peak_equity=12000.0, sharpe_ratio=2.0)
        session.add(p)
        session.commit()

    risk_manager.reconcile_state(trade_logger)
    assert risk_manager.peak_equity == 12000.0
    assert risk_manager.daily.peak_equity == 12000.0

def test_risk_manager_reconcile_no_data(db_url):
    cfg = MagicMock(spec=TradingConfig)
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 5
    cfg.max_losing_streak = 3
    rm = RiskManager(cfg, account_balance=10000.0)

    # Use a fresh trade logger for this test to avoid leakage from other tests
    fresh_logger = TradeLogger(db_url)
    # Should not crash if DB is empty
    rm.reconcile_state(fresh_logger)
    assert rm.balance == 10000.0
    assert rm.peak_equity == 10000.0
    assert len(rm.open_positions) == 0
