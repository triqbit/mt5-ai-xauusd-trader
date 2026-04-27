
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.audit_log import AuditLog, AuditLogger
from src.core.trade_logger import Base

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session

def test_audit_logger_log(db_session):
    logger = AuditLogger(db_session)
    logger.log(
        category="TRADE",
        event_type="EXECUTION",
        details={"ticket": 12345, "symbol": "XAUUSD"},
        reason="Model signal",
        operator="ALGO"
    )

    with db_session() as session:
        log = session.query(AuditLog).first()
        assert log is not None
        assert log.category == "TRADE"
        assert log.event_type == "EXECUTION"
        assert log.details == {"ticket": 12345, "symbol": "XAUUSD"}
        assert log.reason == "Model signal"
        assert log.operator == "ALGO"

def test_audit_logger_error_handling(db_session, caplog):
    # Pass something that isn't a session factory to trigger an error
    logger = AuditLogger(None)
    with caplog.at_level("ERROR"):
        logger.log("CAT", "EVT")
    assert "Failed to record audit log" in caplog.text
