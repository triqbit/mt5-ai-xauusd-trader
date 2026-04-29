"""
Unit tests for src/research/stress_lab.py
"""

import numpy as np
import pytest
from src.research.stress_lab import StressScenario, AdversarialTradingEnv, StressLab

@pytest.fixture
def dummy_data():
    # 100 steps, 4 features (OHLC)
    return np.random.rand(100, 4)

@pytest.fixture
def default_scenario():
    return StressScenario(
        name="Default Adversity",
        description="Standard stress test"
    )

def test_adversarial_env_init(dummy_data, default_scenario):
    env = AdversarialTradingEnv(dummy_data, default_scenario)
    assert env.scenario.name == "Default Adversity"
    assert env.data.shape == dummy_data.shape

def test_missing_ticks(dummy_data):
    scenario = StressScenario(
        name="Missing Ticks",
        description="High probability of missing ticks",
        missing_ticks_prob=1.0
    )
    env = AdversarialTradingEnv(dummy_data, scenario)
    obs, _ = env.reset()

    # Since prob=1.0, every step should just advance current_step and return 0 reward
    obs_next, reward, terminated, truncated, info = env.step(1)
    assert reward == 0.0
    assert env.current_step == env.window_size + 1

def test_service_degradation(dummy_data):
    scenario = StressScenario(
        name="Service Degradation",
        description="All actions dropped",
        service_degradation_prob=1.0
    )
    env = AdversarialTradingEnv(dummy_data, scenario)
    env.reset()

    # Try to buy, but should be dropped to Hold (0)
    obs, reward, terminated, truncated, info = env.step(1)
    assert env.position == 0.0

def test_stress_lab_report(dummy_data):
    class MockStrategy:
        def predict(self, obs, deterministic=True):
            return 0, {} # Always Hold

    scenarios = [
        StressScenario(name="S1", description="D1", spread_multiplier=2.0),
        StressScenario(name="S2", description="D2", slippage_prob=0.5, slippage_avg_pips=2.0)
    ]

    lab = StressLab(dummy_data, MockStrategy())
    report = lab.run_stress_test(scenarios)

    assert report.strategy_name == "MockStrategy"
    assert len(report.results) == 2
    assert report.overall_resilience_score >= 0.0
