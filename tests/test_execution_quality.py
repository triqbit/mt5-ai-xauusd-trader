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
from src.core.trade_logger import ModelSignal, Trade


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
        "execution_cost_pips": 2.5,
        "markout_pnls": {"1m": 0.5, "5m": 2.0}
    }
    model = TradeExecutionQuality(**data)
    assert model.trade_id == 1
    assert model.slippage_pips == 1.5
    assert model.spread_at_execution == 2.0

def test_analyze_trade_logic(analyzer, mock_connector):
    """Test the core slippage and latency calculation logic."""
    with analyzer.Session() as session:
        # Create a mock signal and trade
        signal_time = datetime.now(timezone.utc) - timedelta(seconds=1)
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
            entry_price=2300.2, # 2 pips slippage (0.2 / 0.1)
            signal_id=signal.id,
            lot_size=0.1,
            created_at=signal_time + timedelta(milliseconds=500),
            exit_price=2305.0
        )
        session.add(trade)
        session.commit()

        trade_id = trade.id

    quality = analyzer.analyze_trade(trade_id)

    assert quality is not None
    assert pytest.approx(quality.slippage_pips) == 2.0
    assert pytest.approx(quality.execution_latency_ms) == 500.0
    assert quality.fill_quality_score < 1.0
    # theoretical move: 2310 - 2300 = 10.0 (100 pips)
    # realized move: 2305 - 2300.2 = 4.8 (48 pips)
    # spread_pips (mock): 2.0 -> half_spread = 1.0
    # adjusted_realized = 48 - 1.0 = 47.0
    # edge_capture = 47 / 100 = 0.47
    assert pytest.approx(quality.edge_capture) == 0.47

def test_evaluate_opportunity_cost(analyzer, mock_connector):
    """Test analysis of blocked signals."""
    signal = MagicMock(spec=ModelSignal)
    signal.id = 1
    signal.symbol = "XAUUSD"
    signal.direction = 1
    signal.entry_price = 2300.0
    signal.take_profit = 2310.0
    signal.stop_loss = 2290.0
    signal.lot_size = 0.1
    signal.timestamp = datetime.now(timezone.utc) - timedelta(minutes=60)

    # Mock market movement: goes to 2315 (hits TP)
    df = pd.DataFrame([
        {"time": signal.timestamp + timedelta(minutes=15), "open": 2300.0, "high": 2315.0, "low": 2299.0, "close": 2312.0}
    ])
    mock_connector.get_rates.return_value = df
    mock_connector.get_rates_range.return_value = df

    analysis = analyzer._evaluate_opportunity_cost(signal, "Risk limit reached")

    assert analysis is not None


def test_calculate_markouts(analyzer, mock_connector):
    """Test price drift calculation at different horizons."""
    symbol = "XAUUSD"
    entry_time = datetime.now(timezone.utc)
    entry_price = 2300.0
    direction = 1
    horizons = [1, 5, 15]

    # Mock market data: price goes up
    mock_connector.get_rates_range.return_value = pd.DataFrame([
        {"time": entry_time + timedelta(minutes=1), "close": 2301.0},
        {"time": entry_time + timedelta(minutes=5), "close": 2305.0},
        {"time": entry_time + timedelta(minutes=15), "close": 2315.0},
    ])

    results = analyzer.calculate_markouts(symbol, entry_time, entry_price, direction, horizons)

    assert results["1m"] == 10.0  # (2301 - 2300) / 0.1
    assert results["5m"] == 50.0
    assert results["15m"] == 150.0


def test_evaluate_opportunity_cost_final(analyzer, mock_connector):
    """Re-verify opportunity cost after additions."""
    signal = MagicMock(spec=ModelSignal)
    signal.id = 1
    signal.symbol = "XAUUSD"
    signal.direction = 1
    signal.entry_price = 2300.0
    signal.take_profit = 2310.0
    signal.stop_loss = 2290.0
    signal.lot_size = 0.1
    signal.timestamp = datetime.now(timezone.utc) - timedelta(minutes=60)

    # Mock market movement: goes to 2315 (hits TP)
    df = pd.DataFrame([
        {"time": signal.timestamp + timedelta(minutes=15), "open": 2300.0, "high": 2315.0, "low": 2299.0, "close": 2312.0}
    ])
    mock_connector.get_rates.return_value = df
    mock_connector.get_rates_range.return_value = df

    analysis = analyzer._evaluate_opportunity_cost(signal, "Risk limit reached")
    assert analysis is not None
    assert analysis.would_have_won is True
    assert analysis.max_favorable_excursion > 0
    assert analysis.opportunity_cost_pnl > 0

def test_generate_summary_report(analyzer):
    """Test aggregation into summary report."""
    # Mock analyze_trade and analyze_blocked_signals
    with patch.object(analyzer, 'analyze_trade') as mock_at, \
         patch.object(analyzer, 'analyze_blocked_signals') as mock_abs:

        mock_at.return_value = TradeExecutionQuality(
            trade_id=1, ticket=1, symbol="XAUUSD", slippage_pips=1.0,
            execution_latency_ms=100.0, fill_quality_score=0.9,
            edge_capture=0.5, session="London",
            post_entry_drift_5m=1.0, post_entry_drift_15m=2.0,
            timing_efficiency=0.8, spread_at_execution=2.0,
            slippage_to_spread_ratio=0.5, alpha_decay_pips=0.1,
            execution_cost_pips=2.0, markout_pnls={"5m": 1.0}
        )

        mock_abs.return_value = [
            BlockedSignalQuality(
                signal_id=2, symbol="XAUUSD", rejection_reason="Reason",
                opportunity_cost_pnl=50.0, max_favorable_excursion=10.0,
                max_adverse_excursion=2.0, would_have_won=True
            )
        ]

        # Add a trade to DB so it gets picked up
        with analyzer.Session() as session:
            t = Trade(ticket=1, symbol="XAUUSD", direction=1, entry_price=2300.0, lot_size=0.1, created_at=datetime.now(timezone.utc))
            session.add(t)
            session.commit()

        summary = analyzer.generate_summary_report(days=1)

        assert summary.executed_trade_count == 1
        assert summary.rejected_signal_count == 1
        assert summary.total_opportunity_cost == 50.0
        assert summary.avg_slippage == 1.0

        # Test reporting integration
        report_section = summary.to_report_section()
        assert report_section.efficiency_score == pytest.approx(summary.execution_efficiency_score * 100)
        assert report_section.opportunity_cost == "$50.00"
        assert len(report_section.metrics) > 0

def test_dynamic_properties(analyzer):
    """Test that pip size and contract size are correctly fetched from connector."""
    # XAUUSD: digits=2 -> pip_size = 10^-(2-1) = 0.1
    assert analyzer._get_pip_size("XAUUSD") == 0.1
    assert analyzer._get_contract_size("XAUUSD") == 100.0

    # EURUSD: digits=5 -> pip_size = 10^-(5-1) = 0.0001
    assert analyzer._get_pip_size("EURUSD") == 0.0001
    assert analyzer._get_contract_size("EURUSD") == 100000.0

def test_dynamic_properties_enhanced(analyzer, mock_connector):
    """Test enhanced dynamic property detection with new fields."""
    symbol = "BTCUSD"

    # 1. Test MetaAPI style properties
    def get_meta_props(s):
        return {
            "digits": 2,
            "pip_size": 1.0,
            "trade_contract_size": 1.0,
            "point": 0.01
        }
    mock_connector.get_symbol_properties.side_effect = get_meta_props

    assert analyzer._get_pip_size(symbol) == 1.0
    assert analyzer._get_contract_size(symbol) == 1.0

    # 2. Test fallback to legacy contract_size
    def get_legacy_props(s):
        return {
            "digits": 3,
            "contract_size": 5000.0
        }
    mock_connector.get_symbol_properties.side_effect = get_legacy_props

    assert analyzer._get_pip_size(symbol) == 0.01 # 10^-(3-1)
    assert analyzer._get_contract_size(symbol) == 5000.0

def test_execution_spread_dynamic_point(analyzer, mock_connector):
    """Test that _get_execution_spread uses the point property from connector."""
    trade = MagicMock(spec=Trade)
    trade.symbol = "XAUUSD"
    trade.created_at = datetime.now(timezone.utc)

    # Mock rates with spread=20
    rates_df = pd.DataFrame([
        {"time": trade.created_at, "spread": 20}
    ])
    mock_connector.get_rates_range.return_value = rates_df

    # Mock properties with specific point size
    mock_connector.get_symbol_properties.side_effect = None
    mock_connector.get_symbol_properties.return_value = {
        "digits": 2,
        "point": 0.05 # Non-standard point for testing
    }

    # spread_pips = (avg_spread_points * point_size) / pip_size
    # = (20 * 0.05) / 0.1 = 1.0 / 0.1 = 10.0
    spread_info = analyzer._get_execution_spread(trade)
    assert spread_info["spread_pips"] == 10.0

def test_market_session_detection(analyzer):
    """Test that market sessions are correctly identified."""
    # Asian: 04:00 UTC
    dt_asian = datetime(2024, 1, 1, 4, 0, tzinfo=timezone.utc)
    assert analyzer._get_market_session(dt_asian) == "Asian"

    # London: 10:00 UTC
    dt_london = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    assert analyzer._get_market_session(dt_london) == "London"

    # London-NY Overlap: 14:00 UTC
    dt_overlap = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)
    assert analyzer._get_market_session(dt_overlap) == "London-NY"

    # NY: 18:00 UTC
    dt_ny = datetime(2024, 1, 1, 18, 0, tzinfo=timezone.utc)
    assert analyzer._get_market_session(dt_ny) == "NY"

def test_execution_quality_persistence(analyzer):
    """Test that execution quality metrics can be persisted to DB."""
    quality_data = TradeExecutionQuality(
        trade_id=1,
        ticket=1001,
        symbol="XAUUSD",
        slippage_pips=1.2,
        execution_latency_ms=250.0,
        fill_quality_score=0.85,
        edge_capture=0.6,
        session="London",
        post_entry_drift_5m=0.5,
        post_entry_drift_15m=1.2,
        timing_efficiency=0.75,
        spread_at_execution=2.0,
        slippage_to_spread_ratio=0.6,
        alpha_decay_pips=0.3,
        execution_cost_pips=2.2,
        markout_pnls={"5m": 0.5, "15m": 1.2}
    )

    analyzer.save_execution_quality(quality_data)

    from src.core.trade_logger import ExecutionQuality
    with analyzer.Session() as session:
        saved = session.query(ExecutionQuality).filter_by(trade_id=1).first()
        assert saved is not None
        assert saved.slippage_pips == 1.2
        assert saved.session == "London"
        assert "5m" in saved.markout_data

def test_tick_based_calculations(analyzer, mock_connector):
    """Test that analyzer uses tick data when available."""
    trade = MagicMock(spec=Trade)
    trade.symbol = "XAUUSD"
    trade.created_at = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)
    trade.direction = 1

    signal = MagicMock(spec=ModelSignal)
    signal.timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    signal.direction = 1

    # Mock ticks: 2300.0/2301.0 at signal, 2300.5/2301.5 at trade
    # mid: 2300.5 -> 2301.0 (move = +0.5)
    # alpha decay = 0.5 / 0.1 = 5.0 pips
    mock_ticks = pd.DataFrame([
        {"time": signal.timestamp, "bid": 2300.0, "ask": 2301.0},
        {"time": trade.created_at, "bid": 2300.5, "ask": 2301.5}
    ])
    mock_connector.get_ticks_range.return_value = mock_ticks

    decay = analyzer.calculate_alpha_decay(trade, signal)
    assert decay == 5.0
    mock_connector.get_ticks_range.assert_called()

def test_blocked_signal_persistence(analyzer):
    """Test that blocked signal analysis can be persisted to DB."""
    blocked_data = BlockedSignalQuality(
        signal_id=10,
        symbol="XAUUSD",
        rejection_reason="Max Drawdown Reached",
        opportunity_cost_pnl=150.0,
        max_favorable_excursion=2.5,
        max_adverse_excursion=0.5,
        would_have_won=True
    )

    analyzer.save_blocked_analysis(blocked_data)

    from src.core.trade_logger import BlockedSignalAnalysis
    with analyzer.Session() as session:
        saved = session.query(BlockedSignalAnalysis).filter_by(signal_id=10).first()
        assert saved is not None
        assert saved.opportunity_cost_pnl == 150.0
        assert saved.rejection_reason == "Max Drawdown Reached"
        assert saved.would_have_won is True
