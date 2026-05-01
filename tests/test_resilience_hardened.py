"""
MT5 AI/ML Trading Bot - Resilience Test Suite
tests/test_resilience_hardened.py
"""
import pytest
import time
import sys
from unittest.mock import MagicMock, patch, Mock

# Mock torch and stable_baselines3 before any other imports
torch_mock = MagicMock()
sys.modules['torch'] = torch_mock
sys.modules['torch.nn'] = MagicMock()
sys.modules['torch.optim'] = MagicMock()
sys.modules['stable_baselines3'] = MagicMock()

from src.core.exceptions import MT5ConnectionError, MT5DataError
from src.core.retry import with_retry
from src.trading.mt5_connector import MT5Connector

# --- Retry Decorator Tests ---

def test_retry_decorator_success():
    mock_func = MagicMock(return_value="success")

    @with_retry(max_retries=3, initial_delay=0.01)
    def decorated():
        return mock_func()

    result = decorated()
    assert result == "success"
    assert mock_func.call_count == 1

def test_retry_decorator_eventual_success():
    mock_func = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])

    @with_retry(exceptions=ValueError, max_retries=3, initial_delay=0.01)
    def decorated():
        return mock_func()

    result = decorated()
    assert result == "success"
    assert mock_func.call_count == 3

def test_retry_decorator_max_retries_exceeded():
    mock_func = MagicMock(side_effect=ValueError("fail"))

    @with_retry(exceptions=ValueError, max_retries=2, initial_delay=0.01)
    def decorated():
        return mock_func()

    with pytest.raises(ValueError):
        decorated()
    assert mock_func.call_count == 3 # Initial + 2 retries

# --- MT5Connector Resilience Tests ---

@pytest.fixture
def mock_cfg():
    cfg = MagicMock()
    cfg.mt5_path = ""
    cfg.mt5_login = 12345
    cfg.mt5_password = "password"
    cfg.mt5_server = "server"
    cfg.metaapi_token = ""
    cfg.mode = "demo"
    return cfg

def test_connector_initialize_retry(mock_cfg):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5, \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True):

        # Fail 2 times, then succeed
        mock_mt5.initialize.side_effect = [False, False, True]
        mock_mt5.last_error.return_value = "Timeout"

        connector = MT5Connector(mock_cfg)
        # We need to mock time.sleep to speed up tests
        with patch("time.sleep"):
            result = connector.initialize()

        assert result is True
        assert mock_mt5.initialize.call_count == 3

def test_connector_get_rates_data_error(mock_cfg):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5, \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True):

        mock_mt5.initialize.return_value = True
        connector = MT5Connector(mock_cfg)
        connector.initialize()

        mock_mt5.copy_rates_from_pos.return_value = None
        mock_mt5.last_error.return_value = "No data"

        with pytest.raises(MT5DataError) as excinfo:
            connector.get_rates("XAUUSD", "M5", 200)

        assert "No data" in str(excinfo.value)

# --- Main Loop Recovery Tests ---

def test_run_live_connection_recovery(mock_cfg):
    from main import run_live

    mock_connector = MagicMock(spec=MT5Connector)
    mock_risk = MagicMock()
    mock_model = MagicMock()
    mock_monitor = MagicMock()

    # Simulate connection error on first call, then success on second call after re-init
    mock_connector.get_ohlcv.side_effect = [MT5ConnectionError("Lost connection"), MagicMock()]
    # Mock initialize to do nothing
    mock_connector.initialize.return_value = True

    # Stop the loop after 2 iterations or 1 success
    # We'll use a side effect on predict to break the loop
    mock_model.predict.side_effect = KeyboardInterrupt()

    with patch("time.sleep"): # Fast tests
        run_live(mock_cfg, mock_connector, mock_risk, mock_model, monitor=mock_monitor)

    assert mock_connector.initialize.call_count == 1
    assert mock_connector.get_ohlcv.call_count == 2
