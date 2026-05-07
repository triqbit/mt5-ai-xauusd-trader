import pytest
import os
from src.core.audit_log import AuditLogger, AuditEntry, Base
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

def test_log_mt5_status():
    db_url = "sqlite:///test_audit_slo.db"
    if os.path.exists("test_audit_slo.db"):
        os.remove("test_audit_slo.db")

    # AuditLogger is a singleton
    try:
        logger = AuditLogger(db_url=db_url)
    except Exception:
        logger = AuditLogger.get_instance()

    # Clear and recreate tables for this test
    Base.metadata.drop_all(logger.engine)
    Base.metadata.create_all(logger.engine)

    # Log status
    logger.log_mt5_status("connected", details="Test connection")
    logger.log_mt5_status("disconnected", details="Test disconnection")

    # Verify in DB
    with logger.Session() as session:
        entries = session.execute(select(AuditEntry).where(AuditEntry.action == "mt5_connection_status")).scalars().all()
        assert len(entries) == 2
        assert entries[0].metadata_json["status"] == "connected"
        assert "Test connection" in entries[0].details
        assert entries[1].metadata_json["status"] == "disconnected"
        assert "Test disconnection" in entries[1].details

    if os.path.exists("test_audit_slo.db"):
        os.remove("test_audit_slo.db")
