
import pytest
from src.core.trade_logger import TradeLogger
from src.core.audit_log import AuditLog

def test_audit_log_creation(tmp_path):
    db_file = tmp_path / "test_audit.db"
    db_url = f"sqlite:///{db_file}"
    logger = TradeLogger(db_url=db_url)

    # Test logging a config change
    logger.audit.log_config_change(
        reason="Test update",
        old_config={"param": 1},
        new_config={"param": 2}
    )

    # Verify in DB
    with logger.Session() as session:
        logs = session.query(AuditLog).all()
        assert len(logs) == 1
        assert logs[0].event_type == "CONFIG_CHANGE"
        assert logs[0].details["new_state"]["param"] == 2

def test_audit_risk_decision(tmp_path):
    db_file = tmp_path / "test_risk_audit.db"
    db_url = f"sqlite:///{db_file}"
    logger = TradeLogger(db_url=db_url)

    decision_chain = {"filter1": True, "filter2": False}
    logger.audit.log_risk_decision(passed=False, decision_chain=decision_chain)

    with logger.Session() as session:
        log = session.query(AuditLog).filter_by(event_type="RISK_DECISION").first()
        assert log is not None
        assert log.details["passed"] is False
        assert log.details["decision_chain"]["filter2"] is False

def test_audit_operator_action(tmp_path):
    db_file = tmp_path / "test_op_audit.db"
    db_url = f"sqlite:///{db_file}"
    logger = TradeLogger(db_url=db_url)

    logger.audit.log_operator_action(action="MANUAL_HALT", reason="Security breach")

    with logger.Session() as session:
        log = session.query(AuditLog).filter_by(event_type="OPERATOR_ACTION").first()
        assert log is not None
        assert "Security breach" in log.description
