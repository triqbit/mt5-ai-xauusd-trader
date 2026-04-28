"""Tests for src.environment.gym_env module."""
from __future__ import annotations

import numpy as np
import pytest

from src.environment.gym_env import TradingEnv


@pytest.fixture
def sample_data() -> np.ndarray:
    """Fixture for sample price data."""
    # Create 100 steps of OHLCV data
    data = np.random.randn(100, 5)
    # Ensure prices are positive and have some trend
    data = np.abs(data) + 100.0
    return data


def test_env_reset(sample_data: np.ndarray) -> None:
    """Test environment reset."""
    env = TradingEnv(sample_data, window_size=10)
    obs, info = env.reset()
    assert obs.shape == (10 * 5 + 2,)
    assert info == {}


def test_env_step_hold(sample_data: np.ndarray) -> None:
    """Test environment step with HOLD action."""
    env = TradingEnv(sample_data, window_size=10)
    env.reset()
    obs, reward, terminated, truncated, _info = env.step(0)
    assert obs.shape == (10 * 5 + 2,)
    assert isinstance(reward, (float, np.float32, np.float64))
    assert terminated is False
    assert truncated is False


def test_env_step_buy_sell(sample_data: np.ndarray) -> None:
    """Test environment step with BUY and SELL actions."""
    env = TradingEnv(sample_data, window_size=10)
    env.reset()
    # Step 1: BUY
    _obs, _reward, _terminated, _truncated, _info = env.step(1)
    assert env.position > 0
    # Step 2: SELL (close)
    _obs, _reward, _terminated, _truncated, _info = env.step(2)
    assert env.position == 0


def test_env_termination(sample_data: np.ndarray) -> None:
    """Test environment termination at the end of data."""
    env = TradingEnv(sample_data, window_size=10)
    env.reset()
    # Step until the end
    for _ in range(len(sample_data) - 11):
        _, _, terminated, _, _ = env.step(0)
    _, _, terminated, _, _ = env.step(0)
    assert terminated is True
