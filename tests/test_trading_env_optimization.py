
import numpy as np
import pandas as pd

from src.trading.trading_env import TradingEnv


def test_trading_env_optimized_observation():
    """Verify that the optimized observation retrieval is correct and matches the original data."""
    n_rows = 100
    n_features = 10
    window_size = 20

    # Create random data
    data = np.random.randn(n_rows, n_features).astype(np.float32)
    df = pd.DataFrame(data, columns=[f"feat_{i}" for i in range(n_features)])

    env = TradingEnv(df=df, window_size=window_size)

    # 1. Check if _data was correctly initialized
    assert env._data is not None
    assert env._data.shape == (n_rows, n_features)
    assert env._data.dtype == np.float32
    np.testing.assert_array_almost_equal(env._data, data)

    # 2. Check initial observation
    obs, _info = env.reset()
    assert obs.shape == (window_size, n_features)
    np.testing.assert_array_almost_equal(obs, data[0:window_size])

    # 3. Step forward and check observation
    obs, _reward, _terminated, _truncated, _info = env.step(1)
    # After 1 step, current_step = window_size + 1
    # observation window should be [1 : window_size + 1]
    np.testing.assert_array_almost_equal(obs, data[1:window_size+1])

def test_trading_env_none_data():
    """Verify handling of None DataFrame."""
    env = TradingEnv(df=None, window_size=20)
    assert env._data is None
    obs, _ = env.reset()
    assert np.all(obs == 0)
    assert obs.shape == (20, 140) # Default features

def test_trading_env_empty_data():
    """Verify handling of empty DataFrame."""
    df = pd.DataFrame()
    # If df is empty but has no columns, df.shape[1] is 0
    env = TradingEnv(df=df, window_size=20)
    assert env.observation_space.shape == (20, 0)

def test_observation_dtype():
    """Verify that observation always returns float32."""
    n_rows = 50
    n_features = 5
    data = np.random.randn(n_rows, n_features).astype(np.float64) # Input as float64
    df = pd.DataFrame(data)

    env = TradingEnv(df=df, window_size=10)
    assert env._data.dtype == np.float32
    obs, _ = env.reset()
    assert obs.dtype == np.float32
