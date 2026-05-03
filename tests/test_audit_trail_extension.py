"""
Tests for the extended audit trail functionality.
"""
import pytest
import os
from datetime import datetime, timezone
from src.core.audit_log import AuditLogger, AuditEntry, get_audit_logger
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def test_db():
    db_url = "sqlite:///:memory:"
    # Reset singleton for testing
    AuditLogger._instance = None
    AuditLogger._initialized = False
    logger = AuditLogger(db_url=db_url)
    return logger

def test_audit_log_config_change(test_db):
    old_cfg = {"risk": 0.01}
    new_cfg = {"risk": 0.02}
    reason = "Manual adjustment"

    test_db.log_config_change(old_cfg, new_cfg, reason)

    with test_db.Session() as session:
        entry = session.query(AuditEntry).filter_by(action="config_change").first()
        assert entry is not None
        assert entry.actor == "system"
        assert entry.details == reason
        assert entry.metadata_json["old"] == old_cfg
        assert entry.metadata_json["new"] == new_cfg

def test_audit_log_trade_blocked(test_db):
    symbol = "XAUUSD"
    reason = "Blocked by execution layer: ATR_VOLATILITY"
    decision_chain = {"ATR_VOLATILITY": False, "TREND_ANGLE": True}

    test_db.log_trade_blocked(symbol, reason, decision_chain)

    with test_db.Session() as session:
        entry = session.query(AuditEntry).filter_by(action="trade_blocked").first()
        assert entry is not None
        assert entry.actor == "risk_engine"
        assert symbol in entry.details
        assert entry.metadata_json["decision_chain"] == decision_chain

def test_audit_log_model_prediction(test_db):
    symbol = "EURUSD"
    direction = 1
    confidence = 0.85
    metadata = {"volatility": 0.002}

    test_db.log_model_prediction(symbol, direction, confidence, metadata)

    with test_db.Session() as session:
        entry = session.query(AuditEntry).filter_by(action="prediction").first()
        assert entry is not None
        assert entry.actor == "ai_model"
        assert entry.metadata_json["direction"] == direction
        assert entry.metadata_json["confidence"] == confidence
        assert entry.metadata_json["volatility"] == 0.002

def test_audit_log_risk_decision(test_db):
    symbol = "GBPUSD"
    passed = True
    decision_chain = {"daily_loss": True, "max_positions": True}

    test_db.log_risk_decision(symbol, passed, decision_chain)

    with test_db.Session() as session:
        entry = session.query(AuditEntry).filter_by(action="risk_decision").first()
        assert entry is not None
        assert entry.metadata_json["passed"] is True
        assert entry.metadata_json["decision_chain"] == decision_chain

def test_audit_log_operator_action(test_db):
    actor = "admin"
    action = "emergency_halt"
    reason = "High volatility detected"

    test_db.log_operator_action(actor, action, reason)

    with test_db.Session() as session:
        entry = session.query(AuditEntry).filter_by(action=action).first()
        assert entry is not None
        assert entry.actor == actor
        assert entry.details == reason

def test_audit_log_deployment_event(test_db):
    version = "1.2.3"
    environment = "production"
    status = "SUCCESS"

    test_db.log_deployment_event(version, environment, status)

    with test_db.Session() as session:
        entry = session.query(AuditEntry).filter_by(action="deployment").first()
        assert entry is not None
        assert entry.metadata_json["version"] == version
        assert entry.metadata_json["status"] == status
