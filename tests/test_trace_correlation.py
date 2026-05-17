"""
Unit tests for trace correlation across logging and database layers.
"""

import uuid

import pytest
from sqlalchemy import select

from src.core.audit_log import AuditEntry, AuditLogger
from src.core.trade_logger import ModelSignal, Trade, TradeLogger


@pytest.fixture
def audit_logger(tmp_path):
    db_path = tmp_path / "audit.db"
    return AuditLogger(db_url=f"sqlite:///{db_path}")

@pytest.fixture
def trade_logger(tmp_path):
    db_path = tmp_path / "trades.db"
    return TradeLogger(db_url=f"sqlite:///{db_path}")

def test_trace_id_propagation(audit_logger, trade_logger):
    # 1. Setup structlog with contextvars
    import structlog.contextvars
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.JSONRenderer(),
        ]
    )

    trace_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=trace_id)

    # 2. Log to Audit trail
    audit_logger.log(actor="test_actor", action="test_action", details="Test details")

    # 3. Log Signal
    signal_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "algorithm": "test_algo",
        "confidence": 0.95
    }
    signal_id = trade_logger.log_signal(signal_data)

    # 4. Log Trade
    trade_logger.log_trade(
        ticket=12345,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id
    )

    # 5. Verify AuditEntry has the correct trace_id
    with audit_logger.Session() as session:
        entry = session.execute(select(AuditEntry).where(AuditEntry.action == "test_action")).scalar_one()
        assert entry.trace_id == trace_id

    # 6. Verify ModelSignal has the correct trace_id
    with trade_logger.Session() as session:
        signal = session.execute(select(ModelSignal).where(ModelSignal.id == signal_id)).scalar_one()
        assert signal.trace_id == trace_id

    # 7. Verify Trade has the correct trace_id
    with trade_logger.Session() as session:
        trade = session.execute(select(Trade).where(Trade.ticket == 12345)).scalar_one()
        assert trade.trace_id == trace_id

def test_trace_id_isolation(audit_logger):
    import structlog.contextvars

    # Trace 1
    trace_id_1 = "trace-1"
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=trace_id_1)
    audit_logger.log(actor="actor1", action="action1")

    # Trace 2
    trace_id_2 = "trace-2"
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=trace_id_2)
    audit_logger.log(actor="actor2", action="action2")

    with audit_logger.Session() as session:
        entry1 = session.execute(select(AuditEntry).where(AuditEntry.action == "action1")).scalar_one()
        entry2 = session.execute(select(AuditEntry).where(AuditEntry.action == "action2")).scalar_one()

        assert entry1.trace_id == trace_id_1
        assert entry2.trace_id == trace_id_2
