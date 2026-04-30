"""
Unit tests for Execution Quality Analytics.
tests/test_execution_quality.py
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from src.analytics.execution_quality import ExecutionAnalyzer
from src.core.trade_logger import ModelSignal, Trade


@pytest.fixture
def analyzer():
    return ExecutionAnalyzer(pip_value=0.1)


@pytest.fixture
def sample_market_data():
    base_time = datetime.now(timezone.utc) - timedelta(hours=1)
    data = []
    for i in range(120):
        data.append({
            "time": base_time + timedelta(minutes=i),
            "open": 2300.0 + (i * 0.1),
            "high": 2300.5 + (i * 0.1),
            "low": 2299.5 + (i * 0.1),
            "close": 2300.0 + (i * 0.1),
        })
    return pd.DataFrame(data)


def test_analyze_trade_metrics(analyzer, sample_market_data):
    # Setup Signal
    signal_time = sample_market_data.iloc[0]["time"]
    signal = ModelSignal(
        id=1,
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        timestamp=signal_time
    )

    # Setup Trade (with slippage and latency)
    trade_time = signal_time + timedelta(seconds=2)
    trade = Trade(
        ticket=12345,
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.2,  # 2 pips slippage
        status="CLOSED",
        created_at=trade_time,
        updated_at=trade_time + timedelta(minutes=30)
    )
    trade.exit_price = 2305.0

    quality = analyzer.analyze_trade(trade, signal, sample_market_data)

    assert quality.ticket == 12345
    assert quality.slippage_pips == pytest.approx(2.0)
    assert quality.execution_latency_ms == 2000.0
    assert quality.fill_quality < 1.0
    assert quality.mfe_pips > 0
    assert quality.mae_pips >= 0
    assert quality.post_entry_drift_5m > 0


def test_analyze_blocked_signal(analyzer, sample_market_data):
    signal_time = sample_market_data.iloc[10]["time"]
    signal = ModelSignal(
        id=2,
        symbol="XAUUSD",
        direction=1,
        entry_price=2301.0,
        timestamp=signal_time
    )

    blocked = analyzer.analyze_blocked_signal(signal, sample_market_data, "Risk Limit")

    assert blocked.signal_id == 2
    assert blocked.rejection_reason == "Risk Limit"
    # Trend is up, so opportunity cost should be positive for BUY
    assert blocked.opportunity_cost_pips > 0
    assert blocked.was_correct_rejection is False


def test_get_summary(analyzer, sample_market_data):
    signal = ModelSignal(id=1, symbol="XAUUSD", direction=1, entry_price=2300.0, timestamp=datetime.now(timezone.utc))
    trade = Trade(ticket=1, symbol="XAUUSD", direction=1, entry_price=2300.1, created_at=datetime.now(timezone.utc))

    # Mocking results for summary
    q1 = analyzer.analyze_trade(trade, signal, sample_market_data)

    summary = analyzer.get_summary([q1], [])

    assert summary.total_trades == 1
    assert summary.avg_slippage_pips == q1.slippage_pips
    assert summary.blocked_signals_count == 0
