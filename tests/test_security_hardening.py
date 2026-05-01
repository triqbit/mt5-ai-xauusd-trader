import os
import stat
import pytest
from pydantic import SecretStr
from src.core.config import TradingConfig
from src.core.trade_logger import TradeLogger


def test_config_secret_masking():
    """Verify that sensitive fields are masked in TradingConfig."""
    config = TradingConfig(
        mt5_password="secret_password",
        mt5_server="test_server",
        metaapi_token="secret_token",
        telegram_token="secret_tg",
        database_url="postgresql://user:pass@host:5432/db",
        redis_url="redis://:pass@host:6379/0",
    )

    config_str = str(config)
    assert "secret_password" not in config_str
    assert "secret_token" not in config_str
    assert "secret_tg" not in config_str
    assert "pass@host" not in config_str

    # Check they are SecretStr
    assert isinstance(config.mt5_password, SecretStr)
    assert isinstance(config.metaapi_token, SecretStr)
    assert isinstance(config.telegram_token, SecretStr)
    assert isinstance(config.database_url, SecretStr)
    assert isinstance(config.redis_url, SecretStr)


def test_db_permission_hardening(tmp_path):
    """Verify that TradeLogger sets 0o600 permissions on SQLite database."""
    db_file = tmp_path / "test_secure.db"
    db_url = f"sqlite:///{db_file}"

    # Initialise logger
    logger = TradeLogger(db_url=db_url)

    # Check permissions
    assert os.path.exists(db_file)
    mode = os.stat(db_file).st_mode
    # 0o600 means -rw-------
    assert stat.S_IMODE(mode) == 0o600


def test_secret_access_validation():
    """Verify that we can still access the actual values via get_secret_value()."""
    config = TradingConfig(
        mt5_password="secret_password",
        mt5_server="test_server",
        metaapi_token="secret_token",
        telegram_token="secret_tg",
        database_url="postgresql://user:pass@host:5432/db",
        redis_url="redis://:pass@host:6379/0",
    )

    assert config.mt5_password.get_secret_value() == "secret_password"
    assert config.metaapi_token.get_secret_value() == "secret_token"
    assert config.telegram_token.get_secret_value() == "secret_tg"
    assert config.database_url.get_secret_value() == "postgresql://user:pass@host:5432/db"
    assert config.redis_url.get_secret_value() == "redis://:pass@host:6379/0"
