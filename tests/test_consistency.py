import numpy as np
import pytest
from src.environment.gym_env import TradingEnv

def test_observation_consistency():
    # Use fixed seed for reproducibility
    np.random.seed(42)
    data = np.random.randn(100, 5).astype(np.float32)
    env = TradingEnv(data, window_size=10)

    # Step through a bit
    for _ in range(5):
        env.step(0)

    obs = env._get_observation()

    # Manually calculate expected observation using old logic
    window = env.data[env.current_step - env.window_size : env.current_step]
    expected_obs_window = (window - window.mean(axis=0)) / (window.std(axis=0) + 1e-8)
    expected_portfolio = np.array([env.balance / env.initial_balance, env.position], dtype=np.float32)
    expected_obs = np.concatenate([expected_obs_window.flatten(), expected_portfolio]).astype(np.float32)

    # Check shape
    assert obs.shape == expected_obs.shape

    # Check values with tolerance due to potential float32 precision differences
    # especially when moving from numpy mean/std to pandas rolling or pre-calculated
    np.testing.assert_allclose(obs, expected_obs, rtol=1e-5, atol=1e-6)

if __name__ == "__main__":
    test_observation_consistency()
    print("Consistency test passed!")
