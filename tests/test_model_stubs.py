
import numpy as np
import pytest
import torch
from src.models import PPOAgent, LSTMModel, DreamerAgent, Signal
from src.trading.trading_env import TradingEnv

def test_signal_dataclass():
    sig = Signal(direction=1, confidence=0.8)
    assert sig.direction == 1
    assert sig.confidence == 0.8

def test_lstm_model_predict():
    input_dim = 64
    model = LSTMModel(input_dim=input_dim)
    features = np.random.randn(10, input_dim).astype(np.float32)
    signal = model.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction in [1, -1, 0]
    assert 0.0 <= signal.confidence <= 1.0

def test_dreamer_agent_predict():
    agent = DreamerAgent()
    features = np.random.randn(100).astype(np.float32)
    signal = agent.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction == 0
    assert signal.confidence == 0.0

def test_ppo_agent_predict_no_model():
    # Should return Hold if no model/env is provided
    agent = PPOAgent()
    features = np.random.randn(100).astype(np.float32)
    signal = agent.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction == 0
    assert signal.confidence == 0.0

def test_trading_env_skeleton():
    env = TradingEnv()
    obs, info = env.reset()
    assert obs.shape == (100,)
    assert isinstance(info, dict)

    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    assert obs.shape == (100,)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)
