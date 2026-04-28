import os
import time
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.data_cleanup import cleanup_files, cleanup_db
from src.core.trade_logger import Base, Trade, ModelSignal, RiskEvent, PerformanceMetric

@pytest.fixture
def temp_dirs(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # Create an old log file
    old_log = log_dir / "old.log"
    old_log.write_text("old content")

    # Set modification time to 100 days ago
    old_time = time.time() - (100 * 86400)
    os.utime(old_log, (old_time, old_time))

    # Create a new log file
    new_log = log_dir / "new.log"
    new_log.write_text("new content")

    # Backtest dir
    bt_dir = tmp_path / "backtest"
    bt_dir.mkdir()
    old_bt = bt_dir / "old_result.csv"
    old_bt.write_text("old bt")
    bt_time = time.time() - (200 * 86400)
    os.utime(old_bt, (bt_time, bt_time))

    return {"logs": log_dir, "backtest": bt_dir}

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_trades.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # Create an old trade (should be kept because retention is 7 years)
        old_trade = Trade(
            ticket=1001,
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            lot_size=0.1,
            created_at=datetime.now(timezone.utc) - timedelta(days=365 * 2)
        )
        # Create a VERY old trade (should be deleted)
        very_old_trade = Trade(
            ticket=1000,
            symbol="XAUUSD",
            direction=1,
            entry_price=1900.0,
            lot_size=0.1,
            created_at=datetime.now(timezone.utc) - timedelta(days=365 * 8)
        )

        # Create an old signal (should be deleted because retention is 1 year)
        old_signal = ModelSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2010.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=400)
        )

        # Create an old performance metric (should be archived and deleted)
        old_metric = PerformanceMetric(
            sharpe_ratio=2.5,
            profit_factor=1.8,
            created_at=datetime.now(timezone.utc) - timedelta(days=400)
        )

        session.add_all([old_trade, very_old_trade, old_signal, old_metric])
        session.commit()

    return db_url

def test_cleanup_files(temp_dirs):
    log_dir = temp_dirs["logs"]
    # Run cleanup
    cleanup_files(log_dir, days=90, pattern="*.log")

    assert not (log_dir / "old.log").exists()
    assert (log_dir / "new.log").exists()

    bt_dir = temp_dirs["backtest"]
    cleanup_files(bt_dir, days=180)
    assert not (bt_dir / "old_result.csv").exists()

def test_cleanup_db_and_archival(temp_db, tmp_path):
    # Change to tmp_path to control where 'archives' is created
    os.chdir(tmp_path)

    # Run cleanup
    cleanup_db(temp_db)

    engine = create_engine(temp_db)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        # Check Trades
        trades = session.query(Trade).all()
        assert len(trades) == 1
        assert trades[0].ticket == 1001

        # Check Signals
        signals = session.query(ModelSignal).all()
        assert len(signals) == 0

        # Check Metrics
        metrics = session.query(PerformanceMetric).all()
        assert len(metrics) == 0

    # Verify archival
    archive_dir = tmp_path / "archives"
    assert archive_dir.exists()
    archives = list(archive_dir.glob("performance_metrics_archive_*.csv"))
    assert len(archives) == 1

    with open(archives[0], newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        assert len(rows) == 1
        assert float(rows[0]['sharpe_ratio']) == 2.5
