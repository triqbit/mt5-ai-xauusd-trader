import pytest
import os
import json
from src.core.audit_log import AuditLogger, AuditLog
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.database import Base

@pytest.fixture
def audit_logger():
    db_url = "sqlite:///test_audit.db"
    logger = AuditLogger(db_url=db_url)
    yield logger
    if os.path.exists("test_audit.db"):
        os.remove("test_audit.db")

def test_log_deployment(audit_logger):
    audit_logger.log_deployment("1.0.0", "test", {"param": "value"})

    with audit_logger.Session() as session:
        log = session.query(AuditLog).filter_by(event_type="DEPLOYMENT").first()
        assert log is not None
        assert "1.0.0" in log.description
        assert "test" in log.description
        metadata = json.loads(log.metadata_json)
        assert metadata["version"] == "1.0.0"
        assert metadata["config"]["param"] == "value"

def test_log_model_prediction(audit_logger):
    audit_logger.log_model_prediction("XAUUSD", 1, 0.85, {"ppo": 0.9, "lstm": 0.8})

    with audit_logger.Session() as session:
        log = session.query(AuditLog).filter_by(event_type="MODEL_PREDICTION").first()
        assert log is not None
        assert "XAUUSD" in log.description
        metadata = json.loads(log.metadata_json)
        assert metadata["outcome"] == 1
        assert metadata["confidence"] == 0.85
        assert metadata["votes"]["ppo"] == 0.9

def test_log_trade_blocked(audit_logger):
    filters = {"circuit_breaker": True, "daily_loss": False}
    audit_logger.log_trade_blocked("XAUUSD", "Daily loss limit", filters)

    with audit_logger.Session() as session:
        log = session.query(AuditLog).filter_by(event_type="TRADE_BLOCKED").first()
        assert log is not None
        assert "Daily loss limit" in log.description
        metadata = json.loads(log.metadata_json)
        assert metadata["filters"]["daily_loss"] is False

def test_log_operator_action(audit_logger):
    audit_logger.log_operator_action("MANUAL_SHUTDOWN", "User request")

    with audit_logger.Session() as session:
        log = session.query(AuditLog).filter_by(event_type="OPERATOR_ACTION").first()
        assert log is not None
        assert "MANUAL_SHUTDOWN" in log.description
        metadata = json.loads(log.metadata_json)
        assert metadata["action"] == "MANUAL_SHUTDOWN"
