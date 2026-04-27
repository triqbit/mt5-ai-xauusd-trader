"""
Tests for new model stubs and the Gymnasium environment.
"""

import numpy as np
import pytest
import torch
from src.models.base import Signal, BaseModel
from src.models.ppo_agent import PPOAgent
from src.models.lstm_model import LSTMModel
from src.models.dreamer_agent import DreamerAgent
from src.trading.trading_env import TradingEnv

@pytest.fixture
def dummy_data():
    return np.random.rand(1000, 10)  # 1000 steps, 10 features

@pytest.fixture
def env(dummy_data):
    return TradingEnv(dummy_data, window_size=60)

def test_signal_dataclass():
    sig = Signal(direction=1, confidence=0.8)
    assert sig.direction == 1
    assert sig.confidence == 0.8

def test_trading_env_flow(env):
    obs, _ = env.reset()
    assert obs.shape == (60 * 10 + 2,)

    # Take a step
    next_obs, reward, terminated, truncated, info = env.step(1)  # Buy
    assert next_obs.shape == (60 * 10 + 2,)
    assert "balance" in info
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert info["position"] == 1.0

def test_ppo_agent_interface(env):
    agent = PPOAgent(env=env)
    obs, _ = env.reset()
    signal = agent.predict(obs)
    assert isinstance(signal, Signal)
    assert signal.direction in [-1, 0, 1]
    assert 0.0 <= signal.confidence <= 1.0

def test_lstm_model_interface():
    model = LSTMModel(input_dim=10)
    features = np.random.rand(60, 10)
    signal = model.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction in [-1, 0, 1]
    assert 0.0 <= signal.confidence <= 1.0

def test_dreamer_agent_interface():
    agent = DreamerAgent()
    features = np.random.rand(60 * 10 + 2)
    signal = agent.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction == 0
    assert signal.confidence == 0.0

def test_base_model_inheritance():
    assert issubclass(PPOAgent, BaseModel)
    assert issubclass(LSTMModel, BaseModel)
    assert issubclass(DreamerAgent, BaseModel)
