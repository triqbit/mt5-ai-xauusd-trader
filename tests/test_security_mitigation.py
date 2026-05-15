
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import joblib
import pytest

from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator
from src.models.regime_detector import MarketRegime, RegimeDetector


@pytest.fixture
def mock_config(tmp_path):
    config = MagicMock(spec=TradingConfig)
    # Ensure env_file is in the tmp_path
    config.model_config = {"env_file": tmp_path / ".env"}
    config.mode = "demo"
    return config

def test_regime_detector_load_path_validation(tmp_path):
    """Verify that RegimeDetector rejects models from untrusted paths."""
    detector = RegimeDetector()

    # Create a dummy model in an untrusted path
    untrusted_dir = tmp_path / "untrusted_dir"
    untrusted_dir.mkdir()
    untrusted_path = untrusted_dir / "malicious.joblib"

    state = {"gmm": "malicious_gmm", "cluster_to_regime": {}}
    joblib.dump(state, untrusted_path)

    # Ensure it has restrictive permissions so it doesn't fail on that check
    os.chmod(untrusted_path, 0o600)

    # Attempting to load from untrusted path should log error and not load
    # Mock is_relative_to to fail for both models and tmp
    with patch("src.models.regime_detector.Path.is_relative_to", return_value=False):
        detector.load_model(str(untrusted_path))
        assert detector._gmm is None

def test_regime_detector_load_path_bypass_attempt(tmp_path):
    """Verify that RegimeDetector rejects models that attempt to bypass with string prefixes."""
    detector = RegimeDetector()

    # Instead of creating in /app root, we'll use tmp_path to simulate a sibling directory
    base_dir = tmp_path / "base"
    models_dir = (base_dir / "models").resolve()
    fake_models_dir = (base_dir / "models_attacker").resolve()

    models_dir.mkdir(parents=True)
    fake_models_dir.mkdir(parents=True)

    untrusted_path = fake_models_dir / "payload.joblib"
    state = {"gmm": "malicious_gmm", "cluster_to_regime": {}}
    joblib.dump(state, untrusted_path)
    os.chmod(untrusted_path, 0o600)

    # Mock ROOT to point to base_dir
    with patch("src.core.config.ROOT", base_dir):
        # We mock is_relative_to to return True ONLY if it's truly relative (pathlib's own logic)
        # and we must ensure it doesn't match /tmp (which it will if we don't mock it, because it IS in /tmp)

        real_is_relative_to = Path.is_relative_to
        def mock_is_relative(self, other):
            # Block the /tmp check specifically for this test to ensure it hits the models check logic
            if str(other) in ("/tmp", "/var/tmp"):
                return False
            # Ensure we are checking against the expected models_dir
            return real_is_relative_to(self, other)

        with patch("src.models.regime_detector.Path.is_relative_to", mock_is_relative):
            detector.load_model(str(untrusted_path))
            assert detector._gmm is None

@pytest.mark.skipif(sys.platform == "win32", reason="Permission hardening only on Linux/Mac")
def test_config_validator_auto_hardening(tmp_path, mock_config):
    """Verify that ConfigValidator automatically fixes insecure permissions."""
    env_file = tmp_path / ".env"
    env_file.write_text("MT5_PASSWORD=secret")

    # Set insecure permissions (0o644 - world readable)
    os.chmod(env_file, 0o644)
    assert (os.stat(env_file).st_mode & 0o777) == 0o644

    # Mock sensitive_files to include our test file
    validator = ConfigValidator(mock_config)

    # Run validation
    validator._check_file_permissions()

    # Verify permissions are hardened to 0o600
    assert (os.stat(env_file).st_mode & 0o777) == 0o600

def test_regime_detector_load_from_trusted_path(tmp_path):
    """Verify that RegimeDetector accepts models from the trusted models/ directory."""
    from src.core.config import ROOT
    trusted_dir = ROOT / "models" / "trained"
    trusted_dir.mkdir(parents=True, exist_ok=True)

    trusted_path = trusted_dir / "test_model_mitigation.joblib"
    state = {"gmm": "mock_gmm", "cluster_to_regime": {0: MarketRegime.RANGING}}
    joblib.dump(state, trusted_path)

    # Ensure it has restrictive permissions
    os.chmod(trusted_path, 0o600)

    try:
        detector = RegimeDetector()
        detector.load_model(str(trusted_path))

        # If it loaded, _gmm should not be None (it will be "mock_gmm")
        assert detector._gmm == "mock_gmm"
    finally:
        if trusted_path.exists():
            trusted_path.unlink()

@pytest.mark.skipif(sys.platform == "win32", reason="Permission check only on Linux/Mac")
def test_regime_detector_insecure_permissions(tmp_path):
    """Verify that RegimeDetector rejects models with insecure permissions."""
    from src.core.config import ROOT
    trusted_dir = ROOT / "models" / "trained"
    trusted_dir.mkdir(parents=True, exist_ok=True)

    path = trusted_dir / "insecure_model.joblib"
    state = {"gmm": "mock_gmm", "cluster_to_regime": {}}
    joblib.dump(state, path)

    # Set insecure permissions (0o644)
    os.chmod(path, 0o644)

    try:
        detector = RegimeDetector()
        detector.load_model(str(path))
        assert detector._gmm is None
    finally:
        if path.exists():
            path.unlink()
