"""
Unit tests for StressLab research module.
"""

import numpy as np
import pandas as pd
import pytest
from src.research.stress_lab import StressLab, StressType, StressReport


class MockStrategy:
    """Simple strategy that buys if price is above average, otherwise holds."""
    def predict(self, obs: np.ndarray) -> int:
        close = obs[3]
        if close > 1900:
            return 1
        return 0


@pytest.fixture
def sample_data():
    """Generate 100 bars of synthetic XAUUSD data."""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="h")
    data = pd.DataFrame({
        "open": np.linspace(1900, 1910, 100),
        "high": np.linspace(1905, 1915, 100),
        "low": np.linspace(1895, 1905, 100),
        "close": np.linspace(1900, 1910, 100),
        "tick_volume": np.random.randint(100, 1000, 100)
    }, index=dates)
    return data


def test_stress_lab_initialization(sample_data):
    lab = StressLab(sample_data)
    assert len(lab.data) == 100
    assert lab.initial_balance == 10000.0


def test_benchmark_run(sample_data):
    lab = StressLab(sample_data)
    strategy = MockStrategy()
    pnl = lab.run_benchmark(strategy)
    # With price going from 1900 to 1910, strategy should make some profit
    assert pnl != 0


def test_stress_test_report_generation(sample_data):
    lab = StressLab(sample_data)
    strategy = MockStrategy()
    report = lab.run_stress_test(
        strategy,
        stressors=[StressType.SPREAD_WIDENING, StressType.SLIPPAGE_SPIKES]
    )

    assert isinstance(report, StressReport)
    assert report.strategy_name == "MockStrategy"
    assert len(report.scenarios_run) == 2
    assert hasattr(report.metrics, "stability_score")


def test_missing_ticks_stressor(sample_data):
    lab = StressLab(sample_data)
    strategy = MockStrategy()
    # High intensity missing ticks should result in a report entry
    report = lab.run_stress_test(strategy, stressors=[StressType.MISSING_TICKS], intensity=5.0)

    missing_tick_events = [f for f in report.failure_points if f.stress_type == StressType.MISSING_TICKS]
    assert len(missing_tick_events) > 0


def test_all_stressors(sample_data):
    lab = StressLab(sample_data)
    strategy = MockStrategy()
    stressors = [
        StressType.SPREAD_WIDENING,
        StressType.SLIPPAGE_SPIKES,
        StressType.MISSING_TICKS,
        StressType.DELAYED_FILLS,
        StressType.CHOPPY_FAKE_BREAKOUTS,
        StressType.REGIME_TRANSITIONS,
        StressType.DEGRADED_SERVICE,
    ]
    report = lab.run_stress_test(strategy, stressors=stressors)
    assert len(report.scenarios_run) == 7
    assert isinstance(report.summary, str)
