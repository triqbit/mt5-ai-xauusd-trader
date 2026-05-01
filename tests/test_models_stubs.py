
import pytest
import numpy as np
import torch
from unittest.mock import MagicMock, patch
from src.models.ppo_agent import PPOAgent
from src.models.lstm_model import LSTMModel
from src.models.dreamer_agent import DreamerAgent
from src.models.base import Signal
from src.trading.trading_env import TradingEnv
from src.models.ensemble import EnsembleModel, LSTMAttentionModel
from src.models.dynamic_ensemble import DynamicEnsemble
from src.models.regime_detector import MarketRegime

def test_trading_env_skeleton():
    data = np.random.rand(100, 10)
    env = TradingEnv(data=data, window_size=10)
    obs, info = env.reset()
    assert obs.shape == (10, 10)

    action = env.action_space.sample()
    next_obs, reward, terminated, truncated, info = env.step(action)
    assert next_obs.shape == (10, 10)
    assert isinstance(reward, float)
    env.render()

def test_ppo_agent_predict():
    pytest.importorskip("stable_baselines3")
    data = np.random.rand(100, 10)
    env = TradingEnv(data=data, window_size=10)
    agent = PPOAgent(env=env)

    obs, _ = env.reset()
    # SB3 expect (batch, ...) or just obs. My PPOAgent handles it.
    signal = agent.predict(obs)

    assert isinstance(signal, Signal)
    assert signal.direction in [-1, 0, 1]
    assert 0.0 <= signal.confidence <= 1.0

    # Test evaluation
    results = agent.evaluate(n_eval_episodes=1)
    assert "mean_reward" in results

def test_lstm_model_predict():
    pytest.importorskip("torch")
    n_features = 10
    model = LSTMModel(n_features=n_features)

    # Mock input: (seq_len, n_features)
    features = np.random.rand(20, n_features)
    signal = model.predict(features)

    assert isinstance(signal, Signal)
    assert signal.direction in [-1, 0, 1]
    assert 0.0 <= signal.confidence <= 1.0

def test_dreamer_agent_predict():
    agent = DreamerAgent()
    features = np.random.rand(20, 10)
    signal = agent.predict(features)

    assert isinstance(signal, Signal)
    assert signal.direction == 0
    assert signal.confidence == 0.0

    agent.update_context(features, 0, 0.0)

def test_dynamic_ensemble_basic():
    models = ["ppo", "lstm", "dreamer"]
    de = DynamicEnsemble(model_names=models)
    weights = de.get_weights()
    assert len(weights) == 3
    assert sum(weights.values()) == pytest.approx(1.0)

    metrics = {
        "ppo": {"accuracy": 0.8, "calibration_error": 0.1, "drift_score": 0.1},
        "lstm": {"accuracy": 0.6, "calibration_error": 0.2, "drift_score": 0.2},
        "dreamer": {"accuracy": 0.4, "calibration_error": 0.3, "drift_score": 0.3}
    }

    new_weights = de.update_weights(metrics, regime=MarketRegime.TRENDING)
    assert new_weights["ppo"] > weights["ppo"]
    assert new_weights["dreamer"] < weights["dreamer"]
    assert sum(new_weights.values()) == pytest.approx(1.0)

def test_ensemble_model_predict_mocked():
    pytest.importorskip("torch")
    # Mock PPO to avoid needing the full SB3 for this specific test if it's slow
    with patch("stable_baselines3.PPO") as mock_ppo_class:
        mock_ppo = MagicMock()
        mock_ppo.predict.return_value = (0, None) # Hold

        ensemble = EnsembleModel(device="cpu")
        ensemble._ppo_model = mock_ppo

        ensemble.lstm_model = MagicMock()
        # Mock LSTM output: [Hold, Buy, Sell] logits -> [0, 10, 0] makes Buy most likely
        ensemble.lstm_model.return_value = torch.tensor([[0.0, 10.0, 0.0]])

        obs = np.random.rand(10)
        seq = torch.rand(1, 10, 140)

        direction, confidence, votes = ensemble.predict(obs, seq=seq)

        assert direction in [-1, 0, 1]
        assert "ppo" in votes
        assert "lstm" in votes

def test_ensemble_weight_adaptation():
    ensemble = EnsembleModel(device="cpu")
    initial_weights = ensemble.weights.copy()

    # Record some fake returns
    for _ in range(60):
        ensemble.record_return("ppo", 0.01)
        ensemble.record_return("lstm", -0.01)

    assert ensemble.weights != initial_weights
    assert ensemble.weights["ppo"] > ensemble.weights["lstm"]
