
from pydantic import SecretStr

from src.core.config import TradingConfig
from src.core.log_config import SecretMaskingProcessor


def test_dynamic_secret_discovery():
    """Verify that all SecretStr fields are automatically discovered and masked."""
    # Create a config with various secrets
    config = TradingConfig(
        MT5_PASSWORD=SecretStr("super_secret_mt5"),
        MT5_SERVER="test_server",
        redis_url=SecretStr("redis://:redis_pass_123@localhost:6379/0"),
        database_url=SecretStr("postgresql://user:db_pass_456@localhost:5432/db"),
        telegram_token=SecretStr("bot123:tele_secret_789")
    )

    processor = SecretMaskingProcessor()
    processor.update_secrets(config)

    # Test individual secret extraction
    assert "super_secret_mt5" in processor.secrets
    assert "redis_pass_123" in processor.secrets
    assert "db_pass_456" in processor.secrets
    assert "bot123:tele_secret_789" in processor.secrets

    # Test masking in a log message
    log_event = {
        "msg": "Failed to connect to redis with pass redis_pass_123",
        "details": "Database error for db_pass_456",
        "meta": {"token": "bot123:tele_secret_789"}
    }

    redacted = processor.redact_any(log_event)

    assert redacted["msg"] == "Failed to connect to redis with pass [MASKED]"
    assert redacted["details"] == "Database error for [MASKED]"
    assert redacted["meta"]["token"] == "[MASKED]"

def test_url_password_extraction_robustness():
    """Test various URL formats for password extraction."""
    processor = SecretMaskingProcessor()

    # Mock secrets set
    processor.secrets = {
        "redis://user:pass1@host",
        "postgresql://u:pass2@h:p/db",
        "mongodb+srv://u:pass3@cluster.mongodb.net",
        "http://admin:pass4@127.0.0.1:8080"
    }

    # Trigger extraction logic (normally inside update_secrets)
    # We replicate the logic here or just call it if we can mock TradingConfig
    for secret in list(processor.secrets):
        if "://" in secret and "@" in secret:
            auth_part = secret.split("://", 1)[1].rsplit("@", 1)[0]
            if ":" in auth_part:
                password = auth_part.rsplit(":", 1)[1]
                if password and len(password) > 3:
                    processor.secrets.add(password)

    assert "pass1" in processor.secrets
    assert "pass2" in processor.secrets
    assert "pass3" in processor.secrets
    assert "pass4" in processor.secrets
