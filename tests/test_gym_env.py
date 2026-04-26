
import numpy as np
import pytest
from src.environment.gym_env import TradingEnv

def test_trading_env_obs_shape():
    n_features = 5
    window_size = 10
    data = np.random.rand(100, n_features).astype(np.float32)
    env = TradingEnv(data, window_size=window_size)

    obs, _ = env.reset()
    expected_shape = (window_size * n_features + 2,)
    assert obs.shape == expected_shape
    assert obs.dtype == np.float32

def test_trading_env_normalization():
    # Constant data to make it easy to check mean/std
    n_features = 2
    window_size = 3
    data = np.array([
        [1.0, 10.0],
        [2.0, 20.0],
        [3.0, 30.0],
        [4.0, 40.0]
    ], dtype=np.float32)

    env = TradingEnv(data, window_size=window_size)
    env.current_step = 3 # window is [0, 1, 2]

    obs = env._get_observation()

    window = data[0:3]
    mean = window.mean(axis=0)
    std = window.std(axis=0)
    expected_normalized = (window - mean) / (std + 1e-8)

    # Obs is [normalized_window.flatten(), balance/initial, position]
    # balance/initial = 1.0, position = 0.0 at start
    expected_obs = np.concatenate([expected_normalized.flatten(), [1.0, 0.0]]).astype(np.float32)

    np.testing.assert_allclose(obs, expected_obs, atol=1e-6)

def test_trading_env_step():
    data = np.random.rand(100, 4).astype(np.float32)
    env = TradingEnv(data, window_size=10)
    env.reset()

    # Test Buy
    obs, reward, terminated, truncated, info = env.step(1)
    assert env.position == 1.0
    assert env.entry_price > 0

    # Test Sell
    obs, reward, terminated, truncated, info = env.step(2)
    assert env.position == 0.0
    assert env.entry_price == 0.0
