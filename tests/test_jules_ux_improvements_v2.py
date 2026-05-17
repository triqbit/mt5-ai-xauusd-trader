"""
Jules02 UX Improvements Tests
tests/test_jules_ux_improvements_v2.py
"""
import os
from unittest.mock import patch

from main import get_parser
from src.core.config import get_config


def test_cli_short_aliases():
    """Verify that short CLI aliases are correctly mapped."""
    test_args = [
        "main.py",
        "-m", "live",
        "-a", "ppo",
        "-s", "XAUUSD",
        "-t", "H1"
    ]

    with patch("sys.argv", test_args), \
         patch.dict(os.environ, {
             "MT5_PASSWORD": "test",
             "MT5_SERVER": "test",
         }):

        parser = get_parser()
        args = parser.parse_args()

        assert args.mode == "live"
        assert args.algorithm == "ppo"
        assert args.symbol == "XAUUSD"
        assert args.timeframe == "H1"

def test_poll_interval_config():
    """Verify that poll_interval is correctly loaded from environment."""
    with patch.dict(os.environ, {
             "POLL_INTERVAL": "45",
             "MT5_PASSWORD": "test",
             "MT5_SERVER": "test",
         }):

        get_config.cache_clear()
        cfg = get_config()
        assert cfg.poll_interval == 45
