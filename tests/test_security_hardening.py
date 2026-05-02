"""
Security Hardening Verification Tests for MT5 AI/ML Trader.
"""
import os
from pathlib import Path
import pytest
from pydantic import SecretStr
from src.core.config import TradingConfig, get_config
from src.core.trade_logger import TradeLogger
from src.core.config_validator import ConfigValidator

def test_config_secrets_are_secret_str():
    """Verify sensitive fields use SecretStr and don't leak in string representation."""
    os.environ["MT5_LOGIN"] = "12345"
    os.environ["MT5_PASSWORD"] = "sensitive_mt5_pass"
    os.environ["MT5_SERVER"] = "sensitive_mt5_server"
    os.environ["TELEGRAM_TOKEN"] = "sensitive_tg_token"
    os.environ["METAAPI_TOKEN"] = "sensitive_meta_token"
    os.environ["DATABASE_URL"] = "postgresql://user:pass@host/db"
    os.environ["REDIS_URL"] = "redis://:pass@host"

    # Reset cache to ensure fresh load from env
    get_config.cache_clear()
    cfg = get_config()

    # Check types
    assert isinstance(cfg.mt5_password, SecretStr)
    assert isinstance(cfg.telegram_token, SecretStr)
    assert isinstance(cfg.metaapi_token, SecretStr)
    assert isinstance(cfg.database_url, SecretStr)
    assert isinstance(cfg.redis_url, SecretStr)

    # Check string representation (should not contain the secret)
    cfg_str = str(cfg)
    cfg_repr = repr(cfg)

    for secret in [
        "sensitive_mt5_pass",
        "sensitive_tg_token",
        "sensitive_meta_token",
        "postgresql://user:pass@host/db",
        "redis://:pass@host"
    ]:
        assert secret not in cfg_str
        assert secret not in cfg_repr
        # Pydantic SecretStr typically shows as '**********'
        assert "**********" in cfg_str or "SecretStr" in cfg_str

def test_sqlite_db_permissions(tmp_path):
    """Verify that SQLite database files are created with restrictive 0o600 permissions."""
    db_file = tmp_path / "test_secure.db"
    db_url = f"sqlite:///{db_file}"

    # Initialize logger, which should create the file/set permissions
    logger = TradeLogger(db_url=db_url)

    # Check if file exists
    assert db_file.exists()

    # Check permissions
    mode = db_file.stat().st_mode
    # 0o600 means -rw-------
    # In octal, we check the last 3 digits
    assert oct(mode & 0o777) == "0o600"

def test_config_validator_with_secret_str():
    """Verify ConfigValidator correctly handles SecretStr fields."""
    os.environ["MT5_LOGIN"] = "12345"
    os.environ["MT5_PASSWORD"] = "valid_password"
    os.environ["MT5_SERVER"] = "valid_server"
    os.environ["DATABASE_URL"] = "postgresql://trader:password@localhost:5432/mt5_trades"

    get_config.cache_clear()
    cfg = get_config()
    validator = ConfigValidator(cfg)
    result = validator.validate()

    # It should detect the default placeholder DB URL even as a SecretStr
    db_errors = [e for e in result.errors if e.field == "DATABASE_URL"]
    assert len(db_errors) > 0
    assert "placeholder" in db_errors[0].message

    # Change it to something else
    os.environ["DATABASE_URL"] = "postgresql://real_user:real_pass@prod_host/db"
    get_config.cache_clear()
    cfg = get_config()
    validator = ConfigValidator(cfg)
    result = validator.validate()

    db_errors = [e for e in result.errors if e.field == "DATABASE_URL"]
    assert len(db_errors) == 0
