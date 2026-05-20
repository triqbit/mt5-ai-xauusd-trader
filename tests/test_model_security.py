"""
Security tests for model loading and signature verification.
tests/test_model_security.py
"""

import os

import joblib
import pandas as pd
import pytest
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from src.core.config import get_config
from src.models.regime_detector import RegimeDetector


@pytest.fixture
def mock_data():
    """Generate mock OHLCV data for testing."""
    dates = pd.date_range(start="2023-01-01", periods=200, freq="5min")
    df = pd.DataFrame(
        {
            "open": [1900.0] * 200,
            "high": [1905.0] * 200,
            "low": [1895.0] * 200,
            "close": [1900.0] * 200,
            "tick_volume": [100] * 200,
        },
        index=dates,
    )
    return df


@pytest.fixture
def temp_model_path(tmp_path):
    """Create a temporary path for model files."""
    return tmp_path / "test_regime_model.joblib"


def test_signed_model_loading_success(mock_data, temp_model_path):
    """Test that a correctly signed model loads successfully."""
    detector = RegimeDetector()
    detector.fit(mock_data)

    # Save model (should generate .sig)
    detector.save_model(str(temp_model_path))

    assert temp_model_path.exists()
    assert temp_model_path.with_suffix(".joblib.sig").exists()

    # Apply secure permissions to avoid security violation error on Linux
    if os.name != "nt":
        os.chmod(temp_model_path, 0o600)

    # Load model
    new_detector = RegimeDetector()
    new_detector.load_model(str(temp_model_path))

    assert new_detector._gmm is not None
    assert isinstance(new_detector._gmm, GaussianMixture)


def test_unsigned_model_loading_failure(mock_data, temp_model_path):
    """Test that an unsigned model fails to load."""
    # Manually save a model without signature
    state = {
        "gmm": GaussianMixture(n_components=3).fit([[0], [1], [2]]),
        "scaler": StandardScaler(),
        "cluster_to_regime": {},
    }
    joblib.dump(state, temp_model_path)

    assert temp_model_path.exists()
    assert not temp_model_path.with_suffix(".joblib.sig").exists()

    # Load model (should fail)
    new_detector = RegimeDetector()
    new_detector.load_model(str(temp_model_path))

    assert new_detector._gmm is None


def test_tampered_model_loading_failure(mock_data, temp_model_path):
    """Test that a tampered model fails to load."""
    detector = RegimeDetector()
    detector.fit(mock_data)
    detector.save_model(str(temp_model_path))

    # Tamper with the model file
    with open(temp_model_path, "ab") as f:
        f.write(b"tamper")

    # Load model (should fail due to signature mismatch)
    new_detector = RegimeDetector()
    new_detector.load_model(str(temp_model_path))

    assert new_detector._gmm is None


def test_invalid_signature_loading_failure(mock_data, temp_model_path):
    """Test that a model with an invalid signature fails to load."""
    detector = RegimeDetector()
    detector.fit(mock_data)
    detector.save_model(str(temp_model_path))

    # Tamper with the signature file
    sig_path = temp_model_path.with_suffix(".joblib.sig")
    with open(sig_path, "w") as f:
        f.write("invalid_signature")

    # Load model (should fail)
    new_detector = RegimeDetector()
    new_detector.load_model(str(temp_model_path))

    assert new_detector._gmm is None


def test_wrong_key_loading_failure(mock_data, temp_model_path, monkeypatch):
    """Test that a model signed with a different key fails to load."""
    # Sign with key A
    detector = RegimeDetector()
    detector.fit(mock_data)

    # Mock config to use key A
    monkeypatch.setenv("MODEL_SIGNING_KEY", "KEY_A_SECURE_STRING_123456789")
    get_config.cache_clear()
    detector.save_model(str(temp_model_path))

    # Change key to B
    monkeypatch.setenv("MODEL_SIGNING_KEY", "KEY_B_SECURE_STRING_987654321")
    get_config.cache_clear()

    # Load model (should fail)
    new_detector = RegimeDetector()
    new_detector.load_model(str(temp_model_path))

    assert new_detector._gmm is None
