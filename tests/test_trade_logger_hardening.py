
import os
import pytest
from sqlalchemy import text
from src.core.trade_logger import TradeLogger

def test_sqlite_hardening_active():
    """Verify that SQLite hardening (WAL, FK) is active."""
    db_file = "test_hardening.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    try:
        logger = TradeLogger(db_url=f"sqlite:///{db_file}")
        with logger.Session() as session:
            # Check WAL mode
            journal_mode = session.execute(text("PRAGMA journal_mode")).scalar()
            assert journal_mode.lower() == "wal"

            # Check Foreign Keys
            fk_enabled = session.execute(text("PRAGMA foreign_keys")).scalar()
            assert fk_enabled == 1

            # Check Synchronous
            sync_mode = session.execute(text("PRAGMA synchronous")).scalar()
            assert sync_mode == 1  # NORMAL
    finally:
        if os.path.exists(db_file):
            os.remove(db_file)

def test_engine_pooling_configuration():
    """Verify that the engine uses QueuePool with correct settings."""
    logger = TradeLogger(db_url="sqlite:///:memory:")
    assert logger.engine.pool.__class__.__name__ == "QueuePool"
    assert logger.engine.pool.size() == 20
    # In SQLAlchemy 2.0, max_overflow is accessible via _max_overflow or similar depending on implementation
    # but we can at least check it's a QueuePool.
