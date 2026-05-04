import numpy as np
import pandas as pd
from src.core.constants import SignalDirection
from src.models.base_model import Signal
from src.models.dreamer_agent import DreamerAgent
from src.models.lstm_model import LSTMModel
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

    # Test with mock environment
    df = pd.DataFrame(np.random.randn(100, 140))
    env = TradingEnv(df=df)
    agent_with_model = PPOAgent(env=env)
    assert agent_with_model.model is not None

    signal = agent_with_model.predict(obs)
    assert isinstance(signal, Signal)
    assert 0.0 <= signal.confidence <= 1.0
    assert "probabilities" in signal.metadata
    assert len(signal.metadata["probabilities"]) == 3

def test_lstm_model_stub():
    """Test LSTMModel initialization and prediction behavior."""
    # Test with attention
    agent_attn = LSTMModel(input_dim=10, use_attention=True)
    obs = np.zeros((20, 10))
    signal_attn = agent_attn.predict(obs)
    assert isinstance(signal_attn, Signal)
    if agent_attn.model is not None:
        from src.models.lstm_model import LSTMAttentionModel
        assert isinstance(agent_attn.model, LSTMAttentionModel)
        assert signal_attn.direction in [
            SignalDirection.BUY,
            SignalDirection.SELL,
            SignalDirection.HOLD,
        ]

    # Test without attention
    agent_simple = LSTMModel(input_dim=10, use_attention=False)
    signal_simple = agent_simple.predict(obs)
    assert isinstance(signal_simple, Signal)
    if agent_simple.model is not None:
        from src.models.lstm_model import LSTMPricePredictor
        assert isinstance(agent_simple.model, LSTMPricePredictor)
        assert signal_simple.direction in [
            SignalDirection.BUY,
            SignalDirection.SELL,
            SignalDirection.HOLD,
        ]

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
    agent.update_state(obs, 1, 0.0, False)
    agent.reset_state()
    assert agent.state is None

def test_trading_env_skeleton():
    """Test TradingEnv compliance with Gymnasium 0.29+ API."""
    df = np.random.randn(100, 10)
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
