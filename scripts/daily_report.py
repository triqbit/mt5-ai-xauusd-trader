"""
Daily Performance Report Script
Usage: python scripts/daily_report.py
"""
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to sys.path
root_path = Path(__file__).resolve().parents[1]
sys.path.append(str(root_path))

from sqlalchemy import and_  # noqa: E402

from src.core.config import get_config  # noqa: E402
from src.core.monitor import Monitor  # noqa: E402
from src.core.trade_logger import Trade, TradeLogger  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("daily_report")

def generate_report():
    cfg = get_config()
    trade_logger = TradeLogger(
        db_url=cfg.database_url if "sqlite" in cfg.database_url else "sqlite:///trades.db"
    )
    monitor = Monitor(cfg)

    # Define "today" as the last 24 hours
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)

    with trade_logger.Session() as session:
        # Get trades closed in the last 24 hours
        daily_trades = session.query(Trade).filter(
            and_(
                Trade.status == "CLOSED",
                Trade.updated_at >= yesterday
            )
        ).all()

        if not daily_trades:
            logger.info("No trades found for the last 24 hours.")
            return

        total_pnl = sum(t.pnl for t in daily_trades)
        trade_count = len(daily_trades)
        wins = len([t for t in daily_trades if t.pnl > 0])
        win_rate = (wins / trade_count) * 100 if trade_count > 0 else 0

        status = "PROFIT" if total_pnl >= 0 else "LOSS"
        emoji = "📈" if total_pnl >= 0 else "📉"

        msg = (
            f"📅 *Daily Performance Report* {emoji}\n"
            f"Period: {yesterday.strftime('%Y-%m-%d %H:%M')} to {now.strftime('%H:%M')} UTC\n"
            f"--------------------------------\n"
            f"*Status*: {status}\n"
            f"*Net P&L*: ${total_pnl:.2f}\n"
            f"*Total Trades*: {trade_count}\n"
            f"*Win Rate*: {win_rate:.1f}%\n"
            f"--------------------------------\n"
        )

        if daily_trades:
            best_trade = max(daily_trades, key=lambda t: t.pnl)
            worst_trade = min(daily_trades, key=lambda t: t.pnl)
            msg += f"*Best Trade*: ${best_trade.pnl:.2f} ({best_trade.symbol})\n"
            msg += f"*Worst Trade*: ${worst_trade.pnl:.2f} ({worst_trade.symbol})\n"

        logger.info("Sending daily report...")
        monitor.send_message(msg)
        logger.info("Report sent successfully.")

if __name__ == "__main__":
    generate_report()
