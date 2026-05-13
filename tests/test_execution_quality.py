"""
Unit tests for ExecutionAnalyzer and execution quality models.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.analytics.execution_quality import (
    BlockedSignalQuality,
    ExecutionAnalyzer,
    TradeExecutionQuality,
)
from src.core.trade_logger import ExecutionQuality, ModelSignal, Trade


@pytest.fixture
def mock_connector():
    connector = MagicMock()
    # Mock M1 rates for drift and timing efficiency
    rates_df = pd.DataFrame([
        {"time": datetime.now(timezone.utc), "open": 2300.0, "high": 2305.0, "low": 2295.0, "close": 2302.0, "spread": 20}
    ])
    connector.get_rates.return_value = rates_df
    connector.get_rates_range.return_value = rates_df

    # Mock symbol properties
    def get_props(symbol):
        if "XAUUSD" in symbol:
            return {"digits": 2, "contract_size": 100.0, "point": 0.01}
        elif "EURUSD" in symbol:
            return {"digits": 5, "contract_size": 100000.0, "point": 0.00001}
        return None

    connector.get_symbol_properties.side_effect = get_props
    return connector

@pytest.fixture
def analyzer(mock_connector):
    # Use in-memory SQLite for testing
    # Clear cache to ensure fresh DB for each test when using :memory:
    from src.core.database import get_engine
    get_engine.cache_clear()
    return ExecutionAnalyzer(db_url="sqlite:///:memory:", connector=mock_connector)

def test_trade_execution_quality_model():
    """Verify TradeExecutionQuality model validation."""
    data = {
        "trade_id": 1,
        "ticket": 12345,
        "symbol": "XAUUSD",
        "slippage_pips": 1.5,
        "execution_latency_ms": 150.0,
        "fill_quality_score": 0.9,
        "edge_capture": 0.8,
        "session": "London",
        "post_entry_drift_5m": 2.0,
        "post_entry_drift_15m": 5.0,
        "timing_efficiency": 0.7,
        "spread_at_execution": 2.0,
        "slippage_to_spread_ratio": 0.75,
        "alpha_decay_pips": 0.5,
        "broker_slippage_pips": 1.0,
        "effective_spread_pips": 2.0,
        "execution_cost_pips": 2.5,
        "markout_pnls": {"1m": 0.5, "5m": 2.0}
    }
    model = TradeExecutionQuality(**data)
    assert model.trade_id == 1
    assert model.slippage_pips == 1.5
    assert model.broker_slippage_pips == 1.0

def test_analyze_trade_logic(analyzer, mock_connector):
    """Test the core slippage, latency, and alpha decay logic."""
    with analyzer.Session() as session:
        # Create a mock signal and trade
        signal_time = datetime.now(timezone.utc) - timedelta(seconds=2)
        signal = ModelSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.0,
            timestamp=signal_time,
            take_profit=2310.0,
            volatility=5.0
        )
        session.add(signal)
        session.flush()

        trade = Trade(
            ticket=101,
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.2, # 2 pips slippage
            signal_id=signal.id,
            lot_size=0.1,
            created_at=signal_time + timedelta(seconds=1),
            exit_price=2305.0
        )
        session.add(trade)
        session.commit()

        trade_id = trade.id

    # Mock ticks for alpha decay: 2300.0 -> 2300.1 (mid move = 0.1 / 1 pip)
    mock_ticks = pd.DataFrame([
        {"time": signal_time, "bid": 2299.95, "ask": 2300.05}, # mid 2300.0
        {"time": trade.created_at, "bid": 2300.05, "ask": 2300.15} # mid 2300.1
    ])
    mock_connector.get_ticks_range.return_value = mock_ticks

    quality = analyzer.analyze_trade(trade_id)

    assert quality is not None
    assert pytest.approx(quality.slippage_pips) == 2.0
    assert pytest.approx(quality.alpha_decay_pips) == 1.0
    assert pytest.approx(quality.broker_slippage_pips) == 1.0
    assert quality.fill_quality_score < 1.0

def test_run_batch_analysis(analyzer, mock_connector):
    """Test batch analysis of multiple trades."""
    with analyzer.Session() as session:
        signal_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        for i in range(3):
            signal = ModelSignal(
                symbol="XAUUSD", direction=1, entry_price=2300.0,
                timestamp=signal_time, take_profit=2310.0
            )
            session.add(signal)
            session.flush()
            trade = Trade(
                ticket=200 + i, symbol="XAUUSD", direction=1, entry_price=2300.1,
                signal_id=signal.id, lot_size=0.1, created_at=signal_time + timedelta(seconds=1)
            )
            session.add(trade)
        session.commit()

    count = analyzer.run_batch_analysis(days=1)
    assert count == 3

    with analyzer.Session() as session:
        qualities = session.query(ExecutionQuality).all()
        assert len(qualities) == 3

def test_evaluate_opportunity_cost_temporal(analyzer, mock_connector):
    """Test analysis of blocked signals with temporal TP/SL logic."""
    signal = MagicMock(spec=ModelSignal)
    signal.id = 1
    signal.symbol = "XAUUSD"
    signal.direction = 1
    signal.entry_price = 2300.0
    signal.take_profit = 2310.0
    signal.stop_loss = 2290.0
    signal.lot_size = 0.1
    signal.timestamp = datetime.now(timezone.utc) - timedelta(minutes=60)

    # Scenario 1: Hits TP before SL
    df1 = pd.DataFrame([
        {"time": signal.timestamp + timedelta(minutes=5), "open": 2300.0, "high": 2311.0, "low": 2295.0, "close": 2305.0}, # Hits TP
        {"time": signal.timestamp + timedelta(minutes=10), "open": 2305.0, "high": 2306.0, "low": 2285.0, "close": 2290.0}, # Hits SL later
    ])
    mock_connector.get_rates_range.return_value = df1
    analysis1 = analyzer._evaluate_opportunity_cost(signal, "Risk limit reached")
    assert analysis1.would_have_won is True

    # Scenario 2: Hits SL before TP
    df2 = pd.DataFrame([
        {"time": signal.timestamp + timedelta(minutes=5), "open": 2300.0, "high": 2305.0, "low": 2289.0, "close": 2295.0}, # Hits SL
        {"time": signal.timestamp + timedelta(minutes=10), "open": 2295.0, "high": 2315.0, "low": 2294.0, "close": 2312.0}, # Hits TP later
    ])
    mock_connector.get_rates_range.return_value = df2
    analysis2 = analyzer._evaluate_opportunity_cost(signal, "Risk limit reached")
    assert analysis2.would_have_won is False

def test_calculate_markouts(analyzer, mock_connector):
    """Test price drift calculation at different horizons."""
    symbol = "XAUUSD"
    entry_time = datetime.now(timezone.utc)
    entry_price = 2300.0
    direction = 1
    horizons = [1, 5]

    mock_connector.get_rates_range.return_value = pd.DataFrame([
        {"time": entry_time + timedelta(minutes=1), "close": 2301.0},
        {"time": entry_time + timedelta(minutes=5), "close": 2305.0},
    ])

    results = analyzer.calculate_markouts(symbol, entry_time, entry_price, direction, horizons)
    assert results["1m"] == 10.0
    assert results["5m"] == 50.0

def test_generate_summary_report(analyzer):
    """Test aggregation into summary report."""
    with patch.object(analyzer, 'analyze_trade') as mock_at, \
         patch.object(analyzer, 'analyze_blocked_signals') as mock_abs:

        mock_at.return_value = TradeExecutionQuality(
            trade_id=1, ticket=1, symbol="XAUUSD", slippage_pips=1.0,
            execution_latency_ms=100.0, fill_quality_score=0.9,
            edge_capture=0.5, session="London",
            post_entry_drift_5m=1.0, post_entry_drift_15m=2.0,
            timing_efficiency=0.8, spread_at_execution=2.0,
            slippage_to_spread_ratio=0.5, alpha_decay_pips=0.1,
            broker_slippage_pips=0.9, effective_spread_pips=2.0,
            execution_cost_pips=2.0, markout_pnls={"5m": 1.0}
        )
        mock_abs.return_value = [
            BlockedSignalQuality(
                signal_id=10, symbol="XAUUSD", rejection_reason="Risk",
                opportunity_cost_pnl=100.0, max_favorable_excursion=5.0,
                max_adverse_excursion=2.0, would_have_won=True
            )
        ]

        with analyzer.Session() as session:
            t = Trade(ticket=1, symbol="XAUUSD", direction=1, entry_price=2300.0, lot_size=0.1, created_at=datetime.now(timezone.utc))
            session.add(t)
            session.commit()

        summary = analyzer.generate_summary_report(days=1)
        assert summary.avg_broker_slippage == 0.9
        assert summary.total_opportunity_cost == 100.0
        assert summary.avg_mae == 2.0
        assert summary.avg_mfe == 5.0

        report_section = summary.to_report_section()
        assert report_section is not None
        assert "MAE: 2.00" in report_section.opportunity_cost
        assert "MFE: 5.00" in report_section.opportunity_cost

def test_alpha_decay_edge_cases(analyzer, mock_connector):
    """Test alpha decay fallback logic."""
    trade = MagicMock(spec=Trade)
    trade.symbol = "XAUUSD"
    trade.created_at = datetime.now(timezone.utc)
    trade.direction = 1

    signal = MagicMock(spec=ModelSignal)
    signal.timestamp = trade.created_at - timedelta(seconds=2)
    signal.direction = 1

    # Case 1: Ticks fail, fallback to M1 rates
    mock_connector.get_ticks_range.side_effect = Exception("No ticks")
    mock_connector.get_rates_range.return_value = pd.DataFrame([
        {"time": signal.timestamp, "open": 2300.0, "close": 2301.0},
        {"time": trade.created_at, "open": 2301.0, "close": 2302.0}
    ])

    decay = analyzer.calculate_alpha_decay(trade, signal)
    # market_move = (df.iloc[-1]["close"] - df.iloc[0]["open"]) * signal.direction
    # (2302.0 - 2300.0) * 1 = 2.0
    # XAUUSD pip_size = 0.1 -> 20.0 pips
    assert decay == 20.0

    # Case 2: Everything fails
    mock_connector.get_rates_range.return_value = pd.DataFrame()
    decay = analyzer.calculate_alpha_decay(trade, signal)
    assert decay == 0.0

def test_market_session_detection(analyzer):
    """Test that market sessions are correctly identified."""
    dt_asian = datetime(2024, 1, 1, 4, 0, tzinfo=timezone.utc)
    assert analyzer._get_market_session(dt_asian) == "Asian"
    dt_london = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    assert analyzer._get_market_session(dt_london) == "London"

def test_execution_quality_persistence(analyzer):
    """Test that execution quality metrics can be persisted to DB."""
    # Since foreign keys are now enforced, we must create a trade first
    with analyzer.Session() as session:
        trade = Trade(
            ticket=1001,
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            lot_size=0.1,
            status="CLOSED"
        )
        session.add(trade)
        session.commit()
        trade_id = trade.id

    quality_data = TradeExecutionQuality(
        trade_id=trade_id, ticket=1001, symbol="XAUUSD", slippage_pips=1.2,
        execution_latency_ms=250.0, fill_quality_score=0.85,
        edge_capture=0.6, session="London", post_entry_drift_5m=0.5,
        post_entry_drift_15m=1.2, timing_efficiency=0.75,
        spread_at_execution=2.0, slippage_to_spread_ratio=0.6,
        alpha_decay_pips=0.3, broker_slippage_pips=0.9,
        effective_spread_pips=2.0, execution_cost_pips=2.2,
        markout_pnls={"5m": 0.5}
    )

    analyzer.save_execution_quality(quality_data)

    with analyzer.Session() as session:
        saved = session.query(ExecutionQuality).filter_by(trade_id=trade_id).first()
        assert saved is not None
        assert saved.broker_slippage_pips == 0.9
        assert saved.effective_spread_pips == 2.0

def test_dynamic_properties(analyzer):
    """Test that pip size and contract size are correctly fetched from connector."""
    assert analyzer._get_pip_size("XAUUSD") == 0.1
    assert analyzer._get_contract_size("XAUUSD") == 100.0
    assert analyzer._get_pip_size("EURUSD") == 0.0001
    assert analyzer._get_contract_size("EURUSD") == 100000.0

def test_tick_based_calculations(analyzer, mock_connector):
    """Test that analyzer uses tick data when available."""
    trade = MagicMock(spec=Trade)
    trade.symbol = "XAUUSD"
    trade.created_at = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)
    trade.direction = 1

    signal = MagicMock(spec=ModelSignal)
    signal.timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    signal.direction = 1

    mock_ticks = pd.DataFrame([
        {"time": signal.timestamp, "bid": 2300.0, "ask": 2301.0},
        {"time": trade.created_at, "bid": 2300.5, "ask": 2301.5}
    ])
    mock_connector.get_ticks_range.return_value = mock_ticks

    decay = analyzer.calculate_alpha_decay(trade, signal)
    assert decay == 5.0
