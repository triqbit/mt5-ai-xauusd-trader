"""
Enhanced unit tests for ExecutionAnalyzer focusing on new institutional metrics.
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


def test_calculate_excursions_buy(analyzer, mock_connector):
    """Test MFE/MAE calculation for a BUY trade."""
    trade = Trade(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        exit_price=2305.0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )

    # High 2307, Low 2298
    # MFE = 2307 - 2300 = 7.0 (70 pips)
    # MAE = 2300 - 2298 = 2.0 (20 pips)
    mock_connector.get_rates_range.return_value = pd.DataFrame(
        [
            {"high": 2302.0, "low": 2299.0},
            {"high": 2307.0, "low": 2301.0},
            {"high": 2305.0, "low": 2298.0},
        ]
    )

    excursions = analyzer.calculate_excursions(trade)
    assert excursions["mfe"] == 70.0
    assert excursions["mae"] == 20.0


def test_implementation_shortfall_calculation(analyzer, mock_connector):
    """Verify implementation shortfall: slippage + alpha decay."""
    signal_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    signal = ModelSignal(symbol="XAUUSD", direction=1, entry_price=2300.0, timestamp=signal_time)

    trade = Trade(
        ticket=777,
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.5,  # 5 pips slippage
        lot_size=0.1,
        created_at=signal_time + timedelta(seconds=5),
        exit_price=2310.0,
    )

    # Mock alpha decay: 2300.0 to 2300.2 = 2 pips
    analyzer.calculate_alpha_decay = MagicMock(return_value=2.0)
    analyzer.calculate_excursions = MagicMock(return_value={"mfe": 0.0, "mae": 0.0})
    analyzer.calculate_markouts = MagicMock(return_value={})
    analyzer.calculate_edge_capture = MagicMock(return_value=0.0)

    with analyzer.Session() as session:
        session.add(signal)
        session.flush()
        trade.signal_id = signal.id
        session.add(trade)
        session.commit()
        trade_id = trade.id

    quality = analyzer.analyze_trade(trade_id)
    # slippage = 5.0, alpha_decay = 2.0 -> IS = 7.0
    assert quality.implementation_shortfall_pips == 7.0


def test_conservative_opportunity_cost(analyzer, mock_connector):
    """Verify that SL hit is prioritized over TP in the same candle for blocked signals."""
    signal = ModelSignal(
        id=999,
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        take_profit=2310.0,
        stop_loss=2290.0,
        lot_size=0.1,
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=30),
    )

    # One candle hits both: High 2315, Low 2285
    df = pd.DataFrame(
        [
            {
                "time": signal.timestamp + timedelta(minutes=5),
                "close": 2300.0,
                "high": 2315.0,
                "low": 2285.0,
            }
        ]
    )
    mock_connector.get_rates_range.return_value = df

    analysis = analyzer._evaluate_opportunity_cost(signal, "Risk")
    assert analysis.would_have_won is False  # Conservative assumption
    assert analysis.opportunity_cost_pnl < 0  # Loss due to SL hit
