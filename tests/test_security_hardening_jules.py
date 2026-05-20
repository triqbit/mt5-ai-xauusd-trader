"""
Verification tests for security hardening implemented by Jules02.
tests/test_security_hardening_jules.py
"""

import os
import stat
import sys

import pytest
from pydantic import SecretStr
from sqlalchemy import text

from src.core.config import TradingConfig
from src.core.database import get_engine
from src.core.log_config import SecretMaskingProcessor


@pytest.mark.skipif(sys.platform == "win32", reason="Permission checks only on Linux/Mac")
def test_sqlite_directory_permissions_hardening(tmp_path):
    """Verify that get_engine enforces 0o700 on parent directories."""
    secure_dir = tmp_path / "secure_data"
    db_file = secure_dir / "trades.db"
    db_url = f"sqlite:///{db_file}"

    get_engine.cache_clear()
    get_engine(db_url)

    assert secure_dir.exists()
    mode = stat.S_IMODE(secure_dir.stat().st_mode)
    assert mode == 0o700, f"Expected 0o700 for directory, got {oct(mode)}"

    # Test hardening existing directory
    os.chmod(secure_dir, 0o755)
    get_engine.cache_clear()
    get_engine(db_url)
    mode = stat.S_IMODE(secure_dir.stat().st_mode)
    assert mode == 0o700, f"Expected hardening to 0o700, got {oct(mode)}"

def test_sqlite_secure_delete_pragma(tmp_path):
    """Verify that secure_delete is enabled for SQLite connections."""
    db_file = tmp_path / "test_pragma.db"
    db_url = f"sqlite:///{db_file}"
    get_engine.cache_clear()
    engine = get_engine(db_url)

    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA secure_delete")).scalar()
        # 1 means ON, 0 means OFF
        assert result == 1 or result == "1" or result is True

def test_short_secret_masking():
    """Verify that short secrets (length < 4) are correctly masked."""
    # Create a config with a short password
    config = TradingConfig(
        MT5_PASSWORD=SecretStr("abc"),
        MT5_SERVER="Broker-Demo",
        MT5_LOGIN=12345
    )

    processor = SecretMaskingProcessor(config=config)

    # Test direct masking of the secret value
    assert processor.redact_any("abc") == "[MASKED]"

    # Test masking within a larger string
    log_msg = "Attempting login with password abc for account 12345"
    redacted = processor.redact_any(log_msg)
    assert "abc" not in redacted
    assert "[MASKED]" in redacted

    # Verify that it doesn't over-mask common small words unless they are secrets
    assert processor.redact_any("test msg") == "test msg"

def test_config_validator_directory_hardening(tmp_path):
    """Verify that ConfigValidator hardens operational directories."""
    from src.core.config_validator import ConfigValidator

    # Create mock directories
    data_dir = tmp_path / "data"
    data_dir.mkdir(mode=0o755)

    # Create config
    config = TradingConfig(
        MT5_PASSWORD=SecretStr("password"),
        MT5_SERVER="Server",
        MT5_LOGIN=1
    )

    validator = ConfigValidator(config)

    # Test the _harden_path helper
    validator._harden_path(data_dir, 0o700, stat.S_IRWXG | stat.S_IRWXO)

    mode = stat.S_IMODE(data_dir.stat().st_mode)
    assert mode == 0o700

if __name__ == "__main__":
    # Manual run support
    pytest.main([__file__])
