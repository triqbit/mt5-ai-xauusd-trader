import pytest
import numpy as np
from src.environment.gym_env import TradingEnv

@pytest.fixture
def dummy_data():
    # 200 bars, 5 features (OHLCV)
    return np.random.randn(200, 5)

def test_gym_env_indicators(dummy_data):
    env = TradingEnv(data=dummy_data, initial_balance=10000.0, window_size=60)
    # df should have SMA_20, SMA_50, RSI_14 added
    # Original 5 + 3 = 8 features
    assert env.data.shape[1] == 8
    assert "sma_20" in env.df.columns
    assert "rsi_14" in env.df.columns

def test_gym_env_reward_drawdown(dummy_data):
    env = TradingEnv(data=dummy_data, initial_balance=10000.0, window_size=60)
    env.reset()

    # Force a position and a loss to create drawdown
    env.position = 1.0
    env.entry_price = 100.0
    # Next price is lower
    env.data[env.current_step, 3] = 90.0

    _, reward, _, _, info = env.step(0) # Hold

    assert info["drawdown"] > 0
    # Reward should be penalized if drawdown > 0.05
    # peak=10000, equity = 10000 + (90-100) = 9990. Drawdown = 10/10000 = 0.001.
    # Not enough for 5% penalty yet.

    # Force 10% drawdown
    env.peak_equity = 10000.0
    env.equity = 9000.0
    # Trigger 10% drawdown in next step
    env.data[env.current_step, 3] = 90.0
    env.balance = 9000.0
    env.position = 0.0

    _, reward, _, _, info = env.step(0)
    assert info["drawdown"] >= 0.1
    assert reward < 0 # Penalized
