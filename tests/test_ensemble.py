"""Tests for EnsembleModel module."""
import pytest
import numpy as np
import torch
from src.models.ensemble import EnsembleModel

def test_ensemble_initialization():
    model = EnsembleModel(device="cpu")
    assert model.device.type == "cpu"
    assert len(model.weights) == 3

def test_ensemble_predict_no_models():
    model = EnsembleModel(device="cpu")
    obs = np.random.randn(10)
    direction, confidence, per_algo = model.predict(obs)
    assert direction == 0
    assert confidence == 0.0
    assert per_algo == {}

def test_ensemble_rebalance():
    model = EnsembleModel(device="cpu")
    # Mock performance
    model._performance["ppo"] = [0.01] * 60
    model._performance["lstm"] = [-0.01] * 60
    model._performance["dreamer"] = [0.0] * 60

    model._rebalance_weights()
    assert model.weights["ppo"] > model.weights["lstm"]
    assert np.isclose(sum(model.weights.values()), 1.0)
