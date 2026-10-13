"""
End-to-end traceability verification for the audit trail.
Verifies that multiple system events can be linked via trace_id.
"""

import pytest
import structlog.contextvars
import uuid
from src.core.audit_log import AuditLogger, AuditEntry
from src.core.schemas import TradeSignal
from src.trading.audited_risk_manager import AuditedRiskManager
from src.core.config import get_config

@pytest.fixture
def audit_logger():
    # Reset singleton
    AuditLogger._instance = None
    AuditLogger._initialized = False
    return AuditLogger("sqlite:///:memory:")

@pytest.fixture
def risk_manager(audit_logger):
    cfg = get_config()
    return AuditedRiskManager(cfg, account_balance=10000.0)

def test_trace_id_propagation_e2e(audit_logger, risk_manager):
    """
    Test that a single trace_id correctly links a prediction,
    risk decision, and blocked trade event.
    """
    trace_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(trace_id=trace_id)

    # 1. Log a prediction
    audit_logger.log_prediction("XAUUSD", 1, 0.9)

    # 2. Trigger a risk rejection
    # Daily loss limit is 0.05 by default. If we set a signal with huge confidence
    # but the risk manager is in a state that rejects, it should log.
    # To force a rejection, we can use a signal that fails min_confidence if we set it high.
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        confidence=0.1, # Below min_confidence 0.55
        algorithm="ppo"
    )

    risk_manager.approve(signal)

    # 3. Verify all entries have the same trace_id
    with audit_logger.Session() as session:
        entries = session.query(AuditEntry).filter(AuditEntry.trace_id == trace_id).all()

        # Should have:
        # 1. prediction
        # 2. risk_decision (from AuditedRiskManager)
        # 3. trade_blocked (from AuditedRiskManager because risk failed)

        actions = [e.action for e in entries]
        assert "prediction" in actions
        assert "risk_decision" in actions
        assert "trade_blocked" in actions

        for entry in entries:
            assert entry.trace_id == trace_id

def test_blocked_trade_reason_granularity(audit_logger, risk_manager):
    """Verify that blocked trade audit entries contain granular reasons."""
    trace_id = "test-rejection-trace"
    structlog.contextvars.bind_contextvars(trace_id=trace_id)

    # Signal that fails confidence
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        confidence=0.2,
        algorithm="ppo"
    )

    risk_manager.approve(signal)

    with audit_logger.Session() as session:
        blocked_entry = session.query(AuditEntry).filter(
            AuditEntry.action == "trade_blocked",
            AuditEntry.trace_id == trace_id
        ).first()

        assert blocked_entry is not None
        assert "Risk validation failed" in blocked_entry.details
        assert "min_confidence" in blocked_entry.details
        assert blocked_entry.metadata_json["reason"] == "Risk validation failed: min_confidence"
