"""
MT5 AI/ML Trading Bot - Setup Wizard Tests
tests/test_jules_setup_wizard.py
"""
from unittest.mock import mock_open, patch

from main import run_setup_wizard


def test_setup_wizard_save_logic():
    """Verify that the setup wizard correctly saves configuration to .env."""

    # Mock rich prompts and getpass
    with patch("rich.prompt.Prompt.ask") as mock_ask, \
         patch("rich.prompt.IntPrompt.ask") as mock_int_ask, \
         patch("getpass.getpass", return_value="secure_pass"), \
         patch("main.Path.exists", return_value=True), \
         patch("main.os.chmod"):

        # Setup mock responses
        # 1. Mode, Symbol, Timeframe
        # 2. Server
        # 3. Use MetaAPI
        # 4. Ready to save
        mock_ask.side_effect = ["demo", "XAUUSD", "M5", "IC-Markets-Demo", "n", "y"]
        mock_int_ask.return_value = 123456

        # Mock open for .env.example (minimal content)
        example_content = "MT5_LOGIN=0\nMT5_PASSWORD=\nMT5_SERVER=\nSYMBOL=\nTIMEFRAME=\nMODE=\n"
        m = mock_open(read_data=example_content)

        with patch("main.set_key") as mock_set_key:
            result = run_setup_wizard()

            assert result == 0

            # Verify set_key calls
            mock_set_key.assert_any_call(".env", "MT5_LOGIN", "123456")
            mock_set_key.assert_any_call(".env", "MT5_PASSWORD", "secure_pass")
            mock_set_key.assert_any_call(".env", "MT5_SERVER", "IC-Markets-Demo")
            mock_set_key.assert_any_call(".env", "SYMBOL", "XAUUSD")
            mock_set_key.assert_any_call(".env", "MODE", "demo")
