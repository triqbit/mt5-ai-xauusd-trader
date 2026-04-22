import numpy as np
import pytest
from src.models import BaseModel, Signal, DreamerAgent

def test_imports():
    """Verify that base models can be imported."""
    assert BaseModel is not None
    assert Signal is not None
    assert DreamerAgent is not None

def test_dreamer_stub():
    """Verify DreamerAgent stub."""
    agent = DreamerAgent()
    features = np.zeros((60, 140))
    signal = agent.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction == 0
    assert signal.confidence == 0.0

def test_lstm_stub():
    """Verify LSTMModel stub if torch is available."""
    pytest.importorskip("torch")
    from src.models import LSTMModel
    if LSTMModel is None:
        pytest.skip("LSTMModel could not be imported")

    model = LSTMModel(input_dim=10)
    features = np.zeros((60, 10))
    signal = model.predict(features)
    assert isinstance(signal, Signal)
    assert signal.direction in [-1, 0, 1]
    assert signal.confidence >= 0.0

def test_ppo_stub():
    """Verify PPOAgent stub if SB3 is available."""
    pytest.importorskip("stable_baselines3")
    from src.models import PPOAgent
    from src.trading.trading_env import XAUUSDTradingEnv
    if PPOAgent is None:
        pytest.skip("PPOAgent could not be imported")

    data = np.zeros((100, 10))
    env = XAUUSDTradingEnv(data=data)
    agent = PPOAgent(env=env)
    features = np.zeros((1, 602)) # Depends on env observation space
    # Just check initialization and interface
    assert agent is not None

def test_env_init():
    """Verify XAUUSDTradingEnv initialization."""
    data = np.zeros((100, 10))
    from src.trading.trading_env import XAUUSDTradingEnv
    env = XAUUSDTradingEnv(data=data)
    if hasattr(env, 'observation_space'):
        assert env.observation_space is not None
        assert env.action_space is not None
