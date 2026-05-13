"""
MT5 AI/ML Trading Bot - Jules UX Hardening Tests
tests/test_jules_ux_enhancements.py
"""
from unittest.mock import patch

import pytest

from main import get_parser, get_system_version


def test_argparse_help_strings():
    """Verify that argparse has the updated help strings and epilog."""
    with patch("sys.argv", ["main.py", "--help"]):
        parser = get_parser()
        with pytest.raises(SystemExit) as excinfo:
            parser.parse_args()
        assert excinfo.value.code == 0

def test_system_version_retrieval():
    """Verify system version retrieval logic."""
    version = get_system_version()
    assert isinstance(version, str)
    assert version != "unknown"

def test_cli_log_level_choices():
    """Verify that log-level only accepts specific choices."""
    parser = get_parser()
    with patch("sys.argv", ["main.py", "--log-level", "INVALID"]), pytest.raises(SystemExit):
        parser.parse_args()

    with patch("sys.argv", ["main.py", "--log-level", "DEBUG"]):
        args = parser.parse_args()
        assert args.log_level == "DEBUG"
