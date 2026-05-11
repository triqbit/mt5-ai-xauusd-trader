import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from src.core.config import TradingConfig
from src.core.config_validator import ConfigValidator


@pytest.mark.skipif(sys.platform == "win32", reason="Permission check only on Linux/Mac")
def test_live_mode_enforces_restrictive_permissions(tmp_path, monkeypatch):
    """Verify that insecure permissions on .env block startup in live mode but only warn in demo."""

    # 1. Create a dummy .env file with insecure permissions
    env_file = tmp_path / ".env.insecure"
    env_file.write_text("MT5_PASSWORD=secret")
    os.chmod(env_file, 0o644)  # World-readable

    # 2. Setup mock config for LIVE mode
    live_cfg = MagicMock(spec=TradingConfig)
    live_cfg.mode = "live"
    live_cfg.mt5_server = "LiveServer"
    live_cfg.mt5_password = SecretStr("secret")
    live_cfg.mt5_login = 12345
    live_cfg.symbol = "XAUUSD"
    live_cfg.timeframe = "M5"
    live_cfg.model_path = Path("nonexistent.pt")
    # Simulate the model_config property accessed by validator
    monkeypatch.setattr(live_cfg, "model_config", {"env_file": env_file})
    live_cfg.confirm_live_trading = "YES"
    live_cfg.database_url = SecretStr("sqlite:///test.db")
    live_cfg.redis_url = SecretStr("redis://localhost")
    live_cfg.telegram_token = SecretStr("")
    live_cfg.telegram_chat_id = ""
    live_cfg.metaapi_token = SecretStr("")
    live_cfg.metaapi_account_id = SecretStr("")
    live_cfg.risk_per_trade = 0.01
    live_cfg.max_daily_loss = 0.05
    live_cfg.daily_loss_lvl1 = 0.01
    live_cfg.daily_loss_lvl2 = 0.02
    live_cfg.daily_loss_lvl3 = 0.03
    live_cfg.daily_loss_hard_stop = 0.06
    live_cfg.max_weekly_loss = 0.10
    live_cfg.max_monthly_loss = 0.15
    live_cfg.min_spread_pips = 0.1
    live_cfg.spread_alert_pips = 0.5
    live_cfg.spread_reduce_pips = 1.0
    live_cfg.spread_halt_pips = 1.5
    live_cfg.min_confidence = 0.60
    live_cfg.max_positions = 5
    live_cfg.max_leverage = 10.0
    live_cfg.max_position_size_pct = 0.10
    live_cfg.max_drawdown = 0.30
    live_cfg.model_drift_threshold = 0.3
    live_cfg.model_accuracy_floor = 0.5
    live_cfg.model_win_rate_floor = 0.45
    live_cfg.model_calibration_threshold = 0.25
    live_cfg.max_single_direction_pct = 0.30
    live_cfg.max_total_notional_pct = 1.00
    live_cfg.max_trades_per_day = 20
    live_cfg.min_lot_size = 0.01
    live_cfg.margin_alert_pct = 0.70
    live_cfg.margin_halt_pct = 0.80
    live_cfg.margin_liquidation_pct = 0.90
    live_cfg.volatility_high_threshold = 1.5
    live_cfg.volatility_very_high_threshold = 2.0
    live_cfg.volatility_extreme_threshold = 3.0
    live_cfg.log_level = "INFO"

    # 3. Validate for LIVE mode (should be CRITICAL)
    validator = ConfigValidator(live_cfg)
    result = validator.validate()

    permission_errors = [e for e in result.errors if e.field == "FILE_PERMISSION"]
    assert len(permission_errors) > 0
    assert any(e.critical for e in permission_errors), "Permissions should be critical in LIVE mode"
    assert not result.success

    # 4. Setup mock config for DEMO mode
    demo_cfg = MagicMock(spec=TradingConfig)
    demo_cfg.mode = "demo"
    demo_cfg.mt5_server = "DemoServer"
    demo_cfg.mt5_password = SecretStr("secret")
    demo_cfg.mt5_login = 12345
    demo_cfg.symbol = "XAUUSD"
    demo_cfg.timeframe = "M5"
    demo_cfg.model_path = Path("nonexistent.pt")
    monkeypatch.setattr(demo_cfg, "model_config", {"env_file": env_file})
    demo_cfg.confirm_live_trading = ""
    demo_cfg.database_url = SecretStr("sqlite:///test.db")
    demo_cfg.redis_url = SecretStr("redis://localhost")
    demo_cfg.telegram_token = SecretStr("")
    demo_cfg.telegram_chat_id = ""
    demo_cfg.metaapi_token = SecretStr("")
    demo_cfg.metaapi_account_id = SecretStr("")
    demo_cfg.risk_per_trade = 0.01
    demo_cfg.max_daily_loss = 0.05
    demo_cfg.daily_loss_lvl1 = 0.01
    demo_cfg.daily_loss_lvl2 = 0.02
    demo_cfg.daily_loss_lvl3 = 0.03
    demo_cfg.daily_loss_hard_stop = 0.06
    demo_cfg.max_weekly_loss = 0.10
    demo_cfg.max_monthly_loss = 0.15
    demo_cfg.min_spread_pips = 0.1
    demo_cfg.spread_alert_pips = 0.5
    demo_cfg.spread_reduce_pips = 1.0
    demo_cfg.spread_halt_pips = 1.5
    demo_cfg.min_confidence = 0.60
    demo_cfg.max_positions = 5
    demo_cfg.max_leverage = 10.0
    demo_cfg.max_position_size_pct = 0.10
    demo_cfg.max_drawdown = 0.30
    demo_cfg.model_drift_threshold = 0.3
    demo_cfg.model_accuracy_floor = 0.5
    demo_cfg.model_win_rate_floor = 0.45
    demo_cfg.model_calibration_threshold = 0.25
    demo_cfg.max_single_direction_pct = 0.30
    demo_cfg.max_total_notional_pct = 1.00
    demo_cfg.max_trades_per_day = 20
    demo_cfg.min_lot_size = 0.01
    demo_cfg.margin_alert_pct = 0.70
    demo_cfg.margin_halt_pct = 0.80
    demo_cfg.margin_liquidation_pct = 0.90
    demo_cfg.volatility_high_threshold = 1.5
    demo_cfg.volatility_very_high_threshold = 2.0
    demo_cfg.volatility_extreme_threshold = 3.0
    demo_cfg.log_level = "INFO"

    # 5. Validate for DEMO mode (should NOT be critical)
    validator = ConfigValidator(demo_cfg)
    result = validator.validate()

    permission_errors = [e for e in result.errors if e.field == "FILE_PERMISSION"]
    assert len(permission_errors) > 0
    assert not any(e.critical for e in permission_errors), "Permissions should NOT be critical in DEMO mode"

def test_get_sanitized_dump_redacts_secrets():
    """Verify that get_sanitized_dump correctly identifies and redacts all Secret types."""
    cfg = TradingConfig.model_construct(
        mt5_password=SecretStr("my_secret_password"),
        mt5_server="TestServer",
        database_url=SecretStr("postgresql://user:pass@localhost/db"),
        telegram_token=SecretStr("123456:ABC-DEF"),
        metaapi_token=SecretStr("meta_token_123"),
        metaapi_account_id=SecretStr("meta_id_456"),
        symbol="XAUUSD",
        mode="demo"
    )

    dump = cfg.get_sanitized_dump()

    # Check that secret fields are excluded
    assert "mt5_password" not in dump
    assert "database_url" not in dump
    assert "telegram_token" not in dump
    assert "metaapi_token" not in dump
    assert "metaapi_account_id" not in dump

    # Check that non-secret fields are present
    assert dump["symbol"] == "XAUUSD"
    assert dump["mode"] == "demo"

def test_secret_masking_processor_discovery():
    """Verify that SecretMaskingProcessor correctly discovers secrets from TradingConfig."""
    from src.core.log_config import SecretMaskingProcessor

    cfg = TradingConfig.model_construct(
        mt5_password=SecretStr("ULTRA_SECRET_MT5_PASS"),
        mt5_server="TestServer",
        database_url=SecretStr("postgresql://trader:DB_PASS_WORD@localhost/mt5")
    )

    processor = SecretMaskingProcessor(config=cfg)

    # Check if the specific secret values are in the mask list
    assert "ULTRA_SECRET_MT5_PASS" in processor.secrets
    assert "DB_PASS_WORD" in processor.secrets

    # Test redaction
    log_msg = "Attempting login with ULTRA_SECRET_MT5_PASS to DB_PASS_WORD"
    redacted = processor.redact_any(log_msg)
    assert "ULTRA_SECRET_MT5_PASS" not in redacted
    assert "DB_PASS_WORD" not in redacted
    assert redacted.count("[MASKED]") == 2
