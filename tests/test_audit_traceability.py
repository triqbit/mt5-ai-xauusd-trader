"""
Unit tests for specialized AuditLogger methods and traceability.
"""

import pytest
from src.core.audit_log import AuditEntry, AuditLogger
from src.core.database import DatabaseManager, Base

@pytest.fixture
def audit_logger():
    # Reset singleton for testing
    if DatabaseManager._instance:
        DatabaseManager._instance._initialized = False
    DatabaseManager("sqlite:///:memory:")
    Base.metadata.create_all(DatabaseManager.get_instance().engine)

    AuditLogger._instance = None
    AuditLogger._initialized = False
    return AuditLogger()

def test_log_config_snapshot(audit_logger):
    config_data = {"SYMBOL": "XAUUSD", "MODE": "live"}
    entry_id = audit_logger.log_config_snapshot(config_data, reason="unit_test")

    from src.core.database import get_db_manager
    with get_db_manager().get_session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "config_snapshot"
        assert entry.metadata_json == config_data
        assert "unit_test" in entry.details

def test_log_prediction(audit_logger):
    metadata = {"weights": [0.5, 0.5]}
    entry_id = audit_logger.log_prediction("XAUUSD", 1, 0.95, metadata)

    from src.core.database import get_db_manager
    with get_db_manager().get_session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "prediction"
        assert entry.metadata_json["symbol"] == "XAUUSD"
        assert entry.metadata_json["direction"] == 1
        assert entry.metadata_json["confidence"] == 0.95
        assert entry.metadata_json["model_context"] == metadata

def test_log_risk_decision(audit_logger):
    decision_chain = {"circuit_breaker": True, "daily_loss": False}
    entry_id = audit_logger.log_risk_decision("XAUUSD", -1, decision_chain, False)

    from src.core.database import get_db_manager
    with get_db_manager().get_session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "risk_decision"
        assert entry.metadata_json["passed"] is False
        assert entry.metadata_json["decision_chain"] == decision_chain

def test_log_blocked_trade(audit_logger):
    context = {"filter": "ATR"}
    entry_id = audit_logger.log_blocked_trade("XAUUSD", "High Volatility", context)

    from src.core.database import get_db_manager
    with get_db_manager().get_session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "trade_blocked"
        assert "High Volatility" in entry.details
        assert entry.metadata_json["context"] == context

def test_log_operator_action(audit_logger):
    entry_id = audit_logger.log_operator_action("admin", "emergency_halt", "System anomaly")

    from src.core.database import get_db_manager
    with get_db_manager().get_session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.actor == "admin"
        assert entry.action == "operator_emergency_halt"
        assert "System anomaly" in entry.details

def test_log_deployment(audit_logger):
    entry_id = audit_logger.log_deployment("1.1.0", "production")

    from src.core.database import get_db_manager
    with get_db_manager().get_session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "deployment"
        assert entry.metadata_json["version"] == "1.1.0"
        assert entry.metadata_json["environment"] == "production"

def test_log_trade_outcome(audit_logger):
    metadata = {"entry": 2000.0, "exit": 2010.0}
    entry_id = audit_logger.log_trade_outcome(12345, "XAUUSD", 100.0, "market_close", metadata)

    from src.core.database import get_db_manager
    with get_db_manager().get_session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "trade_outcome"
        assert entry.metadata_json["ticket"] == 12345
        assert entry.metadata_json["pnl"] == 100.0
        assert entry.metadata_json["context"] == metadata

def test_log_config_change(audit_logger):
    old = {"MODE": "demo"}
    new = {"MODE": "live"}
    entry_id = audit_logger.log_config_change(old, new, "Manual switch")

    from src.core.database import get_db_manager
    with get_db_manager().get_session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.action == "config_change"
        assert entry.metadata_json["old"] == old
        assert entry.metadata_json["new"] == new
        assert "Manual switch" in entry.details

def test_log_operator_action_refined(audit_logger):
    # Test the refined version of log_operator_action
    entry_id = audit_logger.log_operator_action("admin", "emergency_halt", "System anomaly", {"extra": "data"})

    from src.core.database import get_db_manager
    with get_db_manager().get_session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.actor == "admin"
        assert entry.action == "operator_emergency_halt"
        assert entry.metadata_json["action_type"] == "emergency_halt"
        assert entry.metadata_json["reason"] == "System anomaly"
        assert entry.metadata_json["extra"] == "data"
