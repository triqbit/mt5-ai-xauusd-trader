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

def test_log_trade_outcome(audit_logger):
    metadata = {"entry": 2000.0, "exit": 2010.0}
    entry_id = audit_logger.log_trade_outcome(12345, "XAUUSD", 100.0, "market_close", metadata)

    with audit_logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "trade_outcome"
        assert entry.metadata_json["ticket"] == 12345
        assert entry.metadata_json["pnl"] == 100.0
        assert entry.metadata_json["context"] == metadata

def test_log_config_change(audit_logger):
    old = {"MODE": "demo"}
    new = {"MODE": "live"}
    entry_id = audit_logger.log_config_change(old, new, "Manual switch")

    with audit_logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "config_change"
        assert entry.metadata_json["old"] == old
        assert entry.metadata_json["new"] == new
        assert "Manual switch" in entry.details

def test_log_operator_action_refined(audit_logger):
    # Test the refined version of log_operator_action
    entry_id = audit_logger.log_operator_action("admin", "emergency_halt", "System anomaly", {"extra": "data"})

    with audit_logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.actor == "admin"
        assert entry.action == "operator_emergency_halt"
        assert entry.metadata_json["action_type"] == "emergency_halt"
        assert entry.metadata_json["reason"] == "System anomaly"
        assert entry.metadata_json["extra"] == "data"


def test_log_system_restored(audit_logger):
    """Test logging a system restoration event."""
    incident_id = "INC-123"
    details = "Manual DB restore completed"
    entry_id = audit_logger.log_system_restored(incident_id=incident_id, details=details)

    with audit_logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)

    assert entry is not None
    assert entry.actor == "system"
    assert entry.action == "system_restored"
    assert entry.details == details
    assert entry.metadata_json["incident_id"] == incident_id
