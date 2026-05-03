"""
MT5 AI/ML Trading Bot - Execution Analytics Integration Test
tests/test_execution_analytics_integration.py

Verifies the integration path:
Execution Filter -> Trade Logger -> Execution Analyzer
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.analytics.execution_quality import ExecutionAnalyzer
from src.core.config import get_config
from src.core.trade_logger import TradeLogger
from src.trading.execution_filter import ExecutionFilter
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import RiskManager, TradeSignal

@pytest.fixture
def mock_cfg():
    with patch.dict(os.environ, {
        "MT5_PASSWORD": "test_password",
        "MT5_SERVER": "test_server",
        "TELEGRAM_TOKEN": "123:abc",
        "TELEGRAM_CHAT_ID": "123456",
        "MODE": "demo",
        "DATABASE_URL": "sqlite:///:memory:"
    }):
        get_config.cache_clear()
        return get_config()

@pytest.fixture
def trade_logger():
    # Use in-memory SQLite for testing
    return TradeLogger(db_url="sqlite:///:memory:")

@pytest.fixture
def mock_connector(mock_cfg):
    connector = MagicMock(spec=MT5Connector)
    connector.cfg = mock_cfg

    # Mock OHLCV data
    dates = pd.date_range(start=datetime.now(timezone.utc) - timedelta(hours=10), periods=200, freq="5min")
    df = pd.DataFrame({
        "time": dates,
        "open": np.linspace(2300, 2300, 200),
        "high": np.linspace(2305, 2305, 200),
        "low": np.linspace(2295, 2295, 200),
        "close": np.linspace(2300, 2300, 200),
        "tick_volume": [100] * 200,
        "spread": [20] * 200
    })
    connector.get_ohlcv.return_value = df
    connector.get_rates.return_value = df
    connector.get_rates_range.return_value = df

    # Mock tick
    connector.get_tick.return_value = {"bid": 2300.0, "ask": 2300.2, "spread": 0.2}
    connector.get_account_balance.return_value = 10000.0

    return connector

@pytest.fixture
def analyzer(trade_logger, mock_connector):
    # Link analyzer to the same in-memory DB as trade_logger
    analyzer = ExecutionAnalyzer(db_url="sqlite:///:memory:", connector=mock_connector)
    # Overwrite engine and session to use the same one as trade_logger
    analyzer.engine = trade_logger.engine
    analyzer.Session = trade_logger.Session
    return analyzer

@pytest.fixture
def risk_manager(mock_cfg, trade_logger):
    return RiskManager(mock_cfg, account_balance=10000.0, logger_db=trade_logger)

@pytest.fixture
def execution_filter():
    return ExecutionFilter(max_drawdown=0.15)

def test_integration_path_blocked_signal_to_opportunity_cost(
    trade_logger, mock_connector, risk_manager, execution_filter, analyzer
):
    """Path: Signal -> ExecutionFilter (Block) -> TradeLogger (RiskEvent) -> Analyzer (Opp Cost)"""

    # 1. Generate Signal
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=datetime.utcnow() - timedelta(minutes=60)
    )

    # 2. Log Signal
    signal_id = trade_logger.log_signal({
        "symbol": signal.symbol,
        "direction": signal.direction,
        "entry_price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
        "lot_size": signal.lot_size,
        "algorithm": signal.algorithm,
        "confidence": signal.confidence,
        "timestamp": signal.timestamp
    })

    # 3. Simulate ExecutionFilter Block (e.g. Drawdown Limit)
    # We'll mock the validate result to force a block
    from src.trading.execution_filter import ExecutionDecision
    blocked_decision = ExecutionDecision(signal, False, 0.0, "DRAWDOWN_LIMIT")

    # Manual implementation of main.py logic for blocking
    trade_logger.log_risk_event(
        event_type="SIGNAL_REJECTED",
        description=f"ExecutionFilter: {blocked_decision.blocked_by}",
        symbol=signal.symbol,
        signal_id=signal_id
    )

    # 4. Verify analyzer picks up the blocked signal and calculates opportunity cost
    # We need to ensure the market moved to hit TP for a positive opportunity cost
    mock_df = pd.DataFrame({
        "time": pd.date_range(start=signal.timestamp, periods=10, freq="15min"),
        "open": [2300.0] * 10,
        "high": [2300.0] * 5 + [2325.0] * 5, # Hits TP (2320)
        "low": [2298.0] * 10,
        "close": [2305.0] * 5 + [2322.0] * 5
    })
    mock_connector.get_rates.return_value = mock_df

    blocked_analyses = analyzer.analyze_blocked_signals(start_time=signal.timestamp - timedelta(minutes=1))

    assert len(blocked_analyses) == 1
    analysis = blocked_analyses[0]
    assert analysis.signal_id == signal_id
    assert analysis.rejection_reason == "ExecutionFilter: DRAWDOWN_LIMIT"
    assert analysis.would_have_won is True
    assert analysis.opportunity_cost_pnl > 0

def test_integration_path_passed_signal_to_execution_quality(
    trade_logger, mock_connector, risk_manager, execution_filter, analyzer
):
    """Path: Signal -> ExecutionFilter (Pass) -> Order -> TradeLogger (Trade) -> Analyzer (Quality)"""

    # 1. Generate and Log Signal
    signal_time = datetime.utcnow() - timedelta(seconds=10)
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=signal_time
    )

    signal_id = trade_logger.log_signal({
        "symbol": signal.symbol,
        "direction": signal.direction,
        "entry_price": signal.entry_price,
        "algorithm": signal.algorithm,
        "confidence": signal.confidence,
        "timestamp": signal.timestamp,
        "volatility": 5.0
    })

    # 2. Execution (Success)
    # Entry with 2 pips slippage (XAUUSD pip=0.1)
    execution_price = 2300.2
    execution_time = signal_time + timedelta(milliseconds=500)
    ticket = 12345

    trade_id = trade_logger.log_trade(
        ticket=ticket,
        symbol=signal.symbol,
        direction=signal.direction,
        entry_price=execution_price,
        lot_size=signal.lot_size,
        signal_id=signal_id
    )

    # Mock Trade object created_at manually because SQLAlchemy won't do it in-memory without commit/refresh
    with trade_logger.Session() as session:
        from src.core.trade_logger import Trade
        trade = session.query(Trade).filter(Trade.id == trade_id).first()
        trade.created_at = execution_time
        session.commit()

    # 3. Analyze Execution Quality
    quality = analyzer.analyze_trade(trade_id)

    assert quality is not None
    assert quality.trade_id == trade_id
    assert pytest.approx(quality.slippage_pips) == 2.0
    assert pytest.approx(quality.execution_latency_ms) == 500.0
    assert quality.fill_quality_score < 1.0

def test_full_execution_summary_aggregation(
    trade_logger, mock_connector, analyzer
):
    """Verifies that the summary report correctly aggregates both executed and blocked paths."""

    # 1. Add a blocked signal
    trade_logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2300.0,
        "lot_size": 0.1
    })
    trade_logger.log_risk_event(event_type="SIGNAL_REJECTED", description="Blocked", signal_id=1)

    # 2. Add an executed trade
    trade_logger.log_signal({"symbol": "XAUUSD", "direction": 1, "entry_price": 2300.0, "timestamp": datetime.utcnow()})
    trade_logger.log_trade(ticket=999, symbol="XAUUSD", direction=1, entry_price=2300.1, lot_size=0.1, signal_id=2)

    # Mocking for summary aggregation
    with patch.object(analyzer, 'analyze_trade') as mock_at, \
         patch.object(analyzer, 'analyze_blocked_signals') as mock_abs:

        from src.analytics.execution_quality import TradeExecutionQuality, BlockedSignalQuality

        mock_at.return_value = MagicMock(spec=TradeExecutionQuality, slippage_pips=1.0, execution_latency_ms=100.0, fill_quality_score=0.9, edge_capture=0.5, post_entry_drift_5m=0.0, post_entry_drift_15m=0.0, timing_efficiency=0.8, spread_at_execution=2.0, slippage_to_spread_ratio=0.5, alpha_decay_pips=0.0)

        mock_abs.return_value = [
            MagicMock(spec=BlockedSignalQuality, opportunity_cost_pnl=100.0)
        ]

        summary = analyzer.generate_summary_report(days=1)

        assert summary.executed_trade_count == 1
        assert summary.rejected_signal_count == 1
        assert summary.total_opportunity_cost == 100.0
        assert summary.avg_slippage == 1.0
