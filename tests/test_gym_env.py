"""
Tests for the custom Gymnasium trading environment.
"""
import pytest
import numpy as np
import logging
from src.environment.gym_env import TradingEnv

def test_trading_env_init():
    """Test environment initialization."""
    data = np.random.randn(100, 5)  # 100 steps, 5 features
    env = TradingEnv(data=data)
    assert env.data.shape == (100, 5)
    assert env.balance == 10000.0
    assert env.position == 0.0

def test_trading_env_reset():
    """Test environment reset."""
    data = np.random.randn(100, 5)
    env = TradingEnv(data=data)
    obs, info = env.reset()
    assert isinstance(obs, np.ndarray)
    assert isinstance(info, dict)
    assert env.current_step == env.window_size

def test_trading_env_step():
    """Test environment step."""
    data = np.random.randn(100, 5)
    env = TradingEnv(data=data)
    env.reset()
    obs, reward, terminated, truncated, info = env.step(1)  # Buy
    assert env.position == 1.0
    assert isinstance(reward, float)
    assert not terminated

def test_trading_env_render(caplog):
    """Test environment render logging."""
    data = np.random.randn(100, 5)
    env = TradingEnv(data=data)
    env.reset()
    with caplog.at_level(logging.INFO):
        env.render()
    assert "Step:" in caplog.text
    assert "Balance:" in caplog.text
