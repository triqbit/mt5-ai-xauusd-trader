"""
MT5 AI/ML Trading Bot - Data Cleanup Script
scripts/data_cleanup.py
Enforces data retention policies by purging old records and logs.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

# Add src to path to import models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.trade_logger import ModelSignal, PerformanceMetric, RiskEvent, Trade

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

RETENTION_POLICIES = {
    "logs": 90,  # Days
    "model_signals": 365,  # 1 Year
    "trades": 7 * 365,  # 7 Years
    "risk_events": 7 * 365,  # 7 Years
    "performance_metrics": 7 * 365,  # 7 Years
    "backtest_results": 2 * 365,  # 2 Years
}


def purge_db_records(db_url: str, dry_run: bool = False):
    """Purge old records from the database based on retention policies."""
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)

    now = datetime.now(timezone.utc)

    with Session() as session:
        # Table mapping for convenience
        tables = [
            (ModelSignal, RETENTION_POLICIES["model_signals"]),
            (Trade, RETENTION_POLICIES["trades"]),
            (RiskEvent, RETENTION_POLICIES["risk_events"]),
            (PerformanceMetric, RETENTION_POLICIES["performance_metrics"]),
        ]

        for model_class, days in tables:
            cutoff_date = now - timedelta(days=days)

            # Compliance Warning for Trade Records and Risk Events
            if model_class in [Trade, RiskEvent] and not dry_run:
                logger.warning(
                    f"COMPLIANCE NOTICE: {model_class.__tablename__} requires 'Archive then Purge'. "
                    "Ensure data is backed up to long-term storage before continuing."
                )

            # Both ModelSignal and other tables have created_at or similar
            # ModelSignal has 'timestamp', others use 'created_at' from AuditMixin
            date_col = getattr(model_class, "created_at", getattr(model_class, "timestamp", None))

            if date_col is None:
                logger.error(f"Could not find date column for {model_class.__tablename__}")
                continue

            # Count records to be deleted
            count_query = session.query(model_class).filter(date_col < cutoff_date)
            count = count_query.count()

            if count > 0:
                if dry_run:
                    logger.info(f"[DRY-RUN] Would delete {count} records from {model_class.__tablename__} (older than {cutoff_date})")
                else:
                    logger.info(f"Deleting {count} records from {model_class.__tablename__} (older than {cutoff_date})")
                    stmt = delete(model_class).where(date_col < cutoff_date)
                    session.execute(stmt)
            else:
                logger.info(f"No records to purge for {model_class.__tablename__}")

        if not dry_run:
            session.commit()


def purge_backtest_results(backtest_dir: str, dry_run: bool = False):
    """Purge old backtest results (e.g., CSV, JSON, PNG) from the filesystem."""
    backtest_path = Path(backtest_dir)
    if not backtest_path.exists():
        logger.info(f"Backtest directory {backtest_dir} does not exist. Skipping.")
        return

    now = time.time()
    cutoff_sec = RETENTION_POLICIES["backtest_results"] * 24 * 60 * 60

    count = 0
    # Search for common backtest artifact extensions
    for artifact in backtest_path.rglob("*"):
        if artifact.is_file() and artifact.suffix.lower() in [".csv", ".json", ".png", ".html"]:
            try:
                file_age = now - artifact.stat().st_mtime
                if file_age > cutoff_sec:
                    if dry_run:
                        logger.info(f"[DRY-RUN] Would delete backtest artifact: {artifact}")
                    else:
                        logger.info(f"Deleting backtest artifact: {artifact}")
                        artifact.unlink()
                    count += 1
            except Exception as e:
                logger.error(f"Failed to process backtest artifact {artifact}: {e}")

    if count == 0:
        logger.info(f"No backtest results to purge in {backtest_dir}")
    else:
        logger.info(f"Purged {count} backtest artifacts.")


def purge_log_files(log_dir: str, dry_run: bool = False):
    """Purge old log files from the specified directory."""
    log_path = Path(log_dir)
    if not log_path.exists():
        logger.info(f"Log directory {log_dir} does not exist. Skipping.")
        return

    now = time.time()
    cutoff_sec = RETENTION_POLICIES["logs"] * 24 * 60 * 60

    count = 0
    for log_file in log_path.glob("*.log*"):
        try:
            file_age = now - log_file.stat().st_mtime
            if file_age > cutoff_sec:
                if dry_run:
                    logger.info(f"[DRY-RUN] Would delete log file: {log_file}")
                else:
                    logger.info(f"Deleting log file: {log_file}")
                    log_file.unlink()
                count += 1
        except Exception as e:
            logger.error(f"Failed to process log file {log_file}: {e}")

    if count == 0:
        logger.info(f"No log files to purge in {log_dir}")
    else:
        logger.info(f"Purged {count} log files.")


def main():
    parser = argparse.ArgumentParser(description="Cleanup old data and logs.")
    parser.add_argument("--db-url", default="sqlite:///trades.db", help="Database URL")
    parser.add_argument("--log-dir", default="logs", help="Directory containing log files")
    parser.add_argument("--backtest-dir", default="testing/backtest", help="Directory containing backtest results")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without deleting")

    args = parser.parse_args()

    logger.info("Starting data cleanup process...")
    if args.dry_run:
        logger.info("DRY-RUN MODE ENABLED")

    try:
        purge_db_records(args.db_url, args.dry_run)
        purge_log_files(args.log_dir, args.dry_run)
        purge_backtest_results(args.backtest_dir, args.dry_run)
        logger.info("Cleanup process completed successfully.")
    except Exception as e:
        logger.exception(f"Cleanup process failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
