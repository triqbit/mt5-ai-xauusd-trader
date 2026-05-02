import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from scripts.data_cleanup import cleanup_backtests, cleanup_database, cleanup_logs
from src.core.trade_logger import Base, ModelSignal, PerformanceMetric, RiskEvent, Trade


class TestDataCleanup(unittest.TestCase):
    def setUp(self):
        # Setup temporary database
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db_url = "sqlite:///:memory:"  # Not used directly by cleanup_database in this test but good for reference

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
        count = cleanup_backtests(backtest_dir, dry_run=False)

        self.assertEqual(count, 1)
        self.assertFalse(old_file.exists())
        self.assertFalse(old_subdir.exists())  # Should be removed as empty
        self.assertTrue(new_file.exists())

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

    def test_database_cleanup(self):
        now = datetime.now(timezone.utc)

        with self.Session() as session:
            # 1. Old unlinked signal (should be purged)
            old_unlinked = ModelSignal(
                symbol="XAUUSD",
                direction=1,
                entry_price=2000.0,
                created_at=now - timedelta(days=100),
            )
            # 2. New unlinked signal (should be kept)
            new_unlinked = ModelSignal(
                symbol="XAUUSD",
                direction=1,
                entry_price=2001.0,
                created_at=now - timedelta(days=10),
            )
            # 3. Old linked signal (should be kept because trade is new)
            old_linked = ModelSignal(
                symbol="XAUUSD",
                direction=-1,
                entry_price=2002.0,
                created_at=now - timedelta(days=100),
            )
            session.add_all([old_unlinked, new_unlinked, old_linked])
            session.flush()

            trade = Trade(
                ticket=123,
                symbol="XAUUSD",
                direction=-1,
                entry_price=2002.0,
                lot_size=0.1,
                signal_id=old_linked.id,
                created_at=now - timedelta(days=10),
            )

            # 4. Old Risk Event (should be purged)
            old_risk = RiskEvent(event_type="CIRCUIT_BREAKER", created_at=now - timedelta(days=800))
            # 5. New Risk Event (should be kept)
            new_risk = RiskEvent(event_type="REJECTION", created_at=now - timedelta(days=10))

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

            session.add_all([trade, old_risk, new_risk, old_perf, very_old_trade])
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

        try:
            results = cleanup_database("dummy_url", dry_run=False)
        finally:
            scripts.data_cleanup.create_engine = original_create_engine

        self.assertEqual(results["model_signals"], 1)  # only old_unlinked
        self.assertEqual(results["risk_events"], 1)  # only old_risk
        self.assertEqual(results["performance_metrics"], 1)
        self.assertEqual(results["trades"], 1)  # very_old_trade

        with self.Session() as session:
            signals = session.execute(select(ModelSignal)).scalars().all()
            signal_ids = [s.id for s in signals]
            self.assertIn(new_unlinked_id, signal_ids)
            self.assertIn(old_linked_id, signal_ids)
            self.assertNotIn(old_unlinked_id, signal_ids)

            trades = session.execute(select(Trade)).scalars().all()
            self.assertEqual(len(trades), 1)
            self.assertEqual(trades[0].ticket, 123)


if __name__ == "__main__":
    unittest.main()
