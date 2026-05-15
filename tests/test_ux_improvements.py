"""
MT5 AI/ML Trading Bot - UX Improvement Tests
tests/test_ux_improvements.py
"""
import os
import sys
from unittest.mock import MagicMock, patch, mock_open

import pytest
from main import get_parser, main, run_setup_wizard
from src.core.config import get_config

def test_cli_aliases():
    """Verify that short CLI aliases work as expected."""
    test_args = [
        "main.py",
        "-m", "backtest",
        "-a", "ppo",
        "-s", "EURUSD",
        "-t", "H1"
    ]

    with patch("sys.argv", test_args), \
         patch.dict(os.environ, {
             "MT5_PASSWORD": "test",
             "MT5_SERVER": "test",
             "DATABASE_URL": "sqlite:///test.db"
         }), \
         patch("main.configure_logging"):

        get_config.cache_clear()

        parser = get_parser()
        args = parser.parse_args()

        assert args.mode == "backtest"
        assert args.algorithm == "ppo"
        assert args.symbol == "EURUSD"
        assert args.timeframe == "H1"

def test_poll_interval_config():
    """Verify that poll_interval is correctly loaded from environment."""
    with patch.dict(os.environ, {
             "MT5_PASSWORD": "test",
             "MT5_SERVER": "test",
             "DATABASE_URL": "sqlite:///test.db",
             "POLL_INTERVAL": "45"
         }):

        get_config.cache_clear()
        cfg = get_config()
        assert cfg.poll_interval == 45

def test_setup_wizard_onboarding_jump(capsys):
    """Verify that setup wizard can trigger health check."""
    with patch("rich.prompt.Prompt.ask") as mock_ask, \
         patch("rich.prompt.IntPrompt.ask") as mock_int_ask, \
         patch("getpass.getpass", return_value="secure_pass"), \
         patch("main.Path.exists", return_value=True), \
         patch("main.os.chmod"):

        # 1. Mode, Symbol, Timeframe
        # 2. Server
        # 3. Use MetaAPI
        # 4. Ready to save
        # 5. Run Health Check? (NEW)
        mock_ask.side_effect = ["demo", "XAUUSD", "M5", "IC-Markets-Demo", "n", "y", "y"]
        mock_int_ask.return_value = 123456

        example_content = "MT5_LOGIN=0\nMT5_PASSWORD=\nMT5_SERVER=\nSYMBOL=\nTIMEFRAME=\nMODE=\n"
        m = mock_open(read_data=example_content)

        with patch("builtins.open", m):
            result = run_setup_wizard()
            assert result == 2 # Special code for "run health check"

def test_main_onboarding_flow():
    """Verify that main() handles the jump from setup to health check."""
    with patch("main.run_setup_wizard", return_value=2), \
         patch("main.get_parser") as mock_get_parser, \
         patch("sys.argv", ["main.py", "--setup"]), \
         patch("main.configure_logging"), \
         patch("src.core.health.HealthChecker.startup_gate"), \
         patch("src.core.config_validator.ConfigValidator.validate") as mock_val:

        mock_val.return_value = MagicMock(success=True, errors=[])
        mock_parser = MagicMock()
        mock_get_parser.return_value = mock_parser

        # We need to mock health check result to avoid it failing and aborting
        from src.core.health import HealthReport, HealthStatus
        with patch("src.core.health.HealthChecker.get_full_report", return_value=HealthReport(status=HealthStatus.HEALTHY, components={})):
            # Create a real-ish config mock to avoid comparisons with MagicMock failing
            mock_cfg = MagicMock()
            mock_cfg.mode = "demo"
            mock_cfg.symbol = "XAUUSD"
            mock_cfg.timeframe = "M5"
            mock_cfg.algorithm = "ensemble"
            mock_cfg.risk_per_trade = 0.01
            mock_cfg.max_daily_loss = 0.05
            mock_cfg.max_positions = 5
            mock_cfg.min_confidence = 0.55
            mock_cfg.mt5_login = 123456
            mock_cfg.mt5_server = "test"
            mock_cfg.database_url.get_secret_value.return_value = "sqlite:///test.db"
            mock_cfg.log_level = "INFO"
            mock_cfg.model_fields = {}

            with patch("src.core.config.get_config", return_value=mock_cfg):
                # Mock parse_args to return an object with check=True when called with ["--check"]
                # and setup=True when called with no args (first pass)
                def side_effect(args=None):
                    m = MagicMock()
                    m.setup = True if args is None else False
                    m.doctor = False
                    m.check = True if args == ["--check"] else False
                    m.show_config = False
                    m.version = False
                    return m

                mock_parser.parse_args.side_effect = side_effect

                try:
                    main()
                except (SystemExit, TypeError, Exception):
                    pass

                # Check if parser.parse_args was called with ["--check"]
                mock_parser.parse_args.assert_any_call(["--check"])
