"""
Tests for the Data Cleanup Script and Retention Policy Enforcement.
"""

import os
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from scripts.data_cleanup import (
    RETENTION_AUDIT_LOG,
    RETENTION_BACKTESTS,
    RETENTION_LOGS,
    RETENTION_PERFORMANCE_METRICS,
    RETENTION_RISK_EVENTS,
    RETENTION_TRADES,
    RETENTION_UNLINKED_SIGNALS,
    check_disk_space,
    cleanup_backtests,
    cleanup_database,
    cleanup_logs,
)
from src.core.audit_log import AuditEntry, Base as AuditBase
from src.core.trade_logger import (
    Base as TradeBase,
    ModelSignal,
    PerformanceMetric,
    RiskEvent,
    Trade,
)


@pytest.fixture
def test_env(tmp_path):
    """Setup a temporary environment for cleanup tests."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    backtest_dir = tmp_path / "backtests"
    backtest_dir.mkdir()
    archive_dir = tmp_path / "archives"
    archive_dir.mkdir()

    db_path = tmp_path / "test_trades.db"
    db_url = f"sqlite:///{db_path}"

    audit_db_path = tmp_path / "test_audit.db"
    audit_db_url = f"sqlite:///{audit_db_path}"

    # Initialize Databases
    trade_engine = create_engine(db_url)
    TradeBase.metadata.create_all(trade_engine)
    TradeSession = sessionmaker(bind=trade_engine)

    audit_engine = create_engine(audit_db_url)
    AuditBase.metadata.create_all(audit_engine)
    AuditSession = sessionmaker(bind=audit_engine)

    return {
        "logs_dir": logs_dir,
        "backtest_dir": backtest_dir,
        "archive_dir": archive_dir,
        "db_url": db_url,
        "audit_db_url": audit_db_url,
        "TradeSession": TradeSession,
        "AuditSession": AuditSession
    }

def test_cleanup_logs(test_env):
    logs_dir = test_env["logs_dir"]

    # Create old and new log files
    old_log = logs_dir / "old.log"
    old_log.write_text("old")
    # Use UTC for consistency as per refactored script
    old_time = datetime.now(timezone.utc) - timedelta(days=RETENTION_LOGS + 1)
    os.utime(old_log, (old_time.timestamp(), old_time.timestamp()))

    new_log = logs_dir / "new.log"
    new_log.write_text("new")

    count = cleanup_logs(logs_dir, dry_run=False)

    assert count == 1
    assert not old_log.exists()
    assert new_log.exists()

def test_cleanup_backtests(test_env):
    backtest_dir = test_env["backtest_dir"]
    archive_dir = test_env["archive_dir"]

    # Create old and new backtest results
    old_bt = backtest_dir / "old_result.csv"
    old_bt.write_text("old backtest")
    old_time = datetime.now(timezone.utc) - timedelta(days=RETENTION_BACKTESTS + 1)
    os.utime(old_bt, (old_time.timestamp(), old_time.timestamp()))

    new_bt = backtest_dir / "new_result.csv"
    new_bt.write_text("new backtest")

    count = cleanup_backtests(backtest_dir, dry_run=False, archive_dir=archive_dir)

    assert count == 1
    assert not old_bt.exists()
    assert new_bt.exists()

    # Check if archive exists
    archives = list(archive_dir.glob("research/archive_backtests_*.tar.gz"))
    assert len(archives) == 1
    assert Path(str(archives[0]) + ".sha256").exists()

    # Verify archive content
    with tarfile.open(archives[0], "r:gz") as tar:
        names = tar.getnames()
        assert "old_result.csv" in names

def test_cleanup_database_retention(test_env):
    db_url = test_env["db_url"]
    audit_db_url = test_env["audit_db_url"]
    archive_dir = test_env["archive_dir"]
    TradeSession = test_env["TradeSession"]
    AuditSession = test_env["AuditSession"]

    now = datetime.now(timezone.utc)

    with TradeSession() as session:
        # 1. Unlinked Signal (Old) -> Should be purged
        old_unlinked = ModelSignal(symbol="XAUUSD", direction=1, entry_price=2000.0, created_at=now - timedelta(days=RETENTION_UNLINKED_SIGNALS + 1))

        # 2. Linked Signal to Trade (Old) -> Should be preserved
        old_linked_signal = ModelSignal(symbol="XAUUSD", direction=1, entry_price=2000.0, created_at=now - timedelta(days=RETENTION_UNLINKED_SIGNALS + 1))

        # 3. Linked Signal to RiskEvent (Old) -> Should be preserved
        old_risk_linked_signal = ModelSignal(symbol="XAUUSD", direction=1, entry_price=2000.0, created_at=now - timedelta(days=RETENTION_UNLINKED_SIGNALS + 1))

        session.add_all([old_unlinked, old_linked_signal, old_risk_linked_signal])
        session.commit()

        old_linked_signal_id = old_linked_signal.id
        old_risk_linked_signal_id = old_risk_linked_signal.id

        # Trade linked to the old signal (New)
        new_trade = Trade(ticket=123, symbol="XAUUSD", direction=1, entry_price=2000.0, lot_size=0.1, signal_id=old_linked_signal_id, created_at=now)
        # Old Trade -> Should be archived and purged
        old_trade = Trade(ticket=456, symbol="XAUUSD", direction=1, entry_price=1900.0, lot_size=0.1, created_at=now - timedelta(days=RETENTION_TRADES + 1))

        # Risk Event linked to signal (New) -> Signal should be preserved
        new_risk = RiskEvent(event_type="CIRCUIT_BREAKER", description="test", signal_id=old_risk_linked_signal_id, created_at=now)

        # Old Risk Event -> Should be archived and purged
        old_risk = RiskEvent(event_type="CIRCUIT_BREAKER", description="test", created_at=now - timedelta(days=RETENTION_RISK_EVENTS + 1))

        # Old Performance Metric -> Should be archived and purged
        old_perf = PerformanceMetric(sharpe_ratio=1.5, created_at=now - timedelta(days=RETENTION_PERFORMANCE_METRICS + 1))

        session.add_all([new_trade, old_trade, new_risk, old_risk, old_perf])
        session.commit()

    with AuditSession() as session:
        # Old Audit Entry -> Should be archived and purged
        old_audit = AuditEntry(action="TEST", actor="SYS", created_at=now - timedelta(days=RETENTION_AUDIT_LOG + 1))
        session.add(old_audit)
        session.commit()

    # Run Cleanup
    results = cleanup_database(db_url, audit_db_url=audit_db_url, dry_run=False, archive_dir=archive_dir)

    assert results["model_signals"] == 1 # only the unlinked one
    assert results["risk_events"] == 1
    assert results["performance_metrics"] == 1
    assert results["trades"] == 1
    assert results["audit_log"] == 1

    # Verify DB state
    with TradeSession() as session:
        # Check ModelSignal
        signals = session.execute(select(ModelSignal).order_by(ModelSignal.id)).scalars().all()
        assert len(signals) == 2
        signal_ids = [s.id for s in signals]
        assert old_linked_signal_id in signal_ids
        assert old_risk_linked_signal_id in signal_ids

        # Check Trades
        trades = session.execute(select(Trade)).scalars().all()
        assert len(trades) == 1
        assert trades[0].ticket == 123

        # Check RiskEvents
        risks = session.execute(select(RiskEvent)).scalars().all()
        assert len(risks) == 1
        assert risks[0].event_type == "CIRCUIT_BREAKER"

        # Check Performance Metrics
        perfs = session.execute(select(PerformanceMetric)).scalars().all()
        assert len(perfs) == 0

    with AuditSession() as session:
        audits = session.execute(select(AuditEntry)).scalars().all()
        assert len(audits) == 0

    # Verify Archives
    assert len(list(archive_dir.glob("audit/archive_risk_events_*.csv"))) == 1
    assert len(list(archive_dir.glob("performance/archive_performance_metrics_*.csv"))) == 1
    assert len(list(archive_dir.glob("compliance/archive_trades_*.csv"))) == 1
    assert len(list(archive_dir.glob("audit/archive_audit_log_*.csv"))) == 1
    assert len(list(archive_dir.glob("**/*.sha256"))) >= 4

def test_check_disk_space(test_env):
    archive_dir = test_env["archive_dir"]

    # Should pass on normal systems
    assert check_disk_space(archive_dir, min_mb=1) is True

    # Should fail if we ask for an impossible amount (e.g. 1000 TB)
    assert check_disk_space(archive_dir, min_mb=1000 * 1024 * 1024) is False
