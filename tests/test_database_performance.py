import logging
from unittest.mock import patch

from sqlalchemy import create_engine, text

from src.core.database import SLOW_QUERY_THRESHOLD, get_engine


def test_sqlite_pragmas_applied(tmp_path):
    """
    Verify that the hardened SQLite pragmas are applied to new connections.
    """
    # Use a file-based SQLite because :memory: doesn't support WAL mode
    db_file = tmp_path / "test_pragmas.db"
    db_url = f"sqlite:///{db_file}"

    # Use a fresh engine to ensure the connect event triggers
    get_engine.cache_clear()
    engine = get_engine(db_url)

    with engine.connect() as conn:
        # Check foreign keys
        fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert fk == 1 or fk == "ON"

        # Check journal mode
        jm = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert jm.lower() == "wal"

        # Check busy timeout
        bt = conn.execute(text("PRAGMA busy_timeout")).scalar()
        assert bt == 5000

        # Check synchronous mode
        sync = conn.execute(text("PRAGMA synchronous")).scalar()
        # 1 = NORMAL
        assert sync == 1 or sync == "NORMAL"


def test_slow_query_logging(caplog):
    """
    Verify that slow queries trigger a warning log.
    """
    caplog.set_level(logging.WARNING)

    # We'll use a real engine but mock time.perf_counter to simulate a delay
    engine = create_engine("sqlite:///:memory:")

    # The listeners are already registered globally on the Engine class in src.core.database
    # But for this test, we want to ensure they are active.
    # Since they are registered on the 'Engine' class, they should apply to any engine instance.

    # Mock time.perf_counter to return 0.0 then 2.0 (exceeding 1.0s threshold)
    with patch("src.core.database.time.perf_counter") as mock_time:
        mock_time.side_effect = [10.0, 10.0 + SLOW_QUERY_THRESHOLD + 0.1]

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    # Check if the warning was logged
    assert any("Slow query detected" in record.message for record in caplog.records)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_fast_query_no_logging(caplog):
    """
    Verify that fast queries do NOT trigger a warning log.
    """
    caplog.set_level(logging.WARNING)
    caplog.clear()

    engine = create_engine("sqlite:///:memory:")

    with patch("src.core.database.time.perf_counter") as mock_time:
        mock_time.side_effect = [10.0, 10.0 + SLOW_QUERY_THRESHOLD - 0.1]

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    # Check if the warning was NOT logged
    assert not any("Slow query detected" in record.message for record in caplog.records)
