"""
Tests for the audit logging system.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.audit_log import AuditLog, AuditLogger
from src.core.trade_logger import Base

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session

def test_audit_log_creation(session):
    logger = AuditLogger(session)
    logger.log_event(event_type="TEST", description="Test description")

    with session() as s:
        logs = s.query(AuditLog).all()
        assert len(logs) == 1
        assert logs[0].event_type == "TEST"
        assert logs[0].description == "Test description"

def test_log_config_change(session):
    logger = AuditLogger(session)
    logger.log_config_change(
        reason="Test change",
        old_config={"param": 1},
        new_config={"param": 2}
    )

    with session() as s:
        log = s.query(AuditLog).filter_by(event_type="CONFIG_CHANGE").first()
        assert log is not None
        assert "Test change" in log.description
        assert '"old": {"param": 1}' in log.metadata_json

def test_log_trade_blocked(session):
    logger = AuditLogger(session)
    logger.log_trade_blocked(
        symbol="XAUUSD",
        reason="Risk limit",
        decision_chain={"filter1": False}
    )

    with session() as s:
        log = s.query(AuditLog).filter_by(event_type="TRADE_BLOCKED").first()
        assert log is not None
        assert "XAUUSD" in log.description
        assert '"filter1": false' in log.metadata_json

def test_log_prediction(session):
    logger = AuditLogger(session)
    logger.log_prediction(
        symbol="XAUUSD",
        direction=1,
        confidence=0.85,
        metadata={"algo1": 0.8}
    )

    with session() as s:
        log = s.query(AuditLog).filter_by(event_type="MODEL_PREDICTION").first()
        assert log is not None
        assert "0.85" in log.description
        assert '"confidence": 0.85' in log.metadata_json
        assert '"algo1": 0.8' in log.metadata_json
