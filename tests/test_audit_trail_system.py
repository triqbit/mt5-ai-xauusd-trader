"""
Tests for the enhanced Audit Trail system.
"""

import os
import pytest
from datetime import datetime, timezone
from src.core.audit_log import AuditLogger, AuditEntry, get_audit_logger
from src.trading.risk_manager import RiskManager, TradeSignal
from src.core.config import TradingConfig

@pytest.fixture
def db_url():
    return "sqlite:///test_audit.db"

@pytest.fixture
def audit_logger(db_url):
    # Reset singleton for testing
    AuditLogger._instance = None
    AuditLogger._initialized = False
    logger = AuditLogger(db_url=db_url)
    yield logger
    # Cleanup
    if os.path.exists("test_audit.db"):
        os.remove("test_audit.db")

def test_audit_logger_specialized_methods(audit_logger):
    # Test Deployment Log
    audit_logger.log_deployment(version="1.1.0", environment="production")

    # Test Config Snapshot
    audit_logger.log_config_snapshot({"symbol": "XAUUSD", "risk": 0.01}, reason="test")

    # Test Blocked Trade
    audit_logger.log_blocked_trade(symbol="XAUUSD", reason="ATR_VOLATILITY", details="High volatility")

    # Test Prediction
    audit_logger.log_prediction(symbol="XAUUSD", direction=1, confidence=0.85, model_name="ensemble")

    # Test Risk Decision
    audit_logger.log_risk_decision(symbol="XAUUSD", passed=False, decision_chain={"max_positions": False})

    # Test Operator Action
    audit_logger.log_operator_action(actor="operator", action="manual_halt", details="Emergency stop")

    with audit_logger.Session() as session:
        entries = session.query(AuditEntry).all()
        assert len(entries) == 6

        # Verify specific entries
        deploy_entry = next(e for e in entries if e.action == "release_deployment")
        assert deploy_entry.metadata_json["version"] == "1.1.0"

        config_entry = next(e for e in entries if e.action == "config_snapshot")
        assert config_entry.metadata_json["symbol"] == "XAUUSD"

        blocked_entry = next(e for e in entries if e.action == "trade_blocked")
        assert "ATR_VOLATILITY" in blocked_entry.details

        prediction_entry = next(e for e in entries if e.action == "prediction_generated")
        assert prediction_entry.metadata_json["confidence"] == 0.85

        risk_entry = next(e for e in entries if e.action == "risk_decision")
        assert risk_entry.metadata_json["decision_chain"]["max_positions"] is False

        halt_entry = next(e for e in entries if e.action == "manual_halt")
        assert halt_entry.actor == "operator"

def test_risk_manager_audit_integration(audit_logger):
    # Use max_positions=1 and fill it up to force rejection
    config = TradingConfig(
        mt5_password="test",
        mt5_server="test",
        max_positions=1
    )
    risk_manager = RiskManager(config=config, account_balance=10000.0)
    risk_manager.open_positions = {"EXISTING": 12345} # Occupy the only slot

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.9
    )

    passed = risk_manager.approve(signal)
    assert passed is False

    with audit_logger.Session() as session:
        risk_entry = session.query(AuditEntry).filter(AuditEntry.action == "risk_decision").first()
        assert risk_entry is not None
        assert risk_entry.metadata_json["passed"] is False
        assert risk_entry.metadata_json["decision_chain"]["max_positions"] is False
        assert risk_entry.metadata_json["decision_chain"]["circuit_breaker"] is True
