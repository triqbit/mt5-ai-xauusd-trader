"""
MT5 AI/ML Trading Bot - Data Cleanup Script
Automates the purging of old operational data based on the Data Retention Policy.
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import sessionmaker

# Add src to path to import models
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.core.config import get_config
from src.core.trade_logger import ModelSignal, PerformanceMetric, RiskEvent, Trade

# -- Setup Logging ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("data_cleanup")

# -- Configuration Constants -----------------------------------------------
# Retention windows in days
RETENTION_LOGS = 90
RETENTION_UNLINKED_SIGNALS = 90
RETENTION_RISK_EVENTS = 2 * 365
RETENTION_PERFORMANCE_METRICS = 2 * 365
RETENTION_TRADES = 7 * 365
RETENTION_BACKTESTS = 365


def cleanup_logs(logs_dir: Path, dry_run: bool = False) -> int:
    """Delete log files older than RETENTION_LOGS days."""
    if not logs_dir.exists():
        logger.info(f"Logs directory {logs_dir} does not exist. Skipping.")
        return 0

    count = 0
    cutoff = datetime.now() - timedelta(days=RETENTION_LOGS)

    logger.info(f"Cleaning up logs in {logs_dir} older than {cutoff.date()}...")

    for log_file in logs_dir.glob("*.log*"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleting old log file: {log_file.name} (mtime: {mtime})")
                if not dry_run:
                    log_file.unlink()
                count += 1
        except Exception as e:
            logger.error(f"Failed to delete log file {log_file}: {e}")

    return count


def cleanup_backtests(backtest_dir: Path, dry_run: bool = False) -> int:
    """Delete backtest results older than RETENTION_BACKTESTS days."""
    if not backtest_dir.exists():
        logger.info(f"Backtest directory {backtest_dir} does not exist. Skipping.")
        return 0

    count = 0
    cutoff = datetime.now() - timedelta(days=RETENTION_BACKTESTS)

    logger.info(f"Cleaning up backtest results in {backtest_dir} older than {cutoff.date()}...")

    # Recursively check for files and directories in backtest_dir
    for item in backtest_dir.rglob("*"):
        if item.is_file():
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime < cutoff:
                    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleting old backtest file: {item.relative_to(backtest_dir)} (mtime: {mtime})")
                    if not dry_run:
                        item.unlink()
                    count += 1
            except Exception as e:
                logger.error(f"Failed to delete backtest file {item}: {e}")

    # After deleting files, attempt to delete empty directories
    for item in sorted(backtest_dir.rglob("*"), reverse=True):
        if item.is_dir() and item != backtest_dir and not any(item.iterdir()):
            try:
                logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleting empty backtest directory: {item.relative_to(backtest_dir)}")
                if not dry_run:
                    item.rmdir()
            except Exception as e:
                logger.error(f"Failed to delete directory {item}: {e}")

    return count


def cleanup_database(db_url: str, dry_run: bool = False) -> dict:
    """Purge old records from the database according to the retention policy."""
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    results = {"model_signals": 0, "risk_events": 0, "performance_metrics": 0, "trades": 0}

    now = datetime.now(timezone.utc)

    with Session() as session:
        # 1. Cleanup Unlinked Model Signals (older than 90 days)
        # We must exclude signals that are linked to trades
        signal_cutoff = now - timedelta(days=RETENTION_UNLINKED_SIGNALS)

        # Subquery for linked signals
        linked_signal_ids = select(Trade.signal_id).where(Trade.signal_id.is_not(None))

        unlinked_signals_query = (
            select(ModelSignal.id)
            .where(ModelSignal.created_at < signal_cutoff)
            .where(ModelSignal.id.not_in(linked_signal_ids))
        )

        unlinked_ids = session.execute(unlinked_signals_query).scalars().all()
        results["model_signals"] = len(unlinked_ids)

        if unlinked_ids:
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Purging {len(unlinked_ids)} unlinked signals older than {signal_cutoff.date()}")
            if not dry_run:
                session.execute(delete(ModelSignal).where(ModelSignal.id.in_(unlinked_ids)))

        # 2. Cleanup Risk Events (older than 2 years)
        risk_cutoff = now - timedelta(days=RETENTION_RISK_EVENTS)
        risk_query = select(RiskEvent.id).where(RiskEvent.created_at < risk_cutoff)
        risk_ids = session.execute(risk_query).scalars().all()
        results["risk_events"] = len(risk_ids)

        if risk_ids:
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Purging {len(risk_ids)} risk events older than {risk_cutoff.date()}")
            if not dry_run:
                session.execute(delete(RiskEvent).where(RiskEvent.id.in_(risk_ids)))

        # 3. Cleanup Performance Metrics (older than 2 years)
        perf_cutoff = now - timedelta(days=RETENTION_PERFORMANCE_METRICS)
        perf_query = select(PerformanceMetric.id).where(PerformanceMetric.created_at < perf_cutoff)
        perf_ids = session.execute(perf_query).scalars().all()
        results["performance_metrics"] = len(perf_ids)

        if perf_ids:
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Purging {len(perf_ids)} performance metrics older than {perf_cutoff.date()}")
            if not dry_run:
                session.execute(delete(PerformanceMetric).where(PerformanceMetric.id.in_(perf_ids)))

        # 4. Cleanup Trades (older than 7 years)
        # Note: This also enables cleanup of linked signals in the next run after 7 years
        trade_cutoff = now - timedelta(days=RETENTION_TRADES)
        trade_query = select(Trade.id).where(Trade.created_at < trade_cutoff)
        trade_ids = session.execute(trade_query).scalars().all()
        results["trades"] = len(trade_ids)

        if trade_ids:
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Purging {len(trade_ids)} trade records older than {trade_cutoff.date()}")
            if not dry_run:
                session.execute(delete(Trade).where(Trade.id.in_(trade_ids)))

        if not dry_run:
            session.commit()

    return results


def main():
    parser = argparse.ArgumentParser(description="MT5 AI/ML Trading Bot - Data Cleanup Utility")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without deleting any data.")
    parser.add_argument("--db-url", help="Override the database URL from config.")
    parser.add_argument("--logs-dir", help="Override the logs directory from config.")
    parser.add_argument("--backtest-dir", help="Override the backtest results directory.")

    args = parser.parse_args()
    cfg = get_config()

    db_url = args.db_url or cfg.database_url.get_secret_value()
    # Ensure we don't accidentally wipe a production PG DB unless intended
    if "sqlite" not in db_url and not args.db_url:
        logger.warning(f"Using production-like DB URL: {db_url}")

    logs_dir = Path(args.logs_dir) if args.logs_dir else cfg.logs_dir
    backtest_dir = Path(args.backtest_dir) if args.backtest_dir else Path(__file__).resolve().parents[1] / "backtest_results"

    logger.info(f"Starting data cleanup (dry_run={args.dry_run})")

    # Filesystem cleanup - Logs
    log_count = cleanup_logs(logs_dir, dry_run=args.dry_run)
    logger.info(f"Log cleanup complete. Total files processed: {log_count}")

    # Filesystem cleanup - Backtests
    backtest_count = cleanup_backtests(backtest_dir, dry_run=args.dry_run)
    logger.info(f"Backtest cleanup complete. Total files processed: {backtest_count}")

    # Database cleanup
    db_results = cleanup_database(db_url, dry_run=args.dry_run)
    logger.info("Database cleanup complete.")
    for table, count in db_results.items():
        logger.info(f"  - {table}: {count} records {'identified' if args.dry_run else 'purged'}")

    logger.info("Cleanup process finished successfully.")


if __name__ == "__main__":
    main()
