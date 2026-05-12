"""
Robustness tests for ExecutionAnalyzer.
Focuses on edge cases, missing data, and malformed inputs.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.analytics.execution_quality import (
    ExecutionAnalyzer,
)
from src.core.trade_logger import ModelSignal, Trade


@pytest.fixture
def mock_connector():
    connector = MagicMock()
    connector.get_symbol_properties.return_value = {"digits": 2, "contract_size": 100.0}
    connector.get_rates_range.return_value = pd.DataFrame()
    connector.get_ticks_range.return_value = pd.DataFrame()
    return connector

@pytest.fixture
def analyzer(mock_connector):
    from src.core.database import get_engine
    get_engine.cache_clear()
    return ExecutionAnalyzer(db_url="sqlite:///:memory:", connector=mock_connector)

def test_analyze_trade_missing_signal(analyzer):
    """Verify that a trade without a signal is handled gracefully."""
    with analyzer.Session() as session:
        trade = Trade(
            ticket=999,
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.0,
            lot_size=0.1,
            signal_id=None # No signal
        )
        session.add(trade)
        session.commit()
        trade_id = trade.id

    result = analyzer.analyze_trade(trade_id)
    assert result is None

def test_analyze_trade_missing_market_data(analyzer, mock_connector):
    """Verify analysis continues even if market data is missing for some metrics."""
    with analyzer.Session() as session:
        signal = ModelSignal(
            symbol="XAUUSD", direction=1, entry_price=2300.0,
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=10)
        )
        session.add(signal)
        session.flush()
        trade = Trade(
            ticket=888, symbol="XAUUSD", direction=1, entry_price=2300.1,
            signal_id=signal.id, lot_size=0.1
        )
        session.add(trade)
        session.commit()
        trade_id = trade.id

    # Mock empty data returns
    mock_connector.get_rates_range.return_value = pd.DataFrame()
    mock_connector.get_ticks_range.return_value = pd.DataFrame()

    quality = analyzer.analyze_trade(trade_id)
    assert quality is not None
    assert pytest.approx(quality.slippage_pips) == 1.0
    assert quality.alpha_decay_pips == 0.0 # Default fallback
    assert quality.timing_efficiency == 0.5 # Default fallback

def test_evaluate_opportunity_cost_empty_data(analyzer, mock_connector):
    """Verify opportunity cost analysis handles missing historical data."""
    signal = ModelSignal(
        id=1, symbol="XAUUSD", direction=1, entry_price=2300.0,
        timestamp=datetime.now(timezone.utc), lot_size=0.1
    )
    mock_connector.get_rates_range.return_value = pd.DataFrame()
    mock_connector.get_rates.return_value = pd.DataFrame()

    result = analyzer._evaluate_opportunity_cost(signal, "Test rejection")
    assert result is None

def test_analyze_blocked_signals_no_events(analyzer):
    """Verify analyze_blocked_signals handles no rejection events."""
    start_time = datetime.now(timezone.utc) - timedelta(hours=1)
    results = analyzer.analyze_blocked_signals(start_time)
    assert results == []

def test_run_batch_analysis_no_trades(analyzer):
    """Verify batch analysis handles empty database."""
    count = analyzer.run_batch_analysis(days=1)
    assert count == 0

def test_pip_size_robustness(analyzer, mock_connector):
    """Test pip size detection for various symbol formats."""
    # 1. JPY pair (3 digits)
    mock_connector.get_symbol_properties.return_value = {"digits": 3}
    assert analyzer._get_pip_size("USDJPY") == 0.01

    # 2. Standard FX (5 digits)
    mock_connector.get_symbol_properties.return_value = {"digits": 5}
    assert analyzer._get_pip_size("EURUSD") == 0.0001

    # 3. Gold with 3 digits
    mock_connector.get_symbol_properties.return_value = {"digits": 3}
    assert analyzer._get_pip_size("XAUUSD.m") == 0.1

    # 4. Unknown crypto
    mock_connector.get_symbol_properties.return_value = {"digits": 2}
    assert analyzer._get_pip_size("BTCUSD") == 1.0

def test_timing_efficiency_flat_candle(analyzer, mock_connector):
    """Test timing efficiency when candle has no range (high == low)."""
    trade = Trade(direction=1, entry_price=2300.0, created_at=datetime.now(timezone.utc))
    mock_connector.get_rates_range.return_value = pd.DataFrame([
        {"high": 2300.0, "low": 2300.0}
    ])

    # Range is 0, should return 1.0 (perfect timing if we hit the only available price)
    eff = analyzer._calculate_timing_efficiency(trade)
    assert eff == 1.0
