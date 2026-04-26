import pytest
import numpy as np
from src.models.performance_tracker import PerformanceTracker
from src.core.config import TradingConfig
from unittest.mock import MagicMock

def test_accuracy_drift(monkeypatch):
    monkeypatch.delenv("RISK_PER_TRADE", raising=False)
    config = TradingConfig(mt5_password="pass", mt5_server="serv")
    config.drift_window_short = 5
    config.drift_window_long = 10
    config.drift_accuracy_threshold = 0.2

    tracker = PerformanceTracker(config)

    # Fill history with wins (high baseline)
    for i in range(10):
        tracker.record_prediction(i, np.array([0.8, 0.1, 0.1]), 0.8, 1, {"algo1": 1.0}, {"algo1": 0})
        tracker.record_outcome(i, True)

    # Add losses (drift)
    for i in range(10, 15):
        tracker.record_prediction(i, np.array([0.8, 0.1, 0.1]), 0.8, 1, {"algo1": 1.0}, {"algo1": 0})
        tracker.record_outcome(i, False)

    drifts = tracker.check_drift()
    assert "accuracy_degradation" in drifts
    assert drifts["accuracy_degradation"]["recent"] == 0.0

def test_confidence_drift(monkeypatch):
    monkeypatch.delenv("RISK_PER_TRADE", raising=False)
    config = TradingConfig(mt5_password="pass", mt5_server="serv")
    config.drift_window_short = 5
    config.drift_confidence_threshold = 0.1

    tracker = PerformanceTracker(config)

    # Confidence is 0.9 but win rate is 0.5 -> drift
    for i in range(5):
        tracker.record_prediction(i, np.array([0.9, 0.05, 0.05]), 0.9, 1, {"algo1": 1.0}, {"algo1": 0})
        tracker.record_outcome(i, i % 2 == 0)

    drifts = tracker.check_drift()
    assert "confidence_drift" in drifts

def test_weight_imbalance(monkeypatch):
    monkeypatch.delenv("RISK_PER_TRADE", raising=False)
    config = TradingConfig(mt5_password="pass", mt5_server="serv")
    tracker = PerformanceTracker(config)

    # Skewed weights
    tracker.record_prediction(1, np.array([0.6, 0.2, 0.2]), 0.6, 1, {"ppo": 0.98, "lstm": 0.01, "dreamer": 0.01}, {"ppo": 0})
    tracker.record_outcome(1, True)

    drifts = tracker.check_drift()
    assert "weight_imbalance" in drifts
