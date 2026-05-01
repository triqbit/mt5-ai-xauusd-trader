"""
Integration test for ensemble adaptivity.
"""
import pytest
import numpy as np
from src.models.ensemble import EnsembleModel

def test_ensemble_weight_adaptivity():
    ensemble = EnsembleModel(device="cpu")
    # Simulate ppo being good, lstm being bad
    for _ in range(60):
        ensemble.record_return("ppo", 0.05)
        ensemble.record_return("lstm", -0.05)
        ensemble.record_return("dreamer", 0.01)

    # Check that PPO has highest weight
    assert ensemble.weights["ppo"] > ensemble.weights["lstm"]
    assert ensemble.weights["ppo"] > ensemble.weights["dreamer"]

    # Simulate ppo becoming bad, lstm becoming good
    for _ in range(60):
        ensemble.record_return("ppo", -0.1)
        ensemble.record_return("lstm", 0.1)

    assert ensemble.weights["lstm"] > ensemble.weights["ppo"]
