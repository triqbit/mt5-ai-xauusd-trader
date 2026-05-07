import numpy as np
import pytest
from pathlib import Path
from src.core.constants import SignalDirection
from src.models.base_model import Signal
from src.models.dreamer_agent import DreamerAgent
from src.models.lstm_model import LSTMModel, LSTMAttentionModel, LSTMPricePredictor
from src.models.ppo_agent import PPOAgent
from src.trading.trading_env import TradingEnv

def test_ppo_agent_stub():
    """Test PPOAgent initialization and prediction behavior."""
    # Test initialization without env
    agent = PPOAgent()
    assert agent.model is None

    # Test predict when model is None
    obs = np.zeros((20, 140))
    signal = agent.predict(obs)
    assert isinstance(signal, Signal)
    assert signal.direction == SignalDirection.HOLD
    assert signal.confidence == 0.0
    assert "error" in signal.metadata

def test_lstm_model_stub():
    """Test LSTMModel initialization and prediction behavior."""
    agent = LSTMModel(input_dim=10)
    # Even if torch is missing, it should handle gracefully (returning HOLD)
    obs = np.zeros((20, 10))
    signal = agent.predict(obs)
    assert isinstance(signal, Signal)
    if agent.model is not None:
        assert isinstance(agent.model, LSTMPricePredictor)
        assert signal.direction in [
            SignalDirection.BUY,
            SignalDirection.SELL,
            SignalDirection.HOLD,
        ]
    else:
        assert signal.direction == SignalDirection.HOLD
        assert "error" in signal.metadata

def test_lstm_model_attention():
    """Test LSTMModel with attention architecture."""
    agent = LSTMModel(input_dim=10, use_attention=True)
    if agent.model is not None:
        assert isinstance(agent.model, LSTMAttentionModel)
        obs = np.zeros((20, 10))
        signal = agent.predict(obs)
        assert isinstance(signal, Signal)
    else:
        pytest.skip("PyTorch not available")

def test_dreamer_agent_stub():
    """Test DreamerAgent initialization and placeholder behavior."""
    agent = DreamerAgent()
    obs = np.zeros((20, 140))
    signal = agent.predict(obs)
    assert isinstance(signal, Signal)
    assert signal.direction == SignalDirection.HOLD
    assert signal.confidence == 0.0
    assert signal.metadata["status"] == "placeholder"

    # Test state management methods
    agent.observe(obs, 1, 0.0, False)
    agent.reset_state()
    assert agent.state is None

def test_dreamer_agent_save(tmp_path):
    """Test DreamerAgent save method."""
    agent = DreamerAgent()
    save_path = tmp_path / "dreamer.pt"
    agent.save(save_path)
    # Since it's a placeholder, it doesn't actually write a file,
    # but it shouldn't crash and should log something.

def test_trading_env_skeleton():
    """Test TradingEnv compliance with Gymnasium 0.29+ API."""
    df = np.random.randn(100, 10)
    import pandas as pd
    df_pd = pd.DataFrame(df)

    env = TradingEnv(df=df_pd, window_size=10)
    obs, info = env.reset()
    assert obs.shape == (10, 10)
    assert isinstance(info, dict)

    action = 1  # BUY
    obs, reward, terminated, truncated, info = env.step(action)
    assert obs.shape == (10, 10)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert "action" in info
