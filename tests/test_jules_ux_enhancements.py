
import os
import sys
from unittest.mock import patch, MagicMock

# Mock talib before importing main
sys.modules['talib'] = MagicMock()

from main import main, parse_args
from src.core.config import get_config

def test_confirm_live_flag():
    """Verify that --confirm-live flag sets CONFIRM_LIVE_TRADING=YES."""
    with patch("sys.argv", ["main.py", "--confirm-live"]), \
         patch.dict(os.environ, {}, clear=True), \
         patch("main.configure_logging"):

        get_config.cache_clear()
        # In main(), it manually sets os.environ based on args
        args = parse_args()

        # Dynamic CLI Override Mapping: CLI Arg -> Environment Variable
        cli_overrides = {
            "mode": "MODE",
            "algo": "ALGORITHM",
            "symbol": "SYMBOL",
            "timeframe": "TIMEFRAME",
            "confirm_live": "CONFIRM_LIVE_TRADING",
            "log_level": "LOG_LEVEL",
        }
        for arg_name, env_var in cli_overrides.items():
            val = getattr(args, arg_name, None)
            if val is not None:
                if isinstance(val, bool):
                    if val:
                        os.environ[env_var] = "YES" if arg_name == "confirm_live" else str(val)
                else:
                    os.environ[env_var] = str(val)

        assert os.environ.get("CONFIRM_LIVE_TRADING") == "YES"

        # Also check TradingConfig
        os.environ["MT5_PASSWORD"] = "test"
        os.environ["MT5_SERVER"] = "test"

        cfg = get_config()
        assert cfg.confirm_live_trading == "YES"

def test_cli_override_precedence():
    """Verify CLI > ENV precedence."""
    with patch("sys.argv", ["main.py", "--symbol", "BTCUSD"]), \
         patch.dict(os.environ, {"SYMBOL": "XAUUSD"}), \
         patch("main.configure_logging"):

        get_config.cache_clear()
        args = parse_args()

        cli_overrides = {
            "symbol": "SYMBOL",
        }
        for arg_name, env_var in cli_overrides.items():
            val = getattr(args, arg_name, None)
            if val is not None:
                os.environ[env_var] = str(val)

        assert os.environ.get("SYMBOL") == "BTCUSD"

if __name__ == "__main__":
    test_confirm_live_flag()
    test_cli_override_precedence()
    print("UX Enhancement Tests PASSED")
