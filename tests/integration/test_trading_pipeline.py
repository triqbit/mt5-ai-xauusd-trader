import pytest
from src.trading.risk_manager import RiskManager, TradeSignal
from src.core.trade_logger import RiskEvent

def test_pipeline_execution_flow(test_cfg, db_logger, mock_connector):
    """
    Verifies the flow from signal generation (mocked) through risk approval to logging.
    """
    # 1. Initialize RiskManager with our fixtures
    risk = RiskManager(
        config=test_cfg,
        account_balance=mock_connector.get_account_balance(),
        logger_db=db_logger
    )

    # 2. Create a high-confidence signal that should pass all filters
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,  # Buy
        entry_price=2000.0,
        stop_loss=1990.0,  # RR = (2020-2000)/(2000-1990) = 2.0 > 1.5
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.85  # > 0.55
    )

    # 3. Log the signal first (as main.py does)
    signal_id = db_logger.log_signal({
        "symbol": signal.symbol,
        "direction": signal.direction,
        "entry_price": signal.entry_price,
        "algorithm": signal.algorithm,
        "confidence": signal.confidence
    })

    # 4. Pass through Risk approval
    approved = risk.approve(signal, signal_id=signal_id)
    assert approved is True

    # 5. Simulate successful execution
    ticket = 99999
    mock_connector.place_order.return_value = ticket

    # 6. Log the trade
    db_logger.log_trade(
        ticket=ticket,
        symbol=signal.symbol,
        direction=signal.direction,
        entry_price=signal.entry_price,
        lot_size=signal.lot_size,
        signal_id=signal_id
    )

    # 7. Verify database state
    # Check trade exists
    trade = db_logger.get_trade_by_ticket(ticket)
    assert trade is not None
    assert trade.symbol == "XAUUSD"
    assert trade.signal_id == signal_id

def test_pipeline_rejection_flow(test_cfg, db_logger, mock_connector):
    """
    Verifies that a bad signal is rejected and the rejection is logged.
    """
    risk = RiskManager(
        config=test_cfg,
        account_balance=mock_connector.get_account_balance(),
        logger_db=db_logger
    )

    # Low confidence signal
    bad_signal = TradeSignal(
        symbol="XAUUSD",
        direction=-1,
        entry_price=2000.0,
        stop_loss=2010.0,
        take_profit=1990.0,
        lot_size=0.1,
        algorithm="lstm",
        confidence=0.4  # < 0.55 threshold
    )

    signal_id = db_logger.log_signal({
        "symbol": bad_signal.symbol,
        "direction": bad_signal.direction,
        "entry_price": bad_signal.entry_price,
        "algorithm": bad_signal.algorithm,
        "confidence": bad_signal.confidence
    })

    approved = risk.approve(bad_signal, signal_id=signal_id)
    assert approved is False

    # Verify RiskEvent was logged
    with db_logger.Session() as session:
        event = session.query(RiskEvent).filter_by(signal_id=signal_id).first()
        assert event is not None
        assert "Confidence" in event.description
        assert event.event_type == "SIGNAL_REJECTED"
