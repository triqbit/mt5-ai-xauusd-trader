
import numpy as np
import pytest
try:
    import gymnasium as gym
except ImportError:
    gym = None

from src.environment.gym_env import TradingEnv

pytestmark = pytest.mark.skipif(gym is None, reason="gymnasium not installed")

def test_trading_env_init():
    data = np.random.randn(100, 5).astype(np.float32)
    env = TradingEnv(data, window_size=10)
    assert env.data.shape == (100, 5)
    assert env.window_size == 10
    assert env.observation_space.shape == (10 * 5 + 2,)

def test_trading_env_reset():
    data = np.random.randn(100, 5).astype(np.float32)
    env = TradingEnv(data, window_size=10)
    obs, info = env.reset()
    assert obs.shape == (10 * 5 + 2,)
    assert env.current_step == 10
    assert env.balance == 10000.0
    assert env.position == 0.0

def test_trading_env_step():
    data = np.ones((100, 5)).astype(np.float32)
    # Set different prices to see PnL
    data[:, 3] = np.arange(100) # Close price
    env = TradingEnv(data, window_size=10, commission=0.0)
    env.reset()

    # Step with Buy action (1)
    obs, reward, terminated, truncated, info = env.step(1)
    assert env.position == 1.0
    assert env.entry_price == 10.0 # Price at step 10

    # Step with Hold (0)
    obs, reward, terminated, truncated, info = env.step(0)
    assert env.position == 1.0
    # Reward should include unrealized PnL: (11 - 10) / 10000 = 0.0001
    assert pytest.approx(reward) == 0.0001

    # Step with Sell (2)
    obs, reward, terminated, truncated, info = env.step(2)
    assert env.position == 0.0
    # PnL: 12 - 10 = 2.0. Reward: 2.0 / 10000 * 100 + unrealized(0.0) = 0.02
    # Wait, the code says:
    # reward = pnl / self.initial_balance * 100
    # if self.position == 1: ... reward += unrealized ...
    # After selling, position is 0, so unrealized is not added.
    assert pytest.approx(reward) == 0.02
    assert env.balance == 10002.0

def test_observation_normalization():
    data = np.random.randn(100, 5).astype(np.float32)
    env = TradingEnv(data, window_size=10)
    obs, _ = env.reset()

    # Check if window part is normalized (mean close to 0, std close to 1)
    window_obs = obs[:-2].reshape(10, 5)
    assert np.allclose(window_obs.mean(axis=0), 0, atol=1e-5)
    assert np.allclose(window_obs.std(axis=0), 1, atol=1e-1) # std might be slightly off due to 1e-8
