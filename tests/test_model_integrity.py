import os
from unittest.mock import MagicMock, patch

import joblib
import pytest
from pydantic import SecretStr

from src.core.config import TradingConfig
from src.models.regime_detector import RegimeDetector
from src.utils.security import compute_hmac


@pytest.fixture
def signing_key():
    return "test_signing_key_12345"


@pytest.fixture
def mock_config(signing_key):
    config = MagicMock(spec=TradingConfig)
    config.model_signing_key = SecretStr(signing_key)
    config.mode = "demo"
    return config


def test_model_signing_on_save(tmp_path, mock_config, signing_key):
    """Verify that save_model creates a valid signature file."""
    model_path = tmp_path / "test_model.joblib"
    sig_path = tmp_path / "test_model.joblib.sig"

    detector = RegimeDetector()
    # Mock some state to save
    detector._gmm = "mock_gmm"

    with patch("src.core.config.get_config", return_value=mock_config):
        detector.save_model(str(model_path))

    assert model_path.exists()
    assert sig_path.exists()

    # Verify signature content
    expected_sig = compute_hmac(model_path, signing_key)
    assert sig_path.read_text().strip() == expected_sig


def test_model_loading_with_valid_signature(tmp_path, mock_config, signing_key):
    """Verify that a signed model loads correctly."""
    model_path = tmp_path / "test_model.joblib"

    detector = RegimeDetector()
    detector._gmm = "mock_gmm"

    with patch("src.core.config.get_config", return_value=mock_config):
        detector.save_model(str(model_path))
        # Ensure restrictive permissions for the load check
        os.chmod(model_path, 0o600)

        # New detector to load the model
        loader = RegimeDetector()

        # Mock Path.is_relative_to to allow loading from tmp_path
        with patch("src.models.regime_detector.Path.is_relative_to", return_value=True):
            loader.load_model(str(model_path))
            assert loader._gmm == "mock_gmm"


def test_model_loading_fails_without_signature(tmp_path, mock_config):
    """Verify that loading fails if the .sig file is missing."""
    model_path = tmp_path / "test_model.joblib"

    # Manually save without signing
    state = {"gmm": "mock_gmm"}
    joblib.dump(state, model_path)
    os.chmod(model_path, 0o600)

    loader = RegimeDetector()
    with patch("src.core.config.get_config", return_value=mock_config), patch(
        "src.models.regime_detector.Path.is_relative_to", return_value=True
    ):
        loader.load_model(str(model_path))
        assert loader._gmm is None


def test_model_loading_fails_with_invalid_signature(tmp_path, mock_config):
    """Verify that loading fails if the signature is tampered."""
    model_path = tmp_path / "test_model.joblib"
    sig_path = tmp_path / "test_model.joblib.sig"

    # Save normally
    state = {"gmm": "mock_gmm"}
    joblib.dump(state, model_path)
    os.chmod(model_path, 0o600)
    sig_path.write_text("invalid_signature")

    loader = RegimeDetector()
    with patch("src.core.config.get_config", return_value=mock_config), patch(
        "src.models.regime_detector.Path.is_relative_to", return_value=True
    ):
        loader.load_model(str(model_path))
        assert loader._gmm is None


def test_model_loading_fails_with_wrong_key(tmp_path, mock_config, signing_key):
    """Verify that loading fails if a different key was used for signing."""
    model_path = tmp_path / "test_model.joblib"

    # Sign with one key
    detector = RegimeDetector()
    detector._gmm = "mock_gmm"
    with patch("src.core.config.get_config", return_value=mock_config):
        detector.save_model(str(model_path))
    os.chmod(model_path, 0o600)

    # Try to load with a different key
    wrong_config = MagicMock(spec=TradingConfig)
    wrong_config.model_signing_key = SecretStr("wrong_key")

    loader = RegimeDetector()
    with patch("src.core.config.get_config", return_value=wrong_config), patch(
        "src.models.regime_detector.Path.is_relative_to", return_value=True
    ):
        loader.load_model(str(model_path))
        assert loader._gmm is None
