
import numpy as np
import pytest
from src.environment.gym_env import TradingEnv

def test_observation_consistency():
    """Verify that the optimized observation matches the naive calculation."""
    data = np.random.randn(100, 5).astype(np.float32)
    env = TradingEnv(data, window_size=10)
    obs, _ = env.reset()

    # Manually calculate naive observation
    window = data[env.current_step - env.window_size : env.current_step]
    expected_normalized = (window - window.mean(axis=0)) / (window.std(axis=0, ddof=0) + 1e-8)
    expected_portfolio = np.array([env.balance / env.initial_balance, env.position], dtype=np.float32)
    expected_obs = np.concatenate([expected_normalized.flatten(), expected_portfolio])

    np.testing.assert_allclose(obs, expected_obs, atol=1e-6)

    # Step and check again
    obs, _, _, _, _ = env.step(1)
    window = data[env.current_step - env.window_size : env.current_step]
    expected_normalized = (window - window.mean(axis=0)) / (window.std(axis=0, ddof=0) + 1e-8)
    expected_portfolio = np.array([env.balance / env.initial_balance, env.position], dtype=np.float32)
    expected_obs = np.concatenate([expected_normalized.flatten(), expected_portfolio])

    np.testing.assert_allclose(obs, expected_obs, atol=1e-6)
