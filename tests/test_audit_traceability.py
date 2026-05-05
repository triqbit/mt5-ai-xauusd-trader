"""
Unit tests for specialized AuditLogger methods and traceability.
"""

import pytest

from src.core.audit_log import AuditEntry, AuditLogger


@pytest.fixture
def audit_logger():
    # Reset singleton for testing
    AuditLogger._instance = None
    AuditLogger._initialized = False
    return AuditLogger("sqlite:///:memory:")

def test_log_config_snapshot(audit_logger):
    config_data = {"SYMBOL": "XAUUSD", "MODE": "live"}
    entry_id = audit_logger.log_config_snapshot(config_data, reason="unit_test")

    with audit_logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "config_snapshot"
        assert entry.metadata_json == config_data
        assert "unit_test" in entry.details

def test_log_prediction(audit_logger):
    metadata = {"weights": [0.5, 0.5]}
    entry_id = audit_logger.log_prediction("XAUUSD", 1, 0.95, metadata)

    with audit_logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "prediction"
        assert entry.metadata_json["symbol"] == "XAUUSD"
        assert entry.metadata_json["direction"] == 1
        assert entry.metadata_json["confidence"] == 0.95
        assert entry.metadata_json["model_context"] == metadata

def test_log_risk_decision(audit_logger):
    decision_chain = {"circuit_breaker": True, "daily_loss": False}
    entry_id = audit_logger.log_risk_decision("XAUUSD", -1, decision_chain, False)

    with audit_logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "risk_decision"
        assert entry.metadata_json["passed"] is False
        assert entry.metadata_json["decision_chain"] == decision_chain

def test_log_blocked_trade(audit_logger):
    context = {"filter": "ATR"}
    entry_id = audit_logger.log_blocked_trade("XAUUSD", "High Volatility", context)

    with audit_logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "trade_blocked"
        assert "High Volatility" in entry.details
        assert entry.metadata_json["context"] == context

def test_log_operator_action(audit_logger):
    entry_id = audit_logger.log_operator_action("admin", "emergency_halt", "System anomaly")

    with audit_logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.actor == "admin"
        assert entry.action == "operator_emergency_halt"
        assert "System anomaly" in entry.details

def test_log_deployment(audit_logger):
    entry_id = audit_logger.log_deployment("1.1.0", "production")

    with audit_logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "deployment"
        assert entry.metadata_json["version"] == "1.1.0"
        assert entry.metadata_json["environment"] == "production"
