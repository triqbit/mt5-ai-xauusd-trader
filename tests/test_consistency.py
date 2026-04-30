import numpy as np
import pytest
from src.environment.gym_env import TradingEnv

def test_observation_consistency():
    n_features = 5
    window_size = 10
    data = np.random.randn(100, n_features).astype(np.float32)
    env = TradingEnv(data, window_size=window_size)

    # Manually calculate expected observation for the first step (current_step = window_size)
    current_step = window_size
    window = data[current_step - window_size:current_step]
    mean = window.mean(axis=0)
    std = window.std(axis=0, ddof=0)
    expected_normalized = (window - mean) / (std + 1e-8)

    obs, _ = env.reset()

    # Portfolio state [balance/initial, position]
    # initial reset: balance = initial_balance, position = 0
    expected_portfolio = np.array([1.0, 0.0], dtype=np.float32)
    expected_obs = np.concatenate([expected_normalized.ravel(), expected_portfolio])

    np.testing.assert_allclose(obs, expected_obs, atol=1e-6)

def test_observation_update():
    n_features = 5
    window_size = 10
    data = np.random.randn(100, n_features).astype(np.float32)
    env = TradingEnv(data, window_size=window_size)

    env.reset()
    # Step forward
    action = 0 # Hold
    obs, reward, terminated, truncated, info = env.step(action)

    current_step = window_size + 1
    window = data[current_step - window_size:current_step]
    mean = window.mean(axis=0)
    std = window.std(axis=0, ddof=0)
    expected_normalized = (window - mean) / (std + 1e-8)
    expected_portfolio = np.array([1.0, 0.0], dtype=np.float32)
    expected_obs = np.concatenate([expected_normalized.ravel(), expected_portfolio])

    np.testing.assert_allclose(obs, expected_obs, atol=1e-6)
