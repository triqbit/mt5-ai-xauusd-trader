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

    # Test NaN handling
    features = np.array([1.0, np.nan, 2.0])
    signal = agent.predict(features)
    assert signal.direction == SignalDirection.HOLD
    assert "NaN or Inf" in signal.metadata["error"]

    # Test Inf handling
    features_inf = np.array([1.0, np.inf, 2.0])
    signal_inf = agent.predict(features_inf)
    assert signal_inf.direction == SignalDirection.HOLD
    assert "NaN or Inf" in signal_inf.metadata["error"]

def test_lstm_model_nan_handling():
    agent = LSTMModel(input_dim=5)

    # Test Inf handling
    features = np.array([[1.0, 2.0, 3.0, 4.0, np.inf]])
    signal = agent.predict(features)
    assert signal.direction == SignalDirection.HOLD
    assert "NaN or Inf" in signal.metadata["error"]

    # Test NaN handling
    features_nan = np.array([[1.0, 2.0, np.nan, 4.0, 5.0]])
    signal_nan = agent.predict(features_nan)
    assert signal_nan.direction == SignalDirection.HOLD
    assert "NaN or Inf" in signal_nan.metadata["error"]

def test_dreamer_agent_nan_handling():
    agent = DreamerAgent()

    # Test NaN
    features = np.array([np.nan])
    signal = agent.predict(features)
    assert signal.direction == SignalDirection.HOLD
    assert "NaN or Inf" in signal.metadata["error"]

    # Test Inf
    features_inf = np.array([np.inf])
    signal_inf = agent.predict(features_inf)
    assert signal_inf.direction == SignalDirection.HOLD
    assert "NaN or Inf" in signal_inf.metadata["error"]
