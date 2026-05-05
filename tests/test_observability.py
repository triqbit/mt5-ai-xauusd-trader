import uuid
import structlog
import pytest
from src.core.audit_log import AuditLogger, AuditEntry
from src.core.log_config import configure_logging

def test_trace_id_propagation():
    """Verify that trace_id bound in structlog is captured by AuditLogger."""
    # Setup
    configure_logging(level="DEBUG")
    db_url = "sqlite:///:memory:"
    logger = AuditLogger(db_url=db_url)

    trace_id = str(uuid.uuid4())

    # Bind trace_id to context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=trace_id)

    # Log an action
    audit_id = logger.log(actor="test_actor", action="test_action", details="test_details")

    # Verify
    with logger.Session() as session:
        entry = session.query(AuditEntry).filter(AuditEntry.id == audit_id).first()
        assert entry is not None
        assert entry.trace_id == trace_id
        assert entry.actor == "test_actor"
        assert entry.action == "test_action"

def test_manual_trace_id_override():
    """Verify that manually provided trace_id takes precedence."""
    configure_logging(level="DEBUG")
    db_url = "sqlite:///:memory:"
    logger = AuditLogger(db_url=db_url)

    context_trace_id = "context-id"
    manual_trace_id = "manual-id"

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=context_trace_id)

    # Log with manual override
    audit_id = logger.log(
        actor="test_actor",
        action="test_action",
        trace_id=manual_trace_id
    )

    with logger.Session() as session:
        entry = session.query(AuditEntry).filter(AuditEntry.id == audit_id).first()
        assert entry.trace_id == manual_trace_id

def test_no_trace_id():
    """Verify logging works even without a trace_id."""
    db_url = "sqlite:///:memory:"
    logger = AuditLogger(db_url=db_url)

    structlog.contextvars.clear_contextvars()

    audit_id = logger.log(actor="test_actor", action="test_action")

    with logger.Session() as session:
        entry = session.query(AuditEntry).filter(AuditEntry.id == audit_id).first()
        assert entry.trace_id is None
