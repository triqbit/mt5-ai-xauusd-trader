"""
Tests for Execution Quality Analytics.
"""

import pytest

from src.analytics.execution_quality import ExecutionAnalyzer


@pytest.fixture
def analyzer():
    return ExecutionAnalyzer(symbol="XAUUSD")


def test_calculate_slippage(analyzer):
    # Buy: requested 2000.0, executed 2000.10 -> 10 pips slippage
    slippage = analyzer.calculate_slippage(2000.0, 2000.10, 1)
    assert pytest.approx(slippage) == 10.0

    # Sell: requested 2000.0, executed 1999.90 -> 10 pips slippage
    slippage = analyzer.calculate_slippage(2000.0, 1999.90, -1)
    assert pytest.approx(slippage) == 10.0

    # Buy: requested 2000.0, executed 1999.95 -> -5 pips slippage (price improvement)
    slippage = analyzer.calculate_slippage(2000.0, 1999.95, 1)
    assert pytest.approx(slippage) == -5.0


def test_calculate_fill_quality(analyzer):
    # Slippage 0, spread 2 -> Score 1.0
    assert analyzer.calculate_fill_quality(0.0, 2.0) == 1.0

    # Slippage 1, spread 2 -> Score 1 - (1/4) = 0.75
    assert analyzer.calculate_fill_quality(1.0, 2.0) == 0.75

    # Slippage 4, spread 2 -> Score 1 - (4/4) = 0.0
    assert analyzer.calculate_fill_quality(4.0, 2.0) == 0.0

    # Negative slippage (improvement) -> Score 1.0
    assert analyzer.calculate_fill_quality(-1.0, 2.0) == 1.0


def test_analyze_timing_efficiency(analyzer):
    # Buy: Range 2000-2010, Entry 2000 -> 1.0 (perfect)
    assert analyzer.analyze_timing_efficiency(2000.0, 2010.0, 2000.0, 1) == 1.0

    # Buy: Entry 2010 -> 0.0 (worst)
    assert analyzer.analyze_timing_efficiency(2010.0, 2010.0, 2000.0, 1) == 0.0

    # Sell: Entry 2010 -> 1.0 (perfect)
    assert analyzer.analyze_timing_efficiency(2010.0, 2010.0, 2000.0, -1) == 1.0


def test_measure_edge_capture(analyzer):
    # Buy: Entry 2000, Exit 2010 (1000 pips), Spread 10 -> (1000 - 10) / 10 = 99.0
    edge = analyzer.measure_edge_capture(2000.0, 2010.0, 10.0, 1)
    assert pytest.approx(edge) == 99.0


def test_analyze_post_entry_drift(analyzer):
    intervals = {"5m": 2001.0, "15m": 1999.0}
    drift = analyzer.analyze_post_entry_drift(2000.0, intervals, 1)
    assert drift["5m"] == 100.0
    assert drift["15m"] == -100.0


def test_evaluate_blocked_trade(analyzer):
    # Blocked Buy: Signal 2000.0, Exit 2005.0 -> 500 pips opportunity cost
    cost = analyzer.evaluate_blocked_trade(2000.0, 2005.0, 1)
    assert pytest.approx(cost) == 500.0
