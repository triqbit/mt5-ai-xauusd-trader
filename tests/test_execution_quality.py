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
    assert pytest.approx(quality.edge_capture) == 0.48

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
    mock_connector.get_rates.return_value = pd.DataFrame([
        {"time": signal.timestamp + timedelta(minutes=15), "open": 2300.0, "high": 2315.0, "low": 2299.0, "close": 2312.0}
    ])

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
    mock_connector.get_rates.return_value = pd.DataFrame([
        {"time": signal.timestamp + timedelta(minutes=15), "open": 2300.0, "high": 2315.0, "low": 2299.0, "close": 2312.0}
    ])

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
            edge_capture=0.5, post_entry_drift_5m=1.0, post_entry_drift_15m=2.0,
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
