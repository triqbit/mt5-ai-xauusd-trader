import os
import stat
import sys
from pathlib import Path
import pytest
from pydantic import SecretStr

from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator
from src.core.log_config import SecretMaskingProcessor

def test_secret_masking_short_secrets():
    """Verify that short secrets are now masked."""
    class MockConfig:
        model_fields = {"api_key": None}
        api_key = SecretStr("abc")

    processor = SecretMaskingProcessor()
    processor.update_secrets(MockConfig())

    assert "abc" in processor.secrets
    assert processor.redact_any("Your key is abc") == "Your key is [MASKED]"

def test_secret_masking_nested_structures():
    """Verify masking in various data structures."""
    class MockConfig:
        model_fields = {"password": None}
        password = SecretStr("topsecret")

    processor = SecretMaskingProcessor()
    processor.update_secrets(MockConfig())

    data = {
        "msg": "Connected with topsecret",
        "nested": {"key": "topsecret"},
        "list": ["topsecret", "other"],
        "mixed": [{"secret": "topsecret"}, "topsecret"]
    }

    redacted = processor.redact_any(data)
    assert redacted["msg"] == "Connected with [MASKED]"
    assert redacted["nested"]["key"] == "[MASKED]"
    assert redacted["list"][0] == "[MASKED]"
    assert redacted["mixed"][0]["secret"] == "[MASKED]"
    assert redacted["mixed"][1] == "[MASKED]"

@pytest.mark.skipif(sys.platform == "win32", reason="File permissions behavior differs on Windows")
def test_config_validator_file_hardening(tmp_path):
    """Verify that ConfigValidator hardens SQLite file permissions."""
    db_file = tmp_path / "test_hardened.db"
    db_file.touch()
    # Make it insecure: 0o666
    os.chmod(db_file, 0o666)

    # Create a config pointing to this db
    config = TradingConfig(
        MT5_PASSWORD="fake",
        MT5_SERVER="fake",
        database_url=f"sqlite:///{db_file}"
    )

    validator = ConfigValidator(config)
    result = validator.validate()

    # Check if hardening message is in errors (as a non-critical warning/info)
    hardening_errors = [e for e in result.errors if e.field == "FILE_PERMISSION" and "Hardened" in e.message]
    assert len(hardening_errors) >= 1

    # Verify file mode is now 0o600
    current_mode = stat.S_IMODE(os.stat(db_file).st_mode)
    assert current_mode == 0o600

@pytest.mark.skipif(sys.platform == "win32", reason="File permissions behavior differs on Windows")
def test_config_validator_fallback_hardening(tmp_path, monkeypatch):
    """Verify that ConfigValidator hardens default database files if they exist."""
    # Change current working directory to tmp_path so we can test "trades.db" fallback
    monkeypatch.chdir(tmp_path)

    trades_db = Path("trades.db")
    trades_db.touch()
    os.chmod(trades_db, 0o644)

    config = TradingConfig(
        MT5_PASSWORD="fake",
        MT5_SERVER="fake"
    )

    validator = ConfigValidator(config)
    validator.validate()

    current_mode = stat.S_IMODE(os.stat(trades_db).st_mode)
    assert current_mode == 0o600
