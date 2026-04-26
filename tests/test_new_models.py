import numpy as np
import pytest
from src.trading.trading_env import TradingEnv
from src.models.ppo_agent import PPOAgent
from src.models.lstm_model import LSTMModel
from src.models.dreamer_agent import DreamerAgent
from src.models.base import Signal

@pytest.fixture
def dummy_data():
    return np.random.randn(100, 10).astype(np.float32)

def test_trading_env(dummy_data):
    env = TradingEnv(dummy_data, window_size=10)
    obs, info = env.reset()
    assert obs.shape == (10 * 10 + 2,)

    action = 1 # Buy
    obs, reward, terminated, truncated, info = env.step(action)
    assert info["position"] == 1.0

    action = 2 # Sell
    obs, reward, terminated, truncated, info = env.step(action)
    assert info["position"] == 0.0

def test_ppo_agent(dummy_data):
    # Test PPO with env
    env = TradingEnv(dummy_data, window_size=10)
    agent = PPOAgent(env=env)
    features = np.random.randn(102).astype(np.float32) # window_size=10 * 10 features + 2
    signal = agent.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction in [-1, 0, 1]
    assert signal.confidence == 1.0

def test_lstm_model():
    model = LSTMModel(n_features=10)
    features = np.random.randn(10, 10).astype(np.float32)
    signal = model.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction in [-1, 0, 1]
    assert 0.0 <= signal.confidence <= 1.0

def test_dreamer_agent():
    agent = DreamerAgent()
    features = np.random.randn(102).astype(np.float32)
    signal = agent.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction == 0
    assert signal.confidence == 1.0
