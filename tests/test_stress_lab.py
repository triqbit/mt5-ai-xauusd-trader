
import pytest
import numpy as np
import gymnasium as gym
from src.environment.gym_env import TradingEnv
from src.research.stress_lab import StressScenario, AdversarialTradingEnv, StressLab

class MockModel:
    def predict(self, obs, deterministic=True):
        # Simple strategy: Always buy for testing execution logic
        return 1, None

@pytest.fixture
def base_env():
    # Create synthetic data: 200 steps, 5 features (OHLCV)
    data = np.zeros((200, 5))
    # Ensure close prices are positive and somewhat trending
    data[:, 3] = np.linspace(100, 110, 200) + np.random.normal(0, 0.1, 200)
    # Open, High, Low
    data[:, 0] = data[:, 3] - 0.1
    data[:, 1] = data[:, 3] + 0.2
    data[:, 2] = data[:, 3] - 0.2
    data[:, 4] = 1000 # Volume
    return TradingEnv(data=data, initial_balance=10000.0, window_size=20)

def test_adversarial_env_slippage(base_env):
    scenario = StressScenario(
        name="Slippage Test",
        description="Tests slippage injection",
        slippage_bps=100.0 # 1% slippage
    )
    adv_env = AdversarialTradingEnv(base_env, scenario)

    obs, info = adv_env.reset()
    action = 1 # Buy
    obs, reward, terminated, truncated, info = adv_env.step(action)

    assert adv_env.total_slippage > 0

def test_adversarial_env_delay(base_env):
    scenario = StressScenario(
        name="Delay Test",
        description="Tests execution delay",
        execution_delay_steps=5
    )
    adv_env = AdversarialTradingEnv(base_env, scenario)

    obs, _ = adv_env.reset()

    # Step 0: Action 1 (Buy) is queued
    _, _, _, _, info = adv_env.step(1)
    assert info["position"] == 0 # Should not have executed yet

    # Step 1-4: Action 1 still in queue
    for _ in range(4):
        _, _, _, _, info = adv_env.step(0)
        assert info["position"] == 0

    # Step 5: Action 1 should execute
    _, _, _, _, info = adv_env.step(0)
    assert info["position"] == 1

def test_adversarial_env_noise_and_ticks(base_env):
    scenario = StressScenario(
        name="Data Adversity",
        description="Tests noise and tick drop",
        price_noise_sigma=0.5,
        tick_drop_rate=0.2
    )
    original_len = len(base_env.data)
    adv_env = AdversarialTradingEnv(base_env, scenario)

    # Check if data was modified
    assert len(base_env.data) < original_len
    # Noise would have changed values

def test_adversarial_env_spread_widening(base_env):
    scenario = StressScenario(
        name="Spread Test",
        description="Tests spread widening",
        spread_multiplier=5.0
    )
    # Baseline run
    base_env.reset()
    _, reward_base, _, _, _ = base_env.step(1)

    # Stressed run
    base_env.reset()
    adv_env = AdversarialTradingEnv(base_env, scenario)
    _, reward_stressed, _, _, _ = adv_env.step(1)

    assert reward_stressed < reward_base

def test_stress_lab_report(base_env):
    model = MockModel()
    lab = StressLab(strategy_name="MockStrategy", model=model)

    scenario = StressScenario(
        name="Stress Test",
        description="Full stress test",
        slippage_bps=50.0,
        service_degradation=0.1
    )

    report = lab.run_scenario(base_env, scenario)

    assert report.strategy_name == "MockStrategy"
    assert report.scenario_name == "Stress Test"
    assert report.baseline_metrics.sharpe_ratio != 1.5 # Should be real calculated value
    assert isinstance(report.failure_points, list)
    assert isinstance(report.resilience_weaknesses, list)
