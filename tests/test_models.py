
import pytest
import numpy as np
import torch
from src.models.ppo_agent import PPOAgent
from src.models.lstm_model import LSTMModel
from src.models.dreamer_agent import DreamerAgent
from src.models.base_model import Signal
from src.trading.trading_env import XAUUSDTradingEnv

@pytest.fixture
def dummy_data():
    return np.random.randn(100, 5).astype(np.float32)

def test_trading_env(dummy_data):
    env = XAUUSDTradingEnv(dummy_data, window_size=10)
    obs, info = env.reset()
    assert obs.shape == (10 * 5,)

    next_obs, reward, terminated, truncated, info = env.step(1)
    assert next_obs.shape == (10 * 5,)
    assert isinstance(reward, float)

def test_ppo_agent_predict():
    agent = PPOAgent() # No env, no model
    signal = agent.predict(np.random.randn(50))
    assert isinstance(signal, Signal)
    assert signal.direction == 0
    assert signal.confidence == 0.0

def test_lstm_model_predict():
    model = LSTMModel(input_size=5)
    signal = model.predict(np.random.randn(10, 5).astype(np.float32))
    assert isinstance(signal, Signal)
    assert signal.direction in [1, -1, 0]
    assert 0.0 <= signal.confidence <= 1.0

def test_dreamer_agent_predict():
    agent = DreamerAgent()
    signal = agent.predict(np.random.randn(50))
    assert isinstance(signal, Signal)
    assert signal.direction == 0
    assert signal.confidence == 0.0
