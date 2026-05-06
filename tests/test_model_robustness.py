import numpy as np
import pytest
from src.core.constants import SignalDirection
from src.models.ppo_agent import PPOAgent
from src.models.lstm_model import LSTMModel
from src.models.dreamer_agent import DreamerAgent

def test_ppo_agent_nan_handling():
    # Use a dummy env to ensure model is initialized
    from src.trading.trading_env import TradingEnv
    import pandas as pd
    df = pd.DataFrame(np.random.randn(50, 4)) # 4 features
    env = TradingEnv(df=df)
    agent = PPOAgent(env=env)

    features = np.array([1.0, np.nan, 2.0])
    signal = agent.predict(features)
    assert signal.direction == SignalDirection.HOLD
    assert any(x in signal.metadata["error"] for x in ["NaN or Inf", "Model not loaded"])

def test_lstm_model_nan_handling():
    agent = LSTMModel(input_dim=5)
    features = np.array([[1.0, 2.0, 3.0, 4.0, np.inf]])
    signal = agent.predict(features)
    assert signal.direction == SignalDirection.HOLD
    assert any(x in signal.metadata["error"] for x in ["NaN or Inf", "Model not initialized"])

def test_dreamer_agent_nan_handling():
    agent = DreamerAgent()
    features = np.array([np.nan])
    signal = agent.predict(features)
    assert signal.direction == SignalDirection.HOLD
    assert "NaN or Inf" in signal.metadata["error"]
