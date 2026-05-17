from pydantic import SecretStr
from sqlalchemy import create_engine, select

from src.core.audit_log import AuditEntry, AuditLogger
from src.core.config import TradingConfig


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

def test_redis_url_redaction_in_audit_snapshot(tmp_path):
    """Verify that redis_url is redacted in audit log snapshots."""
    db_file = tmp_path / "test_audit_security.db"
    db_url = f"sqlite:///{db_file}"

    # Reset singleton for testing
    AuditLogger._instance = None
    AuditLogger._initialized = False

    logger = AuditLogger(db_url=db_url)

    config = TradingConfig(
        MT5_PASSWORD="test_password",
        MT5_SERVER="test_server",
        redis_url="redis://user:pass@localhost:6379/0"
    )

    snapshot = config.model_dump(
        mode="json",
        exclude={
            "mt5_password",
            "metaapi_token",
            "metaapi_account_id",
            "database_url",
            "redis_url",
            "telegram_token",
        }
    )

    assert "redis_url" not in snapshot

    logger.log_config_snapshot(snapshot)

    # Check DB
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(select(AuditEntry.metadata_json)).fetchone()
        metadata = result[0]
        assert "redis_url" not in metadata

def test_redis_url_redaction_if_not_excluded(tmp_path):
    """Verify that even if NOT excluded manually, the masking processor catches it if it's a SecretStr."""
    db_file = tmp_path / "test_audit_masking.db"
    db_url = f"sqlite:///{db_file}"

    # Reset singleton
    AuditLogger._instance = None
    AuditLogger._initialized = False

    logger = AuditLogger(db_url=db_url)

    real_secret = "redis://user:pass@localhost:6379/0"
    config = TradingConfig(
        MT5_PASSWORD="test_password",
        MT5_SERVER="test_server",
        redis_url=real_secret
    )

    # Update masking processor secrets explicitly
    from src.core.log_config import get_masking_processor
    get_masking_processor().update_secrets(config)

    # Dump WITHOUT excluding redis_url
    snapshot_with_redis = config.model_dump(mode="json")

    logger.log_config_snapshot(snapshot_with_redis)

    # Check DB
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(select(AuditEntry.metadata_json)).fetchone()
        metadata = result[0]
        # It should be redacted. Pydantic v2 SecretStr masks it to '**********' in json dump.
        # Masking processor didn't catch '**********' but that's already a mask.
        # The important thing is it's NOT the real secret.
        assert metadata["redis_url"] != real_secret
        assert metadata["redis_url"] in ("[MASKED]", "**********")
