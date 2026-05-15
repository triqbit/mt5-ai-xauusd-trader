import os
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
        "nested": {"token": "SUPER_SECRET_123", "safe": "data"},
        "list": ["SUPER_SECRET_123", "safe"],
        "password_field": "some_value",  # Should be redacted by key name
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
        metadata={"key": "API_KEY_HIDDEN", "nested": {"password": "secret_pass"}},
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


def test_audit_logger_details_redaction(tmp_path):
    db_file = tmp_path / "test_audit_details.db"
    db_url = f"sqlite:///{db_file}"

    # Reset singleton for testing
    AuditLogger._instance = None
    AuditLogger._initialized = False

    from src.core.log_config import get_masking_processor

    processor = get_masking_processor()
    processor.secrets.add("SENSITIVE_DETAIL_123")

    logger = AuditLogger(db_url=db_url)

    # Log something sensitive in the narrative details
    logger.log(
        actor="test",
        action="detail_action",
        details="User accessed SENSITIVE_DETAIL_123 in a narrative",
    )

    # Check the database
    from sqlalchemy import create_engine, select

    from src.core.audit_log import AuditEntry

    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(select(AuditEntry.details)).fetchone()
        details_masked = result[0]
        assert "SENSITIVE_DETAIL_123" not in details_masked
        assert "[MASKED]" in details_masked


def test_standard_logging_masking():
    import logging

    from src.core.log_config import get_masking_processor

    processor = get_masking_processor()
    processor.secrets.add("LOG_SECRET_456")

    root_logger = logging.getLogger()
    # Remove existing filters to avoid duplicates if test runs multiple times
    for f in root_logger.filters[:]:
        root_logger.removeFilter(f)

    root_logger.addFilter(processor)

    # Standard logging call
    logging.warning("Standard log with secret: %s", "LOG_SECRET_456")

    # Capture output if necessary, but here we check the record itself if we used a mock handler
    # Or just check if the message was modified in a custom handler
    class TestHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []

        def emit(self, record):
            self.records.append(record)

    handler = TestHandler()
    root_logger.addHandler(handler)

    logging.error("Another secret: LOG_SECRET_456")

    found = False
    for rec in handler.records:
        if "Another secret" in str(rec.msg):
            assert "LOG_SECRET_456" not in str(rec.msg)
            assert "[MASKED]" in str(rec.msg)
            found = True

    assert found


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
    config.max_slippage_pips = 0.5
    config.execution_latency_threshold = 1.0
    config.daily_win_cap = 0.05
    config.max_losing_streak = 3
    config.max_winning_streak = 5
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
    config.daily_loss_lvl1 = 0.01
    config.daily_loss_lvl2 = 0.02
    config.daily_loss_lvl3 = 0.03
    config.daily_loss_hard_stop = 0.07
    config.max_weekly_loss = 0.1
    config.max_monthly_loss = 0.2
    config.min_spread_pips = 1.0
    config.spread_alert_pips = 2.0
    config.spread_reduce_pips = 3.0
    config.spread_halt_pips = 5.0
    config.max_single_direction_pct = 0.2
    config.max_total_notional_pct = 0.5
    config.max_trades_per_day = 20
    config.min_lot_size = 0.01
    config.confirm_live_trading = "NO"
    config.margin_alert_pct = 0.7
    config.margin_halt_pct = 0.8
    config.margin_liquidation_pct = 0.9
    config.volatility_high_threshold = 1.5
    config.volatility_very_high_threshold = 2.0
    config.volatility_extreme_threshold = 3.0

    validator = ConfigValidator(config)

    # We need to mock unique_paths in _check_file_permissions or just let it find our file
    # _check_file_permissions uses resolve() and Path(".env") etc.
    # Let's monkeypatch Path.exists to return True for our specific test files

    result = validator.validate()

    # Check if FILE_PERMISSION warning is present
    permission_errors = [e for e in result.errors if e.field == "FILE_PERMISSION"]
    assert len(permission_errors) > 0
    assert "Hardened insecure permissions" in permission_errors[0].message


def test_safe_pytorch_loading():
    """
    Statically analyze the codebase to ensure all torch.load calls
    include the weights_only=True argument for security.
    """
    import ast

    root_dir = Path(__file__).resolve().parents[1]
    violations = []

    for path in root_dir.rglob("*.py"):
        if ".git" in str(path) or "venv" in str(path) or "tests" in str(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check for torch.load(...)
                    is_torch_load = False
                    if isinstance(node.func, ast.Attribute):
                        if (
                            isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "torch"
                            and node.func.attr == "load"
                        ):
                            is_torch_load = True
                    elif isinstance(node.func, ast.Name) and node.func.id == "load":
                        # Could be 'from torch import load'
                        # For simplicity, we check if weights_only is present if it looks like a load call
                        # but we prioritize torch.load
                        pass

                    if is_torch_load:
                        has_weights_only = False
                        for keyword in node.keywords:
                            if keyword.arg == "weights_only":
                                if (
                                    isinstance(keyword.value, ast.Constant)
                                    and keyword.value.value is True
                                ):
                                    has_weights_only = True
                                elif (
                                    isinstance(keyword.value, ast.NameConstant)
                                    and keyword.value.value is True
                                ):
                                    # For older python versions
                                    has_weights_only = True

                        if not has_weights_only:
                            violations.append(f"{path.relative_to(root_dir)}:{node.lineno}")

    assert not violations, (
        f"Unsafe torch.load calls found in: {violations}. Always use weights_only=True."
    )
