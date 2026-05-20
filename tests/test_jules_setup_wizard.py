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

        with patch("builtins.open", m):
            result = run_setup_wizard()

            assert result == 0

            # Use writelines as in main.py
            # Collect all lines from all writelines calls
            written_lines = []
            for call in m.return_value.writelines.call_args_list:
                written_lines.extend(call.args[0])

            written_data = "".join(written_lines)

            assert "MT5_LOGIN=123456\n" in written_data
            assert "MT5_PASSWORD=secure_pass\n" in written_data
            assert "MT5_SERVER=IC-Markets-Demo\n" in written_data
            assert "SYMBOL=XAUUSD\n" in written_data
            assert "MODE=demo\n" in written_data
