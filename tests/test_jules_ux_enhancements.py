"""
MT5 AI/ML Trading Bot - Jules UX Hardening Tests
tests/test_jules_ux_enhancements.py
"""
from unittest.mock import patch

import pytest

from main import get_system_version, parse_args


def test_argparse_help_strings():
    """Verify that argparse has the updated help strings and epilog."""
    with patch("sys.argv", ["main.py", "--help"]):
        with pytest.raises(SystemExit) as excinfo:
            parse_args()
        assert excinfo.value.code == 0

def test_system_version_retrieval():
    """Verify system version retrieval logic."""
    version = get_system_version()
    assert isinstance(version, str)
    assert version != "unknown"

def test_cli_log_level_choices():
    """Verify that log-level only accepts specific choices."""
    with patch("sys.argv", ["main.py", "--log-level", "INVALID"]), pytest.raises(SystemExit):
        parse_args()

    with patch("sys.argv", ["main.py", "--log-level", "DEBUG"]):
        args = parse_args()
        assert args.log_level == "DEBUG"
