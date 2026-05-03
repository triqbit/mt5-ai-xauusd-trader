import pytest
import os
from src.core.audit_log import AuditLogger, AuditCategory, get_audit_logger


@pytest.fixture
def temp_db():
    db_path = "test_audit.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    yield f"sqlite:///{db_path}"
    if os.path.exists(db_path):
        os.remove(db_path)


def test_audit_logger_initialization(temp_db):
    # Reset singleton for test
    AuditLogger._instance = None
    logger = AuditLogger(db_url=temp_db)
    assert logger._initialized is True
    assert get_audit_logger() is logger


def test_audit_logging(temp_db):
    AuditLogger._instance = None
    logger = AuditLogger(db_url=temp_db)

    logger.log(
        category=AuditCategory.RISK,
        event_type="TEST_EVENT",
        description="This is a test audit entry",
        metadata={"key": "value"},
    )

    with logger.Session() as session:
        from src.core.audit_log import AuditEntry

        entry = session.query(AuditEntry).filter_by(event_type="TEST_EVENT").first()
        assert entry is not None
        assert entry.category == "RISK"
        assert entry.description == "This is a test audit entry"
        assert entry.metadata_json == {"key": "value"}


def test_audit_logger_singleton():
    AuditLogger._instance = None
    logger1 = AuditLogger(db_url="sqlite:///test1.db")
    logger2 = AuditLogger(db_url="sqlite:///test2.db")
    assert logger1 is logger2
    # Second init should be ignored if already initialized

    if os.path.exists("test1.db"):
        os.remove("test1.db")
    if os.path.exists("test2.db"):
        os.remove("test2.db")
