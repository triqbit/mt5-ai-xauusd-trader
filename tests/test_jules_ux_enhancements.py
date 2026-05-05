
import os
import sys
from unittest.mock import patch, MagicMock

# Mock talib before importing main
sys.modules['talib'] = MagicMock()

from main import main, parse_args
from src.core.config import get_config

def test_confirm_live_flag():
    """Verify that --confirm-live flag sets CONFIRM_LIVE_TRADING=YES via main()."""
    # We mock components called by main() to test initialization logic only
    with patch("sys.argv", ["main.py", "--confirm-live"]), \
         patch.dict(os.environ, {"MT5_PASSWORD": "test", "MT5_SERVER": "test"}, clear=True), \
         patch("main.configure_logging"), \
         patch("main.Console"), \
         patch("src.core.config_validator.ConfigValidator.validate") as mock_val, \
         patch("src.core.audit_log.AuditLogger"), \
         patch("src.trading.mt5_connector.MT5Connector"):

        mock_val.return_value.errors = []
        mock_val.return_value.success = True

        get_config.cache_clear()

        # Trigger main() initialization logic. We expect it to fail later (when components are used),
        # so we look for the side effect of environment variable setting.
        try:
            main()
        except Exception:
            pass

        assert os.environ.get("CONFIRM_LIVE_TRADING") == "YES"

        # Also check TradingConfig
        cfg = get_config()
        assert cfg.confirm_live_trading == "YES"

def test_cli_override_precedence():
    """Verify CLI > ENV precedence via main()."""
    with patch("sys.argv", ["main.py", "--symbol", "BTCUSD"]), \
         patch.dict(os.environ, {"SYMBOL": "XAUUSD", "MT5_PASSWORD": "test", "MT5_SERVER": "test"}), \
         patch("main.configure_logging"), \
         patch("main.Console"), \
         patch("src.core.config_validator.ConfigValidator.validate") as mock_val, \
         patch("src.core.audit_log.AuditLogger"), \
         patch("src.trading.mt5_connector.MT5Connector"):

        mock_val.return_value.errors = []
        mock_val.return_value.success = True

        get_config.cache_clear()
        try:
            main()
        except Exception:
            pass

        assert os.environ.get("SYMBOL") == "BTCUSD"
        cfg = get_config()
        assert cfg.symbol == "BTCUSD"

def test_default_does_not_override_env():
    """Verify that CLI defaults (like log-level=INFO) do NOT override ENV."""
    with patch("sys.argv", ["main.py"]), \
         patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "MT5_PASSWORD": "test", "MT5_SERVER": "test"}), \
         patch("main.configure_logging"), \
         patch("main.Console"), \
         patch("src.core.config_validator.ConfigValidator.validate") as mock_val, \
         patch("src.core.audit_log.AuditLogger"), \
         patch("src.trading.mt5_connector.MT5Connector"):

        mock_val.return_value.errors = []
        mock_val.return_value.success = True

        get_config.cache_clear()
        try:
            main()
        except Exception:
            pass

        # LOG_LEVEL should remain DEBUG if --log-level was NOT passed on CLI
        cfg = get_config()
        assert cfg.log_level == "DEBUG"

if __name__ == "__main__":
    test_confirm_live_flag()
    test_cli_override_precedence()
    print("UX Enhancement Tests PASSED")
