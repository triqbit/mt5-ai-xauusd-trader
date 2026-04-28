#!/usr/bin/env python3
"""
Data Retention Cleanup Script
Purges old logs and database records according to the Data Retention Policy.
"""

import argparse
import logging
import os
import sys
import time
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import sessionmaker

# Add src to sys.path to allow imports if running from root
sys.path.append(os.getcwd())

try:
    from src.core.config import get_config
    from src.core.trade_logger import ModelSignal, Trade, RiskEvent, PerformanceMetric
except ImportError:
    print("Error: Could not import core modules. Please run this script from the repository root.")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("data_cleanup")

# Default Retention windows (days) according to docs/DATA_RETENTION_POLICY.md
RETENTION_CONFIG = {
    "logs": 90,
    "trades": 7 * 365,
    "model_signals": 365,
    "risk_events": 2 * 365,
    "performance_metrics": 365,
    "backtest_results": 180
}

def cleanup_files(directory: Path, days: int, pattern: str = "*", dry_run: bool = False):
    """Delete files older than X days in a given directory."""
    if not directory.exists():
        logger.warning(f"Directory {directory} does not exist. Skipping cleanup.")
        return

    cutoff = time.time() - (days * 86400)
    logger.info(f"Cleaning up {pattern} older than {days} days in {directory}...")

    count = 0
    for file_path in directory.glob(pattern):
        if file_path.is_file() and file_path.stat().st_mtime < cutoff:
            if dry_run:
                logger.info(f"[DRY RUN] Would delete file: {file_path.name} (Modified: {datetime.fromtimestamp(file_path.stat().st_mtime)})")
            else:
                try:
                    file_path.unlink()
                    logger.info(f"Deleted file: {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_path.name}: {e}")
            count += 1
    logger.info(f"Cleaned up {count} files in {directory}.")

def archive_performance_metrics(session, cutoff_date: datetime, archive_dir: Path, dry_run: bool = False):
    """Archive PerformanceMetric records to CSV before deletion."""
    records = session.query(PerformanceMetric).filter(PerformanceMetric.created_at < cutoff_date).all()
    if not records:
        return 0

    if dry_run:
        logger.info(f"[DRY RUN] Would archive {len(records)} performance metrics.")
        return len(records)

    archive_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = archive_dir / f"performance_metrics_archive_{timestamp}.csv"

    logger.info(f"Archiving {len(records)} metrics to {filename}...")

    try:
        with open(filename, 'w', newline='') as csvfile:
            # Get columns from the model
            columns = [column.name for column in PerformanceMetric.__table__.columns]
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            for record in records:
                row = {col: getattr(record, col) for col in columns}
                # Convert datetime objects to string
                for key, val in row.items():
                    if isinstance(val, datetime):
                        row[key] = val.isoformat()
                writer.writerow(row)
        return len(records)
    except Exception as e:
        logger.error(f"Failed to archive metrics: {e}")
        raise

def cleanup_db(db_url: str, dry_run: bool = False):
    """Purge old records from the database based on retention policy."""
    if db_url.startswith("sqlite") and not db_url.startswith("sqlite:///"):
        if "://" not in db_url:
            db_url = f"sqlite:///{db_url}"

    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
    except Exception as e:
        logger.error(f"Failed to connect to database at {db_url}: {e}")
        return

    now = datetime.now(timezone.utc)

    model_mapping = {
        Trade: RETENTION_CONFIG["trades"],
        ModelSignal: RETENTION_CONFIG["model_signals"],
        RiskEvent: RETENTION_CONFIG["risk_events"],
        PerformanceMetric: RETENTION_CONFIG["performance_metrics"]
    }

    with Session() as session:
        for model, days in model_mapping.items():
            cutoff_date = now - timedelta(days=days)
            date_col = model.created_at

            try:
                # Special handling for PerformanceMetric archival
                if model == PerformanceMetric:
                    archive_dir = Path("archives")
                    archive_performance_metrics(session, cutoff_date, archive_dir, dry_run=dry_run)

                # Batch deletion for efficiency and safety
                batch_size = 1000
                total_deleted = 0

                while True:
                    # Get IDs to delete in this batch
                    ids_query = session.query(model.id).filter(date_col < cutoff_date).limit(batch_size).all()
                    if not ids_query:
                        break

                    ids_to_delete = [r[0] for r in ids_query]

                    if dry_run:
                        logger.info(f"[DRY RUN] Would delete {len(ids_to_delete)} records from '{model.__tablename__}' older than {cutoff_date}")
                        break
                    else:
                        session.execute(delete(model).where(model.id.in_(ids_to_delete)))
                        session.commit()
                        total_deleted += len(ids_to_delete)
                        logger.info(f"Deleted {total_deleted} records from '{model.__tablename__}'...")

                if total_deleted == 0 and not dry_run:
                    logger.info(f"No records to purge for '{model.__tablename__}' (Retention: {days} days).")
                elif total_deleted > 0:
                    logger.info(f"Completed purging '{model.__tablename__}'. Total deleted: {total_deleted}")

            except Exception as e:
                logger.error(f"Error purging table '{model.__tablename__}': {e}")
                session.rollback()

def main():
    parser = argparse.ArgumentParser(description="Data Retention Cleanup Script")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without deleting data")
    parser.add_argument("--db-url", help="Database URL (overrides config)")
    parser.add_argument("--log-dir", help="Log directory (overrides config)")
    args = parser.parse_args()

    # Load config
    try:
        cfg = get_config()
        db_url = args.db_url or cfg.database_url
        log_dir = Path(args.log_dir or cfg.logs_dir)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        db_url = args.db_url or "sqlite:///trades.db"
        log_dir = Path(args.log_dir or "logs")

    logger.info("Starting data retention cleanup...")
    if args.dry_run:
        logger.info("Running in DRY RUN mode. No data will be deleted.")

    # 1. Cleanup Logs
    cleanup_files(log_dir, RETENTION_CONFIG["logs"], pattern="*.log", dry_run=args.dry_run)

    # 2. Cleanup Backtest Results
    backtest_dirs = [Path("testing/backtest"), Path("data/backtest_results"), Path("backtest")]
    for bt_dir in backtest_dirs:
        cleanup_files(bt_dir, RETENTION_CONFIG["backtest_results"], dry_run=args.dry_run)

    # 3. Cleanup Database
    cleanup_db(db_url, dry_run=args.dry_run)

    logger.info("Cleanup process completed.")

if __name__ == "__main__":
    main()
