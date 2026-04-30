"""
Tests for scripts/data_cleanup.py
"""
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.data_cleanup import cleanup_directory, cleanup_db
from src.core.trade_logger import Base, Trade, ModelSignal

@pytest.fixture
def temp_logs(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # Create an old log file
    old_log = log_dir / "old.log"
    old_log.write_text("old")
    old_time = time.time() - (100 * 86400) # 100 days ago
    os.utime(old_log, (old_time, old_time))

    # Create a new log file
    new_log = log_dir / "new.log"
    new_log.write_text("new")

    return log_dir

def test_cleanup_logs(temp_logs):
    # Dry run
    count = cleanup_directory(temp_logs, "*.log", 90, dry_run=True)
    assert count == 1
    assert (temp_logs / "old.log").exists()

    # Actual cleanup
    count = cleanup_directory(temp_logs, "*.log", 90, dry_run=False)
    assert count == 1
    assert not (temp_logs / "old.log").exists()
    assert (temp_logs / "new.log").exists()

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_cleanup.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    now = datetime.now(timezone.utc)

    with Session() as session:
        # Old signal (2 years ago)
        old_signal = ModelSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            created_at=now - timedelta(days=400)
        )
        # New signal
        new_signal = ModelSignal(
            symbol="XAUUSD",
            direction=-1,
            entry_price=2010.0,
            created_at=now
        )
        # Old trade (8 years ago, closed)
        old_trade = Trade(
            ticket=123,
            symbol="XAUUSD",
            direction=1,
            entry_price=1800.0,
            lot_size=0.1,
            status="CLOSED",
            created_at=now - timedelta(days=3000)
        )
        # Old trade (8 years ago, OPEN - should NOT be deleted)
        old_open_trade = Trade(
            ticket=456,
            symbol="XAUUSD",
            direction=1,
            entry_price=1800.0,
            lot_size=0.1,
            status="OPEN",
            created_at=now - timedelta(days=3000)
        )

        session.add_all([old_signal, new_signal, old_trade, old_open_trade])
        session.commit()

    return db_url

def test_cleanup_db(temp_db):
    engine = create_engine(temp_db)
    Session = sessionmaker(bind=engine)

    # Run cleanup
    cleanup_db(temp_db, dry_run=False)

    with Session() as session:
        signals = session.query(ModelSignal).all()
        assert len(signals) == 1
        # SQLite doesn't store timezone info easily, so sqlalchemy returns naive datetimes
        # or it depends on how it is configured. Let's make the comparison safe.
        now = datetime.now(timezone.utc)
        sig_created = signals[0].created_at
        if sig_created.tzinfo is None:
            sig_created = sig_created.replace(tzinfo=timezone.utc)
        assert sig_created > now - timedelta(days=1)

        trades = session.query(Trade).all()
        # Should have the new-ish open trade if there was one,
        # and the old OPEN trade.
        # In our fixture we only had one old closed, one old open.
        assert len(trades) == 1
        assert trades[0].ticket == 456
        assert trades[0].status == "OPEN"
