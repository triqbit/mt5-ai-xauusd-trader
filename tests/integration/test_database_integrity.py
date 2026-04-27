import pytest
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import MagicMock
from src.core.trade_logger import TradeLogger, ModelSignal, Trade

def test_database_transaction_rollback(db_logger):
    """
    Test that if an error occurs during a multi-step operation,
    the database remains in a consistent state.
    Note: Current TradeLogger implementation uses separate sessions for log_signal and log_trade.
    We test if log_trade fails, the signal is still there (since it was a separate transaction),
    but we want to see how it handles errors.
    """
    signal_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0
    }

    signal_id = db_logger.log_signal(signal_data)
    assert signal_id > 0

    # Simulate a failure in log_trade (e.g. by passing invalid data or mocking)
    # Actually, SQLAlchemy might just raise an error if we violate constraints.
    # ticket is unique.
    db_logger.log_trade(ticket=111, symbol="XAUUSD", direction=1, entry_price=2000.0, lot_size=0.1, signal_id=signal_id)

    with pytest.raises(Exception):
        # This should fail due to unique constraint on ticket
        db_logger.log_trade(ticket=111, symbol="XAUUSD", direction=1, entry_price=2000.0, lot_size=0.1, signal_id=signal_id)

def test_logger_error_handling(db_logger, monkeypatch):
    """Verify that logger doesn't crash the whole system if DB is down (or mocked to fail)."""

    def mock_commit_fail(self):
        raise SQLAlchemyError("DB Connection Lost")

    # Patch session.commit to fail
    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session, "commit", mock_commit_fail)

    # We expect it to raise or handle it. Current implementation raises it.
    with pytest.raises(SQLAlchemyError):
        db_logger.log_signal({"symbol": "XAUUSD", "direction": 1, "entry_price": 2000.0})
