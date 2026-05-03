"""
Tests for system resilience and graceful degradation.
Specifically verifies that models handle missing dependencies (like torch) correctly.
"""

import sys
from unittest.mock import patch

import numpy as np
import pytest

from src.core.constants import SignalDirection
from src.models.ensemble import EnsembleModel
from src.models.lstm_model import LSTMModel
from src.models.transformer_model import TimeSeriesTransformer


def test_ensemble_graceful_degradation_no_torch():
    """Verify EnsembleModel handles missing torch gracefully."""
    # We mock torch as None to simulate environment without it
    with patch("src.models.ensemble.torch", None), \
         patch("src.models.ensemble.nn", None):

        ensemble = EnsembleModel(device="cpu")
        features = np.random.rand(1, 140)

        # Should return HOLD signal if no models are loaded
        signal = ensemble.predict(features)

        assert signal.direction == SignalDirection.HOLD
        assert signal.confidence == 0.0


def test_lstm_model_no_torch():
    """Verify LSTMModel handles missing torch gracefully."""
    with patch("src.models.lstm_model.torch", None), \
         patch("src.models.lstm_model.nn", None):

        model = LSTMModel(input_dim=140)
        features = np.random.rand(10, 140)

        signal = model.predict(features)

        assert signal.direction == SignalDirection.HOLD
        assert "missing" in signal.metadata.get("error", "").lower()


def test_transformer_model_initialization_failure():
    """Verify TimeSeriesTransformer cannot be used without torch/nn."""
    with patch("src.models.transformer_model.torch", None), \
         patch("src.models.transformer_model.nn", None):

        # In our implementation, TimeSeriesTransformer(nn.Module if nn else object)
        # But __init__ calls super().__init__() which might fail if nn is None
        # Actually nn.Module is a class, object is a class.

        with pytest.raises(Exception): # It calls super().__init__() which is object.__init__() but also tries to define layers
             TimeSeriesTransformer(input_dim=140)
