import sys
from unittest.mock import MagicMock

# 1. PRE-EMPTIVE MOCKING of MetaTrader5 before any other imports
mock_mt5_obj = MagicMock()
mock_mt5_obj.initialize.return_value = True
mock_mt5_obj.last_error.return_value = (0, "Success")
mock_tick = MagicMock()
mock_tick.bid = 2000.0
mock_tick.ask = 2000.5
mock_mt5_obj.symbol_info_tick.return_value = mock_tick
mock_result = MagicMock()
mock_result.retcode = 10009
mock_result.order = 123456
mock_result.comment = "Success"
mock_mt5_obj.order_send.return_value = mock_result
mock_acc = MagicMock()
mock_acc.balance = 10000.0
mock_acc._asdict.return_value = {"balance": 10000.0}
mock_mt5_obj.account_info.return_value = mock_acc
mock_mt5_obj.TRADE_RETCODE_DONE = 10009

sys.modules["MetaTrader5"] = mock_mt5_obj

import pytest

@pytest.fixture(autouse=True)
def mock_mt5():
    """Access the pre-initialized mock."""
    return mock_mt5_obj

@pytest.fixture(autouse=True)
def mock_metaapi():
    """Mock metaapi_cloud_sdk module."""
    mock = MagicMock()
    sys.modules["metaapi_cloud_sdk"] = mock
    yield mock
    if "metaapi_cloud_sdk" in sys.modules:
        del sys.modules["metaapi_cloud_sdk"]

@pytest.fixture
def mock_config():
    from src.core.config import TradingConfig
    # Use a dummy database for tests
    return TradingConfig(
        mt5_login=12345,
        mt5_password="fake_password",
        mt5_server="fake_server",
        database_url="sqlite:///test_integration.db"
    )
