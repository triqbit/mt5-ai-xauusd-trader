
import numpy as np
import pytest
from src.environment.gym_env import TradingEnv

def test_trading_env_observation_shape():
    n_features = 5
    window_size = 10
    data = np.random.rand(100, n_features).astype(np.float32)
    env = TradingEnv(data, window_size=window_size)

    obs, _ = env.reset()
    assert obs.shape == (window_size * n_features + 2,)

def test_trading_env_step():
    n_features = 5
    window_size = 10
    data = np.random.rand(100, n_features).astype(np.float32)
    env = TradingEnv(data, window_size=window_size)

    env.reset()
    obs, reward, terminated, truncated, info = env.step(1) # Buy
    assert obs.shape == (window_size * n_features + 2,)
    assert env.position == 1.0

def test_trading_env_reset():
    n_features = 5
    window_size = 10
    data = np.random.rand(100, n_features).astype(np.float32)
    env = TradingEnv(data, window_size=window_size)

    env.reset()
    env.step(1)
    env.reset()
    assert env.position == 0.0
    assert env.current_step == window_size

def test_trading_env_normalization_consistency():
    n_features = 2
    window_size = 5
    # Constant data for easy check
    data = np.array([
        [1.0, 10.0],
        [2.0, 20.0],
        [3.0, 30.0],
        [4.0, 40.0],
        [5.0, 50.0],
        [6.0, 60.0]
    ]).astype(np.float32)

    env = TradingEnv(data, window_size=window_size)
    obs, _ = env.reset()

    # window is first 5 rows
    window = data[0:5]
    mean = window.mean(axis=0)
    std = window.std(axis=0)
    expected_obs_part = ((window - mean) / (std + 1e-8)).flatten()

    np.testing.assert_allclose(obs[:-2], expected_obs_part, atol=1e-5)
