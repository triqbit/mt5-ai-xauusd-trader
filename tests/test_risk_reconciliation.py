import pytest
import uuid
import os
from datetime import datetime, UTC, timedelta
from src.core.trade_logger import TradeLogger, Trade
from src.trading.risk_manager import RiskManager
from src.core.config import TradingConfig
from src.core.schemas import TradeSignal

@pytest.fixture
def db_url():
    # Use unique in-memory URL for each test to bypass lru_cache
    # Requires the bypass logic in src/core/database.py
    return f"sqlite:///:memory-{uuid.uuid4()}:"

@pytest.fixture
def trade_logger(db_url):
    return TradeLogger(db_url)

@pytest.fixture
def config():
    # Set required env vars
    os.environ["MT5_PASSWORD"] = "password"
    os.environ["MT5_SERVER"] = "Demo"
    os.environ["SYMBOL"] = "XAUUSD"
    os.environ["MAX_DAILY_LOSS"] = "0.05"
    os.environ["RISK_PER_TRADE"] = "0.01"
    os.environ["MAX_POSITIONS"] = "3"

    return TradingConfig()

def test_trade_logger_reconciliation_data(trade_logger):
    # Setup: 1 trade from yesterday, 2 from today
    yesterday = datetime.now(UTC) - timedelta(days=1)
    today = datetime.now(UTC)

    trade_logger.log_trade(101, "XAUUSD", 1, 2000.0, 0.1, status="CLOSED")
    trade_logger.log_trade(102, "XAUUSD", -1, 2010.0, 0.1, status="CLOSED")
    trade_logger.log_trade(103, "XAUUSD", 1, 2020.0, 0.1, status="OPEN")

    with trade_logger.Session() as session:
        t1 = session.query(Trade).filter(Trade.ticket == 101).first()
        t1.created_at = yesterday
        t1.updated_at = yesterday
        t1.pnl = 100.0

        t2 = session.query(Trade).filter(Trade.ticket == 102).first()
        t2.created_at = today
        t2.updated_at = today
        t2.pnl = -50.0

        session.commit()

    recon = trade_logger.get_reconciliation_data()
    assert recon["today_count"] == 1
    assert recon["today_realised_pnl"] == -50.0
    assert len(recon["all_pnls"]) == 2
    assert recon["all_pnls"] == [100.0, -50.0]

    open_trades = trade_logger.get_open_trades()
    assert open_trades == {"XAUUSD": 103}

def test_risk_manager_reconcile_fresh(config, trade_logger):
    rm = RiskManager(config, 10000.0, logger_db=trade_logger)
    rm.reconcile_state(10000.0)

    assert rm.peak_equity == 10000.0
    assert rm.daily.realised_pnl == 0.0
    assert rm.daily.trade_count == 0

def test_risk_manager_reconcile_with_history(config, trade_logger):
    # Setup history: Start 10000 -> win 500 (peak 10500) -> lose 200 -> current 10300
    # Today: lose 200 (included in win 500 -> lose 200)

    today = datetime.now(UTC)
    trade_logger.log_trade(201, "XAUUSD", 1, 2000.0, 0.1, status="CLOSED")
    trade_logger.log_trade(202, "XAUUSD", -1, 2010.0, 0.1, status="CLOSED")

    with trade_logger.Session() as session:
        t1 = session.query(Trade).filter(Trade.ticket == 201).first()
        t1.pnl = 500.0
        t1.created_at = today - timedelta(hours=5)
        t1.updated_at = today - timedelta(hours=5)

        t2 = session.query(Trade).filter(Trade.ticket == 202).first()
        t2.pnl = -200.0
        t2.created_at = today
        t2.updated_at = today

        session.commit()

    rm = RiskManager(config, 10300.0, logger_db=trade_logger)
    rm.reconcile_state(10300.0)

    # Pre-trade balance = 10300 - (500 - 200) = 10000
    # Equity curve: [10000, 10500, 10300]
    assert rm.peak_equity == 10500.0
    assert rm.daily.realised_pnl == 300.0 # Both trades were today in this setup
    assert rm.daily.trade_count == 2
    # Today's peak should be 10500
    assert rm.daily.peak_equity == 10500.0

def test_risk_manager_circuit_breaker_after_reconcile(config, trade_logger):
    # High drawdown scenario: peak 12000, current 10000 (16.6% drawdown)
    # 15% is the circuit breaker limit in code

    trade_logger.log_trade(301, "XAUUSD", 1, 2000.0, 1.0, status="CLOSED")
    trade_logger.log_trade(302, "XAUUSD", 1, 2100.0, 1.0, status="CLOSED")

    with trade_logger.Session() as session:
        t1 = session.query(Trade).filter(Trade.ticket == 301).first()
        t1.pnl = 2000.0 # Start 10000 -> 12000

        t2 = session.query(Trade).filter(Trade.ticket == 302).first()
        t2.pnl = -2000.0 # 12000 -> 10000

        session.commit()

    rm = RiskManager(config, 10000.0, logger_db=trade_logger)
    rm.reconcile_state(10000.0)

    assert rm.peak_equity == 12000.0

    # Circuit breaker should trigger
    signal = TradeSignal(symbol="XAUUSD", direction=1, entry_price=2000.0, stop_loss=1980.0, take_profit=2040.0, lot_size=0.1, confidence=0.8, algorithm="test")
    assert rm.approve(signal) is False

def test_risk_manager_daily_loss_after_reconcile(config, trade_logger):
    # Daily loss limit: 5% of 10000 = 500
    # Today's loss: 600

    trade_logger.log_trade(401, "XAUUSD", 1, 2000.0, 1.0, status="CLOSED")

    with trade_logger.Session() as session:
        t1 = session.query(Trade).filter(Trade.ticket == 401).first()
        t1.pnl = -600.0
        t1.updated_at = datetime.now(UTC)
        session.commit()

    rm = RiskManager(config, 9400.0, logger_db=trade_logger)
    rm.reconcile_state(9400.0)

    assert rm.daily.realised_pnl == -600.0

    signal = TradeSignal(symbol="XAUUSD", direction=1, entry_price=2000.0, stop_loss=1980.0, take_profit=2040.0, lot_size=0.1, confidence=0.8, algorithm="test")
    assert rm.approve(signal) is False
