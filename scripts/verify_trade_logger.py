
import os
from datetime import UTC, datetime
import structlog
from src.core.trade_logger import TradeLogger

log = structlog.get_logger()

def verify():
    db_path = "verify_trades.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    log.info("TradeLogger initialized")

    # 1. Log Signal
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "algorithm": "ppo"
    })
    log.info("Logged signal", signal_id=signal_id)

    # 2. Log Trade (Executed)
    trade_id = logger.log_trade(
        ticket=12345,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id,
        drawdown_impact=0.01
    )
    log.info("Logged trade", trade_id=trade_id)

    # 3. Update Trade (Closed)
    logger.update_trade(12345, 2010.0, pnl=100.0) # should NOT overwrite 0.01 with 0.0
    log.info("Updated trade to CLOSED", ticket=12345, pnl=100.0)

    # 4. Log Trade (Rejected)
    rejected_id = logger.log_trade(
        ticket=None,
        symbol="XAUUSD",
        direction=-1,
        entry_price=2000.0,
        lot_size=0.1,
        status="REJECTED",
        signal_source="risk_engine",
        drawdown_impact=0.05,
        timestamp=datetime.now(UTC)
    )
    log.info("Logged rejected trade", rejected_id=rejected_id)

    # 5. Read Performance Report
    report = logger.read_performance_report(persist=True)
    log.info("Performance Report", report=report)

    assert report["total_trades"] == 1
    assert report["profit_factor"] == float('inf')
    assert report["max_drawdown"] == 0.0

    # Verify DB state
    with logger.Session() as session:
        from src.core.trade_logger import Trade, PerformanceMetric
        trade = session.get(Trade, trade_id)
        log.info("Verified trade", drawdown_impact=trade.drawdown_impact)
        assert trade.drawdown_impact == 0.01

        rej_trade = session.get(Trade, rejected_id)
        assert rej_trade.ticket is None
        assert rej_trade.status == "REJECTED"
        assert rej_trade.signal_source == "risk_engine"
        assert rej_trade.drawdown_impact == 0.05

        metric = session.query(PerformanceMetric).first()
        assert metric is not None
        assert metric.total_trades == 1

    log.info("Verification successful")
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    verify()
