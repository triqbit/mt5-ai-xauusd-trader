"""
Tests for the Execution Quality module.
"""

from datetime import datetime, timedelta, timezone
import pytest
from src.analytics.execution_quality import ExecutionAnalyzer, ExecutionMetrics, PostEntryDrift


@pytest.fixture
def analyzer():
    return ExecutionAnalyzer(pip_size=0.01)  # XAUUSD


def test_analyze_execution_favorable(analyzer):
    signal_time = datetime.now(timezone.utc) - timedelta(seconds=2)
    execution_time = datetime.now(timezone.utc)

    # BUY signal at 2300.50, executed at 2300.45 (better price)
    metrics = analyzer.analyze_execution(
        ticket=123,
        symbol="XAUUSD",
        direction=1,
        signal_price=2300.50,
        execution_price=2300.45,
        signal_time=signal_time,
        execution_time=execution_time,
        spread=0.1
    )

    assert metrics.slippage_raw > 0
    assert metrics.slippage_pips == 5.0  # (2300.50 - 2300.45) / 0.01
    assert metrics.fill_quality.score == 1.0
    assert metrics.fill_quality.is_favorable is True
    assert metrics.latency_ms >= 2000.0


def test_analyze_execution_unfavorable(analyzer):
    signal_time = datetime.now(timezone.utc) - timedelta(seconds=1)
    execution_time = datetime.now(timezone.utc)

    # SELL signal at 2300.50, executed at 2300.40 (worse price for sell)
    metrics = analyzer.analyze_execution(
        ticket=456,
        symbol="XAUUSD",
        direction=-1,
        signal_price=2300.50,
        execution_price=2300.40,
        signal_time=signal_time,
        execution_time=execution_time,
        spread=0.1
    )

    assert metrics.slippage_raw < 0
    assert metrics.slippage_pips == -10.0  # (2300.40 - 2300.50) / 0.01
    assert metrics.fill_quality.is_favorable is False
    # Spread is 0.1 (10 pips). Slippage is -10 pips.
    # Score = 1.0 - (10 / (10 * 2)) = 1.0 - 0.5 = 0.5
    assert metrics.fill_quality.score == 0.5


def test_calculate_post_entry_drift(analyzer):
    entry_time = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    entry_price = 2300.0

    future_prices = [
        (entry_time + timedelta(minutes=5), 2305.0),
        (entry_time + timedelta(minutes=15), 2310.0),
        (entry_time + timedelta(minutes=30), 2308.0),
        (entry_time + timedelta(minutes=60), 2315.0),
    ]

    # BUY trade
    drift = analyzer.calculate_post_entry_drift(
        ticket=123,
        entry_price=entry_price,
        direction=1,
        future_prices=future_prices,
        entry_time=entry_time
    )

    assert drift.drift_metrics["5m"] == 500.0  # (2305 - 2300) / 0.01
    assert drift.drift_metrics["15m"] == 1000.0
    assert drift.drift_metrics["60m"] == 1500.0


def test_analyze_blocked_trade(analyzer):
    signal_time = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    signal_price = 2300.0

    future_prices = [
        (signal_time + timedelta(minutes=5), 2301.0),
        (signal_time + timedelta(minutes=15), 2303.0),
    ]

    # Blocked BUY signal
    blocked = analyzer.analyze_blocked_trade(
        signal_id=999,
        symbol="XAUUSD",
        reason="Max Exposure Reached",
        direction=1,
        signal_price=signal_price,
        signal_time=signal_time,
        future_prices=future_prices
    )

    assert blocked.opportunity_cost == 300.0  # Max favorable drift was at 15m (3.0 points = 300 pips)
    assert blocked.post_signal_drift["5m"] == 100.0


def test_generate_quality_report(analyzer):
    signal_time = datetime.now(timezone.utc)
    execution_time = signal_time + timedelta(milliseconds=500)

    exec_metrics = analyzer.analyze_execution(
        ticket=789,
        symbol="XAUUSD",
        direction=1,
        signal_price=2300.0,
        execution_price=2300.0,
        signal_time=signal_time,
        execution_time=execution_time,
        spread=0.1
    )

    report = analyzer.generate_quality_report(exec_metrics)

    assert report.ticket == 789
    assert report.overall_score > 0
    assert report.execution.latency_ms == 500.0
