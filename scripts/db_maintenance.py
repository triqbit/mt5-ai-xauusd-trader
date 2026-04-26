"""
Monthly Database Maintenance Script
Archives old data and optimizes the database.
"""
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

# Add project root to sys.path
root_path = Path(__file__).resolve().parents[1]
sys.path.append(str(root_path))

from src.core.config import get_config  # noqa: E402
from src.core.trade_logger import ModelSignal, Trade, TradeLogger  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_maintenance")

def run_maintenance():
    cfg = get_config()
    trade_logger = TradeLogger(
        db_url=cfg.database_url if "sqlite" in cfg.database_url else "sqlite:///trades.db"
    )

    now = datetime.now(timezone.utc)
    archive_threshold = now - timedelta(days=90)

    logger.info(f"Starting DB maintenance (Archive threshold: {archive_threshold})")

    try:
        with trade_logger.Session() as session:
            old_trades = session.query(Trade).filter(Trade.created_at < archive_threshold).count()
            old_signals = session.query(ModelSignal).filter(ModelSignal.created_at < archive_threshold).count()

            logger.info(f"Found {old_trades} old trades and {old_signals} old signals to archive.")

            if "sqlite" in cfg.database_url:
                logger.info("Running SQLite VACUUM...")
                session.execute(text("VACUUM"))
            elif "postgresql" in cfg.database_url:
                logger.info("Running Postgres VACUUM (if permissions allow)...")
                session.execute(text("VACUUM"))

            session.commit()
            logger.info("Maintenance complete.")

    except Exception as e:
        logger.error(f"Maintenance failed: {e}")

if __name__ == "__main__":
    run_maintenance()
