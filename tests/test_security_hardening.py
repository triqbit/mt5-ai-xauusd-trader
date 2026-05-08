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
    config.model_path = MagicMock(spec=Path)
    config.model_path.exists.return_value = True
    config.model_path.is_file.return_value = True

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
    config.redis_url = SecretStr("redis://localhost:6379")
    config.log_level = "INFO"

    config.daily_loss_lvl1 = 0.02
    config.daily_loss_lvl2 = 0.03
    config.daily_loss_lvl3 = 0.04
    config.daily_loss_hard_stop = 0.06

    config.max_weekly_loss = 0.10
    config.max_monthly_loss = 0.15

    config.min_spread_pips = 0.5
    config.spread_alert_pips = 1.0
    config.spread_reduce_pips = 1.5
    config.spread_halt_pips = 2.0

    config.max_single_direction_pct = 0.30
    config.max_total_notional_pct = 1.00

    config.confirm_live_trading = ""

    validator = ConfigValidator(config)

    # Use a more targeted mock for os.stat that doesn't break Path.exists internals
    original_stat = os.stat
    def mock_stat(path, *args, **kwargs):
        if str(path).endswith(".env.test"):
            mock_res = MagicMock()
            mock_res.st_mode = stat.S_IFREG | 0o644
            return mock_res
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", mock_stat)

    result = validator.validate()

    # Check if FILE_PERMISSION warning is present
    permission_errors = [e for e in result.errors if e.field == "FILE_PERMISSION"]
    assert len(permission_errors) > 0
    assert "Insecure permissions" in permission_errors[0].message


# --- New Security Hardening Tests ---

def test_redis_url_masking(monkeypatch):
    """Verify that passwords in redis_url are masked in logs."""
    monkeypatch.setenv("MT5_PASSWORD", "mock_pass")
    monkeypatch.setenv("MT5_SERVER", "mock_server")

    config = TradingConfig(
        redis_url=SecretStr("redis://:super_secret_redis_pass@localhost:6379/0"),
        database_url=SecretStr("postgresql://user:db_pass@localhost:5432/db")
    )

    processor = SecretMaskingProcessor(config=config)

    # 1. Check if the password itself is in the secrets set
    assert "super_secret_redis_pass" in processor.secrets
    assert "db_pass" in processor.secrets

    # 2. Check redaction of strings
    event = {
        "msg": "Connecting to redis://:super_secret_redis_pass@localhost:6379/0",
        "db": "postgresql://user:db_pass@localhost:5432/db",
        "other": "some random text"
    }

    redacted = processor(None, "info", event)

    assert "super_secret_redis_pass" not in redacted["msg"]
    assert "[MASKED]" in redacted["msg"]
    assert "db_pass" not in redacted["db"]
    assert "[MASKED]" in redacted["db"]


def test_torch_load_security_audit():
    """
    Statically audit the codebase for insecure torch.load calls.
    Ensures weights_only=True is used everywhere.
    """
    import ast

    root = Path(__file__).parent.parent
    python_files = list(root.glob("src/**/*.py")) + [root / "main.py"]

    insecure_calls = []

    for py_file in python_files:
        if not py_file.exists():
            continue

        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "load" and isinstance(node.func.value, ast.Name) and node.func.value.id == "torch":
                        func_name = "torch.load"
                elif isinstance(node.func, ast.Name) and node.func.id == "load":
                    # This could be a direct import 'from torch import load'
                    # For simplicity, we check if it looks like a torch load
                    func_name = "load"

                if func_name in ["torch.load", "load"]:
                    # Check for weights_only=True
                    has_weights_only = any(
                        kw.arg == "weights_only" and
                        (isinstance(kw.value, ast.Constant) and kw.value.value is True or
                         isinstance(kw.value, (ast.NameConstant, ast.Constant)) and kw.value.value is True)
                        for kw in node.keywords
                    )
                    if not has_weights_only:
                        insecure_calls.append(f"{py_file}:{node.lineno}")

    assert not insecure_calls, f"Found insecure torch.load calls (missing weights_only=True): {insecure_calls}"


def test_redis_url_type(monkeypatch):
    """Verify that redis_url is a SecretStr in the config."""
    monkeypatch.setenv("MT5_PASSWORD", "mock_pass")
    monkeypatch.setenv("MT5_SERVER", "mock_server")
    config = TradingConfig()
    assert isinstance(config.redis_url, SecretStr)
