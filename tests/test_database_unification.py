"""
Integration tests for TradeLogger and AuditLogger using unified DatabaseManager.
"""
import os
import pytest
from src.core.database import DatabaseManager, Base
from src.core.trade_logger import TradeLogger
from src.core.audit_log import AuditLogger

@pytest.fixture
def db_manager():
    db_path = "test_unified.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    # Initialize singleton DatabaseManager
    # Note: DatabaseManager is a singleton, so we need to be careful if it was already initialized
    if DatabaseManager._instance:
        DatabaseManager._instance._initialized = False # Force re-init for test

    manager = DatabaseManager(db_url=f"sqlite:///{db_path}")
    Base.metadata.create_all(manager.engine)

    yield manager

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def trade_logger(db_manager):
    return TradeLogger()

@pytest.fixture
def audit_logger(db_manager):
    # AuditLogger is also a singleton
    if AuditLogger._instance:
        AuditLogger._instance._initialized = False # Force re-init
    return AuditLogger(db_url="anything") # db_url ignored since it uses DatabaseManager

def test_unified_database_sharing(db_manager, trade_logger, audit_logger):
    # Log a signal (TradeLogger)
    signal_id = trade_logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "algorithm": "ppo",
        "confidence": 0.8
    })

    # Log an audit entry (AuditLogger)
    audit_id = audit_logger.log(actor="test", action="test_action", details="test_details")

    # Verify both are in the same database
    with db_manager.get_session() as session:
        from src.core.trade_logger import ModelSignal
        from src.core.audit_log import AuditEntry

        signal = session.get(ModelSignal, signal_id)
        audit = session.get(AuditEntry, audit_id)

        assert signal is not None
        assert signal.symbol == "XAUUSD"
        assert audit is not None
        assert audit.action == "test_action"

def test_trade_logger_operations(trade_logger):
    ticket = 12345
    trade_logger.log_trade(ticket, "XAUUSD", 1, 2000.0, 0.1)
    trade_logger.update_trade(ticket, 2010.0, 100.0)

    trade = trade_logger.get_trade_by_ticket(ticket)
    assert trade.status == "CLOSED"
    assert trade.pnl == 100.0

def test_performance_report(trade_logger):
    trade_logger.log_trade(1, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    trade_logger.update_trade(1, 2010.0, 100.0)

    report = trade_logger.read_performance_report()
    assert report["total_trades"] == 1
    assert report["win_rate"] == 1.0
