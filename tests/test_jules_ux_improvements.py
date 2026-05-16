import argparse
import contextlib
from unittest.mock import MagicMock, patch

from main import get_parser, run_setup_wizard
from src.core.config import TradingConfig


def test_cli_aliases():
    parser = get_parser()

    # Test short aliases
    args = parser.parse_args(["-m", "live", "-a", "ensemble", "-s", "XAUUSD", "-t", "M5"])
    assert args.mode == "live"
    assert args.algorithm == "ensemble"
    assert args.symbol == "XAUUSD"
    assert args.timeframe == "M5"


def test_poll_interval_config():
    config = TradingConfig(
        MT5_PASSWORD="test_password", MT5_SERVER="test_server", poll_interval=120
    )
    assert config.poll_interval == 120

    # Default value
    default_config = TradingConfig(MT5_PASSWORD="test_password", MT5_SERVER="test_server")
    assert default_config.poll_interval == 60


@patch("rich.prompt.Prompt.ask")
@patch("rich.prompt.IntPrompt.ask")
@patch("getpass.getpass")
@patch("pathlib.Path.exists")
@patch("main.open")
def test_setup_wizard_health_check_prompt(
    mock_open, mock_exists, mock_getpass, mock_int_prompt, mock_prompt
):
    # Mock inputs for the wizard
    # 1. Mode, 2. Symbol, 3. Timeframe, 4. MT5 Server, 5. MetaAPI, 6. Save, 7. Health Check
    mock_prompt.side_effect = ["demo", "XAUUSD", "M5", "test_server", "n", "y", "y"]
    mock_int_prompt.return_value = 12345
    mock_getpass.return_value = "test_password"
    mock_exists.return_value = True

    # Run wizard
    with patch("rich.console.Console.print"):
        result = run_setup_wizard()

    # Check that it returns 2 when health check is accepted
    assert result == 2


@patch("main.run_setup_wizard")
@patch("main.get_parser")
def test_main_handles_setup_health_check(mock_get_parser, mock_run_wizard):
    from main import main

    # Mock CLI args to trigger --setup
    mock_parser = MagicMock()
    mock_get_parser.return_value = mock_parser
    args = argparse.Namespace(
        setup=True, check=False, doctor=False, show_config=False, log_level="INFO"
    )
    mock_parser.parse_args.return_value = args

    # Mock wizard to return 2 (request health check)
    mock_run_wizard.return_value = 2

    # We need to mock more of main to avoid full execution
    with (
        patch("src.core.config.get_config"),
        patch("src.core.config_validator.ConfigValidator.validate") as mock_validate,
        patch("main.configure_logging"),
        patch("main.sys.argv", ["main.py", "--setup"]),
        patch("main.HAS_DEPENDENCIES", True),
    ):
        # Mock validation to fail so it exits early after the check
        mock_validate.return_value.success = False
        mock_validate.return_value.errors = [
            MagicMock(field="MT5_SERVER", message="error", critical=True, remedy="remedy")
        ]

        with contextlib.suppress(SystemExit):
            main()

        # Verify args.check was set to True
        assert args.check is True
