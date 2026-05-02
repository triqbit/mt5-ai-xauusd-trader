"""
Unit tests for StressLab resilience testing framework.
"""

import numpy as np
import pandas as pd
import pytest

from src.research.benchmarks import EMACrossoverStrategy
from src.research.stress_lab import StressLab, StressScenario, StressTestMetrics


@pytest.fixture
def sample_data():
    """Generate 100 steps of ranging market data."""
    np.random.seed(42)
    n = 100
    prices = 2300 + np.cumsum(np.random.normal(0, 1, n))
    df = pd.DataFrame(
        {
            "open": prices - 0.5,
            "high": prices + 1.0,
            "low": prices - 1.0,
            "close": prices,
            "tick_volume": np.random.randint(100, 1000, n),
            "spread": np.ones(n) * 0.2,
        }
    )
    return df


def test_stress_lab_initialization(sample_data):
    strategy = EMACrossoverStrategy()
    lab = StressLab(strategy, sample_data)
    assert lab.strategy.name.startswith("EMA_Crossover")
    assert len(lab.data) == 100


def test_apply_perturbations_noise(sample_data):
    strategy = EMACrossoverStrategy()
    lab = StressLab(strategy, sample_data)
    scenario = StressScenario(
        name="Noise Test", description="Testing price noise", price_noise_sigma=1.0
    )

    perturbed = lab._apply_perturbations(sample_data, scenario)
    assert not np.array_equal(sample_data["close"].values, perturbed["close"].values)
    assert all(perturbed["high"] >= perturbed["low"])


def test_apply_perturbations_missing_ticks(sample_data):
    strategy = EMACrossoverStrategy()
    lab = StressLab(strategy, sample_data)
    scenario = StressScenario(
        name="Missing Ticks", description="Testing missing data", missing_tick_prob=0.2
    )

    perturbed = lab._apply_perturbations(sample_data, scenario)
    assert len(perturbed) < len(sample_data)


def test_run_scenario_execution_delay(sample_data):
    strategy = EMACrossoverStrategy()
    lab = StressLab(strategy, sample_data)

    # Baseline run (no stress)
    normal_scenario = StressScenario(name="Normal", description="No stress")
    normal_metrics = lab.run_scenario(normal_scenario)

    # Delayed run
    delayed_scenario = StressScenario(
        name="Delayed", description="Execution delay", execution_delay_steps=5
    )
    delayed_metrics = lab.run_scenario(delayed_scenario)

    # Metrics should likely differ
    assert (
        normal_metrics.num_trades != delayed_metrics.num_trades
        or normal_metrics.total_return != delayed_metrics.total_return
    )


def test_generate_report(sample_data):
    strategy = EMACrossoverStrategy()
    lab = StressLab(strategy, sample_data)

    baseline = StressTestMetrics(
        total_return=0.1,
        max_drawdown=0.05,
        sharpe_ratio=2.0,
        win_rate=0.6,
        num_trades=10,
        execution_quality_score=1.0,
        latency_impact=0.0,
    )

    # Run a failing scenario
    fail_scenario = StressScenario(name="Crash", description="Heavy slippage", slippage_bps=100.0)
    lab.run_scenario(fail_scenario)

    report = lab.generate_report(baseline)

    assert report.strategy_name == strategy.name
    assert report.resilience_score >= 0
    assert len(report.scenario_results) == 1
    assert "Crash" in report.scenario_results


def test_service_failure_impact(sample_data):
    strategy = EMACrossoverStrategy()
    lab = StressLab(strategy, sample_data)

    fail_scenario = StressScenario(
        name="Service Outage",
        description="High service failure probability",
        service_failure_prob=0.5,
    )
    metrics = lab.run_scenario(fail_scenario)

    assert metrics.execution_quality_score < 1.0
    assert metrics.latency_impact > 0.0


def test_choppy_breakout_perturbation(sample_data):
    strategy = EMACrossoverStrategy()
    lab = StressLab(strategy, sample_data)
    scenario = StressScenario(
        name="Choppy", description="Testing choppy breakouts", choppy_breakout_prob=0.5
    )
    perturbed = lab._apply_perturbations(sample_data, scenario)
    # Check if high/low or close were modified beyond original
    assert not np.array_equal(sample_data["high"].values, perturbed["high"].values)


def test_regime_flip_perturbation(sample_data):
    strategy = EMACrossoverStrategy()
    lab = StressLab(strategy, sample_data)
    scenario = StressScenario(name="Flip", description="Testing regime flip", regime_flip_prob=0.5)
    perturbed = lab._apply_perturbations(sample_data, scenario)
    assert not np.array_equal(sample_data["close"].values, perturbed["close"].values)


def test_generate_summary_critical(sample_data):
    strategy = EMACrossoverStrategy()
    lab = StressLab(strategy, sample_data)

    # Mock results to force a critical summary
    lab.results["Bad"] = StressTestMetrics(
        total_return=-0.5,
        max_drawdown=0.6,
        sharpe_ratio=-1.0,
        win_rate=0.2,
        num_trades=10,
        execution_quality_score=1.0,
        latency_impact=0.0,
    )

    baseline = StressTestMetrics(
        total_return=0.1,
        max_drawdown=0.05,
        sharpe_ratio=2.0,
        win_rate=0.6,
        num_trades=10,
        execution_quality_score=1.0,
        latency_impact=0.0,
    )

    report = lab.generate_report(baseline)
    assert "CRITICAL" in report.degradation_summary


def test_slippage_spike_logic(sample_data):
    strategy = EMACrossoverStrategy()
    lab = StressLab(strategy, sample_data)

    scenario = StressScenario(
        name="Spike",
        description="Testing slippage spikes",
        slippage_bps=5.0,
        slippage_spike_prob=1.0,  # Force spike every step
        slippage_spike_magnitude_bps=100.0,
    )

    metrics = lab.run_scenario(scenario)
    assert metrics.max_slippage_experienced == 105.0


def test_factory_methods():
    hell = StressLab.create_execution_hell_scenario()
    assert hell.name == "Execution Hell"
    assert hell.slippage_spike_prob > 0

    crisis = StressLab.create_liquidity_crisis_scenario()
    assert crisis.name == "Liquidity Crisis"
    assert crisis.missing_tick_prob > 0

    shock = StressLab.create_regime_shock_scenario()
    assert shock.name == "Regime Shock"
    assert shock.regime_flip_prob > 0


def test_to_report_section(sample_data):
    strategy = EMACrossoverStrategy()
    lab = StressLab(strategy, sample_data)

    baseline = StressTestMetrics(
        total_return=0.1,
        max_drawdown=0.05,
        sharpe_ratio=2.0,
        win_rate=0.6,
        num_trades=10,
        execution_quality_score=1.0,
        latency_impact=0.0,
    )

    lab.run_scenario(StressScenario(name="Test", description="test"))
    report = lab.generate_report(baseline)

    section = report.to_report_section()
    from src.research.reporting import StressTestSection

    assert isinstance(section, StressTestSection)
    assert section.resilience_score == report.resilience_score
    assert len(section.scenarios) == 1
    assert section.scenarios[0].name == "Test"


def test_spread_multiplier_impact(sample_data):
    strategy = EMACrossoverStrategy()
    lab = StressLab(strategy, sample_data)

    # Normal spread
    normal_scenario = StressScenario(name="Normal", description="test", spread_multiplier=1.0)
    normal_metrics = lab.run_scenario(normal_scenario)

    # Wider spread
    wide_scenario = StressScenario(name="Wide", description="test", spread_multiplier=10.0)
    wide_metrics = lab.run_scenario(wide_scenario)

    # Returns should be lower with wider spread if trades were made
    if normal_metrics.num_trades > 0:
        assert wide_metrics.total_return < normal_metrics.total_return
