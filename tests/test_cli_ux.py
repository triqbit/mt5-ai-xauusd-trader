import pytest
from unittest.mock import MagicMock, patch
import sys

# Mock torch and other heavy dependencies before importing main
torch_mock = MagicMock()
torch_mock.__path__ = []
mock_modules = {
    "torch": torch_mock,
    "torch.nn": MagicMock(),
    "stable_baselines3": MagicMock(),
    "stable_baselines3.common": MagicMock(),
    "MetaTrader5": MagicMock(),
    "metaapi_cloud_sdk": MagicMock()
}

with patch.dict(sys.modules, mock_modules):
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
