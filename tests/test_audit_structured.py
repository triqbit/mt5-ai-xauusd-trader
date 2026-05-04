"""
Unit tests for modernized structured AuditLogger.
"""

import pytest
from src.core.audit_log import AuditLogger, AuditEntry
from sqlalchemy import select

@pytest.fixture
def db_url():
    return "sqlite:///:memory:"

@pytest.fixture
def logger(db_url):
    # Reset singleton for testing
    AuditLogger._instance = None
    AuditLogger._initialized = False
    return AuditLogger(db_url)

def test_log_with_metadata(logger):
    metadata = {"key": "value", "nested": {"a": 1}}
    entry_id = logger.log("actor", "action", "details", metadata=metadata)

    with logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.metadata_json == metadata

def test_log_config_snapshot(logger):
    config = {"symbol": "XAUUSD", "mode": "demo", "risk": 0.01}
    entry_id = logger.log_config_snapshot(config)

    with logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "config_snapshot"
        assert entry.metadata_json == config

def test_log_blocked_trade(logger):
    signal_id = 123
    reasons = ["ATR_VOLATILITY", "TREND_ANGLE"]
    context = {"atr": 5.0, "threshold": 3.0}
    entry_id = logger.log_blocked_trade(signal_id, reasons, context)

    with logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "trade_blocked"
        assert entry.metadata_json["signal_id"] == signal_id
        assert entry.metadata_json["reasons"] == reasons
        assert entry.metadata_json["context"] == context

def test_log_prediction(logger):
    symbol = "XAUUSD"
    direction = 1
    confidence = 0.85
    metadata = {"model_id": "ppo_v1"}
    entry_id = logger.log_prediction(symbol, direction, confidence, metadata)

    with logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "prediction_generated"
        assert entry.metadata_json["symbol"] == symbol
        assert entry.metadata_json["direction"] == direction
        assert entry.metadata_json["confidence"] == confidence
        assert entry.metadata_json["model_id"] == "ppo_v1"

def test_log_risk_decision(logger):
    signal_id = 456
    decision = True
    context = {"reason": "All checks passed"}
    entry_id = logger.log_risk_decision(signal_id, decision, context)

    with logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "risk_decision"
        assert entry.metadata_json["decision"] is True
        assert "APPROVED" in entry.details

def test_log_deployment(logger):
    version = "1.2.3"
    environment = "production"
    entry_id = logger.log_deployment(version, environment)

    with logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "deployment_started"
        assert entry.metadata_json["version"] == version
        assert entry.metadata_json["environment"] == environment
