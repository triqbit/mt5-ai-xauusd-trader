"""
Weekly Model Drift Audit Script
Compares AI predictions against realized trade outcomes.
"""
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to sys.path
root_path = Path(__file__).resolve().parents[1]
sys.path.append(str(root_path))

from src.core.config import get_config  # noqa: E402
from src.core.monitor import Monitor  # noqa: E402
from src.core.trade_logger import ModelSignal, TradeLogger  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model_drift_audit")

def audit_drift():
    cfg = get_config()
    trade_logger = TradeLogger(
        db_url=cfg.database_url if "sqlite" in cfg.database_url else "sqlite:///trades.db"
    )
    monitor = Monitor(cfg)

    now = datetime.now(timezone.utc)
    last_week = now - timedelta(days=7)

    logger.info("Starting model drift audit for the past 7 days...")

    with trade_logger.Session() as session:
        # Fetch signals from the last week
        signals = session.query(ModelSignal).filter(ModelSignal.timestamp >= last_week).all()

        if not signals:
            logger.info("No signals found for the audit period.")
            return

        # Filter signals that resulted in closed trades for verification
        executed_signals = [s for s in signals if s.trade and s.trade.status == "CLOSED"]

        if not executed_signals:
            logger.info("No executed and closed trades found for the audit period.")
            return

        total_executed = len(executed_signals)
        correct_predictions = len([s for s in executed_signals if s.trade.pnl > 0])

        accuracy = (correct_predictions / total_executed) * 100
        avg_confidence = sum(s.confidence for s in executed_signals if s.confidence) / total_executed

        logger.info(f"Audit Complete: Accuracy={accuracy:.1f}%, Avg Confidence={avg_confidence:.2f}")

        if accuracy < 52.0:
            msg = (
                f"⚠️ *Model Drift Alert*\n"
                f"Period: Last 7 Days\n"
                f"Accuracy: {accuracy:.1f}%\n"
                f"Avg Confidence: {avg_confidence:.2f}\n"
                f"Status: *HIGH DRIFT DETECTED*\n"
                f"Market conditions may have shifted. Consider re-training the ensemble."
            )
            monitor.send_message(msg)
        elif accuracy < avg_confidence * 80:
             msg = (
                f"📉 *Model Performance Warning*\n"
                f"Accuracy ({accuracy:.1f}%) is lagging behind Model Confidence ({avg_confidence*100:.1f}%).\n"
                f"Minor drift detected."
            )
             monitor.send_message(msg)

if __name__ == "__main__":
    audit_drift()
