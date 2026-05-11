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

def test_ppo_agent_train_missing_env():
    """Test PPOAgent.train() raises RuntimeError when env is missing."""
    agent = PPOAgent()
    # Mocking model to be non-None but env to be None
    from unittest.mock import MagicMock
    agent.model = MagicMock()
    agent.model.get_env.return_value = None

    with pytest.raises(RuntimeError, match="No environment set"):
        agent.train(total_timesteps=100)

def test_agent_save_directory_creation(tmp_path):
    """Test that save() automatically creates parent directories for all agents."""
    save_dir = tmp_path / "deep" / "nested" / "path"

    # 1. PPOAgent
    ppo_agent = PPOAgent()
    from unittest.mock import MagicMock
    ppo_agent.model = MagicMock()
    ppo_path = save_dir / "ppo_model.zip"
    ppo_agent.save(ppo_path)
    assert save_dir.exists()
    ppo_agent.model.save.assert_called_once()

    # 2. LSTMModel
    lstm_agent = LSTMModel(input_dim=10)
    if lstm_agent.model is not None:
        lstm_path = save_dir / "lstm_model.pt"
        # We need to mock torch.save to avoid actual file write errors
        import torch
        from unittest.mock import patch
        with patch("torch.save") as mock_save:
            lstm_agent.save(lstm_path)
            assert save_dir.exists()
            mock_save.assert_called_once()

    # 3. DreamerAgent
    dreamer_agent = DreamerAgent()
    dreamer_path = save_dir / "dreamer_model.pt"
    dreamer_agent.save(dreamer_path)
    assert save_dir.exists()

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

def test_trading_env_hold_action():
    """Test the HOLD action (0) in TradingEnv."""
    df = np.zeros((100, 10))
    # Close price at index 3. Set a trend to see equity changes.
    df[:, 3] = np.arange(100) * 0.1
    import pandas as pd
    df_pd = pd.DataFrame(df)

    env = TradingEnv(df=df_pd, window_size=10)
    env.reset()

    # 1. Open Long
    env.step(1)
    assert env.position == 1

    # 2. Step with HOLD (action 0) should close the position in our implementation
    obs, reward, terminated, truncated, info = env.step(0)
    assert env.position == 0
    assert info["position"] == 0

def test_trading_env_render(caplog):
    """Test the render method in TradingEnv."""
    df = np.random.randn(100, 10)
    import pandas as pd
    df_pd = pd.DataFrame(df)

    env = TradingEnv(df=df_pd, window_size=10)
    env.reset()

    with caplog.at_level("INFO"):
        env.render()
        assert "Step:" in caplog.text
        assert "Balance:" in caplog.text

def test_trading_env_column_mapping():
    """Test TradingEnv with custom column mapping."""
    # Data with non-standard column order
    data = {
        "High": [1.1, 1.2, 1.3],
        "Low": [0.9, 1.0, 1.1],
        "Close": [1.0, 1.1, 1.2],
        "Open": [1.0, 1.1, 1.2],
        "Volume": [100, 200, 300]
    }
    import pandas as pd
    df = pd.DataFrame(data)

    # Map Close to index 2
    mapping = {"open": 3, "high": 0, "low": 1, "close": 2, "volume": 4}
    env = TradingEnv(df=df, window_size=1, column_mapping=mapping)
    env.reset()

    # Step should use index 2 for price
    # current_step starts at 1. step(1) increments to 2.
    # index 2 of Close is 1.2
    obs, reward, terminated, truncated, info = env.step(1)
    assert info["entry_price"] > 1.2  # Close (1.2) + spread + slippage
