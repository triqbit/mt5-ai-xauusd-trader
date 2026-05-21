import os
import stat
import sys
from unittest.mock import MagicMock

import pytest

from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator


@pytest.mark.skipif(sys.platform == "win32", reason="Permission hardening only on Linux/Mac")
def test_file_permission_hardening(tmp_path):
    """Verify that ConfigValidator hardens file permissions."""
    env_file = tmp_path / ".env"
    env_file.write_text("TEST=SECRET")
    os.chmod(env_file, 0o644)  # World readable

    config = MagicMock(spec=TradingConfig)
    config.model_config = {"env_file": env_file}
    config.database_url = MagicMock()
    config.database_url.get_secret_value.return_value = "sqlite:///test.db"
    config.model_signing_key = MagicMock()
    config.model_signing_key.get_secret_value.return_value = "secret"

    validator = ConfigValidator(config)
    validator._check_file_permissions()

    # Should be 0o600
    mode = os.stat(env_file).st_mode
    assert stat.S_IMODE(mode) == 0o600


@pytest.mark.skipif(sys.platform == "win32", reason="Permission hardening only on Linux/Mac")
def test_directory_permission_hardening(tmp_path):
    """Verify that ConfigValidator hardens directory permissions."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    os.chmod(data_dir, 0o755)  # World readable

    config = MagicMock(spec=TradingConfig)

    validator = ConfigValidator(config)
    validator._harden_path(data_dir, 0o700, stat.S_IRWXG | stat.S_IRWXO)

    mode = os.stat(data_dir).st_mode
    assert stat.S_IMODE(mode) == 0o700
