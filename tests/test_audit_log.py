"""
Tests for Audit Logging System.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.audit_log import AuditLogger, AuditLog
from src.core.trade_logger import Base

@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def audit_logger(db_engine):
    return AuditLogger(engine=db_engine)

def test_log_config_change(audit_logger, db_engine):
    audit_logger.log_config_change("risk_per_trade", 0.01, 0.02, "Testing")

    Session = sessionmaker(bind=db_engine)
    with Session() as session:
        log = session.query(AuditLog).filter_by(event_type="CONFIG_CHANGE").first()
        assert log is not None
        assert log.actor == "operator"
        assert log.metadata_json["field"] == "risk_per_trade"
        assert log.metadata_json["new_value"] == "0.02"

def test_log_trade_blocked(audit_logger, db_engine):
    decision_chain = {"circuit_breaker": False}
    audit_logger.log_trade_blocked(signal_id=123, reason="Circuit breaker", decision_chain=decision_chain)

    Session = sessionmaker(bind=db_engine)
    with Session() as session:
        log = session.query(AuditLog).filter_by(event_type="TRADE_BLOCKED").first()
        assert log is not None
        assert log.status == "BLOCKED"
        assert log.metadata_json["signal_id"] == 123
        assert log.metadata_json["decision_chain"] == decision_chain

def test_log_model_prediction(audit_logger, db_engine):
    audit_logger.log_model_prediction("XAUUSD", 1, 0.95, {"meta": "data"})

    Session = sessionmaker(bind=db_engine)
    with Session() as session:
        log = session.query(AuditLog).filter_by(event_type="MODEL_PREDICTION").first()
        assert log is not None
        assert log.actor == "ai_model"
        assert log.metadata_json["confidence"] == 0.95

def test_log_risk_decision(audit_logger, db_engine):
    decision_chain = {"filter1": True, "filter2": False}
    audit_logger.log_risk_decision(signal_id=456, passed=False, decision_chain=decision_chain)

    Session = sessionmaker(bind=db_engine)
    with Session() as session:
        log = session.query(AuditLog).filter_by(event_type="RISK_DECISION").first()
        assert log is not None
        assert log.status == "FAILURE"
        assert log.metadata_json["passed"] is False

def test_log_operator_action(audit_logger, db_engine):
    audit_logger.log_operator_action("EMERGENCY_HALT", "Manual intervention")

    Session = sessionmaker(bind=db_engine)
    with Session() as session:
        log = session.query(AuditLog).filter_by(event_type="OPERATOR_ACTION").first()
        assert log is not None
        assert log.action == "EMERGENCY_HALT"

def test_log_deployment_event(audit_logger, db_engine):
    audit_logger.log_deployment_event("1.0.1", "production", "Hotfix applied")

    Session = sessionmaker(bind=db_engine)
    with Session() as session:
        log = session.query(AuditLog).filter_by(event_type="DEPLOYMENT_EVENT").first()
        assert log is not None
        assert log.metadata_json["version"] == "1.0.1"
