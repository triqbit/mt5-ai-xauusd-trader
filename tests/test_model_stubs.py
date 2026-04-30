"""
Unit tests for production model stubs and their common interface.
"""

import pytest
import numpy as np
import torch
from src.models import Signal, BaseModel, PPOAgent, LSTMModel, DreamerAgent
from src.trading.trading_env import XAUUSDTradingEnv

def test_signal_dataclass():
    """Verify Signal dataclass initialization."""
    sig = Signal(direction=1, confidence=0.85, metadata={"test": True})
    assert sig.direction == 1
    assert sig.confidence == 0.85
    assert sig.metadata["test"] is True

def test_ppo_agent_interface():
    """Verify PPOAgent implements BaseModel and returns Signal."""
    env = XAUUSDTradingEnv()
    agent = PPOAgent(env=env)

    # Mock observation
    obs = env.observation_space.sample()

    # Predict
    # PPOAgent might not have SB3 installed in CI, handle gracefully
    try:
        sig = agent.predict(obs)
        assert isinstance(sig, Signal)
        assert sig.direction in [-1, 0, 1]
        assert 0.0 <= sig.confidence <= 1.0
    except ImportError:
        pytest.skip("stable-baselines3 not installed")

def test_lstm_model_interface():
    """Verify LSTMModel implements BaseModel and returns Signal."""
    model = LSTMModel(input_size=10, hidden_size=32)

    # Mock sequence: (batch, seq_len, features)
    features = np.random.randn(1, 24, 10).astype(np.float32)

    sig = model.predict(features)
    assert isinstance(sig, Signal)
    assert sig.direction in [-1, 0, 1]
    assert 0.0 <= sig.confidence <= 1.0

def test_dreamer_agent_interface():
    """Verify DreamerAgent implements BaseModel and returns Signal."""
    agent = DreamerAgent()

    # Mock features
    features = np.zeros((64,))

    sig = agent.predict(features)
    assert isinstance(sig, Signal)
    assert sig.direction == 0 # Current placeholder behavior
    assert sig.confidence == 0.0

def test_base_model_inheritance():
    """Ensure all models inherit from BaseModel."""
    assert issubclass(PPOAgent, BaseModel)
    assert issubclass(LSTMModel, BaseModel)
    assert issubclass(DreamerAgent, BaseModel)
