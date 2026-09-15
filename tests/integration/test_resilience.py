import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.trading.risk_manager import RiskManager, TradeSignal
from src.core.trade_logger import RiskEvent

def test_database_transaction_rollback_scenario(mock_config, db_logger):
    """
    Test that if a database error occurs during a higher-level operation,
    the system handles it.
    We want to ensure we can still use the DB after a failed operation.
    """
    # Simulate a DB error by mocking session.commit to raise an exception
    mock_session = MagicMock()
    mock_session.commit.side_effect = Exception("DB Error")

    # We need to mock the Session constructor to return our mock_session
    with patch.object(db_logger, 'Session', return_value=mock_session):
        try:
            # This will use the mock_session and fail on commit
            db_logger.log_signal({"symbol": "XAUUSD", "direction": 1, "entry_price": 2000.0})
        except Exception:
            pass

    # Verify we can still log after an "error" (using a fresh real session)
    signal_id = db_logger.log_signal({"symbol": "XAUUSD", "direction": 1, "entry_price": 2000.0})
    assert signal_id > 0

def test_telegram_alert_on_circuit_breaker(mock_config, db_logger, monitor, mock_telegram):
    risk = RiskManager(mock_config, account_balance=10000.0, logger_db=db_logger, monitor=monitor)

    # Trigger circuit breaker by dropping equity significantly
    risk.peak_equity = 20000.0
    risk.balance = 10000.0 # 50% drawdown

    # Any call to approve should now trigger circuit breaker
    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2000.0,
        stop_loss=1990.0, take_profit=2020.0, lot_size=0.1,
        algorithm="ppo", confidence=0.8
    )

    with patch("asyncio.run") as mock_asyncio_run:
        result = risk.approve(signal)
        assert result is False

        # Verify Telegram alert was attempted
        mock_asyncio_run.assert_called()

        # Verify RiskEvent was logged
        with db_logger.Session() as session:
            event = session.query(RiskEvent).filter(RiskEvent.event_type == "CIRCUIT_BREAKER").first()
            assert event is not None
            assert "drawdown" in event.description.lower()
