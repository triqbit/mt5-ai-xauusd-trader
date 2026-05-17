"""
MT5 AI/ML Trading Bot - Execution Analysis Pipeline Integration Test
tests/test_execution_analysis_pipeline.py

Verifies the high-value integration path:
Signal Decision (Rejection/Approval) -> Risk Event / Trade Logging -> Execution Quality Analysis -> Reporting
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import select

from src.analytics.execution_quality import ExecutionAnalyzer
from src.core.schemas import TradeSignal
from src.core.trade_logger import (
    BlockedSignalAnalysis,
    ExecutionQuality,
    RiskEvent,
    Trade,
    TradeLogger,
)
from src.trading.audited_risk_manager import AuditedRiskManager


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "trading_test.db"
    return f"sqlite:///{db_file}"

@pytest.fixture
def mock_connector():
    connector = MagicMock()

    # Mock symbol properties for XAUUSD
    def get_props(symbol):
        if "XAUUSD" in symbol:
            return {"digits": 2, "contract_size": 100.0, "point": 0.01, "pip_size": 0.1}
        return None
    connector.get_symbol_properties.side_effect = get_props

    # Mock rates for opportunity cost and drift calculations
    # Need enough data for M5 and M1
    base_time = datetime.now(timezone.utc) - timedelta(hours=2)

    m5_data = []
    for i in range(100):
        m5_data.append({
            "time": base_time + timedelta(minutes=5*i),
            "open": 2300.0 + i,
            "high": 2305.0 + i,
            "low": 2295.0 + i,
            "close": 2302.0 + i,
            "spread": 20
        })
    connector.get_rates.return_value = pd.DataFrame(m5_data)
    connector.get_rates_range.return_value = pd.DataFrame(m5_data)

    # Mock ticks for alpha decay
    ticks_data = []
    for i in range(10):
        ticks_data.append({
            "time": base_time + timedelta(seconds=i),
            "bid": 2299.95 + i*0.1,
            "ask": 2300.05 + i*0.1
        })
    connector.get_ticks_range.return_value = pd.DataFrame(ticks_data)

    return connector

def test_e2e_execution_and_analysis_flow(test_db, mock_connector):
    """
    E2E Path: Signal -> Logging -> Analysis -> Summary
    Verifies that both rejected signals and executed trades are correctly analyzed.
    """
    # Initialize components
    trade_logger = TradeLogger(db_url=test_db)
    analyzer = ExecutionAnalyzer(db_url=test_db, connector=mock_connector)

    # Mock Config for RiskManager
    cfg = MagicMock()
    cfg.max_drawdown = 0.15
    cfg.max_daily_loss = 0.05
    cfg.max_open_positions = 5
    cfg.max_positions = 5
    cfg.max_symbol_allocation = 0.1
    cfg.min_confidence = 0.6
    cfg.risk_reward_ratio_threshold = 1.5
    cfg.max_consecutive_losses = 3
    cfg.max_losing_streak = 3
    cfg.model_drift_threshold = 0.3
    cfg.model_accuracy_floor = 0.45

    risk_manager = AuditedRiskManager(cfg, account_balance=10000.0, logger_db=trade_logger)

    # --- SCENARIO 1: Rejected Signal ---
    signal_time = datetime.now(timezone.utc) - timedelta(hours=1)
    # Use model_construct to bypass R:R validation for rejection testing
    rejected_signal = TradeSignal.model_construct(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2305.0, # Low R:R (0.5), will be rejected by RiskManager
        lot_size=0.1,
        algorithm="test_algo",
        confidence=0.8,
        timestamp=signal_time
    )

    # Manually log signal to get ID
    signal_id = trade_logger.log_signal(rejected_signal.model_dump())

    # Run approval - should fail due to R:R
    # (Using patch to ensure RiskManager fails specifically on R:R if Pydantic allowed it)
    with patch.object(risk_manager, "_check_risk_reward", return_value=False):
        approved = risk_manager.approve(rejected_signal, signal_id=signal_id)
        assert approved is False

    # Verify RiskEvent is in DB
    with trade_logger.Session() as session:
        event = session.execute(select(RiskEvent).where(RiskEvent.signal_id == signal_id)).scalar_one_or_none()
        assert event is not None
        assert "risk_reward" in event.description

    # --- SCENARIO 2: Executed Trade ---
    trade_signal_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    valid_signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0, # 2.0 R:R
        lot_size=0.1,
        algorithm="test_algo",
        confidence=0.9,
        timestamp=trade_signal_time
    )

    signal_id_2 = trade_logger.log_signal(valid_signal.model_dump())

    # Approve
    assert risk_manager.approve(valid_signal, signal_id=signal_id_2) is True

    # Execute (Mocking MT5 successful placement)
    ticket = 123456
    trade_logger.log_trade(
        ticket=ticket,
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.5, # 5 pips slippage
        lot_size=0.1,
        signal_id=signal_id_2
    )

    # Update to closed
    trade_logger.update_trade(
        ticket=ticket,
        exit_price=2310.0,
        pnl=95.0,
        drawdown_impact=0.01
    )

    # --- ANALYSIS PHASE ---

    # 1. Analyze Blocked Signals
    start_analysis = datetime.now(timezone.utc) - timedelta(hours=2)
    blocked_analyses = analyzer.analyze_blocked_signals(start_time=start_analysis, persist=True)

    assert len(blocked_analyses) >= 1
    analysis = next(a for a in blocked_analyses if a.signal_id == signal_id)
    assert analysis.opportunity_cost_pnl > 0 # Since mock price went up to 2302+

    # Verify DB persistence for blocked
    with trade_logger.Session() as session:
        db_blocked = session.execute(select(BlockedSignalAnalysis).where(BlockedSignalAnalysis.signal_id == signal_id)).scalar_one_or_none()
        assert db_blocked is not None
        assert db_blocked.rejection_reason == event.description

    # 2. Analyze Executed Trades
    with trade_logger.Session() as session:
        trade_db = session.execute(select(Trade).where(Trade.ticket == ticket)).scalar_one()
        trade_id = trade_db.id

    quality = analyzer.analyze_trade(trade_id, persist=True)
    assert quality is not None
    assert quality.slippage_pips == pytest.approx(5.0)

    # Verify DB persistence for quality
    with trade_logger.Session() as session:
        db_quality = session.execute(select(ExecutionQuality).where(ExecutionQuality.trade_id == trade_id)).scalar_one_or_none()
        assert db_quality is not None
        assert db_quality.slippage_pips == pytest.approx(5.0)

    # --- REPORTING PHASE ---
    summary = analyzer.generate_summary_report(days=1)
    assert summary.executed_trade_count == 1
    assert summary.rejected_signal_count == 1
    assert summary.avg_slippage == pytest.approx(5.0)
    assert summary.total_opportunity_cost > 0

    report_section = summary.to_report_section()
    assert report_section.trade_count == 1
    assert report_section.rejected_count == 1
