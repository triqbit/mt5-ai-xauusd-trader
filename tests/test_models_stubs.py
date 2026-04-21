
import numpy as np
import pandas as pd
import pytest
from src.models import PPOAgent, LSTMModel, DreamerAgent, Signal
from src.trading.trading_env import XAUUSDTradingEnv

def test_signal_dataclass():
    sig = Signal(direction=1, confidence=0.8, metadata={"test": True})
    assert sig.direction == 1
    assert sig.confidence == 0.8
    assert sig.metadata["test"] is True

def test_trading_env_skeleton():
    df = pd.DataFrame(np.random.randn(100, 5), columns=['open', 'high', 'low', 'close', 'volume'])
    env = XAUUSDTradingEnv(df, window_size=10)
    obs, info = env.reset()
    assert obs.shape == (10 * 5 + 2,)

    action = 1
    next_obs, reward, terminated, truncated, info = env.step(action)
    assert next_obs.shape == (10 * 5 + 2,)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)

def test_ppo_agent_predict():
    # Mock environment for PPO
    df = pd.DataFrame(np.random.randn(200, 5), columns=['open', 'high', 'low', 'close', 'volume'])
    env = XAUUSDTradingEnv(df, window_size=10)
    agent = PPOAgent(env=env)

    obs, _ = env.reset()
    signal = agent.predict(obs)

    assert isinstance(signal, Signal)
    assert signal.direction in [-1, 0, 1]
    assert 0.0 <= signal.confidence <= 1.0

def test_lstm_model_predict():
    model = LSTMModel(input_size=5, hidden_size=16)
    features = np.random.randn(10, 5) # (seq_len, n_features)
    signal = model.predict(features)

    assert isinstance(signal, Signal)
    assert signal.direction in [-1, 0, 1]
    assert 0.0 <= signal.confidence <= 1.0

def test_dreamer_agent_predict():
    agent = DreamerAgent()
    features = np.random.randn(52) # Flattened obs
    signal = agent.predict(features)

    assert isinstance(signal, Signal)
    assert signal.direction == 0
    assert signal.confidence == 0.0
