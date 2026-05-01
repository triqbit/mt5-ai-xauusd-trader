import pytest
from unittest.mock import MagicMock, patch
import sys
from main import parse_args

def test_cli_flags():
    """Verify that new CLI flags are correctly parsed."""
    with patch.object(sys, 'argv', ['main.py', '--check', '--verbose']):
        args = parse_args()
        assert args.check is True
        assert args.verbose is True

def test_cli_defaults():
    """Verify default CLI behavior."""
    with patch.object(sys, 'argv', ['main.py']):
        args = parse_args()
        assert args.check is False
        assert args.verbose is False
