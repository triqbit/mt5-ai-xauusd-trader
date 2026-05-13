import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from scripts.data_cleanup import (
    cleanup_archives,
    cleanup_backtests,
    cleanup_database,
    cleanup_logs,
)
from src.core.audit_log import AuditEntry, Base as AuditBase
from src.core.trade_logger import (
    Base,
    BlockedSignalAnalysis,
    ExecutionQuality,
    ModelSignal,
    PerformanceMetric,
    RiskEvent,
    Trade,
)


class TestDataCleanup(unittest.TestCase):
    def setUp(self):
        # Setup temporary database
        # Use StaticPool to ensure the in-memory database persists across multiple connections from the same engine
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        AuditBase.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db_url = "sqlite:///:memory:" # Not used directly by cleanup_database in this test but good for reference

        # Setup temporary logs directory
        self.test_dir = tempfile.mkdtemp()
        self.logs_dir = Path(self.test_dir) / "logs"
        self.logs_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_backtest_cleanup(self):
        # Setup backtest dir
        backtest_dir = Path(self.test_dir) / "backtests"
        backtest_dir.mkdir()

        archive_dir = Path(self.test_dir) / "archives"
        archive_dir.mkdir()

        old_subdir = backtest_dir / "old_run"
        old_subdir.mkdir()

        old_file = old_subdir / "report.pdf"
        old_file.touch()

        new_file = backtest_dir / "recent_run.json"
        new_file.touch()

        # Set old times
        old_time = (datetime.now() - timedelta(days=400)).timestamp()
        os.utime(old_file, (old_time, old_time))
        os.utime(old_subdir, (old_time, old_time))

        # Run cleanup
        count = cleanup_backtests(backtest_dir, dry_run=False, archive_dir=archive_dir)

        self.assertEqual(count, 1)
        self.assertFalse(old_file.exists())
        self.assertFalse(old_subdir.exists())  # Should be removed as empty
        self.assertTrue(new_file.exists())
        # Verify research archive exists
        self.assertTrue((archive_dir / "research").exists())

    def test_log_cleanup(self):
        # Create some log files
        old_log = self.logs_dir / "old.log"
        new_log = self.logs_dir / "new.log"

        old_log.touch()
        new_log.touch()

        # Manually set mtime for old_log to 100 days ago
        old_time = (datetime.now() - timedelta(days=100)).timestamp()
        os.utime(old_log, (old_time, old_time))

        # Run cleanup
        count = cleanup_logs(self.logs_dir, dry_run=False)

        self.assertEqual(count, 1)
        self.assertFalse(old_log.exists())
        self.assertTrue(new_log.exists())

    def test_archive_cleanup(self):
        archive_dir = Path(self.test_dir) / "archives"
        research_dir = archive_dir / "research"
        research_dir.mkdir(parents=True)

        old_archive = research_dir / "old_archive.tar.gz"
        old_archive.touch()

        new_archive = research_dir / "new_archive.tar.gz"
        new_archive.touch()

        # Set old time (RETENTION_ARCHIVE_RESEARCH is 365 days)
        old_time = (datetime.now() - timedelta(days=400)).timestamp()
        os.utime(old_archive, (old_time, old_time))

        count = cleanup_archives(archive_dir, dry_run=False)
        self.assertEqual(count, 1)
        self.assertFalse(old_archive.exists())
        self.assertTrue(new_archive.exists())

    def test_database_cleanup(self):
        now = datetime.now(timezone.utc)

        with self.Session() as session:
            # 1. Old unlinked signal (should be purged)
            old_unlinked = ModelSignal(
                symbol="XAUUSD", direction=1, entry_price=2000.0,
                created_at=now - timedelta(days=100)
            )
            # 2. New unlinked signal (should be kept)
            new_unlinked = ModelSignal(
                symbol="XAUUSD", direction=1, entry_price=2001.0,
                created_at=now - timedelta(days=10)
            )
            # 3. Old linked signal (should be kept because trade is new)
            old_linked = ModelSignal(
                symbol="XAUUSD", direction=-1, entry_price=2002.0,
                created_at=now - timedelta(days=100)
            )
            session.add_all([old_unlinked, new_unlinked, old_linked])
            session.flush()

            trade = Trade(
                ticket=123, symbol="XAUUSD", direction=-1, entry_price=2002.0,
                lot_size=0.1, signal_id=old_linked.id,
                created_at=now - timedelta(days=10)
            )

            # 4. Old Risk Event (should be purged)
            old_risk = RiskEvent(
                event_type="CIRCUIT_BREAKER", created_at=now - timedelta(days=800)
            )
            # 5. New Risk Event (should be kept)
            new_risk = RiskEvent(
                event_type="REJECTION", created_at=now - timedelta(days=10)
            )

            # 6. Old Perf Metric (should be purged)
            old_perf = PerformanceMetric(
                timestamp=now - timedelta(days=800), created_at=now - timedelta(days=800)
            )

            # 7. Old Trade (older than 7 years, should be purged)
            very_old_trade = Trade(
                ticket=999,
                symbol="XAUUSD",
                direction=1,
                entry_price=1000.0,
                lot_size=0.1,
                created_at=now - timedelta(days=3000),
            )
            session.add(very_old_trade)
            session.flush()

            # 8. Execution Quality for very old trade (should be purged)
            old_eq = ExecutionQuality(
                trade_id=very_old_trade.id,
                slippage_pips=0.5,
                execution_latency_ms=25.0,
                fill_quality_score=0.9,
                edge_capture=0.1,
                timing_efficiency=0.8,
                alpha_decay_pips=0.0,
                execution_cost_pips=0.2,
                created_at=now - timedelta(days=3000),
            )

            # 9. Blocked Signal Analysis for old unlinked signal (should be purged)
            old_bsa = BlockedSignalAnalysis(
                signal_id=old_unlinked.id,
                opportunity_cost_pnl=50.0,
                max_favorable_excursion=10.0,
                max_adverse_excursion=2.0,
                would_have_won=True,
                created_at=now - timedelta(days=100),
            )

            # 10. Audit Log entries
            old_audit = AuditEntry(
                actor="system", action="config_change", created_at=now - timedelta(days=3000)
            )
            new_audit = AuditEntry(
                actor="system", action="startup", created_at=now - timedelta(days=10)
            )

            session.add_all([trade, old_risk, new_risk, old_perf, old_eq, old_bsa, old_audit, new_audit])
            session.commit()

            # Capture IDs while session is still open
            new_unlinked_id = new_unlinked.id
            old_linked_id = old_linked.id
            old_unlinked_id = old_unlinked.id

        # Run cleanup on the in-memory DB
        # We need to monkeypatch create_engine or pass the engine
        import scripts.data_cleanup

        original_create_engine = scripts.data_cleanup.create_engine
        scripts.data_cleanup.create_engine = lambda url: self.engine

        archive_dir = Path(self.test_dir) / "archives"

        try:
            results = cleanup_database("dummy_url", dry_run=False, archive_dir=archive_dir)
        finally:
            scripts.data_cleanup.create_engine = original_create_engine

        self.assertEqual(results["model_signals"], 1)  # only old_unlinked
        self.assertEqual(results["risk_events"], 1)  # only old_risk
        self.assertEqual(results["performance_metrics"], 1)
        self.assertEqual(results["trades"], 1)  # very_old_trade
        self.assertEqual(results["execution_qualities"], 1)
        self.assertEqual(results["blocked_signal_analysis"], 1)
        self.assertEqual(results["audit_log"], 1)

        with self.Session() as session:
            signals = session.execute(select(ModelSignal)).scalars().all()
            signal_ids = [s.id for s in signals]
            self.assertIn(new_unlinked_id, signal_ids)
            self.assertIn(old_linked_id, signal_ids)
            self.assertNotIn(old_unlinked_id, signal_ids)

            trades = session.execute(select(Trade)).scalars().all()
            self.assertEqual(len(trades), 1)
            self.assertEqual(trades[0].ticket, 123)

            eqs = session.execute(select(ExecutionQuality)).scalars().all()
            self.assertEqual(len(eqs), 0)

            bsas = session.execute(select(BlockedSignalAnalysis)).scalars().all()
            self.assertEqual(len(bsas), 0)

            audit_entries = session.execute(select(AuditEntry)).scalars().all()
            self.assertEqual(len(audit_entries), 1)
            self.assertEqual(audit_entries[0].action, "startup")

if __name__ == "__main__":
    unittest.main()
