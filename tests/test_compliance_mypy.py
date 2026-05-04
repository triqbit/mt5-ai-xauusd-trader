"""
MT5 AI/ML Trading Bot - Type Safety Compliance Tests
tests/test_compliance_mypy.py
"""

from datetime import datetime, timezone
import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.core.config import TradingConfig, get_config
from src.core.trade_logger import Base, ModelSignal, Trade, TradeLogger


def test_sqlalchemy_20_mapped_types():
    """Verify that SQLAlchemy 2.0 modernized models work as expected."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Create a signal
        signal = ModelSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.50,
            confidence=0.85,
            timestamp=datetime.now(timezone.utc)
        )
        session.add(signal)
        session.commit()

        # Create a trade linked to the signal
        trade = Trade(
            ticket=12345,
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.50,
            lot_size=0.1,
            signal_id=signal.id,
            status="OPEN"
        )
        session.add(trade)
        session.commit()

        # Verify relationships and Mapped types
        retrieved_trade = session.query(Trade).filter_by(ticket=12345).first()
        assert retrieved_trade is not None
        assert retrieved_trade.signal is not None
        assert retrieved_trade.signal.symbol == "XAUUSD"
        assert isinstance(retrieved_trade.id, int)

        # Verify signal relationship back to trade
        retrieved_signal = session.query(ModelSignal).filter_by(id=signal.id).first()
        assert retrieved_signal.trade is not None
        assert retrieved_signal.trade.ticket == 12345


def test_config_secret_str_handling():
    """Verify that TradingConfig handles SecretStr correctly after refactor."""
    # This ensures that our default=SecretStr("") changes didn't break Pydantic loading
    cfg = TradingConfig(
        mt5_password=SecretStr("test_pass"),
        mt5_server="TestServer",
        database_url=SecretStr("postgresql://user:pass@localhost/db")
    )

    assert isinstance(cfg.mt5_password, SecretStr)
    assert cfg.mt5_password.get_secret_value() == "test_pass"
    assert cfg.database_url.get_secret_value() == "postgresql://user:pass@localhost/db"

    # Test singleton with env vars to satisfy required fields
    import os
    from unittest.mock import patch
    with patch.dict(os.environ, {
        "MT5_PASSWORD": "test_pass",
        "MT5_SERVER": "TestServer",
        "DATABASE_URL": "postgresql://user:pass@localhost/db"
    }):
        get_config.cache_clear()
        cfg_singleton = get_config()
        assert isinstance(cfg_singleton, TradingConfig)
        assert cfg_singleton.mt5_server == "TestServer"


def test_trade_logger_interface_stability():
    """Verify the TradeLogger interface remains stable after model refactor."""
    logger = TradeLogger("sqlite:///:memory:")

    # Log signal
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": -1,
        "entry_price": 2350.0,
        "confidence": 0.7
    })
    assert isinstance(signal_id, int)

    # Log trade
    trade_id = logger.log_trade(
        ticket=99999,
        symbol="XAUUSD",
        direction=-1,
        entry_price=2350.0,
        lot_size=0.05,
        signal_id=signal_id
    )
    assert isinstance(trade_id, int)

    # Get trade
    trade = logger.get_trade_by_ticket(99999)
    assert trade is not None
    assert trade.direction == -1

    # Update trade
    logger.update_trade(99999, exit_price=2340.0)
    trade_updated = logger.get_trade_by_ticket(99999)
    assert trade_updated.status == "CLOSED"
    assert trade_updated.pnl > 0  # Short trade, exit < entry
