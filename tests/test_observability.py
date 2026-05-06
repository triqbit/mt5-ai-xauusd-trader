"""
Tests for end-to-end trace correlation and observability.
"""

import uuid
import structlog
import pytest
from src.core.audit_log import AuditLogger, AuditEntry

@pytest.fixture
def audit_logger():
    # Reset singleton for testing
    AuditLogger._instance = None
    AuditLogger._initialized = False
    return AuditLogger("sqlite:///:memory:")

def test_trace_id_propagation(audit_logger):
    """
    Verify that trace_id bound in structlog context is automatically
    captured by the AuditLogger.
    """
    # 1. Setup structlog with contextvars processor
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.JSONRenderer()
        ]
    )

    # 2. Generate and bind a trace_id
    test_trace_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(trace_id=test_trace_id)

    try:
        # 3. Log something via AuditLogger
        entry_id = audit_logger.log(
            actor="test_actor",
            action="test_action",
            details="Verifying trace propagation"
        )

        # 4. Verify the entry has the correct trace_id
        with audit_logger.Session() as session:
            entry = session.get(AuditEntry, entry_id)
            assert entry.trace_id == test_trace_id

    finally:
        # Cleanup
        structlog.contextvars.clear_contextvars()

def test_trace_id_changes_between_contexts(audit_logger):
    """
    Verify that different contexts result in different trace_ids in the audit log.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.JSONRenderer()
        ]
    )

    # Context 1
    trace1 = "trace-1"
    structlog.contextvars.bind_contextvars(trace_id=trace1)
    id1 = audit_logger.log("actor1", "action1")
    structlog.contextvars.clear_contextvars()

    # Context 2
    trace2 = "trace-2"
    structlog.contextvars.bind_contextvars(trace_id=trace2)
    id2 = audit_logger.log("actor2", "action2")
    structlog.contextvars.clear_contextvars()

    with audit_logger.Session() as session:
        entry1 = session.get(AuditEntry, id1)
        entry2 = session.get(AuditEntry, id2)

        assert entry1.trace_id == "trace-1"
        assert entry2.trace_id == "trace-2"
        assert entry1.trace_id != entry2.trace_id

def test_no_trace_id(audit_logger):
    """
    Verify behavior when no trace_id is present in the context.
    """
    structlog.contextvars.clear_contextvars()

    entry_id = audit_logger.log("actor", "action")

    with audit_logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.trace_id is None
