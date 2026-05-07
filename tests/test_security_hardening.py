import os
import stat
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from src.core.audit_log import AuditLogger
from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator
from src.core.log_config import SecretMaskingProcessor


def test_deep_redaction():
    processor = SecretMaskingProcessor()
    processor.secrets.add("SUPER_SECRET_123")

    data = {
        "msg": "Connected with SUPER_SECRET_123",
        "nested": {
            "token": "SUPER_SECRET_123",
            "safe": "data"
        },
        "list": ["SUPER_SECRET_123", "safe"],
        "password_field": "some_value"  # Should be redacted by key name
    }

    redacted = processor.redact_any(data)

    assert redacted["msg"] == "Connected with [MASKED]"
    assert redacted["nested"]["token"] == "[MASKED]"
    assert redacted["list"][0] == "[MASKED]"
    assert redacted["password_field"] == "[MASKED]"
    assert redacted["nested"]["safe"] == "data"


def test_audit_logger_redaction(tmp_path):
    db_file = tmp_path / "test_audit.db"
    db_url = f"sqlite:///{db_file}"

    # Reset singleton for testing to ensure it uses the test DB
    AuditLogger._instance = None
    AuditLogger._initialized = False

    # Setup masking processor with a secret
    from src.core.log_config import get_masking_processor
    processor = get_masking_processor()
    processor.secrets.add("API_KEY_HIDDEN")

    logger = AuditLogger(db_url=db_url)
    from src.core.database import Base
    Base.metadata.create_all(logger.engine)

    # Log something sensitive in metadata
    logger.log(
        actor="test",
        action="sensitive_action",
        metadata={"key": "API_KEY_HIDDEN", "nested": {"password": "secret_pass"}}
    )

    # Check the database
    from sqlalchemy import create_engine, select
    from src.core.audit_log import AuditEntry
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(select(AuditEntry.metadata_json)).fetchone()
        metadata = result[0]

        assert metadata["key"] == "[MASKED]"
        assert metadata["nested"]["password"] == "[MASKED]"


@pytest.mark.skipif(sys.platform == "win32", reason="Permission check only on Linux/Mac")
def test_config_validator_file_permissions(tmp_path, monkeypatch):
    # Create insecure file
    env_file = tmp_path / ".env.test"
    env_file.write_text("MT5_PASSWORD=test")
    os.chmod(env_file, 0o644)  # World readable

    # Mock config
    config = MagicMock(spec=TradingConfig)
    config.model_config = {"env_file": env_file}
    config.mt5_login = 12345
    config.mt5_server = "TestServer"
    config.mt5_password = SecretStr("test")
    config.database_url = SecretStr("sqlite:///test.db")
    config.telegram_token = SecretStr("")
    config.telegram_chat_id = ""
    config.metaapi_token = SecretStr("")
    config.metaapi_account_id = SecretStr("")
    config.mode = "demo"
    config.symbol = "XAUUSD"
    config.timeframe = "M5"
    config.model_path = Path("nonexistent")
    config.risk_per_trade = 0.01
    config.max_daily_loss = 0.05
    config.min_confidence = 0.6
    config.max_positions = 5
    config.max_leverage = 10
    config.max_position_size_pct = 0.1
    config.max_drawdown = 0.3
    config.model_drift_threshold = 0.3
    config.model_accuracy_floor = 0.5
    config.model_win_rate_floor = 0.45
    config.model_calibration_threshold = 0.25
    config.redis_url = ""
    config.log_level = "INFO"

    validator = ConfigValidator(config)

    # We need to mock unique_paths in _check_file_permissions or just let it find our file
    # _check_file_permissions uses resolve() and Path(".env") etc.
    # Let's monkeypatch Path.exists to return True for our specific test files

    result = validator.validate()

    # Check if FILE_PERMISSION warning is present
    permission_errors = [e for e in result.errors if e.field == "FILE_PERMISSION"]
    assert len(permission_errors) > 0
    assert "Insecure permissions" in permission_errors[0].message
