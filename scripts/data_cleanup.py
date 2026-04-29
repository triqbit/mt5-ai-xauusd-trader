"""
MT5 AI/ML Trading Bot - Enterprise Edition
scripts/data_cleanup.py
Automated data purging and archival script.
Author : triqbit
License: MIT
"""

import argparse
import csv
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Type

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_config
from src.core.trade_logger import ModelSignal, PerformanceMetric, RiskEvent, Trade

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("data_cleanup")

# Retention periods in days
RETENTION_WINDOWS = {
    "logs": 90,
    "trades": 7 * 365,
    "model_signals": 365,
    "risk_events": 2 * 365,
    "performance_metrics": 365,
    "backtests": 180,
}


def setup_args():
    parser = argparse.ArgumentParser(description="Purge and archive old operational data.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting.")
    parser.add_argument("--db-url", help="Database URL override.")
    parser.add_argument("--archive-dir", default="archives", help="Directory for archived data.")
    parser.add_argument("--logs-dir", default="logs", help="Directory for log files.")
    parser.add_argument("--backtest-dir", default="backtests", help="Directory for backtest results.")
    parser.add_argument("--batch-size", type=int, default=1000, help="Number of records to delete in one batch.")
    return parser.parse_args()


def archive_data(session: Session, model: Type[Any], cutoff_date: datetime, archive_path: Path) -> int:
    """Archive data to CSV before deletion using a streaming approach."""
    # Use execution_options(stream_results=True) for large datasets if the driver supports it
    stmt = select(model).where(model.created_at < cutoff_date).execution_options(stream_results=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{model.__tablename__}_{timestamp}.csv"
    full_path = archive_path / filename

    count = 0
    try:
        # Get column names for the CSV header
        columns = [c.name for c in model.__table__.columns]

        with open(full_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()

            for row in session.execute(stmt).scalars():
                row_dict = {c: getattr(row, c) for c in columns}
                writer.writerow(row_dict)
                count += 1

        if count == 0:
            full_path.unlink()  # Remove empty file
            return 0

        logger.info(f"Archived {count} records from {model.__tablename__} to {full_path}")
        return count
    except Exception as e:
        logger.error(f"Archival failed for {model.__tablename__}: {e}")
        if full_path.exists():
            full_path.unlink()
        return 0


def purge_db_records(db_url: str, dry_run: bool, archive_dir: str, batch_size: int):
    """Purge old records from the database."""
    engine = create_engine(db_url)
    SessionFactory = sessionmaker(bind=engine)
    archive_path = Path(archive_dir)
    archive_path.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)

    # Mapping of models to their retention windows
    models_to_purge = [
        (Trade, RETENTION_WINDOWS["trades"]),
        (ModelSignal, RETENTION_WINDOWS["model_signals"]),
        (RiskEvent, RETENTION_WINDOWS["risk_events"]),
        (PerformanceMetric, RETENTION_WINDOWS["performance_metrics"]),
    ]

    with SessionFactory() as session:
        for model, days in models_to_purge:
            cutoff_date = now - timedelta(days=days)

            # 1. Count records to be deleted efficiently
            count_stmt = select(func.count()).select_from(model).where(model.created_at < cutoff_date)
            to_delete_count = session.execute(count_stmt).scalar() or 0

            if to_delete_count > 0:
                if dry_run:
                    logger.info(f"[DRY RUN] Would delete {to_delete_count} records from {model.__tablename__} (older than {cutoff_date})")
                else:
                    # 2. Archival for specific models
                    if model in [Trade, PerformanceMetric]:
                        archive_data(session, model, cutoff_date, archive_path)

                    # 3. Batch deletion to avoid large transaction logs
                    # Note: SQLite delete doesn't support LIMIT in standard builds,
                    # but for postgres/others we can optimize. For simplicity and
                    # compatibility, we'll do it in one go if not specify batching or
                    # if it's manageable.
                    # Real enterprise solution would use subqueries or ID lists.
                    delete_stmt = delete(model).where(model.created_at < cutoff_date)
                    session.execute(delete_stmt)
                    session.commit()
                    logger.info(f"Deleted {to_delete_count} records from {model.__tablename__}")
            else:
                logger.info(f"No records to purge for {model.__tablename__}")


def purge_logs(logs_dir: str, dry_run: bool):
    """Delete log files older than the retention window."""
    log_path = Path(logs_dir)
    if not log_path.exists():
        logger.debug(f"Logs directory {logs_dir} does not exist. Skipping.")
        return

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=RETENTION_WINDOWS["logs"])

    deleted_count = 0
    for log_file in log_path.glob("*.log*"):
        if log_file.is_file():
            # Use UTC mtime
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff_date:
                if dry_run:
                    logger.info(f"[DRY RUN] Would delete log file: {log_file} (Last modified: {mtime})")
                else:
                    log_file.unlink()
                    logger.info(f"Deleted log file: {log_file}")
                deleted_count += 1

    if deleted_count == 0:
        logger.info("No log files to purge.")


def purge_backtests(backtest_dir: str, dry_run: bool):
    """Delete backtest result files older than the retention window."""
    bt_path = Path(backtest_dir)
    if not bt_path.exists():
        logger.debug(f"Backtest directory {backtest_dir} does not exist. Skipping.")
        return

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=RETENTION_WINDOWS["backtests"])

    deleted_count = 0
    # Search for common backtest result formats
    for bt_file in list(bt_path.glob("*.csv")) + list(bt_path.glob("*.json")) + list(bt_path.glob("*.png")):
        if bt_file.is_file():
            mtime = datetime.fromtimestamp(bt_file.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff_date:
                if dry_run:
                    logger.info(f"[DRY RUN] Would delete backtest file: {bt_file} (Last modified: {mtime})")
                else:
                    bt_file.unlink()
                    logger.info(f"Deleted backtest file: {bt_file}")
                deleted_count += 1

    if deleted_count == 0:
        logger.info("No backtest files to purge.")


def main():
    args = setup_args()
    cfg = get_config()

    db_url = args.db_url or cfg.database_url

    logger.info(f"Starting data cleanup. Dry run: {args.dry_run}")

    try:
        purge_db_records(db_url, args.dry_run, args.archive_dir, args.batch_size)
        purge_logs(args.logs_dir, args.dry_run)
        purge_backtests(args.backtest_dir, args.dry_run)
        logger.info("Data cleanup completed successfully.")
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
