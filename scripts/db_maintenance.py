
import logging
import argparse
from src.core.trade_logger import TradeLogger

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("db_maintenance")

def main():
    parser = argparse.ArgumentParser(description="Database maintenance script for MT5 Trading Bot")
    parser.add_argument("--db-url", default="sqlite:///trades.db", help="Database URL")
    parser.add_argument("--purge-days", type=int, default=30, help="Retention period in days")
    parser.add_argument("--skip-purge", action="store_true", help="Skip data purging")
    args = parser.parse_args()

    trade_logger = TradeLogger(db_url=args.db_url)

    logger.info("Starting database maintenance...")

    if not args.skip_purge:
        logger.info(f"Purging data older than {args.purge_days} days...")
        deleted = trade_logger.purge_old_data(days=args.purge_days)
        logger.info(f"Purged {deleted} records.")

    logger.info("Running ANALYZE...")
    trade_logger.analyze()

    logger.info("Running VACUUM...")
    trade_logger.vacuum()

    logger.info("Database maintenance completed successfully.")

if __name__ == "__main__":
    main()
