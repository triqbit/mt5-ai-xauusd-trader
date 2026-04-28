"""
Unit tests for execution quality analytics.
"""
import os
import pytest
from datetime import datetime, timezone
from src.core.trade_logger import TradeLogger, ModelSignal, Trade
from src.analytics.execution_quality import ExecutionAnalyzer

@pytest.fixture
def logger():
    db_path = "test_execution.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    yield logger
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def analyzer(logger):
    return ExecutionAnalyzer(logger)

def test_execution_metrics(logger, analyzer):
    # Log a trade with execution details
    with logger.Session() as session:
        # Create a signal
        signal = ModelSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            timestamp=datetime.now(timezone.utc)
        )
        session.add(signal)
        session.commit()
        signal_id = signal.id

        # Create a trade
        trade = Trade(
            ticket=100,
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.5, # 0.5 negative slippage
            requested_price=2000.0,
            entry_spread=0.2,
            lot_size=0.1,
            signal_id=signal_id,
            execution_latency_ms=150,
            status="CLOSED",
            pnl=100.0,
            mfe=1.5,
            mae=-0.5
        )
        session.add(trade)
        session.commit()

    report = analyzer.analyze_period(symbol="XAUUSD")

    assert "XAUUSD" in report.metrics
    m = report.metrics["XAUUSD"]
    assert m.total_trades == 1
    assert m.avg_latency_ms == 150
    assert m.slippage.avg_slippage == -0.5 # (2000.0 - 2000.5) * 1 = -0.5
    assert m.mfe_avg == 1.5
    assert m.mae_avg == -0.5
    assert m.edge_capture > 0

def test_blocked_trade_analysis(logger, analyzer):
    # Log some risk events
    logger.log_risk_event("SIGNAL_REJECTED", "Daily loss limit reached", symbol="XAUUSD")
    logger.log_risk_event("SIGNAL_REJECTED", "Circuit breaker active", symbol="XAUUSD")

    report = analyzer.analyze_period()
    assert report.blocked_analysis.count == 2
    assert report.blocked_analysis.rejection_reasons["Daily loss limit reached"] == 1
    assert report.blocked_analysis.rejection_reasons["Circuit breaker active"] == 1

def test_slippage_calculation_sell(logger, analyzer):
    with logger.Session() as session:
        trade = Trade(
            ticket=200,
            symbol="XAUUSD",
            direction=-1, # Sell
            entry_price=1999.5, # 0.5 negative slippage (filled lower than requested for sell)
            requested_price=2000.0,
            lot_size=0.1,
            status="CLOSED"
        )
        session.add(trade)
        session.commit()

    report = analyzer.analyze_period(symbol="XAUUSD")
    m = report.metrics["XAUUSD"]
    # (Requested - Entry) * Direction = (2000.0 - 1999.5) * -1 = 0.5 * -1 = -0.5
    assert m.slippage.avg_slippage == -0.5
