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
        {
            "time": datetime.now(timezone.utc),
            "open": 2300.0,
            "high": 2305.0,
            "low": 2295.0,
            "close": 2302.0,
            "spread": 20
        }
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
    mock_connector.get_rates_range.return_value = df

    analysis = analyzer._evaluate_opportunity_cost(signal, "Risk limit reached")

    assert analysis is not None
    assert analysis.would_have_won is True


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

    assert pytest.approx(results["1m"]) == 10.0  # (2301 - 2300) / 0.1
    assert pytest.approx(results["5m"]) == 50.0
    assert pytest.approx(results["15m"]) == 150.0


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

        # Test reporting integration
        report_section = summary.to_report_section()
        assert report_section.efficiency_score == pytest.approx(summary.execution_efficiency_score * 100)
        assert report_section.opportunity_cost == "$50.00"
        assert len(report_section.metrics) > 0


def test_timezone_robustness(analyzer, mock_connector):
    """Test handling of timezone-naive datetimes in markout calculations."""
    symbol = "XAUUSD"
    # Naive datetime
    entry_time = datetime(2024, 1, 1, 12, 0, 0)
    entry_price = 2300.0
    direction = 1
    horizons = [5]

    # Mock returns aware datetime
    mock_connector.get_rates_range.return_value = pd.DataFrame([
        {"time": datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc), "close": 2305.0},
    ])

    results = analyzer.calculate_markouts(symbol, entry_time, entry_price, direction, horizons)
    assert pytest.approx(results["5m"]) == 50.0

def test_price_improvement(analyzer, mock_connector):
    """Test negative slippage (price improvement)."""
    with analyzer.Session() as session:
        signal_time = datetime.now(timezone.utc)
        signal = ModelSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.0,
            timestamp=signal_time,
            take_profit=2310.0
        )
        session.add(signal)
        session.flush()

        trade = Trade(
            ticket=202,
            symbol="XAUUSD",
            direction=1,
            entry_price=2299.8, # 2 pips improvement
            signal_id=signal.id,
            lot_size=0.1,
            created_at=signal_time + timedelta(milliseconds=100)
        )
        session.add(trade)
        session.commit()
        trade_id = trade.id

    quality = analyzer.analyze_trade(trade_id)
    assert pytest.approx(quality.slippage_pips) == -2.0
    # Fill quality should be high for price improvement
    assert quality.fill_quality_score > 0.7

def test_jpy_symbol_logic(analyzer, mock_connector):
    """Test pip and point logic for JPY pairs."""
    symbol = "USDJPY"
    entry_time = datetime.now(timezone.utc)
    entry_price = 150.00
    direction = 1
    horizons = [5]

    # Mock market data: price goes up by 0.05
    mock_connector.get_rates_range.return_value = pd.DataFrame([
        {"time": entry_time + timedelta(minutes=5), "close": 150.05},
    ])

    results = analyzer.calculate_markouts(symbol, entry_time, entry_price, direction, horizons)
    # JPY pip = 0.01. Drift = 0.05 / 0.01 = 5 pips
    assert pytest.approx(results["5m"]) == 5.0

    # Verify spread in pips for JPY
    with analyzer.Session() as session:
        # Create a signal for JPY
        signal = ModelSignal(
            symbol=symbol,
            direction=1,
            entry_price=150.00,
            timestamp=entry_time - timedelta(seconds=1)
        )
        session.add(signal)
        session.flush()

        trade = Trade(
            ticket=303,
            symbol=symbol,
            direction=1,
            entry_price=150.00,
            created_at=entry_time,
            lot_size=0.01,
            signal_id=signal.id
        )
        session.add(trade)
        session.commit()
        trade_id = trade.id

    # Mock spread: 20 points for JPY should be (20 * 0.001) / 0.01 = 2 pips
    # Need to include 'close' to avoid KeyError in markout calculations during analyze_trade
    mock_connector.get_rates_range.return_value = pd.DataFrame([
        {"time": entry_time, "spread": 20, "close": 150.00, "high": 150.01, "low": 149.99},
    ])

    quality = analyzer.analyze_trade(trade_id)
    assert quality is not None
    assert pytest.approx(quality.spread_at_execution) == 2.0
