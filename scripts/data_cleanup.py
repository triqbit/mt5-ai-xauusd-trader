"""
MT5 AI/ML Trading Bot - Data Cleanup Script
Automates the purging of old operational data based on the Data Retention Policy.
Includes archival of audit-critical data before deletion.
"""

import argparse
import csv
import hashlib
import logging
import os
import shutil
import sys
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker

__version__ = "1.1.0"

# Add src to path to import models
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.core.audit_log import AuditEntry, AuditLogger
from src.core.config import get_config
from src.core.trade_logger import (
    BlockedSignalAnalysis,
    ExecutionQuality,
    ModelSignal,
    PerformanceMetric,
    RiskEvent,
    Trade,
)

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
RETENTION_AUDIT_LOG = 7 * 365
RETENTION_BACKTESTS = 365

# Archive retention in days
RETENTION_ARCHIVE_COMPLIANCE = 7 * 365
RETENTION_ARCHIVE_AUDIT = 2 * 365
RETENTION_ARCHIVE_PERFORMANCE = 2 * 365
RETENTION_ARCHIVE_RESEARCH = 365

# Minimum required disk space in MB
MIN_DISK_SPACE_MB = 500

# Archival directory
ARCHIVE_DIR = Path(__file__).resolve().parents[1] / "archives"


def check_disk_space(path: Path, min_mb: int = MIN_DISK_SPACE_MB) -> bool:
    """Check if there is enough disk space available at the given path."""
    try:
        # Use parent if path doesn't exist yet
        check_path = path if path.exists() else path.parent
        usage = shutil.disk_usage(check_path)
        free_mb = usage.free / (1024 * 1024)
        if free_mb < min_mb:
            logger.error(
                f"CRITICAL: Insufficient disk space on {check_path}: {free_mb:.2f}MB available, {min_mb}MB required."
            )
            return False
        logger.info(f"Disk space check passed: {free_mb:.2f}MB available.")
        return True
    except Exception as e:
        logger.error(f"Failed to check disk space: {e}")
        return False


def generate_checksum(filepath: Path) -> str:
    """Generate SHA256 checksum for a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    checksum = sha256_hash.hexdigest()
    checksum_file = filepath.with_suffix(filepath.suffix + ".sha256")
    checksum_file.write_text(checksum, encoding="utf-8")
    logger.info(f"Generated checksum for {filepath.name}: {checksum}")
    return checksum


def archive_records(
    records: List[Any], table_name: str, archive_dir: Path, category: str = "general"
) -> bool:
    """Export a list of SQLAlchemy model instances to a CSV file. Returns True if successful."""
    if not records:
        return True

    # Use category-specific subdirectory
    target_dir = archive_dir / category
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filepath = target_dir / f"archive_{table_name}_{timestamp}.csv"

    logger.info(f"Archiving {len(records)} records from {table_name} to {filepath}...")

    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            # Get columns from the first record
            first_obj = records[0]
            fieldnames = [c.name for c in first_obj.__table__.columns]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for obj in records:
                row = {name: getattr(obj, name) for name in fieldnames}
                # Handle datetime serialization
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
                writer.writerow(row)

        # Generate checksum for the new archive
        generate_checksum(filepath)
        return True
    except Exception as e:
        logger.error(f"Failed to archive {table_name}: {e}")
        return False


def cleanup_archives(archive_dir: Path, dry_run: bool = False) -> int:
    """Purge expired archives based on their category."""
    if not archive_dir.exists():
        return 0

    count = 0
    now = datetime.now(timezone.utc)

    # Category -> Retention mapping
    categories = {
        "compliance": RETENTION_ARCHIVE_COMPLIANCE,
        "audit": RETENTION_ARCHIVE_AUDIT,
        "performance": RETENTION_ARCHIVE_PERFORMANCE,
        "research": RETENTION_ARCHIVE_RESEARCH,
    }

    for category, retention_days in categories.items():
        cat_dir = archive_dir / category
        if not cat_dir.exists():
            continue

        cutoff = now - timedelta(days=retention_days)
        logger.info(f"Checking {category} archives older than {cutoff.date()}...")

        for archive_file in cat_dir.glob("*"):
            if not archive_file.is_file():
                continue

            try:
                mtime = datetime.fromtimestamp(archive_file.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    logger.info(
                        f"{'[DRY RUN] ' if dry_run else ''}Deleting expired {category} archive: {archive_file.name}"
                    )
                    if not dry_run:
                        archive_file.unlink()
                    count += 1
            except Exception as e:
                logger.error(f"Failed to delete archive {archive_file}: {e}")

    return count


def cleanup_logs(logs_dir: Path, dry_run: bool = False) -> int:
    """Delete log files older than RETENTION_LOGS days."""
    if not logs_dir.exists():
        logger.info(f"Logs directory {logs_dir} does not exist. Skipping.")
        return 0

    count = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_LOGS)

    logger.info(f"Cleaning up logs in {logs_dir} older than {cutoff.date()}...")

    for log_file in logs_dir.glob("*.log*"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                logger.info(
                    f"{'[DRY RUN] ' if dry_run else ''}Deleting old log file: {log_file.name} (mtime: {mtime})"
                )
                if not dry_run:
                    log_file.unlink()
                count += 1
        except Exception as e:
            logger.error(f"Failed to delete log file {log_file}: {e}")

    return count


def cleanup_backtests(
    backtest_dir: Path, dry_run: bool = False, archive_dir: Path = ARCHIVE_DIR
) -> int:
    """Archive and delete backtest results older than RETENTION_BACKTESTS days."""
    if not backtest_dir.exists():
        logger.info(f"Backtest directory {backtest_dir} does not exist. Skipping.")
        return 0

    count = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_BACKTESTS)
    to_cleanup = []

    logger.info(f"Checking backtest results in {backtest_dir} older than {cutoff.date()}...")

    # Identify files to cleanup
    for item in backtest_dir.rglob("*"):
        if item.is_file():
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    to_cleanup.append(item)
            except Exception as e:
                logger.error(f"Failed to check backtest file {item}: {e}")

    if not to_cleanup:
        return 0

    # Archive before deletion
    if not dry_run:
        research_archive_dir = archive_dir / "research"
        if not research_archive_dir.exists():
            research_archive_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_path = research_archive_dir / f"archive_backtests_{timestamp}.tar.gz"

        logger.info(f"Archiving {len(to_cleanup)} backtest files to {archive_path}...")
        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                for item in to_cleanup:
                    tar.add(item, arcname=item.relative_to(backtest_dir))

            generate_checksum(archive_path)
        except Exception as e:
            logger.error(f"Failed to archive backtests: {e}")
            return 0

    # Delete files
    for item in to_cleanup:
        try:
            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}Deleting old backtest file: {item.relative_to(backtest_dir)}"
            )
            if not dry_run:
                item.unlink()
            count += 1
        except Exception as e:
            logger.error(f"Failed to delete backtest file {item}: {e}")

    # After deleting files, attempt to delete empty directories
    for item in sorted(backtest_dir.rglob("*"), reverse=True):
        if item.is_dir() and item != backtest_dir and not any(item.iterdir()):
            try:
                if not dry_run:
                    item.rmdir()
            except Exception:
                pass  # Directory might not be empty or already deleted

    return count


def cleanup_database(
    db_url: str,
    audit_db_url: str | None = None,
    dry_run: bool = False,
    archive_dir: Path = ARCHIVE_DIR,
) -> dict:
    """Purge old records from the database according to the retention policy."""
    engine = create_engine(db_url)
    # Ensure tables exist (especially for SQLite)
    from src.core.trade_logger import Base as TradeBase

    TradeBase.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    results = {
        "model_signals": 0,
        "risk_events": 0,
        "performance_metrics": 0,
        "trades": 0,
        "execution_qualities": 0,
        "blocked_signal_analysis": 0,
        "audit_log": 0,
    }

    now = datetime.now(timezone.utc)

    with Session() as session:
        # 1. Cleanup Risk Events (older than 2 years)
        risk_cutoff = now - timedelta(days=RETENTION_RISK_EVENTS)
        risk_query = select(RiskEvent).where(RiskEvent.created_at < risk_cutoff)
        risk_records = session.execute(risk_query).scalars().all()
        results["risk_events"] = len(risk_records)

        if risk_records:
            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}Purging {len(risk_records)} risk events older than {risk_cutoff.date()}"
            )
            if not dry_run:
                # Archiving risk events (Audit 2-year category, archived before purge)
                if archive_records(risk_records, "risk_events", archive_dir, category="audit"):
                    # Also archive associated signals and analysis before deleting risk events
                    signal_ids = {r.signal_id for r in risk_records if r.signal_id}
                    if signal_ids:
                        signals_to_archive = (
                            session.execute(
                                select(ModelSignal).where(ModelSignal.id.in_(signal_ids))
                            )
                            .scalars()
                            .all()
                        )
                        archive_records(
                            signals_to_archive, "linked_risk_signals", archive_dir, category="audit"
                        )

                        bsa_to_archive = (
                            session.execute(
                                select(BlockedSignalAnalysis).where(
                                    BlockedSignalAnalysis.signal_id.in_(signal_ids)
                                )
                            )
                            .scalars()
                            .all()
                        )
                        if bsa_to_archive:
                            archive_records(
                                bsa_to_archive, "linked_risk_bsa", archive_dir, category="audit"
                            )

                    # Bulk delete
                    ids_to_delete = [r.id for r in risk_records]
                    session.execute(delete(RiskEvent).where(RiskEvent.id.in_(ids_to_delete)))
                else:
                    logger.error("Skipping deletion of risk events due to archival failure.")

        # 2. Cleanup Performance Metrics (older than 2 years)
        perf_cutoff = now - timedelta(days=RETENTION_PERFORMANCE_METRICS)
        perf_query = select(PerformanceMetric).where(PerformanceMetric.created_at < perf_cutoff)
        perf_records = session.execute(perf_query).scalars().all()
        results["performance_metrics"] = len(perf_records)

        if perf_records:
            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}Purging {len(perf_records)} performance metrics older than {perf_cutoff.date()}"
            )
            if not dry_run:
                # Archiving performance metrics (Operational 2-year category, archived before purge)
                if archive_records(
                    perf_records, "performance_metrics", archive_dir, category="performance"
                ):
                    ids_to_delete = [p.id for p in perf_records]
                    session.execute(
                        delete(PerformanceMetric).where(PerformanceMetric.id.in_(ids_to_delete))
                    )
                else:
                    logger.error(
                        "Skipping deletion of performance metrics due to archival failure."
                    )

        # 3. Cleanup Trades (older than 7 years)
        trade_cutoff = now - timedelta(days=RETENTION_TRADES)
        trade_query = select(Trade).where(Trade.created_at < trade_cutoff)
        trade_records = session.execute(trade_query).scalars().all()
        results["trades"] = len(trade_records)

        if trade_records:
            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}Purging {len(trade_records)} trade records older than {trade_cutoff.date()}"
            )
            if not dry_run:
                # Mandatory archival for Compliance data
                if archive_records(trade_records, "trades", archive_dir, category="compliance"):
                    ids_to_delete = [t.id for t in trade_records]

                    # Also archive and delete associated execution quality records
                    eq_records = (
                        session.execute(
                            select(ExecutionQuality).where(
                                ExecutionQuality.trade_id.in_(ids_to_delete)
                            )
                        )
                        .scalars()
                        .all()
                    )
                    if eq_records:
                        archive_records(
                            eq_records, "execution_qualities", archive_dir, category="compliance"
                        )
                        results["execution_qualities"] = len(eq_records)
                        session.execute(
                            delete(ExecutionQuality).where(
                                ExecutionQuality.trade_id.in_(ids_to_delete)
                            )
                        )

                    # Also archive associated signals and analysis before deleting trades
                    signal_ids = {t.signal_id for t in trade_records if t.signal_id}
                    if signal_ids:
                        signals_to_archive = (
                            session.execute(
                                select(ModelSignal).where(ModelSignal.id.in_(signal_ids))
                            )
                            .scalars()
                            .all()
                        )
                        archive_records(
                            signals_to_archive, "linked_signals", archive_dir, category="compliance"
                        )

                        bsa_to_archive = (
                            session.execute(
                                select(BlockedSignalAnalysis).where(
                                    BlockedSignalAnalysis.signal_id.in_(signal_ids)
                                )
                            )
                            .scalars()
                            .all()
                        )
                        if bsa_to_archive:
                            archive_records(
                                bsa_to_archive, "linked_bsa", archive_dir, category="compliance"
                            )

                    session.execute(delete(Trade).where(Trade.id.in_(ids_to_delete)))
                else:
                    logger.error("Skipping deletion of trades due to archival failure.")

        # 4. Cleanup Unlinked Model Signals (older than 90 days)
        # We must exclude signals that are STILL linked to any remaining trades OR risk events.
        signal_cutoff = now - timedelta(days=RETENTION_UNLINKED_SIGNALS)

        # Subqueries for linked signals that are NOT being deleted
        # A signal is "kept" if it's linked to a Trade or RiskEvent that is NOT in the deletion list
        kept_trade_signals = select(Trade.signal_id).where(
            Trade.signal_id.is_not(None), Trade.created_at >= trade_cutoff
        )
        kept_risk_signals = select(RiskEvent.signal_id).where(
            RiskEvent.signal_id.is_not(None), RiskEvent.created_at >= risk_cutoff
        )

        unlinked_signals_query = (
            select(ModelSignal)
            .where(ModelSignal.created_at < signal_cutoff)
            .where(ModelSignal.id.not_in(kept_trade_signals))
            .where(ModelSignal.id.not_in(kept_risk_signals))
        )

        unlinked_records = session.execute(unlinked_signals_query).scalars().all()
        results["model_signals"] = len(unlinked_records)

        if unlinked_records:
            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}Purging {len(unlinked_records)} unlinked signals older than {signal_cutoff.date()}"
            )
            if not dry_run:
                # No archival for unlinked signals as per policy (ephemeral)
                ids_to_delete = [s.id for s in unlinked_records]

                # Cleanup BlockedSignalAnalysis for these signals
                bsa_records = (
                    session.execute(
                        select(BlockedSignalAnalysis).where(
                            BlockedSignalAnalysis.signal_id.in_(ids_to_delete)
                        )
                    )
                    .scalars()
                    .all()
                )
                if bsa_records:
                    results["blocked_signal_analysis"] = len(bsa_records)
                    session.execute(
                        delete(BlockedSignalAnalysis).where(
                            BlockedSignalAnalysis.signal_id.in_(ids_to_delete)
                        )
                    )

                session.execute(delete(ModelSignal).where(ModelSignal.id.in_(ids_to_delete)))

        if not dry_run:
            session.commit()

    # 5. Cleanup Audit Log (older than 7 years)
    audit_engine = (
        create_engine(audit_db_url) if audit_db_url and audit_db_url != db_url else engine
    )

    # Ensure audit tables exist
    from src.core.audit_log import Base as AuditBase

    AuditBase.metadata.create_all(audit_engine)

    AuditSession = sessionmaker(bind=audit_engine)

    with AuditSession() as session:
        audit_cutoff = now - timedelta(days=RETENTION_AUDIT_LOG)
        audit_query = select(AuditEntry).where(AuditEntry.created_at < audit_cutoff)
        audit_records = session.execute(audit_query).scalars().all()
        results["audit_log"] = len(audit_records)

        if audit_records:
            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}Purging {len(audit_records)} audit log entries older than {audit_cutoff.date()}"
            )
            if not dry_run:
                # Mandatory archival for Audit data
                if archive_records(audit_records, "audit_log", archive_dir, category="audit"):
                    ids_to_delete = [a.id for a in audit_records]
                    session.execute(delete(AuditEntry).where(AuditEntry.id.in_(ids_to_delete)))
                else:
                    logger.error("Skipping deletion of audit logs due to archival failure.")

        if not dry_run:
            session.commit()

            # Reclaim space for SQLite
            if "sqlite" in db_url.lower():
                try:
                    from sqlalchemy import text

                    session.execute(text("VACUUM"))
                    logger.info("Executed VACUUM on primary database.")
                except Exception as e:
                    logger.error(f"Failed to VACUUM database: {e}")

            if audit_db_url and audit_db_url != db_url and "sqlite" in audit_db_url.lower():
                # For audit DB if separate
                with AuditSession() as audit_session:
                    try:
                        from sqlalchemy import text

                        audit_session.execute(text("VACUUM"))
                        logger.info("Executed VACUUM on audit database.")
                    except Exception as e:
                        logger.error(f"Failed to VACUUM audit database: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(description="MT5 AI/ML Trading Bot - Data Cleanup Utility")
    parser.add_argument(
        "--dry-run", action="store_true", help="Perform a dry run without deleting any data."
    )
    parser.add_argument("--db-url", help="Override the primary database URL from config.")
    parser.add_argument("--audit-db-url", help="Override the audit database URL.")
    parser.add_argument("--logs-dir", help="Override the logs directory from config.")
    parser.add_argument("--backtest-dir", help="Override the backtest results directory.")
    parser.add_argument("--archive-dir", help="Directory where archived data will be stored.")

    args = parser.parse_args()

    # Ensure mandatory config for TradingConfig is present to avoid validation errors
    # these are not actually used by the cleanup script logic but required by Pydantic
    os.environ.setdefault("MT5_PASSWORD", "dummy_for_cleanup")
    os.environ.setdefault("MT5_SERVER", "dummy_for_cleanup")

    cfg = get_config()

    # Determine DB URLs mirroring main.py logic
    db_url = args.db_url or cfg.database_url.get_secret_value()
    audit_db_url = args.audit_db_url or cfg.database_url.get_secret_value()

    # Fallback for SQLite if not fully specified in environment
    if not args.db_url and "://" not in db_url:
        db_url = f"sqlite:///{db_url}" if db_url.endswith(".db") else "sqlite:///trades.db"
    if not args.audit_db_url and "://" not in audit_db_url:
        audit_db_url = (
            f"sqlite:///{audit_db_url}" if audit_db_url.endswith(".db") else "sqlite:///audit.db"
        )

    logs_dir = Path(args.logs_dir) if args.logs_dir else cfg.logs_dir
    backtest_dir = (
        Path(args.backtest_dir)
        if args.backtest_dir
        else Path(__file__).resolve().parents[1] / "backtest_results"
    )
    archive_dir = Path(args.archive_dir) if args.archive_dir else ARCHIVE_DIR

    # Initialize AuditLogger
    try:
        audit_logger = AuditLogger(db_url=audit_db_url)
    except Exception as e:
        logger.warning(f"Could not initialize AuditLogger: {e}. Audit trail will be missing.")
        audit_logger = None

    if audit_logger:
        audit_logger.log("system", "data_cleanup_started", details=f"Dry run: {args.dry_run}")

    logger.info(f"Starting data cleanup (dry_run={args.dry_run})")

    # Disk space check
    if not check_disk_space(archive_dir):
        msg = "Cleanup ABORTED due to insufficient disk space for archival."
        logger.error(msg)
        if audit_logger:
            audit_logger.log("system", "data_cleanup_failed", details=msg)
        sys.exit(1)

    # Filesystem cleanup - Logs
    log_count = cleanup_logs(logs_dir, dry_run=args.dry_run)
    logger.info(f"Log cleanup complete. Total files processed: {log_count}")

    # Filesystem cleanup - Backtests
    backtest_count = cleanup_backtests(backtest_dir, dry_run=args.dry_run, archive_dir=archive_dir)
    logger.info(f"Backtest cleanup complete. Total files processed: {backtest_count}")

    # Filesystem cleanup - Expired Archives
    archive_count = cleanup_archives(archive_dir, dry_run=args.dry_run)
    logger.info(f"Archive cleanup complete. Total archives deleted: {archive_count}")

    # Database cleanup
    db_results = cleanup_database(
        db_url, audit_db_url=audit_db_url, dry_run=args.dry_run, archive_dir=archive_dir
    )
    logger.info("Database cleanup complete.")
    for table, count in db_results.items():
        logger.info(f"  - {table}: {count} records {'identified' if args.dry_run else 'purged'}")

    summary = {
        "logs_deleted": log_count,
        "backtests_deleted": backtest_count,
        "db_purged": db_results,
    }

    if audit_logger:
        audit_logger.log("system", "data_cleanup_completed", details=f"Summary: {summary}")

    logger.info("Cleanup process finished successfully.")


if __name__ == "__main__":
    main()
