#!/usr/bin/env python3
"""
MT5 AI/ML Trading Bot - Data Cleanup Script
Enforces retention policies by purging old logs and database records.
Note: This script performs permanent deletion (Purge/Delete actions).
Archival to cold storage (Archive action) must be performed manually or via a separate process.

Author : triqbit
License: MIT
"""

import argparse
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import sessionmaker

from src.core.config import get_config
from src.core.trade_logger import ModelSignal, PerformanceMetric, RiskEvent, Trade

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger("data_cleanup")

# Retention periods (in days)
RETENTION_LOGS = 90
RETENTION_SIGNALS = 365
RETENTION_RISK_EVENTS = 730
RETENTION_PERFORMANCE = 1095
RETENTION_TRADES = 2555  # 7 years
RETENTION_BACKTESTS = 365
RETENTION_TICKS = 90
RETENTION_OHLCV = 1825  # 5 years


def cleanup_directory(directory: Path, pattern: str, retention_days: int, dry_run: bool = False) -> int:
    """Delete files in a directory matching a pattern older than retention_days."""
    dir_path = Path(directory)
    if not dir_path.exists():
        logger.warning("Directory %s does not exist.", dir_path)
        return 0

    count = 0
    now = time.time()
    cutoff = now - (retention_days * 86400)

    for file_path in dir_path.glob(pattern):
        if file_path.is_file() and file_path.stat().st_mtime < cutoff:
            logger.info("Found old file: %s", file_path.name)
            count += 1
            if not dry_run:
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.error("Failed to delete %s: %s", file_path, e)

    logger.info("Cleanup in %s: %d files %s.", dir_path, count, "would be deleted" if dry_run else "deleted")
    return count


def cleanup_db(db_url: str, dry_run: bool = False) -> None:
    """Purge old records from the database."""
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    now = datetime.now(timezone.utc)

    with Session() as session:
        # 1. Model Signals (1 year)
        signal_cutoff = now - timedelta(days=RETENTION_SIGNALS)
        q_signals = delete(ModelSignal).where(ModelSignal.created_at < signal_cutoff)

        # 2. Risk Events (2 years)
        risk_cutoff = now - timedelta(days=RETENTION_RISK_EVENTS)
        q_risk = delete(RiskEvent).where(RiskEvent.created_at < risk_cutoff)

        # 3. Performance Metrics (3 years)
        perf_cutoff = now - timedelta(days=RETENTION_PERFORMANCE)
        q_perf = delete(PerformanceMetric).where(PerformanceMetric.created_at < perf_cutoff)

        # 4. Trades (7 years) - SAFE DELETE: only closed trades
        trade_cutoff = now - timedelta(days=RETENTION_TRADES)
        q_trades = delete(Trade).where(
            Trade.created_at < trade_cutoff,
            Trade.status != "OPEN"
        )

        if dry_run:
            logger.info("Dry run: Database records older than their respective retention periods would be purged.")
        else:
            try:
                res_signals = session.execute(q_signals)
                res_risk = session.execute(q_risk)
                res_perf = session.execute(q_perf)
                res_trades = session.execute(q_trades)

                # 5. Market Data (Optional tables, use raw SQL for flexibility)
                ohlcv_cutoff = now - timedelta(days=RETENTION_OHLCV)
                tick_cutoff = now - timedelta(days=RETENTION_TICKS)

                # We use try/except for each table in case they don't exist yet
                for table, cutoff, label in [
                    ("market_data", ohlcv_cutoff, "OHLCV"),
                    ("tick_data", tick_cutoff, "Ticks")
                ]:
                    try:
                        # Check table existence before deleting
                        # This varies by dialect, but a simple DELETE will just fail if table missing
                        res = session.execute(
                            text(f"DELETE FROM {table} WHERE created_at < :cutoff"),
                            {"cutoff": cutoff}
                        )
                        logger.info("DB cleanup %s: %d rows deleted", label, res.rowcount)
                    except Exception:
                        # Silently skip if table doesn't exist
                        logger.debug("Table %s not found or cleanup failed, skipping.", table)

                session.commit()
                logger.info(
                    "DB cleanup complete: Signals=%d, RiskEvents=%d, Performance=%d, Trades=%d",
                    res_signals.rowcount,
                    res_risk.rowcount,
                    res_perf.rowcount,
                    res_trades.rowcount
                )
            except Exception as e:
                session.rollback()
                logger.error("Database cleanup failed: %s", e)


def main():
    parser = argparse.ArgumentParser(description="Enforce data retention policies.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting.")
    parser.add_argument("--db-url", help="Override database URL.")
    args = parser.parse_args()

    cfg = get_config()

    logger.info("Starting data cleanup %s...", "[DRY RUN]" if args.dry_run else "")

    # Cleanup Application Logs
    cleanup_directory(cfg.logs_dir, "*.log", RETENTION_LOGS, dry_run=args.dry_run)

    # Cleanup Backtest Results
    backtests_dir = cfg.data_dir / "backtests"
    cleanup_directory(backtests_dir, "*.*", RETENTION_BACKTESTS, dry_run=args.dry_run)

    # Cleanup Database
    db_url = args.db_url or cfg.database_url
    cleanup_db(db_url, dry_run=args.dry_run)

    logger.info("Data cleanup finished.")


if __name__ == "__main__":
    main()
