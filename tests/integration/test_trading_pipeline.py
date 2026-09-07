"""
Integration test for the full trading pipeline:
Signal -> Risk Manager -> Order Execution -> Trade Logger
"""
import os
import pytest
from unittest.mock import MagicMock
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import RiskManager, TradeSignal
from src.core.trade_logger import TradeLogger

# Skip if numpy is not available
pytest.importorskip("numpy")

@pytest.fixture
def clean_db():
    db_path = "test_integration.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

def test_full_trading_pipeline_success(mock_config, clean_db):
    """
    Test a successful trade flow through the entire system.
    """
    # 1. Setup components
    logger = TradeLogger(db_url=f"sqlite:///{clean_db}")
    connector = MT5Connector(mock_config)
    connector.initialize()

    # We mock the account balance to ensure enough capital
    balance = 10000.0
    risk = RiskManager(mock_config, account_balance=balance, logger_db=logger)

    # 2. Simulate a high-confidence Buy Signal
    signal_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "algorithm": "ensemble",
        "confidence": 0.85
    }

    # 3. Step 1: Log the signal
    signal_id = logger.log_signal(signal_data)
    assert signal_id > 0

    # 4. Step 2: Create TradeSignal object
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )

    # 5. Step 3: Risk Approval
    # Should pass because confidence is high and R:R is 2.0
    approved = risk.approve(signal, signal_id=signal_id)
    assert approved is True

    # 6. Step 4: Place Order
    ticket = connector.place_order(signal)
    assert ticket == 123456

    # 7. Step 5: Log the trade
    trade_id = logger.log_trade(
        ticket=ticket,
        symbol=signal.symbol,
        direction=signal.direction,
        entry_price=signal.entry_price,
        lot_size=signal.lot_size,
        signal_id=signal_id
    )
    assert trade_id > 0

    # Verify DB state
    with logger.Session() as session:
        from src.core.trade_logger import Trade, ModelSignal
        db_trade = session.query(Trade).filter_by(ticket=ticket).first()
        assert db_trade is not None
        assert db_trade.signal_id == signal_id

        db_signal = session.query(ModelSignal).get(signal_id)
        assert db_signal.symbol == "XAUUSD"

def test_trading_pipeline_risk_rejection(mock_config, clean_db):
    """
    Test that the pipeline correctly halts when RiskManager rejects a signal.
    """
    logger = TradeLogger(db_url=f"sqlite:///{clean_db}")
    risk = RiskManager(mock_config, account_balance=10000.0, logger_db=logger)

    # Low confidence signal
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.3  # Below threshold
    )

    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "algorithm": "ensemble",
        "confidence": 0.3
    })

    # Risk Approval should fail
    approved = risk.approve(signal, signal_id=signal_id)
    assert approved is False

    # Verify that a RiskEvent was logged
    with logger.Session() as session:
        from src.core.trade_logger import RiskEvent
        event = session.query(RiskEvent).filter_by(signal_id=signal_id).first()
        assert event is not None
        assert "Confidence" in event.description
        assert event.event_type == "SIGNAL_REJECTED"
