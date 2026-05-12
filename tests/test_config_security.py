import pytest
from pydantic import SecretStr
from src.core.config import TradingConfig
from src.core.audit_log import AuditLogger
from sqlalchemy import create_engine, select
from src.core.audit_log import AuditEntry
from pathlib import Path

def test_redis_url_is_secret():
    """Verify that redis_url is a SecretStr in TradingConfig."""
    config = TradingConfig(
        MT5_PASSWORD="test_password",
        MT5_SERVER="test_server",
        redis_url="redis://user:pass@localhost:6379/0"
    )

    assert isinstance(config.redis_url, SecretStr)
    assert str(config.redis_url) == "**********"
    assert config.redis_url.get_secret_value() == "redis://user:pass@localhost:6379/0"

def test_get_sanitized_dump():
    """Verify that get_sanitized_dump() redacts all SecretStr fields."""
    config = TradingConfig(
        MT5_PASSWORD="test_password",
        MT5_SERVER="test_server",
        database_url="postgresql://user:pass@localhost:5432/db",
        redis_url="redis://user:pass@localhost:6379/0",
        telegram_token="123:ABC",
        metaapi_token="meta_token",
        metaapi_account_id="meta_id"
    )

    dump = config.get_sanitized_dump()

    # These are SecretStr/SecretBytes and should be redacted by Pydantic's json mode to '**********'
    # or excluded if we use exclude. get_sanitized_dump uses exclude.
    assert "mt5_password" not in dump
    assert "database_url" not in dump
    assert "redis_url" not in dump
    assert "telegram_token" not in dump
    assert "metaapi_token" not in dump
    assert "metaapi_account_id" not in dump

    # Non-secret fields should be present
    assert dump["mt5_server"] == "test_server"
    assert dump["symbol"] == "XAUUSD"

def test_audit_log_uses_sanitized_dump(tmp_path):
    """Verify that AuditLogger uses the centralized redaction."""
    db_file = tmp_path / "test_audit_sanitized.db"
    db_url = f"sqlite:///{db_file}"

    # Reset singleton
    AuditLogger._instance = None
    AuditLogger._initialized = False

    logger = AuditLogger(db_url=db_url)

    config = TradingConfig(
        MT5_PASSWORD="test_password",
        MT5_SERVER="test_server",
        redis_url="redis://user:pass@localhost:6379/0"
    )

    # Use the dump in audit log
    logger.log_config_snapshot(config.get_sanitized_dump())

    # Check DB
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(select(AuditEntry.metadata_json)).fetchone()
        metadata = result[0]
        assert "mt5_password" not in metadata
        assert "redis_url" not in metadata
        assert metadata["mt5_server"] == "test_server"
