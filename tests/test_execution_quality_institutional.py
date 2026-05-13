"""
Institutional-grade unit tests for ExecutionAnalyzer refinements.
Focuses on mid-price accuracy, effective spread, and hypothetical exit logic.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.analytics.execution_quality import ExecutionAnalyzer
from src.core.trade_logger import ModelSignal, Trade


@pytest.fixture
def mock_connector():
    connector = MagicMock()

    def get_props(symbol):
        if "XAUUSD" in symbol:
            return {"digits": 2, "contract_size": 100.0, "point": 0.01, "pip_size": 0.1}
        return None

    connector.get_symbol_properties.side_effect = get_props
    return connector

@pytest.fixture
def analyzer(mock_connector):
    from src.core.database import get_engine
    get_engine.cache_clear()
    return ExecutionAnalyzer(db_url="sqlite:///:memory:", connector=mock_connector)

def test_effective_spread_calculation(analyzer, mock_connector):
    """Verify institutional effective spread calculation: 2 * |execution - mid|."""
    trade = Trade(
        ticket=123,
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.5,
        lot_size=0.1,
        created_at=datetime.now(timezone.utc)
    )

    # Mock mid price = 2300.4 (spread was 0.2, bid 2300.3, ask 2300.5)
    # distance = |2300.5 - 2300.4| = 0.1
    # effective_spread = 2 * 0.1 = 0.2
    # effective_spread_pips = 0.2 / 0.1 = 2.0 pips
    mock_connector.get_ticks_range.return_value = pd.DataFrame([
        {"bid": 2300.3, "ask": 2300.5}  # mid 2300.4
    ])

    # Add signal to DB to get an ID
    signal = ModelSignal(entry_price=2300.0, direction=1, timestamp=trade.created_at, symbol="XAUUSD")
    with analyzer.Session() as session:
        session.add(signal)
        session.commit()
        signal_id = signal.id

    spread_info = analyzer._get_execution_spread(trade)
    assert spread_info["mid_price"] == 2300.4

    # Mock trade for analyze_trade
    analyzer.calculate_alpha_decay = MagicMock(return_value=0.0)
    analyzer.calculate_markouts = MagicMock(return_value={})
    analyzer.calculate_edge_capture = MagicMock(return_value=0.0)

    trade.signal_id = signal_id
    with analyzer.Session() as session:
        session.add(trade)
        session.commit()
        trade_id = trade.id

    quality = analyzer.analyze_trade(trade_id)
    assert quality.effective_spread_pips == pytest.approx(2.0)
    # execution_cost = abs(slippage) + half_eff_spread
    # slippage = (2300.5 - 2300.0) / 0.1 = 5.0
    # half_eff_spread = 2.0 / 2 = 1.0
    # cost = 6.0
    assert quality.execution_cost_pips == pytest.approx(6.0)

def test_opportunity_cost_with_hypothetical_exit(analyzer, mock_connector):
    """Verify that opportunity cost uses TP/SL prices if hit."""
    signal = ModelSignal(
        id=99,
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        take_profit=2310.0,
        stop_loss=2290.0,
        lot_size=0.1,
        timestamp=datetime.now(timezone.utc) - timedelta(hours=1)
    )

    # Mock price movement: starts at 2300, hits 2312 (TP), ends at 2305
    # Old logic would use 2305. New logic should use 2310.
    # PnL = (2310 - 2300) * 0.1 * 100 = 100.0
    df = pd.DataFrame([
        {"time": signal.timestamp + timedelta(minutes=5), "close": 2300.0, "high": 2302.0, "low": 2298.0},
        {"time": signal.timestamp + timedelta(minutes=10), "close": 2308.0, "high": 2312.0, "low": 2300.0}, # Hits TP
        {"time": signal.timestamp + timedelta(minutes=15), "close": 2305.0, "high": 2306.0, "low": 2304.0}
    ])
    mock_connector.get_rates_range.return_value = df

    analysis = analyzer._evaluate_opportunity_cost(signal, "Risk")
    assert analysis.would_have_won is True
    assert analysis.opportunity_cost_pnl == pytest.approx(100.0)

def test_markout_mid_price_accuracy(analyzer, mock_connector):
    """Verify that markouts use mid-prices derived from close and spread."""
    entry_time = datetime.now(timezone.utc)
    # Bid 2300.0, Spread 20 points (0.2) -> Mid 2300.1
    # Entry 2300.0 (BUY)
    # Drift = 2300.1 - 2300.0 = 0.1 = 1.0 pips
    mock_connector.get_rates_range.return_value = pd.DataFrame([
        {"time": entry_time + timedelta(minutes=1), "close": 2300.0, "spread": 20}
    ])

    results = analyzer.calculate_markouts("XAUUSD", entry_time, 2300.0, 1, [1])
    assert results["1m"] == pytest.approx(1.0)
